import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests, urllib3
urllib3.disable_warnings()

base = 'https://backend-production-2da61.up.railway.app/api/v1'
token = requests.post(f'{base}/auth/login', json={'phone': '0900000000', 'password': 'admin123'}, verify=False, timeout=30).json()['token']
h = {'Authorization': f'Bearer {token}'}
r = requests.get(f'{base}/eeg/sessions?limit=1000', headers=h, verify=False, timeout=60)
sessions = r.json().get('sessions', [])
candidates = [s for s in sessions if (s.get('report_type') or '').startswith('child') or (s.get('report_type') or '').startswith('teen')]

print(f"{'sid':>4} {'name':<22} {'age':>3} {'report_type':<14} {'consultant':<16} {'real_caps':>9} {'fb':>5}")
for s in candidates:
    sid = s['session_id']
    rc = requests.get(f'{base}/sessions/{sid}/captures', headers=h, verify=False, timeout=30)
    caps = rc.json().get('captures', []) if rc.status_code == 200 else []
    name = (s.get('subject_name') or '')[:22]
    consultant = str(s.get('consultant') or '')[:16]
    age = str(s.get('subject_age'))
    rtype = s.get('report_type') or ''
    fb = str(bool(s.get('firebase_session_id')))
    print(f"{sid:>4} {name:<22} {age:>3} {rtype:<14} {consultant:<16} {len(caps):>9} {fb:>5}")
