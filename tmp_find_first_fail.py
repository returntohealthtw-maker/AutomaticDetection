import sys, urllib3, requests, json
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token','')
hdrs = {'Authorization': f'Bearer {token}'}

# 正確的 reports 列表端點
resp = requests.get(f'{BASE}/api/v1/reports/list?limit=20&session_id=63', headers=hdrs, verify=False, timeout=15)
print(f"Reports list: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    reports = data.get('reports', []) if isinstance(data, dict) else data
    print(f"找到 {len(reports)} 筆 session 63 的報告")
    for rpt in reports:
        print(json.dumps({
            'id':      rpt.get('report_id') or rpt.get('id'),
            'status':  rpt.get('report_status') or rpt.get('status'),
            'error':   (rpt.get('error_message') or '')[:200],
            'kind':    rpt.get('talent_report_kind'),
            'created': rpt.get('created_at'),
        }, ensure_ascii=False))
else:
    print(resp.text[:500])

# 嘗試不帶 session_id 查全部最近的報告
print()
resp2 = requests.get(f'{BASE}/api/v1/reports/list?limit=10', headers=hdrs, verify=False, timeout=15)
print(f"All recent reports: {resp2.status_code}")
if resp2.status_code == 200:
    data2 = resp2.json()
    reports2 = data2.get('reports', []) if isinstance(data2, dict) else data2
    for rpt in reports2:
        if rpt.get('session_id') == 63 or rpt.get('report_status') == 'failed':
            print(json.dumps({
                'id':      rpt.get('report_id') or rpt.get('id'),
                'sess':    rpt.get('session_id'),
                'status':  rpt.get('report_status') or rpt.get('status'),
                'error':   (rpt.get('error_message') or '')[:200],
                'kind':    rpt.get('talent_report_kind'),
            }, ensure_ascii=False))
else:
    print(resp2.text[:300])
