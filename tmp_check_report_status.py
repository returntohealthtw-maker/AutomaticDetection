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

# 查 report #85 的詳細狀態
resp = requests.get(f'{BASE}/api/v1/reports/85', headers=hdrs, verify=False, timeout=15)
if resp.status_code == 200:
    rpt = resp.json()
    print(f"\nReport #85:")
    print(f"  status:     {rpt.get('report_status')}")
    print(f"  error_msg:  {rpt.get('error_message') or rpt.get('error_msg') or '(none)'}")
    print(f"  report_url: {rpt.get('report_url','(none)')}")
    print(f"  kind:       {rpt.get('talent_report_kind')}")
    # 顯示所有欄位中含有 error 的
    for k,v in rpt.items():
        if 'error' in k.lower() or 'fail' in k.lower():
            print(f"  {k}: {v}")
else:
    print(f"Report fetch: {resp.status_code} {resp.text[:300]}")

# 查 admin report log (嘗試)
resp2 = requests.get(f'{BASE}/api/admin/reports?session_id=63', headers=hdrs, verify=False, timeout=15)
print(f"\nAdmin reports for session 63:")
try:
    data = resp2.json()
    if isinstance(data, list):
        for rr in data:
            print(json.dumps({k:v for k,v in rr.items() if k in ['report_id','report_status','error_message','talent_report_kind','created_at']}, ensure_ascii=False))
    else:
        print(json.dumps(data, ensure_ascii=False)[:500])
except:
    print(resp2.text[:300])
