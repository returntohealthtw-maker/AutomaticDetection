"""驗證所有夫妻報告的太太資料完整性"""
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

# 取所有 sessions
r2 = s.get(f'{BASE}/api/v1/eeg/sessions?limit=500', timeout=30)
sessions = r2.json().get('sessions', []) if r2.status_code == 200 else []
sess_by_id = {x['session_id']: x for x in sessions}

# 取所有報告（含 custom_sections_json）
r3 = s.get(f'{BASE}/api/v1/reports/list?limit=200', timeout=30)
reports = r3.json().get('reports', []) if r3.status_code == 200 else []

marital_reports = [rep for rep in reports if rep.get('report_type') == 'marital']
print(f'夫妻報告總數: {len(marital_reports)} 筆')
print()

issues = []
for rep in marital_reports:
    rid = rep.get('report_id')
    sid = rep.get('session_id')  # 先生的 session
    cs_raw = rep.get('custom_sections_json') or rep.get('summary_json') or '{}'
    try:
        cs = json.loads(cs_raw) if isinstance(cs_raw, str) else cs_raw
    except Exception:
        cs = {}

    husband_name = cs.get('subject_name') or rep.get('subject_name', '?')
    wife_name    = cs.get('wife_name') or '?'
    wife_sid     = cs.get('wife_session_id')
    husband_sid  = cs.get('husband_session_id') or sid

    # 查太太的 session
    wife_sess = sess_by_id.get(wife_sid) if wife_sid else None

    # 查先生的 session
    husband_sess = sess_by_id.get(husband_sid) if husband_sid else None

    wife_age      = wife_sess['subject_age'] if wife_sess else None
    wife_gender   = wife_sess['subject_gender'] if wife_sess else None
    wife_detected = datetime.datetime.fromtimestamp(wife_sess['created_at']).strftime('%Y-%m-%d') if wife_sess and wife_sess.get('created_at') else None

    husband_age = husband_sess['subject_age'] if husband_sess else None

    has_issue = (wife_age is None or wife_age == 0 or wife_detected is None)
    status = '❌ 有問題' if has_issue else '✅ 正常'

    print(f'report_id={rid} | {husband_name}({husband_age}歲) + {wife_name}({wife_age}歲)')
    print(f'  先生 session_id={husband_sid} | 太太 session_id={wife_sid}')
    print(f'  太太年齡={wife_age} | 檢測日期={wife_detected} | {status}')
    if has_issue:
        issues.append({
            'report_id': rid,
            'wife_name': wife_name,
            'wife_session_id': wife_sid,
            'wife_age': wife_age,
            'wife_detected': wife_detected,
        })
    print()

print(f'{'='*60}')
print(f'有問題的報告: {len(issues)}/{len(marital_reports)} 筆')
for x in issues:
    print(f'  report_id={x["report_id"]} | 太太={x["wife_name"]} | session={x["wife_session_id"]} | age={x["wife_age"]} | date={x["wife_detected"]}')
