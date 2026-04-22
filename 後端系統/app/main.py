from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import urllib.parse

from app.core import models  # 必須在 create_all 前 import，讓 SQLAlchemy 發現所有表
from app.core.database import Base, engine, check_connection
from app.routers import sessions, payments, monitor, companies, client_view

app = FastAPI(
    title="腦波檢測報告系統 API",
    description="自動生成腦波分析報告的後端服務",
    version="1.0.0"
)

# CORS（允許 Android / 前台管理介面呼叫）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載靜態 PDF 目錄
os.makedirs("reports", exist_ok=True)
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

# 掛載前端靜態資源
# __file__ 在容器內為 /app/app/main.py，所以逐層往上：
#   /app/app  → /app  → static-app 在 /app/static-app/
_THIS_FILE     = os.path.abspath(__file__)               # /app/app/main.py
_APP_PKG_DIR   = os.path.dirname(_THIS_FILE)             # /app/app
_BACKEND_DIR   = os.path.dirname(_APP_PKG_DIR)           # /app

# 依序嘗試幾個可能位置（Docker / 本地開發 都相容）
_CANDIDATES = [
    os.path.join(_BACKEND_DIR, "static-app"),                          # /app/static-app  ← Docker
    os.path.join(os.path.dirname(_BACKEND_DIR), "後端系統", "static-app"),  # 本地開發
    os.path.join(os.path.dirname(_BACKEND_DIR), "前端原型"),            # 舊版本相容
]
_STATIC_APP_DIR = next((p for p in _CANDIDATES if os.path.isdir(p)), None)
print(f"[static-app] 使用路徑：{_STATIC_APP_DIR}")

if _STATIC_APP_DIR:
    app.mount("/static-app", StaticFiles(directory=_STATIC_APP_DIR), name="static-app")

# 掛載路由
app.include_router(sessions.router)
app.include_router(payments.router)
app.include_router(monitor.router)
app.include_router(companies.router)
app.include_router(client_view.router)


@app.on_event("startup")
async def startup():
    # 自動建立資料表
    Base.metadata.create_all(bind=engine)
    ok = check_connection()
    status = "OK" if ok else "ERROR"
    print(f"[DB] {status}")


@app.get("/")
def root():
    return {"status": "ok", "message": "腦波報告系統 API 運行中"}

@app.get("/dashboard", response_class=FileResponse)
def dashboard():
    """即時監控儀表板"""
    return FileResponse("dashboard.html")

@app.get("/app", response_class=FileResponse)
def prototype_app():
    """前端 App 原型（手機瀏覽器測試用）"""
    if not _STATIC_APP_DIR:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "static-app directory not found", "checked": _CANDIDATES}, status_code=500)
    proto_path = os.path.join(_STATIC_APP_DIR, "app_prototype.html")
    if not os.path.exists(proto_path):
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": f"app_prototype.html not found at {proto_path}"}, status_code=500)
    return FileResponse(proto_path, media_type="text/html")

