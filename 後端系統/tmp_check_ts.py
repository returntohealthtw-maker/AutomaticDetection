import sys, requests, json, datetime, warnings
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

r2 = s.get(f'{BASE}/api/v1/sessions-recent', params={'limit':5})
data = r2.json()
print("最近 5 筆 session 時間：")
for sess in data[:5]:
    ts = sess.get('created_at') or sess.get('start_time')
    if ts:
        dt = datetime.datetime.fromtimestamp(int(ts))
        print(f"  session {sess.get('session_id')} {sess.get('subject_name')} → {dt} (UTC+8)")
    else:
        print(f"  session {sess.get('session_id')} {sess.get('subject_name')} → 無時間戳")
