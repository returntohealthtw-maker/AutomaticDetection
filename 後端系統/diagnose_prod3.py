"""
深入診斷：生成事件歷史 + 活躍 jobs
"""
import requests, json, urllib3
urllib3.disable_warnings()

BASE = "https://backend-production-2da61.up.railway.app"
s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login", json={"phone":"0900000000","password":"admin123"}, timeout=10).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"

SESSION_ID = 40

# 1. 全部生成事件，篩出 session 40
r = s.get(f"{BASE}/api/v1/reports/events/sessions", timeout=20)
data = r.json()
all_sessions = data.get("sessions", [])
print(f"Total event sessions: {len(all_sessions)}")

target = [x for x in all_sessions if x.get("session_id") == SESSION_ID or "邱" in str(x.get("subject_name",""))]
print(f"Events for session {SESSION_ID}: {len(target)}")
for t in target:
    print(json.dumps(t, ensure_ascii=False, indent=2)[:600])

# 2. 取 session 40 的所有 events
r2 = s.get(f"{BASE}/api/v1/reports/events/sessions", timeout=20)
# Find correlation_id for session 40
if r2.status_code == 200:
    sessions_data = r2.json().get("sessions", [])
    for sess in sessions_data:
        if sess.get("session_id") == SESSION_ID:
            corr_id = sess.get("correlation_id")
            print(f"\nCorrelation ID for session {SESSION_ID}: {corr_id}")
            # Get events for this correlation
            r3 = s.get(f"{BASE}/api/v1/reports/events/{corr_id}", timeout=10)
            if r3.status_code == 200:
                evts = r3.json()
                print(f"Events detail:")
                evts_list = evts if isinstance(evts, list) else evts.get("events", [])
                for e in evts_list:
                    err = e.get('error_message') or ''
                    payload = e.get('payload_json','') or ''
                    print(f"  [{e.get('phase')}] dur={e.get('duration_ms')}ms "
                          f"ts={str(e.get('created_at',''))[:19]}")
                    if err:
                        print(f"    ERROR: {err[:200]}")
                    if payload and len(payload) < 200:
                        print(f"    payload: {payload}")
            else:
                print(f"events detail: {r3.status_code} {r3.text[:100]}")

# 3. 所有活躍 jobs 完整資訊
r4 = s.get(f"{BASE}/api/v1/report-gen/active-jobs", timeout=10)
jobs = r4.json().get("jobs", [])
print(f"\n[Active jobs: {len(jobs)}]")
for j in jobs:
    print(f"\n  job_id={j.get('job_id')} type={j.get('report_type')} "
          f"name={j.get('subject_name')} status={j.get('status')} "
          f"elapsed={j.get('elapsed_min'):.1f}min error={j.get('error')}")
    print(f"  vercel_url={str(j.get('vercel_url',''))[:120]}")

# 4. 顯示 sessions-with-status（找邱心又的 session 狀態）
r5 = s.get(f"{BASE}/api/v1/reports/sessions-with-status", timeout=15)
if r5.status_code == 200:
    items = r5.json() if isinstance(r5.json(), list) else r5.json().get("items",[])
    target2 = [x for x in items if "邱" in str(x) or x.get("session_id") == SESSION_ID]
    print(f"\n[sessions-with-status for 邱心又]")
    for t in target2:
        print(json.dumps(t, ensure_ascii=False)[:300])
