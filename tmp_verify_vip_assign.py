"""驗證 VIP 指派 API 是否部署成功"""
import requests, urllib3, json
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone': '0900000000', 'password': 'admin123'},
                  verify=False, timeout=15)
token = r.json().get('token', '')
s = requests.Session()
s.verify = False
s.headers.update({'Authorization': 'Bearer ' + token})

# 1. GET /payments/admin/vip-unassigned
r1 = s.get(f'{BASE}/api/v1/payments/admin/vip-unassigned', timeout=15)
print(f'GET vip-unassigned: {r1.status_code}')
if r1.status_code == 200:
    data = r1.json()
    pays = data.get('payments', [])
    print(f'  未指派付款: {len(pays)} 筆')
    for p in pays[:5]:
        print(f'  - payment_id={p["payment_id"]} {p["subject_name"]} ({p["report_type"]})')
else:
    print(f'  Error: {r1.text[:300]}')

# 2. GET /auth/consultants (確認顧問列表可取得)
r2 = s.get(f'{BASE}/api/v1/auth/consultants', timeout=15)
print(f'\nGET /auth/consultants: {r2.status_code}')
if r2.status_code == 200:
    cons = r2.json()
    print(f'  顧問數: {len(cons)}')
    for c in cons:
        print(f'  - id={c.get("consultant_id")} name={c.get("name")} role={c.get("role")}')
else:
    print(f'  Error: {r2.text[:300]}')

print('\n=> API 驗證完成')
