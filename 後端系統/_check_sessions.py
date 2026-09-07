import requests, urllib3, json, datetime
urllib3.disable_warnings()
s = requests.Session(); s.verify = False
tok = s.post('https://backend-production-2da61.up.railway.app/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, timeout=15).json().get('token','')
s.headers['Authorization'] = 'Bearer ' + tok
r = s.get('https://backend-production-2da61.up.railway.app/api/v1/eeg/sessions?limit=10', timeout=15)
data = r.json()
sessions = data.get('sessions', data) if isinstance(data, dict) else data
for sess in (sessions if isinstance(sessions, list) else [])[:10]:
    ts = sess.get('created_at', 0)
    dt = datetime.datetime.fromtimestamp(ts/1000 if ts > 1e10 else ts).strftime('%Y-%m-%d %H:%M') if ts else ''
    name = sess.get('subject_name','')
    print(f"session {sess.get('session_id')}: {name} | {dt} | captures={sess.get('total_captures')} | status={sess.get('report_status')}")
