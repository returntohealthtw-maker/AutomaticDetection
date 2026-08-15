"""詳細查看報告結構及夫妻報告是否有對應 PDF"""
import requests, urllib3, json
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone': '0900000000', 'password': 'admin123'},
                  verify=False, timeout=15)
token = r.json().get('token', '')
s = requests.Session()
s.verify = False
s.headers.update({'Authorization': 'Bearer ' + token})

# 取第一筆報告看欄位結構
r2 = s.get(f'{BASE}/api/v1/reports/list?limit=5', timeout=20)
reports = r2.json().get('reports', [])
if reports:
    print('報告欄位結構:')
    print(json.dumps(reports[0], ensure_ascii=False, indent=2))

# 查詢所有報告，找有 client_summary 內含 wife 的
r3 = s.get(f'{BASE}/api/v1/reports/list?limit=500', timeout=30)
all_reports = r3.json().get('reports', [])
print(f'\n總報告: {len(all_reports)}')

marital_found = []
parent_found = []
for rep in all_reports:
    # 直接看 pdf_url 是否包含 marital
    pdf = rep.get('pdf_url') or ''
    kind = rep.get('talent_report_kind') or ''
    cs_raw = rep.get('client_summary') or ''
    
    if 'marital' in pdf or 'marital' in kind or 'wife' in cs_raw:
        marital_found.append(rep)
    if 'parent' in pdf or 'parent_child' in kind or 'members' in cs_raw:
        parent_found.append(rep)

print(f'夫妻相關報告: {len(marital_found)}')
for rep in marital_found:
    print(f'  {rep}')

print(f'\n親子相關報告: {len(parent_found)}')
for rep in parent_found:
    cs_raw = rep.get('client_summary') or ''
    try:
        cs = json.loads(cs_raw) if cs_raw.startswith('{') else {}
    except:
        cs = {}
    print(f'  session_id={rep.get("session_id")} pdf={rep.get("pdf_url","")[:80]}')
    print(f'  members={cs.get("members")}')
