import sys, urllib3, requests, json
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

# 查特定 job
JOB_ID = 'hl-68044bc530ed'
resp = requests.get(f'{BASE}/api/v1/reports/headless/job/{JOB_ID}', headers=hdrs, verify=False, timeout=15)
print(f"Job status: {resp.status_code}")
if resp.status_code == 200:
    j = resp.json()
    print(f"  status:   {j.get('status')}")
    print(f"  error:    {j.get('error')}")
    print(f"  elapsed:  {j.get('elapsed_sec')}s")
    preview = j.get('page_text_preview','')
    print(f"  page_text ({len(preview)} chars):")
    print(f"  {preview[:500]}")
else:
    print(resp.text[:300])
