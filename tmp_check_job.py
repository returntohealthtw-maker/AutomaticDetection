import requests, sys, time
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}'}

# 查 job 狀態
JOB = 'hl-8c20079ee201'
r2 = requests.get(f'{BASE}/api/v1/report-gen/pdf/{JOB}', headers=H, timeout=15, verify=False)
print(f"Job status: HTTP {r2.status_code}")
print(r2.text[:300])

# 查 session 110 狀態
print()
r3 = requests.get(f'{BASE}/api/v1/eeg/sessions/110/stats', headers=H, timeout=15, verify=False)
d = r3.json()
print(f"session 110 report_status: {d.get('report_status')}")
print(f"report_url: {(d.get('report_url') or '')[:80]}")
