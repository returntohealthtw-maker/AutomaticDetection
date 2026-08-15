import requests, sys, json
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r0 = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, timeout=10, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}'}

# 所有 sessions
r = requests.get(f'{BASE}/api/v1/eeg/sessions?limit=200', headers=H, timeout=10, verify=False)
d = r.json()
print(f'sessions: {d["count"]} total')
s = d['sessions'][0]
print('session keys:', list(s.keys()))
print('sample:', json.dumps(s, ensure_ascii=False, default=str))
