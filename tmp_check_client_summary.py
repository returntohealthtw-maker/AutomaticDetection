"""查 report_id=130 的 client_summary 原始內容，並確認目前系統狀態"""
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

# 取版本確認 fix 是否已部署
rv = s.get(f'{BASE}/api/v1/app/version', timeout=10)
vj = rv.json()
print(f'APP_HTML_VERSION={vj.get("html_version")} APK={vj.get("latest_apk_version")}')

# 確認 report_gen.py 的修正有無正確
# 用方法：查 report #130 的 pdf_url 可以存取嗎？
r_rep = s.get(f'{BASE}/api/v1/reports/list?limit=500', timeout=30)
reports = r_rep.json().get('reports', [])

for rep in reports:
    if (rep.get('report_kind') or '').startswith('marital'):
        rid = rep.get('report_id')
        members = rep.get('relation_members', [])
        pdf = rep.get('pdf_url', '')
        print(f'\nreport_id={rid}')
        print(f'completed_at={rep.get("completed_at")}')
        print(f'relation_members={json.dumps(members, ensure_ascii=False)}')
        print(f'pdf_url={pdf[:80]}...')
        
        # 確認王筱琪的 session
        # 查 sessions 找王筱琪
        r_sess = s.get(f'{BASE}/api/v1/eeg/sessions?limit=500', timeout=30)
        sessions = r_sess.json().get('sessions', [])
        wang = [x for x in sessions if '王筱琪' in (x.get('subject_name') or '')]
        print(f'\n王筱琪的 session: {wang}')
        break

print('\n系統目前的關係報告摘要:')
marital_cnt = sum(1 for r in reports if (r.get('report_kind') or '').startswith('marital'))
parent_cnt  = sum(1 for r in reports if (r.get('report_kind') or '').startswith('parent_child'))
couple_cnt  = sum(1 for r in reports if (r.get('report_kind') or '').startswith('couple'))
print(f'  marital: {marital_cnt} 筆')
print(f'  parent_child: {parent_cnt} 筆')
print(f'  couple: {couple_cnt} 筆')
print(f'  總計: {len(reports)} 筆報告')
