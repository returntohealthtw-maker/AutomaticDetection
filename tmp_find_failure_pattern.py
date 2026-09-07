import sys, urllib3, requests, json
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

# 用 admin report list endpoint 查完整報告資料（含 error_message）
resp = requests.get(f'{BASE}/api/v1/reports/list?limit=50', headers=hdrs, verify=False, timeout=15)
data = resp.json()
reports = data.get('reports', data) if isinstance(data, dict) else data

# 用 session stats 端點把所有 session_id 的 report_status 找出來
# 先查 Session 63 的詳細報告 (#78 那次失敗)
failed_ids = [65, 69, 70, 71, 72, 73, 78]
print('=== 失敗報告詳細查詢 ===')
for rid in failed_ids:
    resp2 = requests.get(f'{BASE}/api/v1/reports/headless/job/hl-{rid}', headers=hdrs, verify=False, timeout=10)
    # 嘗試從 reports/list 中找到對應 report
    pass

# 改用 reports list 查所有最近的報告看 error_message
if isinstance(reports, list):
    print(f'共 {len(reports)} 筆報告')
    for rpt in reports:
        status = rpt.get('report_status') or rpt.get('status') or ''
        if status == 'failed':
            eid   = rpt.get('report_id') or rpt.get('id')
            err   = rpt.get('error_message') or rpt.get('error') or ''
            kind  = rpt.get('talent_report_kind') or ''
            name  = rpt.get('subject_name') or rpt.get('notify_email') or ''
            sess  = rpt.get('session_id') or ''
            print(f'  Report #{eid} | sess={sess} | {kind} | {name}')
            print(f'    error: {err[:200] if err else "(空)"}')
else:
    print(type(reports), str(reports)[:300])

# 嘗試用 monitor 端點查最近的 headless 活躍 jobs（含已結束的）
print()
resp3 = requests.get(f'{BASE}/api/v1/reports/headless/jobs', headers=hdrs, verify=False, timeout=15)
if resp3.status_code == 200:
    jobs = resp3.json().get('jobs', [])
    print(f'Headless jobs in memory: {len(jobs)}')
    for j in jobs:
        if j.get('status') in ('failed', 'timeout', 'error'):
            print(f"  job={j.get('job_id')} status={j.get('status')} error={j.get('error','')[:200]}")
    if not any(j.get('status') in ('failed','timeout','error') for j in jobs):
        print('  (無失敗 job 在記憶體中——Railway 重啟後 job 狀態會清空)')
        # 列出所有 job 狀態供參考
        for j in jobs[-5:]:
            print(f"  job={j.get('job_id')} status={j.get('status')} elapsed={j.get('elapsed_sec')}s")
