"""查所有報告中的夫妻及親子報告（用 talent_report_kind 欄位）"""
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

# 查所有報告
r2 = s.get(f'{BASE}/api/v1/reports/list?limit=500', timeout=30)
data = r2.json()
reports = data.get('reports', [])
print(f'總報告數: {len(reports)}')

# 顯示所有不同的 talent_report_kind
kinds = {}
for rep in reports:
    k = rep.get('talent_report_kind') or rep.get('report_type') or '?'
    kinds[k] = kinds.get(k, 0) + 1
print('report kind 分布:')
for k, cnt in sorted(kinds.items()):
    print(f'  {k}: {cnt}')

# 查包含夫妻/親子的報告
relation_reports = [r for r in reports
    if any(kw in (r.get('talent_report_kind') or r.get('report_type') or '')
           for kw in ['marital', 'parent_child', 'couple', 'life_script'])]
print(f'\n關係報告 (marital/parent_child/couple): {len(relation_reports)} 筆')

# 也看 client_summary 欄位
for rep in reports:
    cs_raw = rep.get('client_summary') or rep.get('custom_sections_json') or ''
    try:
        cs = json.loads(cs_raw) if isinstance(cs_raw, str) and cs_raw.startswith('{') else {}
    except:
        cs = {}
    if 'wife_session_id' in cs or 'wife_name' in cs or 'members' in cs:
        print(f'\n  report_id={rep.get("report_id")} kind={rep.get("talent_report_kind")} session={rep.get("session_id")}')
        print(f'  client_summary={cs}')

# 查 sessions 中的 report_type 欄位  
r3 = s.get(f'{BASE}/api/v1/eeg/sessions?limit=500', timeout=30)
sessions = r3.json().get('sessions', []) if r3.status_code == 200 else []
print(f'\n\n所有 session report_type 分布:')
rtypes = {}
for x in sessions:
    k = x.get('report_type') or '?'
    rtypes[k] = rtypes.get(k, 0) + 1
for k, cnt in sorted(rtypes.items()):
    print(f'  {k}: {cnt}')

relation_sess = [x for x in sessions
    if x.get('report_type') in ('marital', 'parent_child', 'couple')]
print(f'\n關係 sessions: {len(relation_sess)} 筆')
for x in relation_sess:
    print(f'  session_id={x["session_id"]} name={x.get("subject_name")} report_type={x.get("report_type")} status={x.get("report_status")}')
