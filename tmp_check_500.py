"""
測試 APP 採集完成畫面相關的 API，找出 500 來源
"""
import sys, requests, urllib3, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

print("=== 測試最近幾筆 session 的 stats 端點 ===")
# 先拿最近 session list
sl = requests.get(BASE+'/eeg/sessions?limit=5', headers=h, verify=False)
sessions = sl.json() if sl.ok else {}
if isinstance(sessions, dict):
    sessions = sessions.get('sessions', [])
elif isinstance(sessions, list):
    pass
print(f"sessions type={type(sessions)}, count={len(sessions) if isinstance(sessions, list) else 'N/A'}")

for s in (sessions[:3] if isinstance(sessions, list) else []):
    sid = s.get('session_id') or s.get('id')
    print(f"\n  session_id={sid}")
    stats = requests.get(BASE+f'/eeg/sessions/{sid}/stats', headers=h, verify=False)
    print(f"  stats: {stats.status_code} {stats.text[:200] if stats.status_code != 200 else 'OK'}")

print()
print("=== 測試 /eeg/sessions (consultant list) ===")
sl2 = requests.get(BASE+'/eeg/sessions', headers=h, verify=False)
print(f"  {sl2.status_code} {sl2.text[:200]}")

print()
print("=== 測試 /reports/all-subjects-overview ===")
ov = requests.get(BASE+'/reports/all-subjects-overview?limit=5', headers=h, verify=False)
print(f"  {ov.status_code} {ov.text[:200]}")
