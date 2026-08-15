"""
正確查看 all-subjects-overview，用正確的 key
"""
import sys, requests, urllib3, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

print("=== 受測者資訊（前10筆，含 sessions_count）===")
ov = requests.get(BASE+'/reports/all-subjects-overview?limit=10', headers=h, verify=False)
subjects = ov.json().get('subjects', [])
for s in subjects:
    print(f"  #{s.get('subject_id')} {s.get('name')} "
          f"sessions_count={s.get('sessions_count')} "
          f"latest_session_id={s.get('latest_session_id')} "
          f"reports={len(s.get('reports',[]))}")

print()
print("=== 找 李悅瑄 和 洪苡樂（今日受測者）===")
for q in ['李悅瑄', '洪苡樂']:
    ov2 = requests.get(BASE+f'/reports/all-subjects-overview?q={q}', headers=h, verify=False)
    d = ov2.json().get('subjects', [])
    for s in d:
        print(f"  #{s.get('subject_id')} {s.get('name')} "
              f"sessions_count={s.get('sessions_count')} "
              f"latest_session_id={s.get('latest_session_id')} "
              f"consultant={s.get('consultant_name')}")

print()
print("=== session #114 和 #113 的完整資料結構 ===")
# 直接查 DB
for sid in [114, 113]:
    sr = requests.get(BASE+f'/eeg/sessions/{sid}/stats', headers=h, verify=False)
    d = sr.json()
    print(f"  #{sid}: subject_name={d.get('subject_name')} subject_id={d.get('subject_id')} "
          f"consultant={d.get('consultant_name') or d.get('consultant')}")
