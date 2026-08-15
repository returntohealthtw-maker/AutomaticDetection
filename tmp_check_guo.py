import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

print("=== 搜尋郭以琳、郭以樂 ===")
ov = requests.get(BASE+'/reports/all-subjects-overview', headers=h, verify=False, timeout=30)
subjects = ov.json().get('subjects', [])

found = []
for s in subjects:
    name = s.get('name','')
    if '郭以' in name:
        found.append(s)

if not found:
    print("❌ 後台找不到！資料可能上傳失敗")
else:
    for s in found:
        print(f"\n  {s.get('name')} (subject_id={s.get('subject_id')})")
        print(f"    sessions_count={s.get('sessions_count')}")
        bw = s.get('latest_brainwave') or {}
        print(f"    latest_brainwave: sample_count={bw.get('sample_count')} _source={bw.get('_source')}")
        for rep in (s.get('reports') or []):
            print(f"    report #{rep.get('report_id')} status={rep.get('status')}")

print()
print("=== 最近 10 筆 sessions ===")
sl = requests.get(BASE+'/eeg/sessions', headers=h, verify=False, timeout=10)
sessions = sl.json().get('sessions', [])
for s in sessions[:10]:
    name = s.get('subject_name','')
    sid = s.get('session_id')
    rt = s.get('report_type','')
    cat = s.get('created_at','')
    print(f"  #{sid} {name:12s} type={rt:12s} created={cat}")
