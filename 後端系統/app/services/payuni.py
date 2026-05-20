"""
PayUni 統一金流串接 (https://www.payuni.com.tw)

加密規則（取自統一金流 API 文件 v1.6）：
  1. 把參數 dict urlencode 成 query string (e.g. MerTradeNo=xxx&TradeAmt=100)
  2. AES-256-CBC 加密該 query string；key=HashKey, iv=HashIV，PKCS7 padding
  3. 轉小寫 hex 得到 EncryptInfo
  4. HashInfo = SHA256( "HashKey=xxx&" + EncryptInfo + "&HashIV=yyy" ).upper()
  5. POST { MerID, Version, EncryptInfo, HashInfo } 到 PayUni endpoint

支援：
  build_create_form() ── 產生「導去 PayUni」的 HTML form data
  decrypt_callback()  ── 回呼 / 通知頁解密 + 驗章
"""
from __future__ import annotations
import json
import hashlib
from urllib.parse import urlencode, parse_qs
from typing import Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from app.core.config import settings


# ──────────────────────────────────────────────────────────────────────
# 端點（依文件）
# ──────────────────────────────────────────────────────────────────────
def _api_base() -> str:
    # 正式  https://api.payuni.com.tw/api
    # 測試  https://sandbox-api.payuni.com.tw/api
    return "https://sandbox-api.payuni.com.tw/api" if settings.PAYUNI_TEST_MODE \
        else "https://api.payuni.com.tw/api"


def upp_url() -> str:
    """整合式信用卡/ATM/超商收款導頁 URL"""
    return f"{_api_base()}/upp"


# ──────────────────────────────────────────────────────────────────────
# AES-256-CBC 加密 / 解密
# ──────────────────────────────────────────────────────────────────────
def _key_iv() -> tuple[bytes, bytes]:
    k = (settings.PAYUNI_HASH_KEY or "").encode()
    v = (settings.PAYUNI_HASH_IV  or "").encode()
    if len(k) != 32 or len(v) != 16:
        raise ValueError(
            f"PayUni HashKey 必須 32 bytes (現:{len(k)}); HashIV 必須 16 bytes (現:{len(v)})"
        )
    return k, v


def is_configured() -> bool:
    return bool(settings.PAYUNI_MER_ID) and \
           len(settings.PAYUNI_HASH_KEY or "") == 32 and \
           len(settings.PAYUNI_HASH_IV  or "") == 16


def aes_encrypt(plain: str) -> str:
    """回傳 lowercase hex"""
    k, v = _key_iv()
    padder = PKCS7(128).padder()
    padded = padder.update(plain.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(k), modes.CBC(v))
    enc = cipher.encryptor()
    ct  = enc.update(padded) + enc.finalize()
    return ct.hex()


def aes_decrypt(hex_str: str) -> str:
    k, v = _key_iv()
    cipher = Cipher(algorithms.AES(k), modes.CBC(v))
    dec = cipher.decryptor()
    padded = dec.update(bytes.fromhex(hex_str)) + dec.finalize()
    unpadder = PKCS7(128).unpadder()
    plain = unpadder.update(padded) + unpadder.finalize()
    return plain.decode("utf-8")


def hash_sign(encrypt_hex: str) -> str:
    """HashInfo = SHA256(HashKey={key}&{enc}&HashIV={iv}).upper()"""
    raw = (
        f"HashKey={settings.PAYUNI_HASH_KEY}&"
        f"{encrypt_hex}&"
        f"HashIV={settings.PAYUNI_HASH_IV}"
    )
    return hashlib.sha256(raw.encode()).hexdigest().upper()


