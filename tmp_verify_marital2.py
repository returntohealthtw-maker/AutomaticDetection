"""查所有報告（含夫妻）- 改用 admin 端點"""
import requests, urllib3, json, datetime
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone': '0900000000', 'password': 'admin123'},
                  verify=False, timeout=15)
token = r.json().get('token', '')
s = requests.Session()
s.verify = False
s.headers.update({'Authorization': 'Bearer ' + token})

# 試各種 list endpoint
for ep in [
    '/api/v1/reports/list?limit=200',
    '/api/v1/reports/admin/list?limit=200',
    '/api/v1/monitor/sessions?limit=200',
]:
    r2 = s.get(f'{BASE}{ep}', timeout=20)
    print(f'{ep}: {r2.status_code}')
    if r2.status_code == 200:
        d = r2.json()
        reps = d.get('reports') or d.get('sessions') or []
        marital = [x for x in reps if x.get('report_type') in ('marital',)]
        print(f'  total={len(reps)}, marital={len(marital)}')
        if marital:
            for m in marital:
                print(f'  marital: {m}')
        break
    else:
        print(f'  {r2.text[:200]}')

# 查 DB sessions 中 report_type=marital 的
r3 = s.get(f'{BASE}/api/v1/eeg/sessions?limit=500', timeout=30)
sessions = r3.json().get('sessions', []) if r3.status_code == 200 else []
marital_sessions = [x for x in sessions if x.get('report_type') == 'marital']
print(f'\nSessions with report_type=marital: {len(marital_sessions)}')
for x in marital_sessions:
    print(f'  session_id={x["session_id"]} subject={x.get("subject_name")} status={x.get("report_status")}')

# 查包含 wife_session_id 的報告（stored in custom_sections_json）
# 用 monitor/reports endpoint
r4 = s.get(f'{BASE}/api/v1/monitor/reports?limit=200', timeout=20)
print(f'\n/monitor/reports: {r4.status_code}')
if r4.status_code == 200:
    d4 = r4.json()
    reps4 = d4.get('reports', [])
    marital4 = [x for x in reps4 if x.get('report_type') == 'marital']
    print(f'  marital 報告: {len(marital4)} 筆')
    for m in marital4:
        cs_raw = m.get('custom_sections_json') or '{}'
        try: cs = json.loads(cs_raw) if isinstance(cs_raw, str) else cs_raw
        except: cs = {}
        print(f'  report_id={m.get("report_id")} wife_name={cs.get("wife_name")} wife_session={cs.get("wife_session_id")}')
