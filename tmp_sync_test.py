import requests, json
base = 'https://backend-production-2da61.up.railway.app/api/v1'
token = requests.post(f'{base}/auth/login', json={'phone':'0900000000','password':'admin123'}).json()['token']
h = {'Authorization': f'Bearer {token}'}

# 先 dry-run 看有多少筆
r = requests.post(f'{base}/admin/sync-sessions-to-firebase', headers=h, params={'dry_run': 'true'})
print(f'dry-run status={r.status_code}')
data = r.json()
print(data.get('message'))
sessions = data.get('sessions', [])
print(f'共 {len(sessions)} 筆需要同步')
for s in sessions[:10]:
    sid = s['session_id']
    name = s['subject_name']
    print(f'  session_id={sid} {name}')
if len(sessions) > 10:
    print(f'  ... 共 {len(sessions)} 筆')
