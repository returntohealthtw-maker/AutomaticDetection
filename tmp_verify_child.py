import sys, urllib3, requests
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}
resp = requests.post(f'{BASE}/api/admin/recompute-braindna?force=true', headers=hdrs, verify=False, timeout=60)
print('Recompute:', resp.json().get('summary'))
import time; time.sleep(2)
resp2 = requests.get(f'{BASE}/api/v1/eeg/sessions/63/stats', headers=hdrs, verify=False, timeout=15).json()
bands = resp2.get('eeg_stats',{}).get('bands_avg',{})
print()
print('Session #63 (3歲，文獻校準後):')
KEYS = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
for k in KEYS:
    v = bands.get(k,'?')
    print(f'  {k:<12}: {v}')
resp3 = requests.get(f'{BASE}/api/v1/eeg/sessions/62/stats', headers=hdrs, verify=False, timeout=15).json()
bands3 = resp3.get('eeg_stats',{}).get('bands_avg',{})
print()
print('Session #62 (成人，確認未影響):')
for k in KEYS:
    v = bands3.get(k,'?')
    print(f'  {k:<12}: {v}')
