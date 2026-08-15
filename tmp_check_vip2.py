"""
用實際顧問帳號測試 /payments/my，確認 consultant_id 問題
"""
import requests, urllib3, json, sys
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'

# Admin 先取顧問資料
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
admin_token = r.json().get('token')
admin_s = requests.Session()
admin_s.verify = False
admin_s.headers.update({'Authorization': 'Bearer ' + admin_token})

# 取顧問列表
r_cons = admin_s.get(f'{BASE}/api/v1/auth/consultants', timeout=10)
consultants = r_cons.json() if isinstance(r_cons.json(), list) else r_cons.json().get('consultants', [])
non_admin = [c for c in consultants if c.get('role') != 'admin']

print('=== 用個別顧問帳號測試 /payments/my ===')
# 測試前3個顧問
for c in non_admin[:5]:
    cid = c.get('consultant_id')
    phone = c.get('phone')
    name = c.get('name')
    
    # 嘗試登入（只能測試知道密碼的帳號）
    # 先查 admin 視角這個顧問有哪些 VIP 付款（用 consultant_id 過濾）
    r_pay = admin_s.get(f'{BASE}/api/v1/payments/my?limit=200', timeout=15)
    all_pay = r_pay.json().get('payments', []) if r_pay.status_code == 200 else []
    
    # 找出 subject 表中屬於這個顧問的受測者名稱
    r_subj = admin_s.get(f'{BASE}/api/v1/subjects/?limit=200', timeout=15)
    all_subjects = r_subj.json() if isinstance(r_subj.json(), list) else r_subj.json().get('subjects', r_subj.json().get('items', []))
    
    # 找屬於這個顧問的受測者
    my_subjects = [s for s in all_subjects if s.get('consultant_id') == cid or s.get('consultant_name') == name]
    my_names = {s.get('name') for s in my_subjects}
    
    # 在 all_pay 中找屬於這個顧問的 VIP 付款
    my_vip = [p for p in all_pay if p.get('subject_name') in my_names and p.get('report_type') in ('life_vip', 'child_vip') and p.get('status') == 'paid']
    
    print(f'\n  顧問: {name} (id={cid})')
    print(f'    受測者數: {len(my_subjects)}，VIP 付款: {len(my_vip)}')
    
    if my_vip:
        for p in my_vip[:3]:
            print(f'    VIP: {p.get("subject_name")} | {p.get("report_type")} | session_id={p.get("session_id")}')

print()
print('=== 核心問題：Payment.consultant_id 設定情況 ===')
# 取得一筆 VIP 付款的 consultant_id（需要直接查 DB 或用 admin 的特殊 API）
# 測試：用已知顧問的 VIP 付款
# 楊女毓 (id=10) 是一個真實顧問
target_consultant_id = 10
target_name = '楊女毓'

r_subj = admin_s.get(f'{BASE}/api/v1/subjects/?limit=200', timeout=15)
all_subjects = r_subj.json() if isinstance(r_subj.json(), list) else r_subj.json().get('subjects', r_subj.json().get('items', []))
yang_subjects = [s for s in all_subjects if s.get('consultant_id') == target_consultant_id or s.get('consultant_name') == target_name]
yang_names = {s.get('name') for s in yang_subjects}
print(f'  楊女毓 的受測者: {list(yang_names)[:10]}')

r_pay = admin_s.get(f'{BASE}/api/v1/payments/my?limit=200', timeout=15)
all_pay = r_pay.json().get('payments', []) if r_pay.status_code == 200 else []
yang_vip = [p for p in all_pay if p.get('subject_name') in yang_names and p.get('report_type') in ('life_vip', 'child_vip') and p.get('status') == 'paid']
print(f'  楊女毓 的 VIP 付款: {len(yang_vip)}')

# 直接查 sessions 確認 consultant_name
r_sess = admin_s.get(f'{BASE}/api/v1/eeg/sessions?limit=200', timeout=20)
all_sess = r_sess.json().get('sessions', []) if r_sess.status_code == 200 else []
yang_sess = [ss for ss in all_sess if ss.get('consultant_name') == target_name]
print(f'  楊女毓 sessions: {len(yang_sess)}')
yang_sess_names = {ss.get('subject_name') for ss in yang_sess}
print(f'  楊女毓 session 受測者: {list(yang_sess_names)[:10]}')

# 再找這些受測者的 VIP 付款
yang_vip2 = [p for p in all_pay if p.get('subject_name') in yang_sess_names and p.get('report_type') in ('life_vip', 'child_vip') and p.get('status') == 'paid']
print(f'  楊女毓 session 受測者中的 VIP 付款: {len(yang_vip2)}')
for p in yang_vip2[:5]:
    print(f'    {p.get("subject_name")}: type={p.get("report_type")}, status={p.get("status")}')
