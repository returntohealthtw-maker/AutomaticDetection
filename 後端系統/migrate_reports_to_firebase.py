"""
把 Railway 已完成的報告 metadata（含 GCS 基礎路徑）同步到 Firebase
"""
import sys, io, json, requests, urllib3, time
from urllib.parse import urlparse, unquote
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()

FIREBASE_API_KEY  = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
FIREBASE_EMAIL    = "migration@returntohealthtw.com"
FIREBASE_PASSWORD = "MigrateEEG@2026"
CF_BASE      = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
RAILWAY_BASE = "https://backend-production-2da61.up.railway.app"
GCS_BUCKET   = "brainwave-child-reports"

def strip_signed_params(url):
    """去除 GCS Signed URL 的簽名參數，回傳合法的 encoded URI"""
    if not url:
        return None, None
    from urllib.parse import urlparse, unquote, quote
    parsed = urlparse(url)
    # 先 unquote 再重新 quote，確保路徑編碼正確（處理資料庫中損壞的中文編碼）
    try:
        decoded = unquote(parsed.path, errors='replace')
        encoded_path = quote(decoded, safe='/')
        base_url = f"{parsed.scheme}://{parsed.netloc}{encoded_path}"
    except Exception:
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    # GCS 相對路徑（供 extraData 存參考）
    raw_path = unquote(parsed.path, errors='replace')
    prefix = f"/{GCS_BUCKET}/"
    gcs_path = raw_path[len(prefix):] if raw_path.startswith(prefix) else raw_path.lstrip("/")
    return gcs_path, base_url

def map_report_type(rt):
    mapping = {"adult": "adult_vip", "child": "child_vip", "parent_child": "parent_child",
               "marital": "marital", "teen": "child_vip"}
    return mapping.get(rt, "session")

# ── 登入 ──────────────────────────────────────────────────────────────────────
r = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
    json={"email": FIREBASE_EMAIL, "password": FIREBASE_PASSWORD, "returnSecureToken": True},
    verify=False, timeout=15)
token = r.json()["idToken"]
fb_hdrs = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("✅ Firebase 登入成功")

rs = requests.Session(); rs.verify = False
rw_tok = rs.post(f"{RAILWAY_BASE}/api/v1/auth/login",
                 json={"phone": "0900000000", "password": "admin123"}, timeout=15).json().get("token", "")
rs.headers["Authorization"] = "Bearer " + rw_tok
print("✅ Railway 登入成功")

# ── 讀 migration_report.json 取得 session map ──────────────────────────────────
with open("migration_report.json", encoding="utf-8") as f:
    report = json.load(f)

session_map = {}
for src in report.get("sources", []):
    if "Railway" in src["label"]:
        session_map = src.get("session_map", {})
        break

print(f"📋 共 {len(session_map)} 個 session\n")

ok = 0; skip = 0; fail = 0

for rw_sid_str, fb_sid in session_map.items():
    rw_sid = int(rw_sid_str)

    # 取 Railway session stats（含 report_url / report_status）
    sr = rs.get(f"{RAILWAY_BASE}/api/v1/eeg/sessions/{rw_sid}/stats", timeout=20).json()
    status    = sr.get("report_status")
    pdf_url   = sr.get("report_url")
    rtype_raw = sr.get("report_type") or "adult"

    if status != "completed" or not pdf_url:
        print(f"  ⏭ session {rw_sid}: status={status}，跳過")
        skip += 1
        continue

    gcs_path, base_url = strip_signed_params(pdf_url)
    report_type = map_report_type(rtype_raw)

    eeg = sr.get("eeg_stats", {}) or {}
    bands = eeg.get("bands_avg") or {}
    def bv(k): return float(bands.get(k) or 0)
    total = sum(bv(k) for k in ["delta","theta","low_alpha","high_alpha","low_beta","high_beta","low_gamma","high_gamma"]) or 1
    def pct(v): return round(v / total * 100, 2)

    payload = {
        "sessionId":    fb_sid,
        "reportType":   report_type,
        "pdfUrl":       base_url,         # 不帶簽名的永久基礎 URL
        "sourceApp":    "railway_migration",
        "alphaAvg":     pct(bv("low_alpha") + bv("high_alpha")),
        "betaAvg":      pct(bv("low_beta")  + bv("high_beta")),
        "thetaAvg":     pct(bv("theta")),
        "deltaAvg":     pct(bv("delta")),
        "attentionAvg": float(eeg.get("attention_percentage") or 0),
        "extraData":    {"gcsBucket": GCS_BUCKET, "gcsPath": gcs_path,
                         "railwaySessionId": rw_sid},
    }

    r2 = requests.post(f"{CF_BASE}/reports/store",
                       json=payload, headers=fb_hdrs, verify=False, timeout=20)
    if r2.status_code in (200, 201):
        ok += 1
        print(f"  ✅ session {rw_sid} → {fb_sid[:8]}... 報告已同步 ({gcs_path[:50]})")
    else:
        fail += 1
        print(f"  ❌ session {rw_sid}: {r2.status_code} {r2.text[:100]}")

    time.sleep(0.1)

print(f"\n完成！成功 {ok}，跳過 {skip}，失敗 {fail}")
