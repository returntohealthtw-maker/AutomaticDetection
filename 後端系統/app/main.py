from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
import urllib.parse
import time

APP_HTML_VERSION = "2026.05.23.1"  # 每次改 HTML/JS 都更新這個

# Android APK 版本（要跟 app/build.gradle versionCode 對應；發新 APK 才 bump）
APK_LATEST_VERSION_CODE = 1
APK_LATEST_VERSION_NAME = "1.0.4"
APK_DOWNLOAD_PATH       = "/static-app/apk/BrainReport-LUKE.apk"
APK_RELEASE_NOTES = (
    "v1.1.2 更新內容：\n"
    "・修正小米(MIUI)裝置更新彈窗重複問題\n"
    "・改用瀏覽器下載 APK，安裝更順暢\n"
    "\n"
    "v1.0.4 歷史更新：\n"
    "・更換 App 圖示\n"
    "\n"
    "v1.0.3 歷史更新：\n"
    "・App 名稱更新為「路加腦波檢測系統」\n"
    "\n"
    "v1.0.2 歷史更新：\n"
    "・付款後自動連線腦波儀（含權限請求）\n"
    "・若腦波儀未就緒，跳出友善對話框（重連／繼續／稍後）\n"
    "・10 秒無訊號保護，避免空跡計時 3 分鐘\n"
    "・修正藍牙 callback 為 null 時的崩潰\n"
    "\n"
    "v1.0.1 歷史更新：\n"
    "・修正點報告無法付款問題\n"
    "・新增「立即付款」大按鈕，免掃 QR Code 也能付\n"
    "・WebView 自動載入最新前端版本\n"
    "・新增 App 自動更新功能"
)

from app.core import models  # 必須在 create_all 前 import，讓 SQLAlchemy 發現所有表
from app.core.database import Base, engine, check_connection
from app.routers import sessions, payments, monitor, companies, client_view, contact_requests, subjects, auth, analysis, report_gen, eeg, reports, share_rules

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
app.include_router(contact_requests.router)
app.include_router(subjects.router)
app.include_router(auth.router)
app.include_router(analysis.router)
app.include_router(report_gen.router)
app.include_router(eeg.router)
app.include_router(reports.router)
app.include_router(share_rules.router)


