import requests, urllib3, datetime, sys
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
h = {'Authorization': 'Bearer '+r.json().get('token','')}

# 查 7/27 之後真實客戶 session 的來源特徵
sl = requests.get(BASE+'/eeg/sessions?limit=200', headers=h, verify=False, timeout=15).json()
all_s = sl.get('sessions', [])
print('7/27 後真實客戶 sessions（排除 _test/_verify）：')
for s in all_s:
    name = s.get('subject_name') or ''
    if name.startswith('_') or 'test' in name.lower() or '驗證' in name or 'verify' in name.lower():
        continue
    ca = s.get('created_at', 0)
    try:
        ts = int(str(ca)[:10])
        if ts < 1753545600:  # roughly before Jul 27
            continue
        dt = datetime.datetime.fromtimestamp(ts).strftime('%m/%d %H:%M')
    except:
        dt = str(ca)
    print(f"  #{s.get('session_id')} {name:12s} {dt} captures={s.get('total_captures')} fb={s.get('firebase_session_id','')[:20] if s.get('firebase_session_id') else '-'}")
