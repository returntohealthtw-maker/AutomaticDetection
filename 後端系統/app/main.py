from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
import urllib.parse
import time

APP_HTML_VERSION = "2026.06.28.01"  # 每次改 HTML/JS 都更新這個

# Android APK 版本（要跟 app/build.gradle versionCode 對應；發新 APK 才 bump）
APK_LATEST_VERSION_CODE = 26
APK_LATEST_VERSION_NAME = "1.2.5"
APK_DOWNLOAD_PATH       = "/static-app/apk/BrainReport-LUKE.apk"
APK_RELEASE_NOTES = (
    "v1.1.9 更新內容：\n"
    "・修正所有人 MBTI 結果都一樣的嚴重 bug\n"
    "  ◎ 原本 Java 端把 8 個 ThinkGear 頻段壓成 5 個（高低 alpha/beta/gamma 平均後遺失）\n"
    "  ◎ 加上 bandTo100 log 壓縮把腦波拉到窄區，個體差異被抹平\n"
    "  ◎ JS 端 la=ha=0.5*alpha 自我抵消 → 多數人卡在 INFP / INFJ\n"
    "・修法：Android 多送 raw_lalpha / raw_halpha 等 8 個原始頻段\n"
    "  ◎ JS 改用對數軸 sigmoid 計算，個體差異有效保留\n"
    "\n"
    "v1.1.8 更新內容：\n"
    "・修正腦波儀健康檢查介面：明明連線中卻顯示「藍牙未開啟 / 0 台配對」\n"
    "  ◎ getBleDebugInfo 多回傳 paired / ble_connected / battery_readable 旗標\n"
    "  ◎ 前端反向推論：電量讀得到 ⇒ 藍牙必為開啟（修正 OEM isEnabled 偶爾誤報）\n"
    "・健康檢查的「腦波儀連線」判讀升級為多源即時跡象判斷\n"
    "\n"
    "v1.1.7 更新內容：\n"
    "・🩺 修正腦波儀健康檢查「明明已連線卻收 0 筆」嚴重 bug\n"
    "  原因：startStreamingEeg 重複 Connect 破壞既有 GATT 通道\n"
    "・健康檢查結果頁加入「工程診斷資料」明確顯示 BLE callback 次數\n"
    "・新增 getStreamingDiag bridge 方法供診斷使用\n"
    "\n"
    "v1.1.6 更新內容：\n"
    "・修正平板橫向 ↔ 直向切換時重複跳出『發現新版本』對話框\n"
    "・修正旋轉螢幕後必須重新登入的問題（同時持久化登入狀態到 Android 端）\n"
    "・腦波儀健康檢查：電量讀不到不再阻擋開始檢測（韌體不提供電量是正常情況）\n"
    "\n"
    "v1.1.5 更新內容：\n"
    "・升級流程加入「升級進行中」追蹤對話框\n"
    "・點立即更新後會持續顯示『下載中』狀態，不再讓加盟商困惑\n"
    "・新增「已完成安裝」「再次開啟下載」操作按鈕\n"
    "・包含 v1.1.4 全部修正（小米 A15 電量顯示等）\n"
    "\n"
    "v1.1.4 更新內容：\n"
    "・修正小米 Android 15 / HyperOS 2 腦波儀電量無法顯示問題\n"
    "・改用 BluetoothManager API（getDefaultAdapter 已淘汰）\n"
    "・新增藍牙診斷工具（長按右上角 🧠 圖示 1.5 秒）\n"
    "・電量斷線時顯示『連線中』而非『--』，操作更直覺\n"
    "\n"
    "v1.1.3 更新內容：\n"
    "・補上 ACCESS_FINE_LOCATION 權限（Android 6~11 BLE 必須）\n"
    "・電量讀取加入 30 分鐘快取機制，斷線時仍能顯示\n"
    "・修正『腦波儀測試』模式可能污染正式檢測流程的 bug\n"
    "・MBTI、腦波頻帶說明文字補足，避免顯示過短\n"
    "\n"
    "v1.1.2 歷史更新：\n"
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
from app.routers import sessions, payments, monitor, companies, client_view, contact_requests, subjects, auth, analysis, report_gen, eeg, reports, share_rules, report_app_api, parent_child

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

    # 掛載成人報告 React App（本機版，不再依賴 Vercel）
    _REPORT_APP_DIR = os.path.join(_STATIC_APP_DIR, "report-app")
    if os.path.isdir(_REPORT_APP_DIR):
        app.mount("/report-app", StaticFiles(directory=_REPORT_APP_DIR, html=True), name="report-app")
        print(f"[report-app] OK 本機成人 React App 掛載：{_REPORT_APP_DIR}")
        # 雙重保障：Vite build 產生的 index.html 使用絕對路徑 /assets/... 
        # 當掛載在子路徑 /report-app/ 時，/assets/ 路徑會 404 導致 React 無法啟動。
        # 除了將 index.html 改為相對路徑外，此處也額外掛載 /assets 作為防護。
        _REPORT_ASSETS_DIR = os.path.join(_REPORT_APP_DIR, "assets")
        if os.path.isdir(_REPORT_ASSETS_DIR):
            try:
                app.mount("/assets", StaticFiles(directory=_REPORT_ASSETS_DIR), name="report-app-assets")
                print(f"[report-app] OK /assets 備援掛載：{_REPORT_ASSETS_DIR}")
            except Exception as _e:
                print(f"[report-app] /assets 掛載跳過（已被其他路由佔用）：{_e}")

    # 掛載兒童報告 React App（本機版，與成人版並列）
    _CHILD_REPORT_APP_DIR = os.path.join(_STATIC_APP_DIR, "child-report-app")
    if os.path.isdir(_CHILD_REPORT_APP_DIR):
        app.mount("/child-report-app", StaticFiles(directory=_CHILD_REPORT_APP_DIR, html=True), name="child-report-app")
        print(f"[child-report-app] OK 本機兒童 React App 掛載：{_CHILD_REPORT_APP_DIR}")

# 掛載親子報告靜態資源（封面圖 + 生成圖片）
_PC_DATA_CANDIDATES = [
    "/app/parent_child_data",                          # Docker / Railway
    os.path.join(_BACKEND_DIR, "parent_child_data"),   # 本地開發
]
_PC_DATA_DIR = next((p for p in _PC_DATA_CANDIDATES if os.path.isdir(p)), None)
if _PC_DATA_DIR:
    app.mount("/parent-child/static", StaticFiles(directory=_PC_DATA_DIR), name="parent-child-static")
    print(f"[parent-child] OK 靜態資源掛載：{_PC_DATA_DIR}")
else:
    # 首次執行自動建立目錄
    _new_pc_dir = os.path.join(_BACKEND_DIR, "parent_child_data")
    os.makedirs(os.path.join(_new_pc_dir, "report_images"), exist_ok=True)
    app.mount("/parent-child/static", StaticFiles(directory=_new_pc_dir), name="parent-child-static")
    print(f"[parent-child] 已建立並掛載靜態資源目錄：{_new_pc_dir}")

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
app.include_router(report_app_api.router)
app.include_router(parent_child.router)


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


def _run_lightweight_migrations():
    """新增缺失欄位（SQLAlchemy create_all 不會 ALTER 既存表）

    冪等：每次都檢查欄位是否存在，不存在才 ADD COLUMN。
    支援 SQLite / PostgreSQL / MySQL（檢查 information_schema 或 PRAGMA）。
    """
    from sqlalchemy import inspect, text
    insp = inspect(engine)

    def has_column(table: str, col: str) -> bool:
        try:
            cols = [c["name"] for c in insp.get_columns(table)]
            return col in cols
        except Exception:
            return False

    pending = []
    # sessions – new columns added over time
    if not has_column("sessions", "subject_id"):
        pending.append("ALTER TABLE sessions ADD COLUMN subject_id INTEGER NULL")
    if not has_column("sessions", "consultant_name"):
        pending.append("ALTER TABLE sessions ADD COLUMN consultant_name VARCHAR(50) NULL")
    if not has_column("sessions", "company_id"):
        pending.append("ALTER TABLE sessions ADD COLUMN company_id INTEGER NULL")
    if not has_column("sessions", "report_audience"):
        pending.append("ALTER TABLE sessions ADD COLUMN report_audience VARCHAR(20) DEFAULT 'student'")
    if not has_column("sessions", "failure_reason"):
        pending.append("ALTER TABLE sessions ADD COLUMN failure_reason VARCHAR(100) NULL")
    # reports – new columns added over time
    if not has_column("reports", "subject_id"):
        pending.append("ALTER TABLE reports ADD COLUMN subject_id INTEGER NULL")
    if not has_column("reports", "consultant_name"):
        pending.append("ALTER TABLE reports ADD COLUMN consultant_name VARCHAR(50) NULL")
    if not has_column("reports", "qr_token"):
        pending.append("ALTER TABLE reports ADD COLUMN qr_token VARCHAR(64) NULL")
    if not has_column("reports", "client_summary"):
        pending.append("ALTER TABLE reports ADD COLUMN client_summary TEXT NULL")
    if not has_column("reports", "notify_email"):
        pending.append("ALTER TABLE reports ADD COLUMN notify_email VARCHAR(200) NULL")
    if not has_column("reports", "email_sent"):
        pending.append("ALTER TABLE reports ADD COLUMN email_sent INTEGER DEFAULT 0")
    if not has_column("reports", "talent_report_kind"):
        pending.append("ALTER TABLE reports ADD COLUMN talent_report_kind VARCHAR(32) NULL")
    if not has_column("reports", "error_message"):
        pending.append("ALTER TABLE reports ADD COLUMN error_message TEXT NULL")
    if not has_column("sessions", "needs_retest"):
        pending.append("ALTER TABLE sessions ADD COLUMN needs_retest BOOLEAN DEFAULT FALSE")
    if not has_column("sessions", "retest_reason"):
        pending.append("ALTER TABLE sessions ADD COLUMN retest_reason VARCHAR(200) NULL")
    if not has_column("reports", "line_user_id"):
        pending.append("ALTER TABLE reports ADD COLUMN line_user_id VARCHAR(100) NULL")
    if not has_column("reports", "line_sent"):
        pending.append("ALTER TABLE reports ADD COLUMN line_sent INTEGER DEFAULT 0")
    if not has_column("reports", "completed_at"):
        pending.append("ALTER TABLE reports ADD COLUMN completed_at TIMESTAMP NULL")
    # firebase_sync_log 表（若不存在則由 SQLAlchemy create_all 建立，這裡補保護性欄位檢查）
    if not has_column("firebase_sync_log", "id"):
        # 整張表不存在，用 create_all 建立（Base.metadata.create_all 已在啟動時呼叫）
        pass
    # eeg_captures – BrainDNA 算術平均 MBTI 欄位
    if not has_column("eeg_captures", "mbti_la"):
        pending.append("ALTER TABLE eeg_captures ADD COLUMN mbti_la INTEGER NULL")
    if not has_column("eeg_captures", "mbti_theta"):
        pending.append("ALTER TABLE eeg_captures ADD COLUMN mbti_theta INTEGER NULL")
    # sessions – 逐秒原始腦波陣列（180 筆 × 8 頻段，JSON 格式永久保存）
    if not has_column("sessions", "raw_arrays_json"):
        pending.append("ALTER TABLE sessions ADD COLUMN raw_arrays_json TEXT NULL")
    # sessions – BrainDNA 計算結果（與 Firebase 欄位名稱、格式完全一致）
    if not has_column("sessions", "mind_stress"):
        pending.append("ALTER TABLE sessions ADD COLUMN mind_stress INTEGER NULL")
    if not has_column("sessions", "mind_balance"):
        pending.append("ALTER TABLE sessions ADD COLUMN mind_balance INTEGER NULL")
    if not has_column("sessions", "mind_energy"):
        pending.append("ALTER TABLE sessions ADD COLUMN mind_energy INTEGER NULL")
    if not has_column("sessions", "mind_color"):
        pending.append("ALTER TABLE sessions ADD COLUMN mind_color INTEGER NULL")
    if not has_column("sessions", "mbti"):
        pending.append("ALTER TABLE sessions ADD COLUMN mbti VARCHAR(4) NULL")
    if not has_column("sessions", "bagua"):
        pending.append("ALTER TABLE sessions ADD COLUMN bagua VARCHAR(20) NULL")
    if not has_column("sessions", "overall_score"):
        pending.append("ALTER TABLE sessions ADD COLUMN overall_score INTEGER NULL")

    if "bdna_mode" not in cols:
        pending.append("ALTER TABLE sessions ADD COLUMN bdna_mode VARCHAR(40) NULL")

    if "firebase_session_id" not in cols:
        pending.append("ALTER TABLE sessions ADD COLUMN firebase_session_id VARCHAR(100) NULL")

    if not pending:
        print("[DB-MIGRATE] all columns up-to-date, nothing to do")
        return

    with engine.connect() as conn:
        for sql in pending:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"[DB-MIGRATE] OK {sql}")
            except Exception as e:
                print(f"[DB-MIGRATE] WARN {sql} -> {e}")


