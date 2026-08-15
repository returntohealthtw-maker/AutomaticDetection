import sys, urllib3, requests, json
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

# 查 headless jobs
resp = requests.get(f'{BASE}/api/v1/reports/headless/jobs', headers=hdrs, verify=False, timeout=15)
print(f"Headless jobs: {resp.status_code}")
if resp.status_code == 200:
    jobs = resp.json()
    if isinstance(jobs, list):
        for j in jobs[-3:]:  # 最近 3 個
            print(f"\n  job_id: {j.get('job_id')}")
            print(f"  status: {j.get('status')}")
            print(f"  error:  {j.get('error')}")
            print(f"  elapsed: {j.get('elapsed_sec')}s")
            preview = j.get('page_text_preview','')
            print(f"  page:   {preview[:200]}")
    else:
        print(json.dumps(jobs, ensure_ascii=False)[:1000])
else:
    print(resp.text[:200])

# 查 session 63 報告狀態
s63 = requests.get(f'{BASE}/api/v1/eeg/sessions/63/stats', headers=hdrs, verify=False, timeout=15).json()
print(f"\nSession 63 report_status: {s63.get('report_status')}")
