"""查 VIP 付款的 consultant_id/name 歸屬"""
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

r2 = s.get(f'{BASE}/api/v1/payments/my?limit=200', timeout=20)
if r2.status_code != 200:
    print(f'API error: {r2.status_code} {r2.text[:300]}')
    exit()

pays = r2.json().get('payments', [])
vip = [p for p in pays if p.get('report_type') in ('life_vip', 'child_vip')
       and p.get('status') == 'paid']

print(f'VIP paid 總筆數: {len(vip)}')
print()
print(f'{"subject_name":<20} {"consultant_id":>14} {"consultant_name":<22} {"report_type":<12}')
print('-' * 75)

cid_null = cname_null = 0
for p in vip:
    cid   = p.get('_consultant_id')
    cname = p.get('_consultant_name') or '(none)'
    if cid is None:   cid_null += 1
    if not p.get('_consultant_name'): cname_null += 1
    print(f'{(p["subject_name"] or "?"):<20} {str(cid):>14} {cname:<22} {p["report_type"]:<12}')

print()
print(f'consultant_id=NULL: {cid_null}/{len(vip)}')
print(f'consultant_name=NULL: {cname_null}/{len(vip)}')
