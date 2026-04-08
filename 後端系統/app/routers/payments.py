"""
統一金流 PAYUNi 付款模組
流程：
  1. POST /payments/create    → Android 建立訂單，取得 QR Code URL
  2. POST /payments/notify    → 統一金流付款完成 Webhook（伺服器接收）
  3. GET  /payments/{id}/status → Android 輪詢付款狀態
"""
import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from app.core.database import get_db
from app.core import models
from app.core.config import settings

router = APIRouter(prefix="/api/v1/payments", tags=["付款"])


# ─── 資料表（Payment Order）需要先加到 models.py ───────────────────────────
# 這裡暫時用 dict 模擬（正式版請將 PaymentOrder 加入 models.py）

# 記憶體暫存（多機部署時改用 Redis）
_payment_store: dict[str, dict] = {}


# ─── Request/Response 模型 ────────────────────────────────────────────────────

class CreatePaymentRequest(BaseModel):
    report_type: str        # life_trial / life_full / life_vip / child_trial / ...
    subject_name: str = ""
    amount: int             # 3000 / 5000 / 12000
    notify_email: str = ""  # 受測者 email（付款成功後報告寄送對象）

class CreatePaymentResponse(BaseModel):
    order_id: str
    qr_code_url: str        # 統一金流 QR Code URL（前端直接顯示）
    amount: int
    expire_minutes: int = 15

class PaymentStatusResponse(BaseModel):
    order_id: str
    status: str             # pending / paid / expired / failed
    paid_at: Optional[int] = None


# ─── 統一金流 工具函數 ────────────────────────────────────────────────────────

PAYUNI_API_URL   = "https://api.payuni.com.tw/api/order"
PAYUNI_HASH_KEY  = settings.PAYUNI_HASH_KEY  if hasattr(settings, 'PAYUNI_HASH_KEY')  else "your_hash_key"
PAYUNI_HASH_IV   = settings.PAYUNI_HASH_IV   if hasattr(settings, 'PAYUNI_HASH_IV')   else "your_hash_iv"
PAYUNI_MERCHANT  = settings.PAYUNI_MERCHANT  if hasattr(settings, 'PAYUNI_MERCHANT')  else "your_merchant_id"


def _sha256_hash(data: str) -> str:
    """SHA-256 雜湊（用於統一金流簽章驗證）"""
    return hashlib.sha256(data.encode("utf-8")).hexdigest().upper()


def _verify_notify_hash(params: dict) -> bool:
    """
    驗證統一金流回調簽章
    驗證方式：將回傳參數（排除 HashStr）排序後組合，加上 HashKey/IV 做 SHA256
    """
    check_code = params.get("HashStr", "")
    # 取出所有非 HashStr 的參數，依 key 字母排序
    sorted_params = sorted(
        [(k, v) for k, v in params.items() if k != "HashStr"],
        key=lambda x: x[0]
    )
    raw = "&".join(f"{k}={v}" for k, v in sorted_params)
    raw = f"HashIV={PAYUNI_HASH_IV}&{raw}&HashKey={PAYUNI_HASH_KEY}"
    computed = _sha256_hash(raw)
    return computed == check_code.upper()


def _generate_order_id() -> str:
    """產生唯一訂單編號"""
    ts = int(time.time() * 1000)
    return f"EEG{ts}"


