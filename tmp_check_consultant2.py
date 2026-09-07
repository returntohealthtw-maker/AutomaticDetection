"""正確查看 sessions 的 consultant 欄位"""
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
# 注意 key 是 "consultant"，不是 "consultant_name"
vals = [repr(sess.get('consultant')) for sess in sessions]
c = Counter(vals)
print('consultant 值分布:')
for val, cnt in c.most_common(10):
    print(f'  {val}: {cnt} 筆')

print('\n最新 15 筆 sessions 的 consultant:')
for sess in sessions[:15]:
    cn = sess.get('consultant')
    print(f'  session_id={sess["session_id"]} subject={sess.get("subject_name","?")} consultant={repr(cn)}')

# 非 None 的
not_none = [sess for sess in sessions if sess.get('consultant') is not None]
print(f'\n有顧問歸屬的 sessions: {len(not_none)}/{len(sessions)}')
for s2 in not_none:
    print(f'  session_id={s2["session_id"]} subject={s2.get("subject_name")} consultant={s2.get("consultant")}')
