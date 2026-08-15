"""查詢 sessions 中 consultant_name 的分布"""
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

r2 = s.get(f'{BASE}/api/v1/eeg/sessions?limit=500', timeout=30)
if r2.status_code != 200:
    print(f'Error: {r2.status_code}')
    exit()

sessions = r2.json().get('sessions', [])
print(f'Total sessions: {len(sessions)}')

# 統計 consultant_name 分布
from collections import Counter
c = Counter(sess.get('consultant_name', '(none)') or '(none)' for sess in sessions)
print('\nconsultant_name 分布:')
for name, cnt in c.most_common():
    print(f'  {name!r}: {cnt}')

# 列出有 consultant_name 的 sessions
print('\n有 consultant_name 的 sessions:')
for sess in sessions:
    cn = sess.get('consultant_name')
    if cn:
        print(f'  session_id={sess["session_id"]} subject={sess.get("subject_name")} consultant={cn}')
