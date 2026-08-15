import requests, json, warnings, datetime
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r0 = requests.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r0.json().get('token', r0.json().get('access_token',''))
h = {'Authorization': f'Bearer {token}'}

# /subjects returns list
r = requests.get(f'{BASE}/subjects?limit=30', headers=h, timeout=10, verify=False)
subjects = r.json() if r.ok else []
print(f'Total subjects: {len(subjects)}')
for s in subjects:
    name = s.get('name','')
    if 'Wayne' in name or 'wayne' in str(s).lower():
        print(f"\nWayne found:")
        print(json.dumps(s, indent=2, ensure_ascii=False))
        created = s.get('created_at','')
        if created and 'T' in str(created):
            dt = datetime.datetime.fromisoformat(str(created).replace('Z',''))
            print(f"\n  DB stored created_at (UTC): {dt}")
            print(f"  Display in UTC+8: {dt + datetime.timedelta(hours=8)}")

# Also look at reports/sessions-with-status for session 85/86
r2 = requests.get(f'{BASE}/reports/sessions-with-status', headers=h, timeout=15, verify=False)
print('\nreports/sessions-with-status:', r2.status_code)
if r2.ok:
    sessions = r2.json().get('sessions', [])
    for s in sessions:
        if s.get('session_id') in [85, 86]:
            print(f"\nSession #{s.get('session_id')}:")
            print(json.dumps(s, indent=2, ensure_ascii=False))