# ──────────────────────────────────────────────────────────────────────
# 對外：建立付款導頁的表單欄位
# ──────────────────────────────────────────────────────────────────────
def build_create_form(
    order_id:     str,
    amount:       int,
    product_desc: str,
    buyer_email:  str = "",
    return_url:   str = "",
    notify_url:   str = "",
    customer_url: str = "",
    payment_methods: str = "ALL",   # CREDIT / WEBATM / ATM / CVS / BARCODE / ALL
) -> dict:
    """
    回傳一個 dict，可丟給前端組成 form POST 到 upp_url()
      { "url": "...", "fields": { "MerID":..., "Version":..., "EncryptInfo":..., "HashInfo":... } }
    """
    if not is_configured():
        raise RuntimeError("PayUni 尚未設定（PAYUNI_MER_ID/HashKey/HashIV）")

    params = {
        "MerID":        settings.PAYUNI_MER_ID,
        "MerTradeNo":   order_id,
        "TradeAmt":     int(amount),
        "ProdDesc":     product_desc[:30],
        "Timestamp":    int(__import__("time").time()),
        "UsrMail":      buyer_email or "",
        "ReturnURL":    return_url,
        "NotifyURL":    notify_url,
        "BackURL":      customer_url,
        # 付款方式
        "CardNoPay":    "0",   # 0=不限定卡別
        "API1ATM":      "0",
        # 顯示語系：1=中文
        "WebLang":      "1",
        # 收款方式 (PayUni 用 ChoosePayment / 或交易類別欄位 — 依文件版本)
        "ChoosePayment": payment_methods,
    }
    # 把空值欄位移掉
    params = {k: v for k, v in params.items() if v not in (None, "")}

    query = urlencode(params, encoding="utf-8")
    enc   = aes_encrypt(query)
    hi    = hash_sign(enc)

    return {
        "url":    upp_url(),
        "fields": {
            "MerID":       settings.PAYUNI_MER_ID,
            "Version":     "1.0",
            "EncryptInfo": enc,
            "HashInfo":    hi,
        },
        "debug": {
            "order_id":   order_id,
            "amount":     amount,
            "test_mode":  settings.PAYUNI_TEST_MODE,
        },
    }


# ──────────────────────────────────────────────────────────────────────
# 對外：回呼解密 + 驗章
# ──────────────────────────────────────────────────────────────────────
def decrypt_callback(encrypt_info: str, hash_info: str) -> dict:
    """
    PayUni Notify / Return 會 POST 過來：
      MerID, Status, Message, EncryptInfo, HashInfo
    本函式驗章後解開 EncryptInfo 為 dict，並標記 ok 欄位

    回傳：
      { ok: True/False, error: "...", data: {...解密後欄位...} }
    """
    if not is_configured():
        return {"ok": False, "error": "PayUni 未設定", "data": {}}

    expected = hash_sign(encrypt_info)
    if expected != (hash_info or "").upper():
        return {"ok": False, "error": "HashInfo 驗章失敗", "data": {}}

    try:
        plain = aes_decrypt(encrypt_info)
    except Exception as e:
        return {"ok": False, "error": f"AES 解密失敗: {e}", "data": {}}

    # 回傳格式可能是 JSON 或 querystring，兩個都試
    data = {}
    plain_s = plain.strip()
    if plain_s.startswith("{"):
        try:
            data = json.loads(plain_s)
        except Exception:
            pass
    if not data:
        try:
            parsed = parse_qs(plain_s, keep_blank_values=True)
            data = {k: (v[0] if v else "") for k, v in parsed.items()}
        except Exception:
            data = {"raw": plain_s}

    # PayUni 成功狀態：Status="SUCCESS"
    success = (data.get("Status") == "SUCCESS") or (data.get("status") == "SUCCESS")
    return {"ok": True, "success": success, "data": data}


# 對外：health
def diag() -> dict:
    return {
        "configured":   is_configured(),
        "test_mode":    settings.PAYUNI_TEST_MODE,
        "merchant_id":  (settings.PAYUNI_MER_ID or "")[:4] + "..." if settings.PAYUNI_MER_ID else "",
        "endpoint":     upp_url(),
        "key_len":      len(settings.PAYUNI_HASH_KEY or ""),
        "iv_len":       len(settings.PAYUNI_HASH_IV  or ""),
    }
