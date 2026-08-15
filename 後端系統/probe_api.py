import sys, io, requests, json, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()

BASE  = "https://backend-production-2da61.up.railway.app"
s = requests.Session(); s.verify = False

TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=10
               ).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"
print("登入成功")

# Try common endpoints
for ep in [
    "/api/v1/reports/sessions-with-status",
    "/api/v1/reports/list",
    "/api/v1/reports",
    "/api/v1/admin/sessions",
    "/api/v1/eeg/sessions",
    "/api/v1/sessions/list",
    "/api/v1/users/sessions",
]:
    r = s.get(f"{BASE}{ep}", timeout=10)
    tag = ""
    if r.status_code == 200:
        body = r.json()
        if isinstance(body, list):
            tag = f"list len={len(body)}"
        elif isinstance(body, dict):
            tag = str(list(body.keys()))[:60]
    print(f"  {ep} → {r.status_code}  {tag}")
