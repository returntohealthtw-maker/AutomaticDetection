"""查看 sessions 的 consultant_name 真實值（區分 null vs 空字串 vs 有值）"""
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
sessions = r2.json().get('sessions', []) if r2.status_code == 200 else []

from collections import Counter
vals = []
for sess in sessions:
    v = sess.get('consultant_name')  # None if not in response, or actual value
    vals.append(repr(v))

c = Counter(vals)
print('consultant_name 值分布:')
for val, cnt in c.most_common(10):
    print(f'  {val}: {cnt} 筆')

# Show recent 10 sessions with their consultant_name
print('\n最新 10 筆 sessions:')
for sess in sessions[:10]:
    cn = sess.get('consultant_name')
    print(f'  session_id={sess["session_id"]} subject={sess.get("subject_name")} consultant={repr(cn)}')
