"""確認 Session #60 和 #62 目前的資料庫值"""
import sys, urllib3, requests
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

for sid in [60, 62]:
    resp = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=hdrs, verify=False, timeout=20)
    if not resp.ok:
        print(f'Session {sid}: {resp.status_code}')
        continue
    d = resp.json()
    eeg = d.get('eeg_stats') or {}
    bands = eeg.get('bands_avg', eeg.get('bands', {}))
    print(f'Session #{sid}  (樣本:{eeg.get("sample_count","?")})  '
          f'hiB={bands.get("high_beta","?")}  loG={bands.get("low_gamma","?")}  '
          f'delta={bands.get("delta","?")}  theta={bands.get("theta","?")}  '
          f'loA={bands.get("low_alpha","?")}  loB={bands.get("low_beta","?")}')
