import requests, sys
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'

# 查 ingest_secret 是否有設定
r = requests.get(f'{BASE}/diag', timeout=10, verify=False)
print(f"GET /diag: HTTP {r.status_code} → {r.text[:300]}")

r2 = requests.get(f'{BASE}/api/v1/reports/diag', timeout=10, verify=False)
print(f"GET /api/v1/reports/diag: HTTP {r2.status_code} → {r2.text[:300]}")
