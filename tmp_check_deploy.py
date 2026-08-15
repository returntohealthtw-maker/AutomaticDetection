import requests, sys
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'

r0 = requests.post(f'{BASE}/api/v1/auth/login',
                   json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}'}

# 查 build version / git hash
for ep in ['/api/v1/reports/diag', '/api/v1/eeg/sessions?limit=1']:
    r = requests.get(f'{BASE}{ep}', headers=H, timeout=10, verify=False)
    print(f"{ep}: {r.status_code} → {r.text[:150]}")

# 直接試新端點
r2 = requests.post(f'{BASE}/api/v1/monitor/sessions/98/restore-pdf-url',
                   headers=H, json={'pdf_url': 'https://test.com/test.pdf'}, timeout=10, verify=False)
print(f"\nrestore-pdf-url: HTTP {r2.status_code} → {r2.text[:200]}")
