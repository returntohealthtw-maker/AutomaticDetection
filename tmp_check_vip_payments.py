"""
診斷：顧問看不到 VIP 名單的原因
"""
import requests, urllib3, json, sys
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'

# Admin 登入
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token')
s = requests.Session()
s.verify = False
s.headers.update({'Authorization': 'Bearer ' + token})

print('=== 1. 全部 Payment 的 report_type 分佈（Admin 視角）===')
r_pay = s.get(f'{BASE}/api/v1/payments/my?limit=200')
payments = r_pay.json().get('payments', []) if r_pay.status_code == 200 else []
type_counts = {}
for p in payments:
    rt = p.get('report_type', 'none') or 'none'
    type_counts[rt] = type_counts.get(rt, 0) + 1
print(f'  Total payments: {len(payments)}')
for rt, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f'  {rt}: {cnt}')

print()
print('=== 2. VIP 付款的 consultant_id 分佈 ===')
VIP_TYPES = {'life_vip', 'child_vip'}
vip_paid = [p for p in payments if p.get('report_type') in VIP_TYPES and p.get('status') == 'paid']
print(f'  life_vip + child_vip paid: {len(vip_paid)}')
# 但 payment response 沒有 consultant_id，需用另一個方式查

print()
print('=== 3. 測試一般顧問帳號的 /payments/my ===')
# 找一個非 admin 顧問來測試 - 先取顧問列表
r_cons = s.get(f'{BASE}/api/v1/auth/consultants', timeout=10)
if r_cons.status_code == 200:
    consultants = r_cons.json() if isinstance(r_cons.json(), list) else r_cons.json().get('consultants', [])
    print(f'  Consultants: {len(consultants)}')
    non_admin = [c for c in consultants if c.get('role') != 'admin'][:3]
    for c in non_admin:
        print(f'  {c.get("name")} | phone={c.get("phone")} | id={c.get("consultant_id")}')
else:
    print(f'  consultants API: {r_cons.status_code}')

print()
print('=== 4. 直接查 Payment 表中 consultant_id 不為空的 VIP ===')
# 用 admin 直接查特定顧問的 VIP 付款
# 先查監控 API 取到顧問列表
r_subjects = s.get(f'{BASE}/api/v1/reports/all-subjects-overview?limit=5', timeout=30)
if r_subjects.status_code == 200:
    subjects = r_subjects.json()
    if isinstance(subjects, list) and subjects:
        s0 = subjects[0]
        print(f'  Sample subject: {s0.get("name")} | consultant={s0.get("consultant_name")} | sessions={s0.get("sessions_count")}')
        
print()
print('=== 5. 前端 _loadVipCustomers 邏輯模擬 ===')
print('  Filter condition: report_type in {life_vip, child_vip} AND status==paid')
vip_names = [p.get('subject_name') for p in vip_paid]
print(f'  VIP customers found (admin): {len(vip_names)}')
print(f'  First 5: {vip_names[:5]}')

print()
print('=== 6. 問題診斷 ===')
print('  Root cause candidates:')
print('  A. Payment.consultant_id 沒有正確設定 → 顧問查 /payments/my 看不到這些 VIP 付款')
print('  B. report_type 名稱不是 life_vip/child_vip → 過濾條件不符')
print()

# 確認 VIP 付款中哪些 report_type 是對的
for p in vip_paid[:3]:
    name = p.get('subject_name', '?')
    rt = p.get('report_type', '?')
    status = p.get('status', '?')
    print(f'  {name}: report_type={rt}, status={status}')
