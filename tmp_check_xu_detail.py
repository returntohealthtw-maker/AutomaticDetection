import requests, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = "https://backend-production-2da61.up.railway.app"
r = requests.post(f"{BASE}/api/v1/auth/login", json={"phone":"0900000000","password":"admin123"}, timeout=15)
token = r.json().get("token","")
H = {"Authorization": f"Bearer {token}"}

# 三人的 session IDs（從上次查詢確認）
sessions_info = [
    {"name": "許恩蕊", "session_id": 100, "firebase_id": "f919a5ce-0e4f-46b1-bc6c-e7d905191baa"},
    {"name": "許睿恩", "session_id": 101, "firebase_id": "61b82071-1d82-4d35-8291-2259e18e78c3"},
    {"name": "許允約",  "session_id": 102, "firebase_id": "fc850d83-9ab5-4558-b4cb-04345ae03cb5"},
]

# 查 Railway captures
print("=== Railway DB captures 數量 ===")
for info in sessions_info:
    sid = info["session_id"]
    r2 = requests.get(f"{BASE}/api/v1/sessions/{sid}/captures", headers=H, timeout=15)
    if r2.status_code == 200:
        data = r2.json()
        if isinstance(data, list):
            count = len(data)
        elif isinstance(data, dict):
            count = data.get("total") or data.get("count") or len(data.get("captures",data.get("data",[])))
        else:
            count = "未知格式"
        print(f"  {info['name']} (session {sid}): Railway captures = {count} 筆")
    else:
        print(f"  {info['name']}: HTTP {r2.status_code}")

# Firebase 認證
print("\n=== Firebase EEG 資料驗證 ===")
API_KEY = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
auth_r = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}",
    json={"email":"migration@returntohealthtw.com","password":"MigrateEEG@2026","returnSecureToken":True},
    timeout=15
)
id_token = auth_r.json().get("idToken","")

FB_BASE = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
FH = {"Authorization": f"Bearer {id_token}"}

# 嘗試用 admin endpoint 查 EEG 資料
for info in sessions_info:
    fb_id = info["firebase_id"]
    
    # 嘗試各種可能的端點
    endpoints = [
        f"/eeg/{fb_id}",
        f"/sessions/{fb_id}/eeg",
        f"/admin/sessions/{fb_id}",
        f"/sessions/{fb_id}",
    ]
    
    print(f"\n{info['name']} (firebase_id={fb_id}):")
    for ep in endpoints:
        r3 = requests.get(f"{FB_BASE}{ep}", headers=FH, timeout=10)
        if r3.status_code != 403 and r3.status_code != 404:
            print(f"  {ep}: HTTP {r3.status_code} → {r3.text[:200]}")
        elif r3.status_code == 404:
            print(f"  {ep}: 404 NOT FOUND")
        else:
            print(f"  {ep}: 403 (權限不足)")

# 嘗試用 BigQuery 查詢（如果有的話）
print("\n=== 嘗試 Firebase Analytics API ===")
try:
    r_summary = requests.get(f"{FB_BASE}/analytics/eeg-summary", headers=FH, timeout=10)
    print(f"GET /analytics/eeg-summary: HTTP {r_summary.status_code}")
    if r_summary.status_code == 200:
        print(r_summary.text[:500])
except Exception as e:
    print(f"Error: {e}")
