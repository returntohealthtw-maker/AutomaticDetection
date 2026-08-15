"""深查 session #49 的 stats 回傳內容"""
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

# 查 session #49 的完整 stats
r2 = s.get(f'{BASE}/api/v1/eeg/sessions/49/stats', timeout=20)
print(f'session #49 stats: {r2.status_code}')
if r2.status_code == 200:
    data = r2.json()
    print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
else:
    print(r2.text[:500])

# 同時查 session #49 的 captures
r3 = s.get(f'{BASE}/api/v1/sessions/49/captures', timeout=20)
print(f'\nsession #49 captures: {r3.status_code}')
if r3.status_code == 200:
    d3 = r3.json()
    caps = d3.get('captures', d3 if isinstance(d3, list) else [])
    print(f'  筆數: {len(caps)}')
    if caps:
        print(f'  第一筆: {caps[0]}')
else:
    print(r3.text[:300])
