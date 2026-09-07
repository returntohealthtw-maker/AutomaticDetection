import requests

BASE = "https://backend-production-2da61.up.railway.app"
s = requests.Session()
r = s.post(f"{BASE}/api/v1/auth/login", json={"phone": "0900000000", "password": "admin123"}, verify=False)
print("login", r.status_code)
token = r.json().get("access_token")
h = {"Authorization": f"Bearer {token}"}

r = s.get(f"{BASE}/api/v1/reports/list?limit=5", headers=h, verify=False)
print(r.status_code)
import json
data = r.json()
print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
