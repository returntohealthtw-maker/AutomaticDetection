import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 搜尋林以瑄、林以樂
print("=== 搜尋林以瑄、林以樂 ===")
ov = requests.get(BASE+'/reports/all-subjects-overview', headers=h, verify=False, timeout=30)
subjects = ov.json().get('subjects', [])

found = []
for s in subjects:
    name = s.get('name','')
    if '林以' in name or '以瑄' in name or '以樂' in name:
        found.append(s)

if not found:
    print("❌ 後台找不到這兩位受測者！")
    print("可能原因：上傳時 500 失敗 → 資料沒有進入後台")
else:
    for s in found:
        print(f"\n  {s.get('name')} (subject_id={s.get('subject_id')})")
        print(f"    sessions_count={s.get('sessions_count')}")
        bw = s.get('latest_brainwave') or {}
        print(f"    latest_brainwave: sample_count={bw.get('sample_count')} _source={bw.get('_source')}")
        for rep in s.get('reports', []):
            print(f"    report #{rep.get('report_id')} status={rep.get('status')}")

print()
print("=== 查詢 session list 最新幾筆 ===")
sl = requests.get(BASE+'/eeg/sessions?limit=10', headers=h, verify=False, timeout=10)
sessions = sl.json().get('sessions', [])
print(f"  最新 {len(sessions)} 筆 sessions：")
for s in sessions[:10]:
    print(f"    #{s.get('session_id')} {s.get('subject_name')} report_type={s.get('report_type')} created_at={s.get('created_at')}")