@app.get("/pay/ecpay/{order_id}")
def pay_ecpay(order_id: str):
    """
    顧客掃描 QR Code 後開啟此頁面，自動 POST 到綠界付款頁

    此路由需在 /pay/{order_id} 之前宣告，避免被通用路由截走
    """
    from fastapi.responses import HTMLResponse
    from app.routers.payments import _payment_store, _calc_check_mac, _ecpay_url
    from app.core.config import settings
    from datetime import datetime

    order = _payment_store.get(order_id)
    if not order:
        return HTMLResponse("<h2>訂單不存在或已過期</h2>", status_code=404)

    base = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    if base:
        notify_url  = f"https://{base}/api/v1/payments/notify"
        return_url  = f"https://{base}/api/v1/payments/return/{order_id}"
    else:
        notify_url  = "http://localhost:8000/api/v1/payments/notify"
        return_url  = "http://localhost:8000/api/v1/payments/return/{order_id}"

    trade_date = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    # 綠界訂單號最多 20 碼
    mer_trade_no = order_id[:20]

    params = {
        "MerchantID":        settings.ECPAY_MERCHANT_ID or "2000132",  # 2000132 為綠界測試商家
        "MerchantTradeNo":   mer_trade_no,
        "MerchantTradeDate": trade_date,
        "PaymentType":       "aio",
        "TotalAmount":       str(order["amount"]),
        "TradeDesc":         urllib.parse.quote(order["trade_desc"]),
        "ItemName":          order["trade_desc"],
        "ReturnURL":         notify_url,
        "ClientBackURL":     return_url,
        "ChoosePayment":     "Credit",
        "EncryptType":       "1",
    }

    params["CheckMacValue"] = _calc_check_mac(
        params,
        settings.ECPAY_HASH_KEY or "pwFHCqoQZGmho4w6",   # 綠界測試 Hash Key
        settings.ECPAY_HASH_IV  or "EkRm7iFT261dpevs",   # 綠界測試 Hash IV
    )

    fields_html = "\n".join(
        f'    <input type="hidden" name="{k}" value="{v}">'
        for k, v in params.items()
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>跳轉至綠界付款頁...</title>
  <style>
    body{{margin:0;display:flex;justify-content:center;align-items:center;
         min-height:100vh;background:#f5f7fa;
         font-family:'Microsoft JhengHei',sans-serif;text-align:center;}}
    .msg{{color:#555;font-size:16px;}}
    .spin{{font-size:36px;animation:spin 1s linear infinite;display:block;margin-bottom:16px;}}
    @keyframes spin{{from{{transform:rotate(0deg)}}to{{transform:rotate(360deg)}}}}
  </style>
</head>
<body>
  <div>
    <span class="spin">⏳</span>
    <div class="msg">正在跳轉至綠界付款頁，請稍候...</div>
    <form id="f" method="POST" action="{_ecpay_url()}">
{fields_html}
    </form>
  </div>
  <script>document.getElementById('f').submit();</script>
</body>
</html>"""
    return HTMLResponse(html)



@app.get("/pay/{order_id}")
def pay_page(order_id: str):
    """付款短連結頁面（舊連結相容，顯示 QR Code）"""
    from fastapi.responses import HTMLResponse
    import urllib.parse as _up
    base = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    pay_url = f"https://{base}/pay/ecpay/{order_id}" if base else f"/pay/ecpay/{order_id}"
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>腦波報告付款</title>
  <style>
    body{{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;
         background:#f5f7fa;font-family:'Microsoft JhengHei',sans-serif;}}
    .card{{background:white;border-radius:20px;padding:32px 24px;
           box-shadow:0 8px 32px rgba(0,0,0,0.12);max-width:360px;width:90%;text-align:center;}}
    .logo{{font-size:40px;margin-bottom:8px;}}
    h2{{color:#1a1a2e;font-size:18px;margin:0 0 4px;}}
    .order-id{{font-size:12px;color:#aaa;margin-bottom:20px;}}
    .qr-wrap{{background:#f8f9ff;border-radius:16px;padding:20px;margin-bottom:16px;}}
    img{{width:200px;height:200px;border-radius:12px;}}
    .hint{{font-size:12px;color:#888;margin-bottom:16px;}}
    a.btn{{display:block;background:#2196F3;color:white;text-decoration:none;
           border-radius:10px;padding:12px;font-size:14px;margin-bottom:12px;}}
    .footer{{font-size:11px;color:#ccc;}}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">🧠</div>
    <h2>腦波報告付款</h2>
    <div class="order-id">訂單號：{order_id}</div>
    <div class="qr-wrap">
      <img src="/api/v1/payments/{order_id}/qr" alt="付款 QR Code"
           onerror="this.style.display='none';document.getElementById('qr-err').style.display='block'">
      <p id="qr-err" style="display:none;color:#e57373;font-size:12px;">QR Code 載入失敗，請直接點下方連結</p>
    </div>
    <div class="hint">使用手機掃描 QR Code，或點下方按鈕前往付款</div>
    <a class="btn" href="{pay_url}">💳 前往綠界付款頁</a>
    <div class="footer">🔒 由綠界科技提供安全金流服務</div>
  </div>
</body>
</html>"""
    return HTMLResponse(html)


@app.get("/health")
def health():
    """Railway Healthcheck 端點（永遠回傳 200，DB 狀態另行回報）"""
    try:
        db_ok = check_connection()
    except Exception:
        db_ok = False
    return {
        "api":      "ok",
        "database": "ok" if db_ok else "error"
    }