async def _create_payuni_order(order_id: str, amount: int, desc: str) -> str:
    """
    呼叫統一金流 API 建立 QR Code 訂單
    回傳 QR Code URL（或 QR Code 圖片 URL）

    真實串接時請依照統一金流 API 文件實作 AES 加密。
    目前為 DEMO 模式：直接回傳模擬 QR Code URL。
    """
    # ── DEMO 模式（尚未取得正式商店號時使用）──────────────────────────
    if PAYUNI_MERCHANT == "your_merchant_id":
        # 回傳靜態 QR Code 圖片（本地的 qr_*.png）
        qr_map = {3000: "qr_trial.png", 5000: "qr_full.png", 12000: "qr_vip.png"}
        qr_file = qr_map.get(amount, "qr_trial.png")
        return f"{settings.REPORT_BASE_URL.replace('/reports','')}/{qr_file}"

    # ── 正式模式：呼叫統一金流 API ────────────────────────────────────
    import httpx, base64
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad

    order_data = {
        "MerID":       PAYUNI_MERCHANT,
        "MerTradeNo":  order_id,
        "TradeAmt":    str(amount),
        "Timestamp":   str(int(time.time())),
        "ItemDesc":    desc,
        "NotifyURL":   f"{settings.REPORT_BASE_URL.replace('/reports','')}/api/v1/payments/notify",
        "ReturnURL":   f"{settings.REPORT_BASE_URL.replace('/reports','')}/api/v1/payments/return",
        "PayType":     "QR",  # QR Code 付款
    }

    # AES-256-CBC 加密
    key = PAYUNI_HASH_KEY.encode("utf-8")[:32]
    iv  = PAYUNI_HASH_IV.encode("utf-8")[:16]
    raw = urllib.parse.urlencode(order_data).encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = base64.b64encode(cipher.encrypt(pad(raw, AES.block_size))).decode()

    # 計算 HashStr（SHA256）
    hash_str = _sha256_hash(
        f"HashIV={PAYUNI_HASH_IV}&EncryptInfo={encrypted}&HashKey={PAYUNI_HASH_KEY}"
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(PAYUNI_API_URL, data={
            "MerID":       PAYUNI_MERCHANT,
            "EncryptInfo": encrypted,
            "HashStr":     hash_str,
        }, timeout=15)
        result = resp.json()

    if result.get("Status") == "SUCCESS":
        return result.get("QRCodeUrl", "")
    raise Exception(f"統一金流建單失敗：{result}")


# ─── API 端點 ────────────────────────────────────────────────────────────────

@router.post("/create", response_model=CreatePaymentResponse)
async def create_payment(req: CreatePaymentRequest):
    """
    Android 呼叫：建立付款訂單，取得 QR Code URL

    Android 顯示 QR Code 圖片後開始輪詢 /payments/{order_id}/status
    """
    report_labels = {
        "life_trial":  "腦波分析人生劇本 體驗版",
        "life_full":   "腦波分析人生劇本 完整版",
        "life_vip":    "腦波分析人生劇本 VIP版",
        "child_trial": "兒童腦波天賦解碼 體驗版",
        "child_full":  "兒童腦波天賦解碼 完整版",
        "child_vip":   "兒童腦波天賦解碼 VIP版",
    }
    desc = report_labels.get(req.report_type, "腦波報告")

    order_id = _generate_order_id()

    # 呼叫統一金流取得 QR Code
    qr_url = await _create_payuni_order(order_id, req.amount, desc)

    # 儲存訂單狀態
    _payment_store[order_id] = {
        "order_id":     order_id,
        "status":       "pending",
        "amount":       req.amount,
        "report_type":  req.report_type,
        "subject_name": req.subject_name,
        "notify_email": req.notify_email,
        "created_at":   int(time.time()),
        "paid_at":      None,
    }

    return CreatePaymentResponse(
        order_id       = order_id,
        qr_code_url    = qr_url,
        amount         = req.amount,
        expire_minutes = 15,
    )


@router.get("/{order_id}/status", response_model=PaymentStatusResponse)
def get_payment_status(order_id: str):
    """
    Android 輪詢付款狀態（建議每 3 秒呼叫一次）

    回傳 status:
      - pending  → 等待付款（繼續顯示 QR Code）
      - paid     → 付款成功（Android 跳轉腦波檢測畫面）
      - expired  → 訂單逾時（Android 顯示逾時提示）
      - failed   → 付款失敗
    """
    order = _payment_store.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")

    # 自動判斷是否逾時（15 分鐘）
    if order["status"] == "pending":
        elapsed = time.time() - order["created_at"]
        if elapsed > 15 * 60:
            order["status"] = "expired"

    return PaymentStatusResponse(
        order_id = order_id,
        status   = order["status"],
        paid_at  = order.get("paid_at"),
    )


@router.post("/notify")
async def payuni_notify(request: Request, background_tasks: BackgroundTasks):
    """
    統一金流付款完成 Webhook（只有統一金流伺服器會呼叫此 API）

    統一金流確認付款後，POST 到此端點。
    我們驗證簽章 → 更新訂單狀態 → 觸發報告生成。
    """
    # 解析 form data
    form_data = await request.form()
    params = dict(form_data)

    print(f"[PayUni Notify] 收到回調：{params}")

    # 1. 驗證簽章
    if not _verify_notify_hash(params):
        print("[PayUni Notify] 簽章驗證失敗！")
        # 統一金流要求回傳 "OK" 才停止重試，驗證失敗仍回 OK 但不處理
        return "FAIL"

    # 2. 解析付款結果
    status_code = params.get("Status", "")
    mer_trade_no = params.get("MerTradeNo", "")  # 我們的訂單號

    if status_code != "SUCCESS":
        print(f"[PayUni Notify] 訂單 {mer_trade_no} 付款未成功，狀態：{status_code}")
        return "OK"

    # 3. 更新訂單狀態
    order = _payment_store.get(mer_trade_no)
    if order and order["status"] == "pending":
        order["status"]  = "paid"
        order["paid_at"] = int(time.time())
        print(f"[PayUni Notify] 訂單 {mer_trade_no} 付款成功！")

        # 4. 背景觸發：若已有腦波數據則生成報告（付款後才正式啟動）
        # background_tasks.add_task(trigger_report_after_payment, mer_trade_no)

    # 統一金流規定：必須回傳純文字 "OK"
    return "OK"


@router.post("/return")
async def payuni_return(request: Request):
    """
    統一金流付款完成後跳轉頁面（Browser ReturnURL）
    App 使用 QR Code 付款時不需要此端點，但統一金流仍可能呼叫。
    """
    return {"message": "付款完成，請返回 App 繼續操作"}


# ─── 測試用：手動模擬付款成功（開發期間使用）────────────────────────────────

@router.post("/simulate-paid/{order_id}")
def simulate_paid(order_id: str):
    """
    【僅限開發測試】模擬統一金流通知付款成功
    正式環境請移除此端點
    """
    order = _payment_store.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    order["status"]  = "paid"
    order["paid_at"] = int(time.time())
    return {"message": f"訂單 {order_id} 已模擬付款成功", "status": "paid"}
