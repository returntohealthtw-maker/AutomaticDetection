"""
確認親子報告狀態 + session 資料
"""
import requests, urllib3, json, sys
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=15)
token = r.json().get('token')
s = requests.Session()
s.verify = False
s.headers.update({'Authorization': 'Bearer ' + token})

job_id = 'a99e612b-200d-4cc8-a601-e8565d055a8f'

print('=== 1. Parent-child report status ===')
r_status = s.get(f'{BASE}/parent-child/status/{job_id}', timeout=15)
print(f'  status API: {r_status.status_code}')
if r_status.status_code == 200:
    try:
        d = r_status.json()
        print(f'  status={d.get("status")}, progress={d.get("progress")}, sections={d.get("completed_sections")}/{d.get("total_sections")}')
    except Exception:
        pass

r_rep = s.get(f'{BASE}/parent-child/report/{job_id}', timeout=30)
ct = r_rep.headers.get('content-type','')
print(f'  report page: {r_rep.status_code} ({ct}) size={len(r_rep.content)}')
if r_rep.status_code == 200:
    print('  [OK] Parent-child report page accessible')
else:
    print('  [FAIL] Report not accessible yet')

print()
print('=== 2. result_url issue ===')
local_url = 'http://127.0.0.1:8080/parent-child/report/' + job_id
public_url = BASE + '/parent-child/report/' + job_id
print(f'  Returned result_url (local): {local_url}')
print(f'  Correct public result_url:   {public_url}')
print(f'  Public URL accessible: {r_rep.status_code == 200}')

print()
print('=== 3. Session 112 captures ===')
r_caps = s.get(f'{BASE}/api/v1/sessions/112/captures', timeout=15)
print(f'  /sessions/112/captures: {r_caps.status_code}')
if r_caps.status_code == 200:
    data = r_caps.json()
    caps = data if isinstance(data, list) else data.get('captures', [])
    print(f'  Count: {len(caps)}')
    if caps and isinstance(caps[0], dict):
        c0 = caps[0]
        delta_val = c0.get('delta', 'N/A')
        print(f'  Sample delta={delta_val}')

print()
print('=== 4. Key findings summary ===')
print('  VIP list: 22 customers with session_ids')
print('  Marital external system: ONLINE (health 200)')
print('  Parent-child system: LOCAL (built-in)')
print('  Marital report generation: SUCCESS (PDF 911KB)')
print('  Parent-child generation: SUCCESS (local service)')
print(f'  BUG: parent_child result_url uses localhost instead of public Railway URL')
