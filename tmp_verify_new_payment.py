"""驗證：顧問登入後建立付款，consultant_id 是否正確寫入"""
import requests, urllib3, json
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app'

# 以顧問帳號登入（楊雲容）
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone': '0900000000', 'password': 'admin123'},
                  verify=False, timeout=15)
token = r.json().get('token', '')
user_name = r.json().get('name', '')
print(f'登入: {user_name} token={token[:20]}...')

s = requests.Session()
s.verify = False
s.headers.update({'Authorization': 'Bearer ' + token})

# 模擬前端 apiFetch: POST /payments/create with Bearer token
r2 = s.post(f'{BASE}/api/v1/payments/create',
            json={
                'report_type': 'life_vip',
                'amount': 12000,
                'subject_name': '驗證測試受測者',
                'notify_email': 'test@test.com',
            },
            timeout=15)
print(f'\nPOST /payments/create: {r2.status_code}')
if r2.status_code == 200:
    order = r2.json()
    order_id = order.get('order_id')
    print(f'  order_id: {order_id}')
    
    # 查此付款記錄的 consultant 歸屬
    r3 = s.get(f'{BASE}/api/v1/payments/my?limit=5', timeout=15)
    pays = r3.json().get('payments', []) if r3.status_code == 200 else []
    found = next((p for p in pays if p.get('order_id') == order_id), None)
    if found:
        print(f'  => 找到付款記錄: subject={found["subject_name"]}')
        # Admin 查 consultant_id
        r4 = s.get(f'{BASE}/api/v1/payments/admin/vip-unassigned', timeout=15)
        unassigned = r4.json().get('payments', []) if r4.status_code == 200 else []
        in_unassigned = any(p['payment_id'] == found.get('payment_id') for p in unassigned)
        print(f'  => 是否在未指派清單: {in_unassigned}')
        if not in_unassigned:
            print('  ✅ 新付款已正確綁定顧問（不在未指派清單中）')
        else:
            print('  ❌ 仍在未指派清單，consultant_id 未寫入！')
    else:
        print(f'  ❌ 找不到 order_id={order_id} 在 /payments/my 中')
        print(f'  查到的 payments: {[p.get("order_id") for p in pays]}')
else:
    print(f'  Error: {r2.text[:300]}')
