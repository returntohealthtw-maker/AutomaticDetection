import requests, sys
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r0 = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, timeout=10, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}'}

rs = requests.get(f'{BASE}/api/v1/subjects', headers=H, timeout=10, verify=False)
subjects = rs.json()

re = requests.get(f'{BASE}/api/v1/eeg/sessions?limit=300', headers=H, timeout=10, verify=False)
sessions = re.json()['sessions']

# 建立 session name -> sessions 的對應
sess_by_name = {}
for s in sessions:
    n = s['subject_name']
    sess_by_name.setdefault(n, []).append(s)

# 列出每個 subject 有幾個 sessions
print(f"{'姓名':<20} {'sessions數':<10} {'有報告':<8} consultant_id")
print('-'*60)
for sub in subjects:
    name = sub['name']
    cid  = sub['consultant_id']
    matched = sess_by_name.get(name, [])
    has_report = any(s['report_status'] == 'completed' and s['report_url'] for s in matched)
    marker = '✅' if matched else '⚠️ '
    print(f"{marker} {name:<18} {len(matched):<10} {'有' if has_report else '無':<8} cid={cid}")
