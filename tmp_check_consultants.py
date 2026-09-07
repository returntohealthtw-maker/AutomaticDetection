"""查詢所有顧問帳號及 VIP 付款受測者"""
import requests, urllib3
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone': '0900000000', 'password': 'admin123'},
                  verify=False, timeout=15)
token = r.json().get('token', '')
s = requests.Session()
s.verify = False
s.headers.update({'Authorization': 'Bearer ' + token})

# 取全部顧問帳號
r2 = s.get(f'{BASE}/api/v1/admin/consultants', timeout=15)
if r2.status_code == 200:
    consultants = r2.json()
    print(f'顧問帳號 ({len(consultants)} 筆):')
    for c in consultants:
        print(f'  id={c.get("consultant_id")} name={c.get("name")} phone={c.get("phone")} role={c.get("role")}')
else:
    # 嘗試其他 endpoint
    r2b = s.get(f'{BASE}/api/v1/admin/users', timeout=15)
    if r2b.status_code == 200:
        users = r2b.json()
        print(f'Users ({len(users)} 筆):')
        for u in users:
            print(f'  id={u.get("consultant_id")} name={u.get("name")} phone={u.get("phone")} role={u.get("role")}')
    else:
        print(f'consultants: {r2.status_code}, users: {r2b.status_code}')

# 取 VIP 付款名單
r3 = s.get(f'{BASE}/api/v1/payments/my?limit=200', timeout=20)
pays = r3.json().get('payments', []) if r3.status_code == 200 else []
vip = [p for p in pays if p.get('report_type') in ('life_vip', 'child_vip') and p.get('status') == 'paid']
print(f'\nVIP 付款受測者 ({len(vip)} 筆):')
for p in vip:
    print(f'  payment_id={p.get("payment_id")} subject={p.get("subject_name")} type={p.get("report_type")}')
