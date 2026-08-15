"""
找 session_id > 120 的所有 session，和報告生成失敗原因
"""
import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

# 查最新 sessions（含 #121 以後）
sl = requests.get(BASE+'/eeg/sessions?limit=20', headers=h, verify=False)
sessions = sl.json()
if isinstance(sessions, dict):
    sessions = sessions.get('sessions', [])
print("=== 最新 20 筆 sessions ===")
for s in sessions:
    sid = s.get('session_id')
    nm  = s.get('subject_name')
    rt  = s.get('report_type')
    cap = s.get('total_captures')
    ts  = s.get('created_at')
    print(f"  #{sid} [{nm}] report_type={rt} captures={cap} ts={ts}")

print()
# 查最新 reports
rlist = requests.get(BASE+'/reports?limit=10', headers=h, verify=False)
reports = rlist.json()
if isinstance(reports, dict):
    reports = reports.get('reports', [])
print("=== 最新 10 筆 reports ===")
for rep in reports:
    print(f"  report#{rep.get('report_id')} session={rep.get('session_id')} "
          f"status={rep.get('status')} kind={rep.get('talent_report_kind')} "
          f"err={str(rep.get('error_message') or '')[:80]}")

print()
# 模擬 APP 啟動報告的 API 呼叫（看 /report-gen/start 或類似端點）
# 先找一個有效 session 試打
print("=== 試打 report-gen start 端點（用 session #121）===")
# 嘗試報告生成端點
gen_resp = requests.post(BASE+'/report-gen/start',
    json={'session_id': 121, 'report_type': 'life_script'},
    headers=h, verify=False, timeout=15)
print(f"  /report-gen/start → {gen_resp.status_code} {gen_resp.text[:200]}")

gen_resp2 = requests.post(BASE+'/report-gen/generate',
    json={'session_id': 121, 'report_type': 'life_script'},
    headers=h, verify=False, timeout=15)
print(f"  /report-gen/generate → {gen_resp2.status_code} {gen_resp2.text[:200]}")
