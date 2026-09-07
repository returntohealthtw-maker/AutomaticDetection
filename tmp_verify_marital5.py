"""深入查看 report_id=130 (洪任佑夫妻報告) 的 client_summary 及太太資料"""
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

# 取所有 session 建立 map
r_sess = s.get(f'{BASE}/api/v1/eeg/sessions?limit=500', timeout=30)
sessions = r_sess.json().get('sessions', []) if r_sess.status_code == 200 else []
sess_by_id = {x['session_id']: x for x in sessions}

# 取所有報告，找所有夫妻/親子報告
r_rep = s.get(f'{BASE}/api/v1/reports/list?limit=500', timeout=30)
all_reports = r_rep.json().get('reports', [])
relation_reports = [x for x in all_reports 
                    if (x.get('report_kind') or '').startswith('marital') 
                    or (x.get('report_kind') or '').startswith('parent_child')
                    or (x.get('report_kind') or '').startswith('couple')]

print(f'關係報告: {len(relation_reports)} 筆')
print()

issues = []
for rep in relation_reports:
    rid = rep.get('report_id')
    rk  = rep.get('report_kind', '')
    members = rep.get('relation_members', [])
    print(f'report_id={rid} | kind={rk}')
    
    all_ok = True
    for m in members:
        name = m.get('name') or ''
        sid  = m.get('session_id')
        role = m.get('role')
        sess = sess_by_id.get(sid) if sid else None
        
        age      = sess['subject_age'] if sess else None
        detected = datetime.datetime.fromtimestamp(sess['created_at']).strftime('%Y-%m-%d') if sess and sess.get('created_at') else None
        gender   = sess.get('subject_gender') if sess else None
        
        ok = bool(name and sid and age and detected)
        mark = 'OK' if ok else 'NG'
        print(f'  [{mark}] [{role}] name={name!r} session_id={sid} age={age} detected_at={detected}')
        
        if not ok:
            all_ok = False
            issues.append({
                'report_id': rid, 'report_kind': rk,
                'role': role, 'name': name, 'session_id': sid,
                'age': age, 'detected': detected,
            })
    print()

print('='*60)
print(f'有問題的 member: {len(issues)} 筆')
for x in issues:
    print(f"  report_id={x['report_id']} [{x['role']}] {x['name']!r} session={x['session_id']} age={x['age']} detected={x['detected']}")

# 單獨拉 report_id=130 detail
print('\n\n--- Report 130 detail ---')
r130 = s.get(f'{BASE}/api/v1/reports/list?limit=500', timeout=30)
for rep in r130.json().get('reports', []):
    if rep.get('report_id') == 130:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        break
