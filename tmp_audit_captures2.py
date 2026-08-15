import requests, sys
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r0 = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, timeout=10, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}'}

# 取受測者清單
rs = requests.get(f'{BASE}/api/v1/subjects', headers=H, timeout=10, verify=False)
subjects = rs.json()
subject_names = set(s['name'] for s in subjects)
print(f"subjects ({len(subjects)} total), first 10 names:")
for s in subjects[:10]:
    print(f"  subject_id={s['subject_id']} name={s['name']} consultant_id={s['consultant_id']}")

# 取 sessions
re = requests.get(f'{BASE}/api/v1/eeg/sessions?limit=300', headers=H, timeout=10, verify=False)
sessions = re.json()['sessions']
session_names = set(s['subject_name'] for s in sessions)
print(f"\nsessions ({len(sessions)} total), first 10 subject_names:")
for s in sessions[:10]:
    print(f"  session_id={s['session_id']} subject_name={s['subject_name']} consultant={s['consultant']}")

# 交集：哪些 subject_name 有 session
matched = subject_names & session_names
only_subject = subject_names - session_names
only_session = session_names - subject_names
print(f"\n交集（subject 與 session 名字都有）: {len(matched)} 筆")
for n in list(matched)[:10]:
    print(f"  ✅ {n}")
print(f"\n只在 subjects 沒在 sessions（{len(only_subject)} 位）：")
for n in list(only_subject)[:10]:
    print(f"  ⚠️  {n}")
print(f"\n只在 sessions 沒在 subjects（{len(only_session)} 筆）：")
for n in list(only_session)[:10]:
    print(f"  📋 {n}")
