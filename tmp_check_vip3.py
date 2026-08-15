"""
確認 VIP 付款記錄的 consultant_name 設定狀況
"""
import requests, urllib3, json, sys
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'

r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
admin_token = r.json().get('token')
s = requests.Session()
s.verify = False
s.headers.update({'Authorization': 'Bearer ' + admin_token})

# 取全部 sessions，看 consultant_name 分佈
r_sess = s.get(f'{BASE}/api/v1/eeg/sessions?limit=200', timeout=20)
all_sess = r_sess.json().get('sessions', []) if r_sess.status_code == 200 else []
consultant_sess = {}
for ss in all_sess:
    cn = ss.get('consultant_name') or '(none)'
    consultant_sess[cn] = consultant_sess.get(cn, 0) + 1

print('=== Sessions 的 consultant_name 分佈 ===')
for cn, cnt in sorted(consultant_sess.items(), key=lambda x: -x[1])[:10]:
    print(f'  {cn}: {cnt} sessions')

# 取全部付款，查 consultant_name
r_pay = s.get(f'{BASE}/api/v1/payments/my?limit=200', timeout=20)
all_pay = r_pay.json().get('payments', []) if r_pay.status_code == 200 else []
print()
print(f'=== 付款記錄總計: {len(all_pay)} ===')
# 找 VIP 付款的樣本
vip_paid = [p for p in all_pay if p.get('report_type') in ('life_vip', 'child_vip') and p.get('status') == 'paid']
print(f'VIP 付款: {len(vip_paid)}')
print()
print('=== VIP 付款 session_id 對應情況 ===')
# 建立 session_id → consultant_name 的對應
sess_by_id = {ss.get('session_id'): ss for ss in all_sess}
for p in vip_paid[:10]:
    sid = p.get('session_id')
    sess = sess_by_id.get(sid) if sid else None
    consultant = sess.get('consultant_name', '(no session)') if sess else f'(no session, sid={sid})'
    name = p.get('subject_name', '?')
    print(f'  {name}: payment.session_id={sid}, session.consultant_name={consultant}')

print()
print('=== 問題診斷 ===')
print('Payment table 中 consultant_name 欄位需透過 DB 直接查詢才能看到')
print('但從 sessions 的 consultant_name 可以推斷：')
print('如果 VIP 付款的 session_id 對應的 session.consultant_name 不等於顧問本人')
print('則顧問看不到這筆 VIP 付款（因為 /payments/my 只過濾 consultant_id）')
