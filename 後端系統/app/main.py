from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os

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

# 掛載靜態 PDF 目錄（本地開發用）
os.makedirs("reports", exist_ok=True)
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

# 掛載前端原型資料夾（QR Code 圖片等靜態資源）
# 後端系統的上一層即專案根目錄，前端原型在同一層
_BACKEND_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 後端系統/
_PROJECT_DIR  = os.path.dirname(_BACKEND_DIR)                                  # AutomaticDetection/
_PROTOTYPE_DIR = os.path.join(_PROJECT_DIR, "前端原型")
if os.path.isdir(_PROTOTYPE_DIR):
    app.mount("/static-app", StaticFiles(directory=_PROTOTYPE_DIR), name="static-app")

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
    proto_path = os.path.join(_PROTOTYPE_DIR, "app_prototype.html")
    return FileResponse(proto_path, media_type="text/html")

@app.get("/pay/{order_id}")
def pay_page(order_id: str):
    """付款短連結頁面：開啟後顯示訂單 QR Code"""
    from fastapi.responses import HTMLResponse
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>腦波報告付款</title>
  <style>
    body{{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;
         background:#f5f7fa;font-family:'Microsoft JhengHei',sans-serif;}}
    .card{{background:white;border-radius:20px;padding:32px 24px;box-shadow:0 8px 32px rgba(0,0,0,0.12);
           max-width:360px;width:90%;text-align:center;}}
    .logo{{font-size:32px;margin-bottom:8px;}}
    h2{{color:#1a1a2e;font-size:18px;margin:0 0 4px;}}
    .order-id{{font-size:12px;color:#aaa;margin-bottom:20px;}}
    .qr-wrap{{background:#f8f9ff;border-radius:16px;padding:20px;margin-bottom:16px;}}
    img{{width:200px;height:200px;border-radius:12px;}}
    .hint{{font-size:12px;color:#888;margin-bottom:20px;}}
    .status{{background:#fff3e0;border-radius:10px;padding:10px;font-size:13px;color:#e65100;}}
    .footer{{font-size:11px;color:#ccc;margin-top:16px;}}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">🧠</div>
    <h2>腦波報告付款</h2>
    <div class="order-id">訂單號：{order_id}</div>
    <div class="qr-wrap">
      <img src="/static-app/qr_test.png" alt="付款 QR Code">
    </div>
    <div class="hint">請使用支援統一金流的 App 掃描 QR Code 完成付款</div>
    <div class="status">⏱️ 請於 15 分鐘內完成付款</div>
    <div class="footer">🔒 由統一金流提供安全金流服務</div>
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
