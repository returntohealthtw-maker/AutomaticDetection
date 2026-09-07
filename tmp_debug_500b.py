import sys, requests, urllib3, datetime
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

print("=== 最新 sessions (含18:49那筆) ===")
sl = requests.get(BASE+'/eeg/sessions?limit=200', headers=h, verify=False, timeout=15)
all_s = sl.json().get('sessions', [])
print(f"總筆數: {len(all_s)}")
for s in all_s[:5]:
    ca = s.get('created_at', 0)
    try:
        dt = datetime.datetime.fromtimestamp(int(ca)).strftime('%m/%d %H:%M')
    except:
        dt = str(ca)
    print(f"  #{s.get('session_id')} {(s.get('subject_name') or '?'):12s} {dt}")

print()
# 試最新 session 的 report start
latest = all_s[0] if all_s else {}
sid = latest.get('session_id')
rt = latest.get('report_type','life_script')
if '鄭' in (latest.get('subject_name') or '') or True:
    resp = requests.post(BASE+'/report-gen/start', json={"session_id": sid, "report_type": rt},
                         headers=h, verify=False, timeout=15)
    print(f"report-gen/start session #{sid}: HTTP {resp.status_code}")
    try:
        print(f"  {resp.json()}")
    except:
        print(f"  {resp.text[:300]}")

# 另外測試鄭靜怡的 session #124
print()
resp2 = requests.post(BASE+'/report-gen/start', json={"session_id": 124, "report_type": "life_script"},
                      headers=h, verify=False, timeout=15)
print(f"report-gen/start session #124: HTTP {resp2.status_code}")
try:
    print(f"  {resp2.json()}")
except:
    print(f"  {resp2.text[:300]}")