async def _startup_self_audit():
    """啟動後驗證關鍵靜態資源路徑，防止 React App 因絕對路徑導致 JS 404。

    已知問題：Vite build 預設產生 /assets/... 絕對路徑，掛載在 /report-app/ 時
    瀏覽器會找不到 JS bundle，React 永遠不啟動。
    修法：index.html 改用 ./assets/ 相對路徑，並在此驗證。
    """
    import asyncio
    await asyncio.sleep(5)
    try:
        static_dir = _STATIC_APP_DIR
        for app_dir_name in ("report-app", "child-report-app"):
            idx = os.path.join(static_dir, app_dir_name, "index.html")
            if not os.path.isfile(idx):
                continue
            with open(idx, "r", encoding="utf-8") as f:
                content = f.read()
            # 偵測是否使用錯誤的絕對路徑（如 src="/assets/... 而非 ./assets/）
            import re as _re
            bad_patterns = _re.findall(r'src="/assets/[^"]+\.js"', content)
            if bad_patterns:
                print(f"[AUDIT-WARN] {app_dir_name}/index.html 含錯誤絕對路徑: {bad_patterns}")
                print(f"[AUDIT-WARN] React App 在 headless 模式下將無法啟動！請改為 ./assets/ 相對路徑。")
            else:
                print(f"[AUDIT-OK] {app_dir_name}/index.html 靜態資源路徑正確")
    except Exception as e:
        print(f"[startup-audit] 路徑檢查失敗（無害）: {e}")


