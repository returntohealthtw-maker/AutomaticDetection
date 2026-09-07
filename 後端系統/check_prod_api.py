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

# list all available endpoints
r = s.get(f"{BASE}/api/v1/sessions", timeout=15)
print("sessions status:", r.status_code)
print("sessions keys:", list(r.json().keys()) if isinstance(r.json(), dict) else f"list len={len(r.json())}")
print("raw (first 500):", r.text[:500])
