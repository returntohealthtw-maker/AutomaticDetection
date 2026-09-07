import requests, sys
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r0 = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, timeout=10, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}'}

# 找所有 "肥" 相關 sessions
re = requests.get(f'{BASE}/api/v1/eeg/sessions?limit=300', headers=H, timeout=10, verify=False)
sessions = re.json()['sessions']

print("所有含「肥」的 sessions：")
for s in sessions:
    if '肥' in s['subject_name']:
        print(f"  session={s['session_id']} subject={s['subject_name']} consultant={s['consultant']} status={s['report_status']}")

# 找 cid=2 的顧問名稱（示範顧問）
print("\n找 cid=2 的顧問名稱：")
users = requests.get(f'{BASE}/api/v1/auth/users', headers=H, timeout=10, verify=False)
if users.ok:
    for u in users.json():
        if u.get('consultant_id') == 2 or u.get('id') == 2:
            print(f"  id={u.get('id')} name={u.get('name')} consultant_id={u.get('consultant_id')}")
else:
    print(f"  /auth/users 失敗: {users.status_code}")

# 找顧問名稱為"示範顧問"的sessions
print("\nconsultant='示範顧問' 的 sessions：")
for s in sessions:
    if '示範' in (s['consultant'] or ''):
        print(f"  session={s['session_id']} subject={s['subject_name']} consultant={s['consultant']}")
print(f"(共 {sum(1 for s in sessions if '示範' in (s['consultant'] or ''))} 筆)")
