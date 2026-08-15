"""
查鄭靜怡今天的 session 和報告啟動 500 原因
"""
import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

print("=== 最近10筆 sessions ===")
sl = requests.get(BASE+'/eeg/sessions?limit=10', headers=h, verify=False)
sessions = sl.json()
if isinstance(sessions, dict):
    sessions = sessions.get('sessions', [])
for s in sessions[:10]:
    print(f"  #{s.get('session_id')} [{s.get('subject_name')}] report_type={s.get('report_type')} "
          f"captures={s.get('total_captures')} consultant={s.get('consultant_name')} ts={s.get('created_at')}")

print()
print("=== 最近10筆 reports ===")
rr = requests.get(BASE+'/reports?limit=10', headers=h, verify=False)
reports_data = rr.json()
if isinstance(reports_data, dict):
    reports_data = reports_data.get('reports', [])
for rep in reports_data[:10]:
    print(f"  report #{rep.get('report_id')} session={rep.get('session_id')} "
          f"status={rep.get('status')} kind={rep.get('talent_report_kind')} "
          f"err={str(rep.get('error_message') or '')[:80]}")

print()
# 找鄭靜怡最新 session
zsy = [s for s in sessions if '鄭靜怡' in (s.get('subject_name') or '')]
if zsy:
    latest = zsy[0]
    sid = latest['session_id']
    print(f"=== 鄭靜怡 最新 session #{sid} 詳細 ===")
    st = requests.get(BASE+f'/eeg/sessions/{sid}/stats', headers=h, verify=False)
    import json
    print(json.dumps(st.json(), ensure_ascii=False, indent=2)[:600])
