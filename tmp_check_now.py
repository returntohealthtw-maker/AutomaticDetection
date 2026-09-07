import requests, urllib3, datetime, sys
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}
sl = requests.get(BASE+'/eeg/sessions?limit=200', headers=h, verify=False, timeout=15).json()
all_s = sl.get('sessions', sl) if isinstance(sl, dict) else sl
print(f'共 {len(all_s)} 筆 sessions')
for s in all_s[:15]:
    ca = s.get('created_at', 0)
    try:
        dt = datetime.datetime.fromtimestamp(int(str(ca)[:10])).strftime('%m/%d %H:%M:%S')
    except:
        dt = str(ca)
    name = (s.get('subject_name') or '?')
    print(f"  #{s.get('session_id'):4d}  {name:18s}  {dt}  captures={s.get('total_captures','?')}  sub_id={s.get('subject_id','?')}")
