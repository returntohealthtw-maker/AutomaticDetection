"""查 王筱琪 的 session 及付款狀況"""
import requests, urllib3
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone': '0900000000', 'password': 'admin123'},
                  verify=False, timeout=15)
token = r.json().get('token', '')
s = requests.Session()
s.verify = False
s.headers.update({'Authorization': 'Bearer ' + token})

# 1. Sessions
r2 = s.get(f'{BASE}/api/v1/eeg/sessions?limit=500', timeout=30)
sessions = r2.json().get('sessions', []) if r2.status_code == 200 else []
wang_sess = [x for x in sessions if '王筱琪' in (x.get('subject_name') or '')]
print(f'王筱琪 sessions ({len(wang_sess)} 筆):')
for x in wang_sess:
    print(f'  session_id={x["session_id"]} consultant={x.get("consultant")} '
          f'captures={x.get("total_captures")} report_status={x.get("report_status")} '
          f'created_at={x.get("created_at")}')

# 2. Payments
r3 = s.get(f'{BASE}/api/v1/payments/my?limit=500', timeout=20)
pays = r3.json().get('payments', []) if r3.status_code == 200 else []
wang_pays = [p for p in pays if '王筱琪' in (p.get('subject_name') or '')]
print(f'\n王筱琪 payments ({len(wang_pays)} 筆):')
for p in wang_pays:
    print(f'  payment_id={p["payment_id"]} type={p["report_type"]} status={p["status"]}')

# 3. 查最新 marital 報告 session 的詳細資料
if wang_sess:
    latest = max(wang_sess, key=lambda x: x['session_id'])
    sid = latest['session_id']
    r4 = s.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', timeout=15)
    if r4.status_code == 200:
        stats = r4.json()
        print(f'\n最新 session #{sid} stats:')
        print(f'  total_captures={stats.get("total_captures")}')
        bw = stats.get('latest_brainwave') or {}
        print(f'  brainwave keys: {list(bw.keys()) if bw else "none"}')
        bands = bw.get('bands_avg') or {}
        print(f'  bands_avg: {bands}')
