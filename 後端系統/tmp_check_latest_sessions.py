import requests, urllib3
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}

# 取最新 10 個 session
r2 = requests.get(f'{BASE}/api/v1/eeg/sessions?limit=10', headers=headers, verify=False)
data = r2.json()
sessions = data if isinstance(data, list) else data.get('sessions', [])
print(f'最新 sessions（共 {len(sessions)} 筆）：')
for s in sessions[:10]:
    sid = s.get('session_id', '?')
    name = s.get('subject_name', '?')
    created = s.get('created_at', '?')
    total = s.get('total_captures', '?')
    rtype = s.get('report_type', '?')
    print(f"  Session {sid} | {name} | captures={total} | type={rtype} | created={created}")