def _friendly_error_html(title: str, message: str, hint: str = "") -> str:
    """通用的友善錯誤頁面 HTML（手機/平板開到 404 看了不會慌）

    使用 color-scheme: light only 強制套用淺色配色，
    避免在使用者開啟系統深色模式時，整張卡片被瀏覽器染黑造成視覺錯亂。
    """
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light only">
  <meta name="supported-color-schemes" content="light">
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light; }}
    html, body {{ background-color: #667eea !important; color: #333; }}
    body{{margin:0;display:flex;justify-content:center;align-items:center;
         min-height:100vh;background:linear-gradient(135deg,#667eea,#764ba2) !important;
         font-family:'Microsoft JhengHei','Helvetica',sans-serif;padding:20px;}}
    .card{{background:white !important;color:#1a1a2e;border-radius:24px;padding:36px 28px;
           box-shadow:0 12px 48px rgba(0,0,0,0.25);max-width:380px;width:100%;text-align:center;}}
    .icon{{font-size:64px;margin-bottom:12px;}}
    h2{{color:#1a1a2e !important;font-size:22px;margin:0 0 10px;}}
    p{{color:#555 !important;font-size:15px;line-height:1.7;margin:6px 0;}}
    .hint{{background:#fff8e1 !important;color:#7a4f00 !important;
           border-left:4px solid #ffb300;
           text-align:left;border-radius:10px;padding:12px 14px;margin-top:18px;
           font-size:13px;line-height:1.6;}}
    a.btn{{display:block;background:#667eea !important;color:white !important;text-decoration:none;
           border-radius:12px;padding:14px;font-size:15px;font-weight:600;
           margin-top:18px;box-shadow:0 4px 14px rgba(102,126,234,0.4);}}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">⚠️</div>
    <h2>{title}</h2>
    <p>{message}</p>
    {f'<div class="hint">{hint}</div>' if hint else ''}
    <a class="btn" href="/app">📱 返回 App 重新開始</a>
  </div>
</body>
</html>"""


def _order_not_found_html(order_id: str) -> str:
    return _friendly_error_html(
        title="訂單已過期",
        message=f"訂單 <code>{order_id}</code> 不存在或已逾時，可能是 15 分鐘內沒完成付款。",
        hint="💡 請回到 App 重新選擇報告類型，會自動建立新訂單。",
    )


@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    """全域 404/HTTP 例外：
    - 「明確要 JSON 的客戶端」（App/前端 fetch API，Accept 有 application/json
      但沒 text/html）→ 回原本 JSON 格式
    - 其他（手機瀏覽器、PayUni 跳轉、Android WebView 等）→ 友善 HTML 頁面
      ⚠️ 這非常重要：PayUni 付款完跳轉回我們時若打到 404，使用者本來會看到
         22 bytes 的 {"detail":"Not Found"}，現在會看到「返回 App」按鈕的友善頁面
    """
    accept = request.headers.get("accept", "")
    path   = request.url.path
    wants_json = "application/json" in accept and "text/html" not in accept
    is_api_only_path = (
        path.startswith("/api/")
        and not path.startswith("/api/v1/payments/")  # 付款相關回應要被使用者看到
    ) or path.startswith("/healthz") or path.startswith("/health") or path.startswith("/reports/")

    if wants_json or is_api_only_path:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    if exc.status_code == 404:
        html = _friendly_error_html(
            title="找不到此頁面",
            message=f"路徑 <code>{path}</code> 不存在。",
            hint="💡 您可能掃到舊版 QR Code 或舊連結。請回到 App 重新建立訂單；若您剛完成付款，請直接回 App，3 秒內會自動確認。",
        )
        return HTMLResponse(html, status_code=404)
    return HTMLResponse(_friendly_error_html(
        title=f"錯誤 {exc.status_code}",
        message=str(exc.detail or "發生未預期的錯誤"),
    ), status_code=exc.status_code)


@app.on_event("startup")
async def startup():
    """
    啟動時嘗試初始化資料庫；若連不到 DB 也不要讓服務掛掉，
    這樣 / 與 /app（前端原型）等不依賴 DB 的端點仍可服務 healthcheck，
    避免 Railway Healthcheck 失敗。
    """
    try:
        Base.metadata.create_all(bind=engine)
        ok = check_connection()
        print(f"[DB] {'OK' if ok else 'ERROR'}")
    except Exception as e:
        # 不 raise，讓 healthcheck 通過；DB 相關 endpoint 失敗時各自回 5xx
        print(f"[DB] startup skipped: {e}")


@app.get("/")
def root():
    return {"status": "ok", "message": "腦波報告系統 API 運行中"}

@app.get("/healthz")
def healthz():
    """Railway Healthcheck 專用，永遠回 200，不依賴 DB"""
    return {"ok": True}

@app.get("/dashboard", response_class=FileResponse)
def dashboard():
    """即時監控儀表板"""
    return FileResponse("dashboard.html")

@app.get("/share-portal")
def share_portal():
    """分潤規則 & 總覽管理入口（加盟商管理者用，需 admin 登入）"""
    if not _STATIC_APP_DIR:
        return JSONResponse({"error": "static-app directory not found"}, status_code=500)
    portal_path = os.path.join(_STATIC_APP_DIR, "share_portal.html")
    if not os.path.exists(portal_path):
        return JSONResponse({"error": f"share_portal.html not found at {portal_path}"}, status_code=500)
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma":        "no-cache",
        "Expires":       "0",
    }
    return FileResponse(portal_path, media_type="text/html", headers=headers)

@app.get("/app")
def prototype_app():
    """前端 App 原型（手機瀏覽器/Android WebView 共用）

    回傳時加上 no-cache 標頭，確保 WebView 每次都拿到最新 HTML
    （加盟商手機上的 App 因此無需重灌就能取得最新版面/邏輯）
    """
    if not _STATIC_APP_DIR:
        return JSONResponse({"error": "static-app directory not found", "checked": _CANDIDATES}, status_code=500)
    proto_path = os.path.join(_STATIC_APP_DIR, "app_prototype.html")
    if not os.path.exists(proto_path):
        return JSONResponse({"error": f"app_prototype.html not found at {proto_path}"}, status_code=500)
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma":        "no-cache",
        "Expires":       "0",
        "X-App-Version": APP_HTML_VERSION,
    }
    return FileResponse(proto_path, media_type="text/html", headers=headers)


@app.get("/api/v1/app/version")
def app_version(request: Request):
    from app.core.config import settings
    """
    Android App 啟動時呼叫，用來：
    1. 顯示前端版本（HTML 變更 → 自動更新無需動作）
    2. 比對 APK versionCode → 若有新版會跳「立即更新」對話框

    要發新 APK 時：
       a) 在 Android Studio bump versionCode → 編 release APK
       b) 把 APK 放到 後端系統/static-app/apk/onlineReport-latest.apk
       c) main.py 把 APK_LATEST_VERSION_CODE bump 上去
       d) git push → Railway 自動部署 → 加盟商開 App 自動收到更新提示
    """
    # 動態組出對外可用的下載 URL
    base = (settings.PUBLIC_BASE_URL
            or os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
            or str(request.base_url).rstrip("/"))
    if base and not base.startswith("http"):
        base = f"https://{base}"
    apk_url = f"{base.rstrip('/')}/download/apk" if base else ""

    # 確認 APK 檔案實際存在（不存在就不公告，避免下載 404）
    apk_exists = False
    if _STATIC_APP_DIR:
        apk_local = os.path.join(_STATIC_APP_DIR, "apk", "BrainReport-LUKE.apk")
        apk_exists = os.path.exists(apk_local)

    return {
        "html_version":        APP_HTML_VERSION,
        "server_time":         int(time.time()),
        "min_apk_version":     1,
        "latest_apk_version":  APK_LATEST_VERSION_CODE if apk_exists else 1,
        "latest_apk_version_name": APK_LATEST_VERSION_NAME,
        "apk_download_url":    apk_url if apk_exists else "",
        "release_notes":       APK_RELEASE_NOTES,
    }

@app.get("/download/apk/qr")
def download_apk_qr(request: Request):
    """產生 APK 下載連結的 QR Code 圖片（PNG），可直接放在說明文件或網頁上讓加盟商掃描安裝。"""
    import qrcode, io
    from app.core.config import settings
    base = (settings.PUBLIC_BASE_URL
            or os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
            or str(request.base_url).rstrip("/"))
    if base and not base.startswith("http"):
        base = f"https://{base}"
    url = f"{base.rstrip('/')}/download/apk"

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    from fastapi.responses import StreamingResponse
    return StreamingResponse(buf, media_type="image/png",
        headers={"Content-Disposition": "inline; filename=BrainReport-LUKE-install-qr.png",
                 "Cache-Control": "no-cache"})


@app.get("/download/apk")
def download_apk():
    """
    APK 下載端點（強制設 Content-Type + Content-Disposition）。
    手機瀏覽器遇到 .apk 時常常把它當 ZIP 解壓，加這個端點就能確保：
      - Content-Type: application/vnd.android.package-archive
      - Content-Disposition: attachment; filename=onlineReport-latest.apk
    讓手機正確辨識並提示安裝。
    """
    if not _STATIC_APP_DIR:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="APK not found")
    apk_path = os.path.join(_STATIC_APP_DIR, "apk", "BrainReport-LUKE.apk")
    if not os.path.exists(apk_path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="APK not found")
    return FileResponse(
        apk_path,
        media_type="application/vnd.android.package-archive",
        filename="BrainReport-LUKE.apk",
        headers={
            "Content-Disposition": "attachment; filename=BrainReport-LUKE.apk",
            "Cache-Control": "no-cache",
        }
    )


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
        return HTMLResponse(_order_not_found_html(order_id), status_code=404)

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
        "MerchantID":        settings.ECPAY_MERCHANT_ID or "3002607",  # 3002607 為綠界官方公開測試特店（搭配下方 HashKey/IV）
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



@app.get("/pay/payuni/{order_id}")
def pay_payuni(order_id: str):
    """
    顧客掃描 PayUni QR Code 後開啟此頁面，自動 POST 到 PayUni 付款導頁
    """
    from fastapi.responses import HTMLResponse
    from app.routers.payments import _payment_store
    from app.services import payuni
    from app.core.config import settings

    order = _payment_store.get(order_id)
    if not order:
        return HTMLResponse(_order_not_found_html(order_id), status_code=404)

    base = settings.PUBLIC_BASE_URL or os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    if base and not base.startswith("http"):
        base = f"https://{base}"
    base = base.rstrip("/")
    notify_url = f"{base}/api/v1/payments/payuni/notify"
    return_url = f"{base}/api/v1/payments/payuni/return/{order_id}"

    try:
        form = payuni.build_create_form(
            order_id     = order_id[:20],
            amount       = int(order["amount"]),
            product_desc = order["trade_desc"],
            buyer_email  = order.get("notify_email", ""),
            return_url   = return_url,
            notify_url   = notify_url,
            customer_url = return_url,
        )
    except Exception as e:
        return HTMLResponse(f"<h2>PayUni 初始化失敗</h2><pre>{e}</pre>", status_code=500)

    fields_html = "\n".join(
        f'    <input type="hidden" name="{k}" value="{v}">'
        for k, v in form["fields"].items()
    )
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>跳轉至 PayUni 統一金流付款頁...</title>
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
    <div class="msg">正在跳轉至統一金流付款頁，請稍候...</div>
    <form id="f" method="POST" action="{form['url']}">
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
    from app.routers.payments import _provider
    provider = _provider()
    pay_url = f"https://{base}/pay/{provider}/{order_id}" if base else f"/pay/{provider}/{order_id}"
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
    <a class="btn" href="{pay_url}">💳 前往統一付款頁</a>
    <div class="footer">🔒 由統一金流 PayUni 提供安全付款服務</div>
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
