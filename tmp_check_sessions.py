import requests, sys, json
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r0 = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, timeout=10, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}'}

# 受測者清單
rs = requests.get(f'{BASE}/api/v1/subjects', headers=H, timeout=10, verify=False)
subs = rs.json()
print(f'subjects count: {len(subs)}')
if subs:
    print('sample subject keys:', list(subs[0].keys()))
    print('first 2:')
    for s in subs[:2]:
        print(' ', json.dumps(s, ensure_ascii=False))

# EEG sessions (含 session 資訊)
re = requests.get(f'{BASE}/api/v1/eeg/sessions?limit=5', headers=H, timeout=10, verify=False)
sess = re.json()
print(f'\nsessions sample keys: {list(sess["sessions"][0].keys())}')
