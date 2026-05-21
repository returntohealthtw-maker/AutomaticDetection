"""
PayUni 統一金流串接 (https://www.payuni.com.tw)

⚠️ 加密規則（取自 PayUni 官方 WooCommerce 外掛 class-payuni.php，亦即實際 API 規範）：
  1. 把參數 dict urlencode 成 query string (e.g. MerTradeNo=xxx&TradeAmt=100)
  2. AES-256-GCM 加密該 query string，key=HashKey(32 bytes)，iv=HashIV(16 bytes)
     openssl_encrypt 預設輸出 base64，並另外輸出 16 bytes GCM tag
  3. EncryptInfo = bin2hex( base64(ciphertext) + ":::" + base64(tag) )
  4. HashInfo = SHA256( HashKey + EncryptInfo + HashIV ).upper()
     ⚠️ 直接字串連接，沒有 "HashKey="、"HashIV=" 等 query 字串！
  5. POST { MerID, Version, EncryptInfo, HashInfo } 到 PayUni endpoint

⚠️ 過去版本曾使用 AES-256-CBC + PKCS7，已不正確；目前已改回 PayUni 官方規格。

支援：
  build_create_form() ── 產生「導去 PayUni」的 HTML form data
  decrypt_callback()  ── 回呼 / 通知頁解密 + 驗章
"""
from __future__ import annotations
import json
import base64
import hashlib
from urllib.parse import urlencode, parse_qs
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

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
# AES-256-GCM 加密 / 解密（與 PayUni PHP 實作對齊）
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
    """
    PayUni AES-256-GCM 加密；對齊 PayUni 官方 PHP：
        $encrypted = openssl_encrypt($plain, 'aes-256-gcm', $HashKey, 0, $HashIV, $tag);
        return bin2hex($encrypted . ':::' . base64_encode($tag));

    cryptography 的 AESGCM.encrypt(nonce, data, aad) 回傳 ciphertext+tag（最後 16 bytes 為 tag）；
    PHP 的 openssl_encrypt 第 4 個參數 0 代表輸出 base64，所以 PayUni 的 ciphertext
    其實是 base64(raw_ciphertext) — 注意這層 base64 千萬別忘。
    """
    key, iv = _key_iv()
    ct_plus_tag = AESGCM(key).encrypt(iv, plain.encode("utf-8"), None)
    ct, tag = ct_plus_tag[:-16], ct_plus_tag[-16:]
    combined = base64.b64encode(ct).decode("ascii") + ":::" + base64.b64encode(tag).decode("ascii")
    return combined.encode("ascii").hex()


def aes_decrypt(hex_str: str) -> str:
    """逆向 aes_encrypt"""
    key, iv = _key_iv()
    raw = bytes.fromhex(hex_str).decode("ascii")
    if ":::" not in raw:
        raise ValueError("EncryptInfo 格式不正確（缺少 ::: 分隔）")
    ct_b64, tag_b64 = raw.split(":::", 1)
    ct  = base64.b64decode(ct_b64)
    tag = base64.b64decode(tag_b64)
    plain = AESGCM(key).decrypt(iv, ct + tag, None)
    return plain.decode("utf-8")


def hash_sign(encrypt_hex: str) -> str:
    """HashInfo = SHA256(HashKey + EncryptHex + HashIV).upper() — 直接字串連接！"""
    raw = (settings.PAYUNI_HASH_KEY or "") + encrypt_hex + (settings.PAYUNI_HASH_IV or "")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()


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
