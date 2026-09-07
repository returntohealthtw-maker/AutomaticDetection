import requests, json, warnings, datetime
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
MONITOR = 'https://backend-production-2da61.up.railway.app/api/v1/monitor'

r0 = requests.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r0.json().get('token', r0.json().get('access_token',''))
h = {'Authorization': f'Bearer {token}'}

# Try monitor endpoint to get subjects
r2 = requests.get(f'{BASE}/monitor/subjects?limit=30', headers=h, timeout=15, verify=False)
print('monitor/subjects:', r2.status_code)
if r2.ok:
    subjects = r2.json().get('subjects', r2.json().get('items', []))
    for s in subjects:
        name = s.get('name','')
        if 'Wayne' in name or 'wayne' in name:
            print(f"Wayne subject:")
            print(json.dumps(s, indent=2, ensure_ascii=False))
            break
else:
    print(r2.text[:300])

# Try GET session #85 full info
r3 = requests.get(f'{BASE}/monitor/sessions/85', headers=h, timeout=15, verify=False)
print('\nmonitor/sessions/85:', r3.status_code)
if r3.ok:
    d = r3.json()
    print('keys:', list(d.keys()))
    for k, v in d.items():
        if k != 'captures':
            print(f'  {k}: {repr(v)[:150]}')
    
    # Check session created_at
    created = d.get('created_at', '')
    if created:
        print(f'\n  created_at raw: {created}')
        if 'T' in str(created):
            dt = datetime.datetime.fromisoformat(str(created).replace('Z',''))
            print(f'  UTC: {dt}')
            print(f'  UTC+8: {dt + datetime.timedelta(hours=8)}')
else:
    print(r3.text[:300])

# Wayne's subject - try searching
r4 = requests.get(f'{BASE}/monitor/subjects/search?q=Wayne', headers=h, timeout=15, verify=False)
print('\nSearch Wayne:', r4.status_code, r4.text[:300])