async def _reset_orphan_generating_reports():
    """啟動後 10 秒，把所有卡在 generating/pending 的 Report 標記為 failed。

    產生原因：Railway 重新部署時 headless_renderer._active_jobs 記憶體清空，
    在途的 Playwright job 消失，但 DB 的 Report 仍停留在 generating。
    管理員在 '報告管理 → 生成監看' 看不到進度，點重新生成也無效。

    修法：啟動 10 秒後掃一次，超過 5 分鐘沒更新的 generating 報告 → failed，
    讓管理員在 '報告管理 → 檢測 ↔ 報告' 看到 failed 並點 '重新生成'。
    """
    import asyncio
    await asyncio.sleep(10)   # 讓 DB 連線初始化完成
    try:
        from app.core.database import SessionLocal
        from app.core import models as _M
        cutoff = time.time() - 5 * 60   # 5 分鐘前建立的才算「孤兒」
        with SessionLocal() as db:
            stuck = db.query(_M.Report).filter(
                _M.Report.status.in_(["generating", "pending"]),
            ).all()
            reset_count = 0
            for rep in stuck:
                # 只重設「建立超過 5 分鐘」的（剛剛才建立的可能真的在跑）
                created = rep.completed_at  # 還沒完成時 completed_at 為 None
                # 用 report_id 估時間（auto-increment，約可推算）
                # 實際上用 created_at 最準，但 Report 可能沒有這欄
                # 直接標記所有 generating/pending — 伺服器剛啟動，任何未完成的都是孤兒
                rep.status = "failed"
                reset_count += 1
            db.commit()
            if reset_count:
                print(f"[startup] 已重設 {reset_count} 筆孤兒 generating/pending 報告 → failed。"
                      f"管理員可在「報告管理 → 檢測↔報告」點「重新生成」。")
    except Exception as e:
        print(f"[startup] 重設孤兒報告失敗（無害）：{e}")


