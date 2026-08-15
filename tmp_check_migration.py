"""
查鄭靜怡所有 sessions + 驗證 life_script migration
"""
import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

sl = requests.get(BASE+'/eeg/sessions?limit=200', headers=h, verify=False)
sessions = sl.json()
if isinstance(sessions, dict):
    sessions = sessions.get('sessions', [])

zsy = [s for s in sessions if '鄭' in (s.get('subject_name') or '')]
print("=== 所有含「鄭」的 sessions ===")
for s in zsy:
    sid = s.get('session_id')
    nm  = s.get('subject_name')
    rt  = s.get('report_type')
    cap = s.get('total_captures')
    ts  = s.get('created_at')
    print(f"  #{sid} [{nm}] report_type={rt} captures={cap} ts={ts}")

print()
print("=== 驗證 migration：life_script (11字) 上傳 ===")
def mc(i):
    return {'seq_num':i,'is_baseline':False,'captured_at':1785000000+i*1000,'good_signal':0,
            'attention':50,'meditation':50,'delta':200000,'theta':80000,'low_alpha':30000,
            'high_alpha':20000,'low_beta':15000,'high_beta':12000,'low_gamma':8000,'high_gamma':3000,'feedback':0}
caps = [mc(i) for i in range(10)]
payload = {
    'subject_name':'migration_test','consultant_name':'admin','subject_age':49,
    'subject_gender':'女','report_type':'life_script','is_success':True,'captures':caps
}
resp = requests.post(BASE+'/sessions/upload', json=payload, headers=h, verify=False, timeout=30)
print(f"  life_script → {resp.status_code} {resp.text[:150]}")

print()
print("=== APP 版本確認 ===")
ver = requests.get(BASE+'/app/version', headers=h, verify=False)
print(f"  html_version: {ver.json().get('html_version')}")
