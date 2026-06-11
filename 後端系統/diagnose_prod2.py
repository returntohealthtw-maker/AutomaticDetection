"""
深入診斷邱心又報告生成歷史
"""
import requests, json, urllib3
urllib3.disable_warnings()

BASE = "https://backend-production-2da61.up.railway.app"
s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login", json={"phone":"0900000000","password":"admin123"}, timeout=10).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"
print("Logged in OK")

SESSION_ID = 40
REPORT_ID  = 45

# 1. Session 詳細資訊
r = s.get(f"{BASE}/api/v1/sessions/{SESSION_ID}", timeout=10)
print(f"\n[Session {SESSION_ID}]")
if r.status_code == 200:
    print(json.dumps(r.json(), ensure_ascii=False, indent=2)[:1000])
else:
    print(r.status_code, r.text[:200])

# 2. 生成事件（正確 endpoint）
r2 = s.get(f"{BASE}/api/v1/reports/events/sessions", timeout=10)
print(f"\n[Events endpoint check] {r2.status_code}")

# Try the events endpoint with different approaches
for ep in [
    f"/api/v1/reports/events",
    f"/api/v1/reports/events/sessions",
]:
    r3 = s.get(f"{BASE}{ep}", params={"session_id": SESSION_ID}, timeout=10)
    print(f"  GET {ep}?session_id={SESSION_ID} -> {r3.status_code} {r3.text[:80]}")

# 3. 同場次的所有報告 (包含刪除的)
r4 = s.get(f"{BASE}/api/v1/reports/sessions-with-status", timeout=15)
if r4.status_code == 200:
    items = r4.json() if isinstance(r4.json(), list) else r4.json().get("items", [])
    target = [x for x in items if "邱" in str(x) or str(SESSION_ID) in str(x.get("session_id",""))]
    print(f"\n[Sessions-with-status for session {SESSION_ID}]")
    for t in target:
        print(json.dumps(t, ensure_ascii=False)[:200])

# 4. 所有 sessions，找邱心又
r5 = s.get(f"{BASE}/api/v1/eeg/sessions", timeout=15)
if r5.status_code == 200:
    sess_data = r5.json()
    sessions = sess_data if isinstance(sess_data, list) else sess_data.get("sessions", sess_data.get("items",[]))
    target_sess = [x for x in sessions if "邱" in str(x.get("subject_name",""))]
    print(f"\n[All sessions for 邱心又]: {len(target_sess)}")
    for s2 in target_sess:
        print(f"  session_id={s2.get('session_id')} status={s2.get('status')} "
              f"captures={s2.get('total_captures')} created={str(s2.get('created_at',''))[:19]}")

# 5. 報告的完整詳情
r6 = s.get(f"{BASE}/api/v1/reports/{REPORT_ID}", timeout=10)
print(f"\n[Report {REPORT_ID} detail] {r6.status_code}")
if r6.status_code == 200:
    print(json.dumps(r6.json(), ensure_ascii=False, indent=2)[:800])

# 6. 生成 jobs 狀況
r7 = s.get(f"{BASE}/api/v1/report-gen/active-jobs", timeout=10)
print(f"\n[Active jobs] {r7.status_code}")
if r7.status_code == 200:
    print(json.dumps(r7.json(), ensure_ascii=False)[:400])

# 7. headless health
r8 = s.get(f"{BASE}/api/v1/report-gen/health", timeout=10)
print(f"\n[Report-gen health] {r8.status_code}")
if r8.status_code == 200:
    print(json.dumps(r8.json(), ensure_ascii=False, indent=2)[:600])
