import requests, json, warnings, datetime
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r0 = requests.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r0.json().get('token', r0.json().get('access_token',''))
h = {'Authorization': f'Bearer {token}'}

# Sessions 85/86 - direct captures with correct header
for sid in [85, 86]:
    r = requests.get(f'{BASE}/sessions/{sid}/captures', headers=h, timeout=15, verify=False)
    print(f'Session #{sid} captures: status={r.status_code}')
    if r.ok:
        d = r.json()
        items = d.get('captures', d.get('items', []))
        total = d.get('total', len(items))
        print(f'  total in DB: {total}')
        for item in items[:2]:
            print(f'  {json.dumps(item, ensure_ascii=False)[:300]}')
    else:
        print(f'  error: {r.text[:200]}')
    print()

# Wayne subject
r2 = requests.get(f'{BASE}/subjects/list?limit=30', headers=h, timeout=15, verify=False)
print('subjects:', r2.status_code)
if r2.ok:
    subjects = r2.json().get('subjects', r2.json().get('items', []))
    for s in subjects:
        name = s.get('name','')
        if 'Wayne' in name or 'wayne' in name or 'waynepan' in str(s):
            print(f"Wayne: {json.dumps(s, indent=2, ensure_ascii=False)}")
            created = s.get('created_at','')
            if created:
                # Parse created_at
                if 'T' in str(created):
                    dt = datetime.datetime.fromisoformat(str(created).replace('Z',''))
                    print(f"  UTC: {dt}, UTC+8: {dt + datetime.timedelta(hours=8)}")
