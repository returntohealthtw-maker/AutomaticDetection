"""測試 Firebase 連線，並嘗試建立遷移用帳號"""
import sys, io, requests, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API_KEY  = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
API_BASE = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api"

# 1. 測試 Cloud Functions API 是否可存取
print("=== 1. 測試 Cloud Functions API ===")
try:
    r = requests.get(f"{API_BASE}/health", timeout=10)
    print(f"  /health  → {r.status_code}: {r.text[:200]}")
except Exception as e:
    print(f"  /health 失敗: {e}")

# 也試 /sessions (未登入應該回 401)
try:
    r = requests.get(f"{API_BASE}/sessions", timeout=10)
    print(f"  GET /sessions (無 token) → {r.status_code}: {r.text[:200]}")
except Exception as e:
    print(f"  GET /sessions 失敗: {e}")

# 2. 嘗試用 Firebase Auth 建立遷移用帳號
print("\n=== 2. 嘗試建立 Firebase 帳號 ===")
MIGRATION_EMAIL    = "migration@returntohealthtw.com"
MIGRATION_PASSWORD = "MigrateEEG@2026"

signup_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
try:
    r = requests.post(signup_url, json={
        "email": MIGRATION_EMAIL,
        "password": MIGRATION_PASSWORD,
        "returnSecureToken": True,
    }, timeout=15)
    print(f"  signUp → {r.status_code}: {r.text[:300]}")
except Exception as e:
    print(f"  signUp 失敗: {e}")

# 3. 嘗試用 Firebase Auth 登入（帳號可能已存在）
print("\n=== 3. 嘗試 Firebase 登入 ===")
signin_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
try:
    r = requests.post(signin_url, json={
        "email": MIGRATION_EMAIL,
        "password": MIGRATION_PASSWORD,
        "returnSecureToken": True,
    }, timeout=15)
    print(f"  signIn → {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        token = data.get("idToken", "")
        uid   = data.get("localId", "")
        print(f"  ✅ 登入成功！uid={uid}, token={token[:40]}...")
        
        # 4. 試用 token 呼叫 API
        print("\n=== 4. 用 token 測試 API ===")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r2 = requests.get(f"{API_BASE}/sessions", headers=headers, timeout=10)
        print(f"  GET /sessions → {r2.status_code}: {r2.text[:300]}")
    else:
        print(f"  ❌ 登入失敗: {r.text[:300]}")
except Exception as e:
    print(f"  登入失敗: {e}")
