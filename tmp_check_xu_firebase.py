import requests, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Firebase 認證
API_KEY = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
auth_r = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}",
    json={"email":"migration@returntohealthtw.com","password":"MigrateEEG@2026","returnSecureToken":True},
    timeout=15
)
id_token = auth_r.json().get("idToken","")
if not id_token:
    print("Firebase auth failed:", auth_r.text[:200])
    sys.exit(1)
print(f"Firebase auth OK, token length={len(id_token)}")

FB_BASE = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
FH = {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}

# 要查的三個 firebase session IDs
sessions_to_check = {
    "許恩蕊": "f919a5ce-0e4f-46b1-bc6c-e7d905191baa",
    "許睿恩": "61b82071-1d82-4d35-8291-2259e18e78c3",
    "許允約":  "fc850d83-9ab5-4558-b4cb-04345ae03cb5",
}

print("\n=== Firebase 各 session 狀況 ===")
for name, fb_id in sessions_to_check.items():
    print(f"\n--- {name} (firebase_session_id={fb_id}) ---")
    
    # 查 session 基本資料
    r = requests.get(f"{FB_BASE}/sessions/{fb_id}", headers=FH, timeout=10)
    print(f"  GET /sessions/{fb_id}: HTTP {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        print(f"  session exists: {json.dumps(d, ensure_ascii=False)[:300]}")
    else:
        print(f"  response: {r.text[:200]}")
    
    # 查 EEG features
    r2 = requests.get(f"{FB_BASE}/eeg/{fb_id}", headers=FH, timeout=10)
    print(f"  GET /eeg/{fb_id}: HTTP {r2.status_code}")
    if r2.status_code == 200:
        eeg_data = r2.json()
        count = len(eeg_data) if isinstance(eeg_data, list) else eeg_data.get("count", "?")
        print(f"  EEG records: {count}")
    else:
        print(f"  response: {r2.text[:200]}")

# 查 Firestore sessions collection 的最近資料
print("\n=== 查 Firebase subjects collection ===")
for name, fb_id in sessions_to_check.items():
    r = requests.get(f"{FB_BASE}/subjects", headers=FH, params={"sessionId": fb_id}, timeout=10)
    print(f"{name}: HTTP {r.status_code} → {r.text[:300]}")
