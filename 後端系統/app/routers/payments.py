"""
金流模組（同時支援 ECPay 綠界、PayUni 統一金流）

切換用：環境變數 PAYMENT_PROVIDER = "ecpay" / "payuni"
"""
import hashlib
import time
import urllib.parse
import io
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.services import payuni

router = APIRouter(prefix="/api/v1/payments", tags=["付款"])


def _provider() -> str:
    p = (settings.PAYMENT_PROVIDER or "ecpay").lower()
    return p if p in ("ecpay", "payuni") else "ecpay"


def _pay_path(order_id: str) -> str:
    return f"/pay/{_provider()}/{order_id}"

# 記憶體暫存訂單（多機部署時改用 Redis）
_payment_store: dict[str, dict] = {}

# ─── 綠界 URL ──────────────────────────────────────────────────────────────────
_ECPAY_TEST_URL = "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5"
_ECPAY_PROD_URL = "https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5"


def _ecpay_url() -> str:
    return _ECPAY_TEST_URL if settings.ECPAY_TEST_MODE else _ECPAY_PROD_URL


def _backend_base() -> str:
    """取得後端 Base URL，用於組合 NotifyURL / QR code 連結"""
    base = settings.REPORT_BASE_URL
    idx = base.find("/reports")
    return base[:idx] if idx != -1 else base.rstrip("/")


# ─── Request/Response 模型 ────────────────────────────────────────────────────

class CreatePaymentRequest(BaseModel):
    report_type: str        # life_trial / life_full / life_vip / ...
    subject_name: str = ""
    amount: int             # 3000 / 5000 / 12000
    notify_email: str = ""

class CreatePaymentResponse(BaseModel):
    order_id: str
    qr_code_url: str        # 我方後端的 QR Code 圖片 URL
    pay_url: str            # 顧客直接點開的付款連結
    amount: int
    expire_minutes: int = 15

class PaymentStatusResponse(BaseModel):
    order_id: str
    status: str             # pending / paid / expired / failed
    paid_at: Optional[int] = None


# ─── 綠界 CheckMacValue 計算 ──────────────────────────────────────────────────

def _calc_check_mac(params: dict, hash_key: str, hash_iv: str) -> str:
    """
    綠界簽章計算：
      1. 所有參數（排除 CheckMacValue）依 key 字母排序
      2. 組合成 QueryString
      3. 前後加上 HashKey= / HashIV=
      4. URL Encode（全小寫）並修正特定字元
      5. SHA256 轉大寫
    """
    sorted_items = sorted(params.items(), key=lambda x: x[0].lower())
    query = "&".join(f"{k}={v}" for k, v in sorted_items)
    raw = f"HashKey={hash_key}&{query}&HashIV={hash_iv}"
    encoded = urllib.parse.quote_plus(raw).lower()
    # 綠界文件規定保留這幾個特殊字元
    for src, dst in [("%21", "!"), ("%28", "("), ("%29", ")"), ("%2a", "*"), ("%2d", "-"), ("%5f", "_")]:
        encoded = encoded.replace(src, dst)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper()


def _verify_ecpay_notify(params: dict) -> bool:
    check_mac = params.pop("CheckMacValue", "")
    computed = _calc_check_mac(
        params,
        settings.ECPAY_HASH_KEY,
        settings.ECPAY_HASH_IV,
    )
    return computed == check_mac.upper()


def _generate_order_id() -> str:
    ts = int(time.time() * 1000) % 10**14
    return f"EEG{ts}"


# ─── QR Code 圖片產生 ─────────────────────────────────────────────────────────

def _generate_qr_bytes(data: str) -> bytes:
    """用 qrcode 套件產生 PNG bytes，供 /payments/{id}/qr 端點回傳"""
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=8, border=4)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # qrcode 套件未安裝時回傳空 bytes，前端改顯示文字連結
        return b""


# ─── API 端點 ────────────────────────────────────────────────────────────────

