import sys, requests, json, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

# Android sessions live under /api/v1/sessions not /api/v1/eeg/sessions
r2 = s.get(f'{BASE}/api/v1/sessions/recent', params={'limit':5})
print(f"/sessions/recent → {r2.status_code}")
if r2.ok:
    data = r2.json()
    print(json.dumps(data[:2], ensure_ascii=False, indent=2))

# Try session detail for 89
r3 = s.get(f'{BASE}/api/v1/sessions/89')
print(f"\n/sessions/89 → {r3.status_code}")
if r3.ok:
    d = r3.json()
    qeeg = d.get('qeeg_scores_json')
    print("qeeg_scores_json 存在：", bool(qeeg))
    if qeeg and isinstance(qeeg, str):
        q = json.loads(qeeg)
        print("signal_quality:", q.get('signal_quality',{}).get('quality_grade'))
    print("可用欄位：", list(d.keys()))

# Try sessions-recent
r4 = s.get(f'{BASE}/api/v1/sessions-recent', params={'limit': 3})
print(f"\n/sessions-recent → {r4.status_code}")
if r4.ok:
    data = r4.json()
    for item in data[:3]:
        sid = item.get('session_id')
        print(f"  session {sid} → qeeg: {'有' if item.get('qeeg_scores_json') else '無'} | 欄位: {list(item.keys())[:8]}")
