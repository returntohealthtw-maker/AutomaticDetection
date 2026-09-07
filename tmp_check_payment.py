import requests, sys
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r0 = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, timeout=10, verify=False)
tok = r0.json()['token']
H = {'Authorization': f'Bearer {tok}'}
r = requests.get(f'{BASE}/api/v1/payments/my?limit=100', headers=H, timeout=10, verify=False)
print(f'GET /payments/my: HTTP {r.status_code}')
d = r.json()
print(f'keys: {list(d.keys())}')
payments = d.get('payments', [])
print(f'payments count: {len(payments)}')
if payments:
    print('first:', payments[0])
