"""
診斷 subject_id=None 問題：為何 session 沒有連結到 subject
"""
import sys, requests, urllib3, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

print("=== 1. 查詢 subjects 表：找李悅瑄、洪苡樂是否存在 ===")
# 嘗試搜尋 subjects
names_to_check = ['李悅瑄', '洪苡樂', '徐資淵', '李芮']
for name in names_to_check:
    sr = requests.get(BASE+f'/subjects?name={name}', headers=h, verify=False)
    if sr.ok:
        data = sr.json()
        print(f"  {name}: {data}")
    else:
        print(f"  {name}: {sr.status_code} {sr.text[:100]}")

print()
print("=== 2. 所有 subjects 清單 ===")
all_s = requests.get(BASE+'/subjects?limit=50', headers=h, verify=False)
if all_s.ok:
    subjects = all_s.json()
    if isinstance(subjects, dict):
        subjects = subjects.get('subjects', subjects.get('data', []))
    print(f"  總共 {len(subjects)} 個 subjects:")
    for s in subjects[:20]:
        print(f"    id={s.get('subject_id')} name={s.get('name')} consultant={s.get('consultant_name') or s.get('consultant')}")
else:
    print(f"  {all_s.status_code} {all_s.text[:200]}")

print()
print("=== 3. session #114 上傳時的 subject_name 和 consultant ===")
sr114 = requests.get(BASE+'/eeg/sessions/114/stats', headers=h, verify=False)
d = sr114.json()
print(f"  subject_name: {d.get('subject_name')}")
print(f"  consultant: {d.get('consultant_name') or d.get('consultant')}")
print(f"  subject_id: {d.get('subject_id')}")

print()
print("=== 4. 後台「受測者資訊」到底怎麼查資料（subjects-overview 完整計數）===")
ov = requests.get(BASE+'/reports/all-subjects-overview?limit=100', headers=h, verify=False)
if ov.ok:
    d = ov.json()
    subjects = d.get('subjects', []) if isinstance(d, dict) else d
    with_sessions = [s for s in subjects if s.get('sessions')]
    no_sessions = [s for s in subjects if not s.get('sessions')]
    print(f"  total: {len(subjects)}, 有session: {len(with_sessions)}, 無session: {len(no_sessions)}")
    print(f"  有session的:")
    for s in with_sessions[:5]:
        print(f"    {s.get('name')}: {len(s.get('sessions',[]))} sessions")
else:
    print(f"  ERROR: {ov.status_code} {ov.text[:200]}")
