import requests, json, warnings, datetime
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r0 = requests.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r0.json().get('token', r0.json().get('access_token',''))
h = {'Authorization': f'Bearer {token}'}

# Try admin endpoints for subjects/sessions
endpoints = [
    '/admin/subjects?limit=5',
    '/admin/sessions?limit=5',
    '/admin/users?limit=5',
    '/sessions?limit=5',
    '/subjects?limit=5',
]
for ep in endpoints:
    r = requests.get(f'{BASE}{ep}', headers=h, timeout=10, verify=False)
    print(f'{ep}: {r.status_code}')
    if r.ok:
        d = r.json()
        print(f'  keys: {list(d.keys())}')
        items = d.get('items', d.get('sessions', d.get('subjects', [])))
        for item in items[:2]:
            print(f'  {json.dumps(item, ensure_ascii=False)[:200]}')

# What does session 85 look like from sessions endpoint?
r2 = requests.get(f'{BASE}/sessions/85', headers=h, timeout=10, verify=False)
print(f'\n/sessions/85: {r2.status_code}')
if r2.ok:
    d2 = r2.json()
    for k, v in d2.items():
        if k != 'captures':
            print(f'  {k}: {repr(v)[:150]}')
    created = d2.get('created_at', d2.get('session_date',''))
    if created:
        print(f'\n  created_at/session_date: {created}')
        try:
            if 'T' in str(created):
                dt = datetime.datetime.fromisoformat(str(created).replace('Z',''))
                print(f'  UTC: {dt} -> UTC+8: {dt + datetime.timedelta(hours=8)}')
        except: pass