@router.post("/create", response_model=CreatePaymentResponse)
async def create_payment(req: CreatePaymentRequest):
    """
    Android 呼叫：建立付款訂單

    - 回傳 qr_code_url（PNG 圖片 URL）→ 顧客掃碼後瀏覽器跳轉綠界付款頁
    - 回傳 pay_url（可直接點開的連結）→ 顧問可貼給顧客用
    """
    report_labels = {
        "life_trial":  "腦波人生劇本體驗版",
        "life_full":   "腦波人生劇本完整版",
        "life_vip":    "腦波人生劇本VIP版",
        "child_trial": "兒童腦波天賦解碼體驗版",
        "child_full":  "兒童腦波天賦解碼完整版",
        "child_vip":   "兒童腦波天賦解碼VIP版",
        "test_1":      "功能測試NT1元",
    }
    desc = report_labels.get(req.report_type, "腦波報告")
    order_id = _generate_order_id()
    base = _backend_base()
    pay_url = f"{base}{_pay_path(order_id)}"

    _payment_store[order_id] = {
        "order_id":     order_id,
        "status":       "pending",
        "amount":       req.amount,
        "report_type":  req.report_type,
        "subject_name": req.subject_name,
        "notify_email": req.notify_email,
        "trade_desc":   desc,
        "created_at":   int(time.time()),
        "paid_at":      None,
    }

    return CreatePaymentResponse(
        order_id       = order_id,
        qr_code_url    = f"{base}/api/v1/payments/{order_id}/qr",
        pay_url        = pay_url,
        amount         = req.amount,
        expire_minutes = 15,
    )


@router.get("/{order_id}/qr")
def get_qr_image(order_id: str):
    """
    回傳該訂單付款連結的 QR Code PNG 圖片
    Android / 前端用 <img src=...> 顯示
    """
    order = _payment_store.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")

    base = _backend_base()
    pay_url = f"{base}{_pay_path(order_id)}"
    png = _generate_qr_bytes(pay_url)

    if not png:
        raise HTTPException(status_code=503, detail="QR Code 產生失敗，請確認 qrcode 套件已安裝")

    return StreamingResponse(io.BytesIO(png), media_type="image/png")


@router.get("/{order_id}/status", response_model=PaymentStatusResponse)
def get_payment_status(order_id: str):
    """
    Android 輪詢付款狀態（建議每 3 秒呼叫一次）

    status:
      pending → 等待付款
      paid    → 付款成功 → Android 跳腦波檢測頁
      expired → 逾時（15 分鐘）
      failed  → 失敗
    """
    order = _payment_store.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")

    if order["status"] == "pending":
        if time.time() - order["created_at"] > 15 * 60:
            order["status"] = "expired"

    return PaymentStatusResponse(
        order_id = order_id,
        status   = order["status"],
        paid_at  = order.get("paid_at"),
    )


@router.post("/notify")
async def ecpay_notify(request: Request):
    """
    【路徑1 - 非同步 Webhook】綠界伺服器付款完成後主動通知（1-10 秒後到達）

    在綠界後台「特店管理 → 系統介接設定」填入：
      付款完成通知網址：https://backend-production-2da61.up.railway.app/api/v1/payments/notify
    """
    form_data = await request.form()
    params = dict(form_data)
    print(f"[ECPay Notify] 收到 Webhook：{params}")

    if not _verify_ecpay_notify(params):
        print("[ECPay Notify] 簽章驗證失敗")
        return "0|ErrorMessage"

    rtn_code     = params.get("RtnCode", "")
    mer_trade_no = params.get("MerchantTradeNo", "")

    if rtn_code != "1":
        print(f"[ECPay Notify] 訂單 {mer_trade_no} 付款未成功，RtnCode={rtn_code}")
        return "1|OK"

    order = _payment_store.get(mer_trade_no)
    if order and order["status"] == "pending":
        order["status"]  = "paid"
        order["paid_at"] = int(time.time())
        print(f"[ECPay Notify] 訂單 {mer_trade_no} Webhook 付款成功！")

    return "1|OK"


