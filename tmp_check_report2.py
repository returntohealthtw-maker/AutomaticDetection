import sys, urllib3, requests, json
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

s63 = requests.get(f'{BASE}/api/v1/eeg/sessions/63/stats', headers=hdrs, verify=False, timeout=15).json()
print(f"report_status: {s63.get('report_status')}")
print(f"report_url:    {s63.get('report_url','(none)')}")

# 查 headless job 狀態（嘗試 admin 端點）
resp3 = requests.get(f'{BASE}/api/admin/headless-jobs?session_id=63', headers=hdrs, verify=False, timeout=15)
print(f"\nHeadless jobs: {resp3.status_code}")
try:
    print(json.dumps(resp3.json(), ensure_ascii=False)[:1000])
except:
    print(resp3.text[:300])

# 查全部報告（含 failed）
resp4 = requests.get(f'{BASE}/api/v1/reports?limit=5&session_id=63', headers=hdrs, verify=False, timeout=15)
print(f"\nReports list: {resp4.status_code}")
try:
    print(json.dumps(resp4.json(), ensure_ascii=False)[:1000])
except:
    print(resp4.text[:300])
