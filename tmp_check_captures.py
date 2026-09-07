"""
檢查最近 session 的 180 筆資料是否有進來
"""
import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

print("=== 最近 10 筆 session（含 total_captures）===")
sl = requests.get(BASE+'/eeg/sessions?limit=10', headers=h, verify=False)
sessions = sl.json()
if isinstance(sessions, dict):
    sessions = sessions.get('sessions', [])

for s in sessions:
    sid = s.get('session_id') or s.get('id')
    name = s.get('subject_name', '?')
    captures = s.get('total_captures', 'N/A')
    created = str(s.get('created_at', ''))[:16]
    status = s.get('status', '?')
    print(f"  #{sid} {name} captures={captures} status={status} created={created}")

print()
print("=== 最近兩筆 session：逐秒資料抽查 ===")
for s in sessions[:2]:
    sid = s.get('session_id') or s.get('id')
    name = s.get('subject_name', '?')
    cap_r = requests.get(BASE+f'/sessions/{sid}/captures', headers=h, verify=False)
    if cap_r.ok:
        caps = cap_r.json()
        if isinstance(caps, dict):
            caps = caps.get('captures', caps.get('data', []))
        print(f"  session #{sid} {name}: captures={len(caps)} 筆")
        if caps:
            c0 = caps[0]
            print(f"    delta={c0.get('delta')} good_signal={c0.get('good_signal')} seq_num={c0.get('seq_num')}")
    else:
        print(f"  #{sid} captures error: {cap_r.status_code} {cap_r.text[:100]}")

print()
print("=== 最新 session 的 stats ===")
if sessions:
    sid = sessions[0].get('session_id') or sessions[0].get('id')
    sr = requests.get(BASE+f'/eeg/sessions/{sid}/stats', headers=h, verify=False)
    print(f"  #{sid} stats: {sr.status_code}")
    if sr.ok:
        d = sr.json()
        bw = d.get('bands_avg') or d.get('brainwave_data') or {}
        print(f"    bands_avg: {bw}")
        print(f"    mbti: {d.get('mbti')}")
        print(f"    braindna: {d.get('braindna_result')}")
