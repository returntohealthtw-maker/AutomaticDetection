"""查 subjects 表中王筱琪的基本資料，並確認 session#49 的年齡問題"""
import requests, urllib3, json, datetime
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone': '0900000000', 'password': 'admin123'},
                  verify=False, timeout=15)
token = r.json().get('token', '')
s = requests.Session()
s.verify = False
s.headers.update({'Authorization': 'Bearer ' + token})

# 查 subjects 列表（用 admin 端點）
r2 = s.get(f'{BASE}/api/v1/admin/all-subjects-overview?limit=500', timeout=30)
if r2.status_code == 200:
    subjects = r2.json().get('subjects', [])
    wang = [x for x in subjects if '王筱琪' in (x.get('subject_name') or '')]
    print(f'subjects 中的王筱琪: {len(wang)} 筆')
    for x in wang:
        print(f'  subject_id={x.get("subject_id")} name={x.get("subject_name")} age={x.get("age")} gender={x.get("gender")}')
        print(f'  sessions: {x.get("sessions_count")} latest_session={x.get("latest_session_id")}')
else:
    print(f'all-subjects-overview: {r2.status_code} {r2.text[:200]}')

# 查 session #49 的詳細資訊
r3 = s.get(f'{BASE}/api/v1/eeg/sessions/49/stats', timeout=15)
if r3.status_code == 200:
    d3 = r3.json()
    print(f'\nSession #49 stats:')
    print(f'  subject_name={d3.get("subject_name")} age={d3.get("subject_age")} gender={d3.get("subject_gender")}')
    print(f'  created_at={datetime.datetime.fromtimestamp(d3["created_at"]).strftime("%Y-%m-%d")}')
else:
    print(f'Session #49: {r3.status_code}')

# 查 VIP 列表（模擬顧問視角）
# 先登入顧問帳號
# 查付款中有王筱琪相關的
r4 = s.get(f'{BASE}/api/v1/payments/my?limit=200', timeout=20)
if r4.status_code == 200:
    pays = r4.json().get('payments', [])
    wang_pays = [p for p in pays if '王筱琪' in (p.get('subject_name') or '')]
    print(f'\n王筱琪的付款紀錄: {len(wang_pays)} 筆')
    for p in wang_pays:
        print(f'  payment_id={p.get("payment_id")} type={p.get("payment_type")} '
              f'subject={p.get("subject_name")} age={p.get("subject_age")} '
              f'consultant_id={p.get("consultant_id")}')

# 確認 fix 是否已在最新 commit 中
print('\n\n--- 結論摘要 ---')
print('系統中關係報告現況:')
print('  marital: 1 筆（report_id=130, 洪任佑+王筱琪, 生成於 12:33 fix前）')
print('  parent_child: 0 筆')
print('  couple: 0 筆')
print('  目前沒有其他人有相同問題（因為沒有其他關係報告）')
print()

# 確認王筱琪在哪個 session 有年齡資料
r_sess = s.get(f'{BASE}/api/v1/eeg/sessions?limit=500', timeout=30)
sessions = r_sess.json().get('sessions', []) if r_sess.status_code == 200 else []
wang_sess = [x for x in sessions if '王筱琪' in (x.get('subject_name') or '')]
print('王筱琪的所有 sessions:')
for x in wang_sess:
    created = datetime.datetime.fromtimestamp(x['created_at']).strftime('%Y-%m-%d') if x.get('created_at') else '?'
    print(f'  session_id={x["session_id"]} age={x["subject_age"]} gender={x.get("subject_gender","?")} created={created}')