@app.on_event("startup")
async def startup():
    """
    啟動時嘗試初始化資料庫；若連不到 DB 也不要讓服務掛掉，
    這樣 / 與 /app（前端原型）等不依賴 DB 的端點仍可服務 healthcheck，
    避免 Railway Healthcheck 失敗。
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[DB] create_all skipped: {e}")
    try:
        _run_lightweight_migrations()
        ok = check_connection()
        print(f"[DB] {'OK' if ok else 'ERROR'}")
    except Exception as e:
        print(f"[DB] migrations skipped: {e}")

    # ── 啟動自我審查：驗證關鍵靜態資源路徑 ────────────────────────────────
    import asyncio
    asyncio.create_task(_startup_self_audit())

    # ── 重啟後自動修復孤兒報告 ────────────────────────────────────────────
    asyncio.create_task(_reset_orphan_generating_reports())

    # ── Firebase 同步服務：啟動排程 ──────────────────────────────────────
    try:
        from app.services import firebase_sync as _fb
        if _fb.is_configured():
            print("[Firebase Sync] ✅ 已設定，新報告將自動同步至 Firebase")
            # 啟動 APScheduler：每 5 分鐘掃一次佇列補漏
            try:
                from apscheduler.schedulers.background import BackgroundScheduler
                from app.core.database import SessionLocal as _SL
                _sched = BackgroundScheduler(timezone="Asia/Taipei")
                _sched.add_job(
                    func=lambda: _fb.run_pending_syncs(_SL),
                    trigger="interval",
                    minutes=5,
                    id="firebase_sync_job",
                    replace_existing=True,
                )
                _sched.start()
                print("[Firebase Sync] ⏱ 排程已啟動（每 5 分鐘補漏）")
                # 啟動後立即跑一次，補漏前次重啟時未完成的記錄
                import threading as _thr
                _thr.Thread(
                    target=lambda: _fb.run_pending_syncs(_SL),
                    daemon=True, name="fb-sync-startup"
                ).start()
            except ImportError:
                print("[Firebase Sync] ⚠ APScheduler 未安裝，排程停用（pip install apscheduler）")
            except Exception as _sched_e:
                print(f"[Firebase Sync] ⚠ 排程啟動失敗（無害）: {_sched_e}")
        else:
            print("[Firebase Sync] ⏭ 未設定（FIREBASE_API_KEY / FIREBASE_EMAIL / FIREBASE_PASSWORD），跳過同步")
    except Exception as _fb_e:
        print(f"[Firebase Sync] 初始化失敗（無害）: {_fb_e}")


@app.get("/")
def root():
    return {"status": "ok", "message": "腦波報告系統 API 運行中"}


@app.get("/debug/test-sessions-insert")
def debug_test_sessions_insert():
    """臨時診斷：直接測試 sessions + reports INSERT 是否成功（測試後刪除）"""
    import traceback
    import uuid
    from app.core.database import SessionLocal
    from app.core import models
    db = SessionLocal()
    result = {"step": "start", "error": None}
    try:
        # Step 1: sessions INSERT
        result["step"] = "sessions_insert"
        import time as _t
        now = int(_t.time() * 1000)
        session = models.Session(
            consultant_name="診斷測試", subject_name="診斷測試", subject_birthday="",
            subject_gender="M", subject_age=0, company_id=None, report_type="adult",
            report_audience="student", start_time=now, end_time=now, total_captures=1,
            status=2, failure_reason="diag", created_at=now
        )
        db.add(session)
        db.flush()
        result["session_id"] = session.session_id
        result["step"] = "eeg_capture_insert"
        cap = models.EegCapture(
            session_id=session.session_id, seq_num=0, is_baseline=0,
            captured_at=int(_t.time()), good_signal=0, attention=65, meditation=55,
            delta=30, theta=60, low_alpha=40, high_alpha=35, low_beta=45,
            high_beta=40, low_gamma=20, high_gamma=15, feedback=0
        )
        db.bulk_save_objects([cap])
        result["step"] = "report_insert"
        report = models.Report(
            session_id=session.session_id, status="pending",
            line_user_id=None, qr_token=uuid.uuid4().hex, notify_email=None
        )
        db.add(report)
        db.commit()
        result["report_id"] = report.report_id
        result["step"] = "done"
        result["success"] = True
        # Cleanup: delete the test records
        db.delete(report)
        db.delete(session)
        db.commit()
    except Exception as e:
        db.rollback()
        result["error"] = f"{type(e).__name__}: {str(e)}"
        result["traceback"] = traceback.format_exc()
        result["success"] = False
    finally:
        db.close()
    return result

@app.get("/debug/test-firebase-sync")
async def debug_test_firebase_sync():
    """診斷：直接測試 Firebase 同步認證與連線（不寫 DB）"""
    import traceback
    from app.services import firebase_sync as _fb
    result = {
        "is_configured": _fb.is_configured(),
        "service_key_set": bool(_fb.FIREBASE_SERVICE_KEY),
        "bearer_credentials_set": bool(_fb.FIREBASE_API_KEY and _fb.FIREBASE_SYNC_EMAIL and _fb.FIREBASE_SYNC_PASSWORD),
        "cached_token_set": bool(_fb._cached_token),
    }
    try:
        _fb._refresh_bearer_token()
        result["bearer_refresh"] = "ok"
        result["cached_token_after"] = bool(_fb._cached_token)
    except Exception as e:
        result["bearer_refresh"] = f"ERROR: {e}"
        result["traceback"] = traceback.format_exc()

    # 嘗試建立一個測試 Firebase session（先用 X-Service-Key，再用 Bearer）
    try:
        import httpx
        # Test 1: X-Service-Key
        sk_headers = _fb._get_auth_headers(force_bearer=False)
        async with httpx.AsyncClient(timeout=10.0) as client:
            r_sk = await client.post(
                f"{_fb.FIREBASE_API_BASE}/sessions",
                headers=sk_headers,
                json={"sourceApp": "debug-test", "deviceType": "ThinkGear", "samplingRate": 1,
                      "platform": "android", "metadata": {"railway_session_id": -2, "subject_name": "debug-sk"}},
            )
            result["service_key_post_status"] = r_sk.status_code
            result["service_key_post_body"]   = r_sk.text[:200]

        # Test 2: Bearer Token
        bt_headers = _fb._get_auth_headers(force_bearer=True)
        async with httpx.AsyncClient(timeout=10.0) as client:
            r_bt = await client.post(
                f"{_fb.FIREBASE_API_BASE}/sessions",
                headers=bt_headers,
                json={"sourceApp": "debug-test", "deviceType": "ThinkGear", "samplingRate": 1,
                      "platform": "android", "metadata": {"railway_session_id": -3, "subject_name": "debug-bt"}},
            )
            result["bearer_post_status"] = r_bt.status_code
            result["bearer_post_body"]   = r_bt.text[:200]
    except Exception as e:
        result["firebase_post_error"] = f"{type(e).__name__}: {e}"

    return result


@app.get("/debug/test-firebase-sync-session/{session_id}")
async def debug_test_firebase_sync_session(session_id: int):
    """直接同步指定 session 到 Firebase 並回傳結果（診斷用）"""
    import traceback
    from app.core.database import SessionLocal
    from app.core import models
    from app.services import firebase_sync as _fb

    db = SessionLocal()
    result = {"session_id": session_id}
    try:
        sess = db.query(models.Session).filter(models.Session.session_id == session_id).first()
        if not sess:
            return {"error": "session not found"}
        captures = db.query(models.EegCapture).filter(
            models.EegCapture.session_id == session_id
        ).order_by(models.EegCapture.seq_num).all()
        result["captures_count"] = len(captures)
        result["subject_name"] = sess.subject_name

        ok = await _fb.sync_captures_to_firebase(
            subject_name=sess.subject_name,
            session_id=sess.session_id,
            captures=captures,
        )
        result["sync_ok"] = ok
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        result["traceback"] = traceback.format_exc()
    finally:
        db.close()
    return result
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
    import os
    db_ok = False
    db_detail = ""
    reports_cols = []
    sessions_cols = []
    try:
        from app.core.database import engine
        from sqlalchemy import text as _text, inspect as _inspect
        with engine.connect() as conn:
            conn.execute(_text("SELECT 1"))
        db_ok = True
        # 額外：列出 reports / sessions 表的欄位（用於診斷遷移）
        try:
            insp = _inspect(engine)
            reports_cols = [c["name"] for c in insp.get_columns("reports")]
            sessions_cols = [c["name"] for c in insp.get_columns("sessions")]
        except Exception:
            pass
    except Exception as e:
        db_detail = f"{type(e).__name__}: {str(e)[:300]}"

    # 診斷：確認環境變數是否真的被注入（只顯示長度，不洩漏值）
    env_diag = {
        "DATABASE_URL_len":    len(os.environ.get("DATABASE_URL", "")),
        "PAYUNI_MER_ID_len":   len(os.environ.get("PAYUNI_MER_ID", "")),
        "PAYUNI_HASH_KEY_len": len(os.environ.get("PAYUNI_HASH_KEY", "")),
        "PAYUNI_HASH_IV_len":  len(os.environ.get("PAYUNI_HASH_IV", "")),
        "USE_SQLITE":          os.environ.get("USE_SQLITE", "(not set)"),
    }

    return {
        "api":      "ok",
        "database": "ok" if db_ok else "error",
        "db_detail": db_detail if not db_ok else "",
        "db_url_prefix": str(engine.url)[:40] if not db_ok else "",
        "env_diag": env_diag,
        "reports_cols": reports_cols,
        "sessions_cols": sessions_cols,
    }
