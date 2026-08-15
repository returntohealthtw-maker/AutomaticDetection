import sys, requests, urllib3, time
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

print("=== 最近 15 筆 sessions ===")
sl = requests.get(BASE+'/eeg/sessions?limit=200', headers=h, verify=False, timeout=15)
all_s = sl.json().get('sessions', [])
for s in all_s[:15]:
    ca = s.get('created_at', 0)
    import datetime
    try:
        dt = datetime.datetime.fromtimestamp(int(ca)).strftime('%m/%d %H:%M')
    except:
        dt = str(ca)
    print(f"  #{s.get('session_id'):4d} {(s.get('subject_name') or '?'):12s} type={s.get('report_type'):12s} {dt} subject_id={s.get('subject_id')}")

print()
print("=== 試呼叫 /report-gen/start (最新 session) ===")
latest_id = all_s[0].get('session_id') if all_s else None
if latest_id:
    payload = {"session_id": latest_id, "report_type": all_s[0].get('report_type','life_script')}
    resp = requests.post(BASE+'/report-gen/start', json=payload, headers=h, verify=False, timeout=15)
    print(f"  session_id={latest_id} status={resp.status_code}")
    try:
        print(f"  response={resp.json()}")
    except:
        print(f"  response text={resp.text[:300]}")