@router.get("/return/{order_id}")
async def ecpay_return(order_id: str, request: Request):
    """
    【路徑2 - 即時 ReturnURL】顧客完成付款後，瀏覽器立即跳轉到此頁（比 Webhook 快）

    這裡同時驗證綠界的回傳參數 → 立即更新訂單狀態
    → Android App 的輪詢最快在 3 秒內就能拿到 "paid" 狀態

    延遲說明：
      ① 顧客付款 → 綠界頁面跳轉到此 URL（幾乎即時，< 1 秒）
      ② 此端點更新訂單狀態（< 0.1 秒）
      ③ Android App 輪詢（每 3 秒）→ 最多 3 秒看到「付款成功」
      ④ Webhook 隨後到達做二次確認（1~10 秒，不影響使用者體驗）
    """
    # 嘗試從 query params 或 form 驗證綠界簽章
    params_raw = dict(request.query_params)

    if params_raw and "RtnCode" in params_raw:
        check_mac = params_raw.pop("CheckMacValue", "")
        computed  = _calc_check_mac(
            params_raw,
            settings.ECPAY_HASH_KEY or "pwFHCqoQZGmho4w6",
            settings.ECPAY_HASH_IV  or "EkRm7iFT261dpevs",
        )
        rtn_code = params_raw.get("RtnCode", "")
        mer_no   = params_raw.get("MerchantTradeNo", order_id)

        if computed == check_mac.upper() and rtn_code == "1":
            order = _payment_store.get(mer_no)
            if order and order["status"] == "pending":
                order["status"]  = "paid"
                order["paid_at"] = int(time.time())
                print(f"[ECPay Return] 訂單 {mer_no} ReturnURL 立即確認付款成功！")
    else:
        # 沒有驗證參數時（測試環境），仍顯示成功頁讓測試流程繼續
        print(f"[ECPay Return] 收到跳轉（無驗證參數），訂單：{order_id}")

    from fastapi.responses import HTMLResponse
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>付款完成</title>
<style>
  body{{margin:0;display:flex;justify-content:center;align-items:center;
       min-height:100vh;background:#f5f7fa;font-family:'Microsoft JhengHei',sans-serif;
       text-align:center;}}
  .card{{background:white;border-radius:20px;padding:36px 28px;
         box-shadow:0 8px 32px rgba(0,0,0,0.12);max-width:340px;width:90%;}}
  .icon{{font-size:56px;margin-bottom:12px;}}
  h2{{color:#1a1a2e;font-size:20px;margin:0 0 8px;}}
  p{{color:#666;font-size:14px;line-height:1.6;}}
  .hint{{background:#e8f5e9;border-radius:10px;padding:12px;margin-top:16px;
         font-size:13px;color:#2e7d32;}}
</style>
</head>
<body>
  <div class="card">
    <div class="icon">✅</div>
    <h2>付款完成！</h2>
    <p>請返回 App 或關閉此頁面。</p>
    <div class="hint">
      📱 系統正在確認付款，<br>
      App 將在 <strong>3 秒內自動跳轉</strong>至腦波檢測頁面。
    </div>
    <p style="color:#aaa;font-size:12px;margin-top:16px;">訂單：{order_id}</p>
  </div>
</body>
</html>"""
    return HTMLResponse(html)


# ─── PayUni 統一金流 ─────────────────────────────────────────────────────────

@router.post("/payuni/notify")
async def payuni_notify(request: Request):
    """
    PayUni 付款完成 Webhook（PayUni 伺服器主動 POST 過來）

    在 PayUni 商家後台「商家設定 → 系統參數設定」填：
      通知網址  https://你的後端網域/api/v1/payments/payuni/notify
    """
    form = await request.form()
    enc  = form.get("EncryptInfo", "")
    hsh  = form.get("HashInfo", "")
    print(f"[PayUni Notify] EncryptInfo={enc[:32]}... HashInfo={hsh[:16]}...")

    result = payuni.decrypt_callback(enc, hsh)
    if not result.get("ok"):
        print(f"[PayUni Notify] 解密/驗章失敗：{result.get('error')}")
        return "FAIL"

    data = result["data"]
    order_id = data.get("MerTradeNo") or data.get("MerchantOrderNo") or ""
    success  = result.get("success") or (data.get("TradeStatus") in ("1", "SUCCESS"))
    print(f"[PayUni Notify] 訂單 {order_id} success={success}")

    if success:
        order = _payment_store.get(order_id)
        if order and order["status"] == "pending":
            order["status"]  = "paid"
            order["paid_at"] = int(time.time())
            order["paid_via"] = "payuni"
            print(f"[PayUni Notify] 訂單 {order_id} 已標記付款成功")

    return "SUCCESS"


async def _handle_payuni_return(request: Request, order_id_from_path: str = "") -> HTMLResponse:
    """共用邏輯：處理 PayUni return 的 POST/GET，order_id 可從路徑或 form 取得

    結果分四種：
      paid_ok=True            付款成功（綠勾）
      result_kind='cancel'    使用者沒帶資料回來 → 「您似乎沒完成付款」（藍色資訊）
      result_kind='fail'      PayUni 回報付款失敗（橘色警告）
      result_kind='sign_err'  HashKey/IV 設錯 → 真正的系統問題（紅色錯誤，內部除錯用）
    """
    enc, hsh = "", ""
    form_data = {}
    if request.method == "POST":
        form = await request.form()
        form_data = dict(form)
        enc = form.get("EncryptInfo", "")
        hsh = form.get("HashInfo", "")
    else:
        enc = request.query_params.get("EncryptInfo", "")
        hsh = request.query_params.get("HashInfo", "")

    real_no    = order_id_from_path or ""
    paid_ok    = False
    result_kind = "cancel"   # 預設：沒帶資料 = 使用者取消
    err_detail  = ""         # 給開發者看的詳細訊息（會印 log）

    if enc and hsh:
        result = payuni.decrypt_callback(enc, hsh)
        if result.get("ok"):
            data = result["data"]
            real_no = data.get("MerTradeNo") or data.get("MerchantOrderNo") or real_no
            if result.get("success"):
                order = _payment_store.get(real_no)
                if order and order["status"] == "pending":
                    order["status"]  = "paid"
                    order["paid_at"] = int(time.time())
                    order["paid_via"] = "payuni"
                    paid_ok = True
                    print(f"[PayUni Return] 訂單 {real_no} 已立即確認付款成功")
                elif order:
                    # webhook 先到、訂單已是 paid
                    paid_ok = (order["status"] == "paid")
                else:
                    result_kind = "fail"
                    err_detail = f"訂單 {real_no} 已從 PayUni 回報付款，但伺服器找不到（可能後端重啟，記憶體訂單已清）"
                    print(f"[PayUni Return] {err_detail}")
            else:
                result_kind = "fail"
                err_detail = f"PayUni 回報付款未成功：data={data}"
                print(f"[PayUni Return] {err_detail}")
        else:
            result_kind = "sign_err"
            err_detail = f"PayUni 簽章驗證失敗：{result.get('error')}（檢查 PAYUNI_HASH_KEY / PAYUNI_HASH_IV 是否與後台一致）"
            print(f"[PayUni Return] {err_detail}")
    else:
        # 沒帶 EncryptInfo/HashInfo = 使用者按取消或瀏覽器返回
        result_kind = "cancel"
        print(f"[PayUni Return] 使用者取消／返回（無 EncryptInfo），order={real_no}，form_keys={list(form_data.keys())}, query_keys={list(request.query_params.keys())}")

    show_id = real_no or "(尚未建立)"
    if paid_ok:
        icon  = "✅"
        bg    = "#43a047"   # 綠
        title = "付款完成！"
        msg   = "我們已收到您的付款，請返回 App。"
        hint  = "📱 App 將在 <strong>3 秒內</strong>自動偵測並進入腦波檢測頁面。"
        hint_bg = "#e8f5e9"; hint_color = "#1b5e20"
    elif result_kind == "cancel":
        icon  = "ℹ️"
        bg    = "#1976d2"   # 藍
        title = "尚未完成付款"
        msg   = "您似乎取消了付款或返回了上一頁。"
        hint  = "💡 如需付款，請回到 App 點「📲 立即付款」重新前往。<br>如果剛剛已成功付款，3 秒內 App 會自動偵測，可以直接返回。"
        hint_bg = "#e3f2fd"; hint_color = "#0d47a1"
    elif result_kind == "fail":
        icon  = "⚠️"
        bg    = "#f57c00"   # 橘
        title = "付款未成功"
        msg   = "金流系統回報這筆交易未完成（可能是卡片驗證失敗或金額不符）。"
        hint  = "💡 您可以回到 App，重新建立訂單再試一次。如果款項已被扣除，請聯絡客服協助退款。"
        hint_bg = "#fff3e0"; hint_color = "#e65100"
    else:  # sign_err
        icon  = "🛠"
        bg    = "#d32f2f"   # 紅
        title = "系統設定問題"
        msg   = "後端與金流的安全簽章驗證對不上，這不是您的問題，請聯絡管理員。"
        hint  = "💡 (技術細節給管理員) 請至 Railway 確認 PAYUNI_HASH_KEY / PAYUNI_HASH_IV 是否與 PayUni 後台「商家設定」頁完全一致（注意大小寫與空白）。"
        hint_bg = "#ffebee"; hint_color = "#b71c1c"

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only">
<meta name="supported-color-schemes" content="light">
<title>{title}</title>
<style>
  :root {{ color-scheme: light; }}
  html, body {{
    background-color: #f5f7fa !important;
    color: #333;
  }}
  body{{margin:0;display:flex;justify-content:center;align-items:center;
       min-height:100vh;font-family:'Microsoft JhengHei','Helvetica',sans-serif;
       text-align:center;padding:20px;}}
  .card{{background:white !important;color:#1a1a2e;border-radius:20px;padding:32px 24px;
         box-shadow:0 8px 32px rgba(0,0,0,0.12);max-width:360px;width:100%;
         border-top:6px solid {bg};}}
  .icon{{font-size:56px;margin-bottom:8px;}}
  h2{{color:#1a1a2e !important;font-size:20px;margin:8px 0;}}
  p{{color:#555 !important;font-size:14px;line-height:1.7;margin:8px 0;}}
  .hint{{background:{hint_bg} !important;color:{hint_color} !important;
         border-radius:10px;padding:12px 14px;margin-top:16px;
         font-size:13px;line-height:1.7;text-align:left;}}
  a.btn{{display:block;background:{bg} !important;color:white !important;text-decoration:none;
         border-radius:12px;padding:14px;font-size:15px;font-weight:600;margin-top:16px;
         box-shadow:0 4px 14px rgba(0,0,0,0.15);}}
  .oid{{color:#aaa;font-size:11px;margin-top:14px;font-family:monospace;}}
</style>
</head>
<body>
<div class="card">
  <div class="icon">{icon}</div>
  <h2>{title}</h2>
  <p>{msg}</p>
  <div class="hint">{hint}</div>
  <a class="btn" href="/app">📱 返回 App</a>
  <div class="oid">訂單編號：{show_id}</div>
</div>
</body>
</html>"""
    return HTMLResponse(html)


@router.api_route("/payuni/return/{order_id}", methods=["GET", "POST"])
async def payuni_return(order_id: str, request: Request):
    """顧客付款完成後跳轉回來的頁面（含 order_id 版本）"""
    return await _handle_payuni_return(request, order_id_from_path=order_id)


@router.api_route("/payuni/return", methods=["GET", "POST"])
async def payuni_return_no_id(request: Request):
    """PayUni 在某些情境下會把 ReturnURL 截掉 order_id 後 POST 回來，
    我們從 EncryptInfo 解出 MerTradeNo 也能正確處理。"""
    return await _handle_payuni_return(request, order_id_from_path="")


@router.get("/diag")
def payment_diag():
    """商業上線前驗 provider 設定是否正確"""
    out = {
        "provider":  _provider(),
        "public_url_base": settings.PUBLIC_BASE_URL or os.environ.get("RAILWAY_PUBLIC_DOMAIN", ""),
        "ecpay": {
            "merchant_id_set": bool(settings.ECPAY_MERCHANT_ID),
            "test_mode": settings.ECPAY_TEST_MODE,
        },
        "payuni": payuni.diag(),
    }
    return out


# ─── 測試用：手動模擬付款成功 ─────────────────────────────────────────────────

@router.post("/simulate-paid/{order_id}")
def simulate_paid(order_id: str):
    """【僅限開發測試】模擬通知付款成功"""
    order = _payment_store.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")
    order["status"]  = "paid"
    order["paid_at"] = int(time.time())
    return {"message": f"訂單 {order_id} 已模擬付款成功", "status": "paid"}
