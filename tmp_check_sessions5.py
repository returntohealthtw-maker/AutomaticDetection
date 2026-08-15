import requests, json, warnings, datetime
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r0 = requests.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
print('login:', r0.status_code, r0.text[:200])
token = r0.json().get('access_token','')
h = {'Authorization': f'Bearer {token}'}

# sessions list
r1 = requests.get(f'{BASE}/eeg/sessions?limit=10', headers=h, timeout=15, verify=False)
print('sessions list:', r1.status_code)
if r1.ok:
    data = r1.json()
    print('keys:', list(data.keys()))
    sessions = data.get('sessions', data.get('items', []))
    for s in sessions[:5]:
        print(json.dumps(s, ensure_ascii=False)[:300])
