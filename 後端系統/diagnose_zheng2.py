"""深入診斷 session 87 / 鄭靜怡"""
import sys, io, json, requests, urllib3
from datetime import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()

BASE = "https://backend-production-2da61.up.railway.app"
SID = 87
NAME = "鄭靜怡"

s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=15).json()["token"]
s.headers["Authorization"] = f"Bearer {TOKEN}"

def get(path, **kw):
    r = s.get(f"{BASE}{path}", timeout=30, **kw)
    try: return r.status_code, r.json()
    except: return r.status_code, r.text[:500]

# sessions-with-status
code, data = get("/api/v1/reports/sessions-with-status?page=1&limit=200")
sessions = data.get("sessions", []) if isinstance(data, dict) else []
match = [x for x in sessions if x.get("session_id") == SID]
print("=== sessions-with-status ===")
if match:
    x = match[0]
    for k in sorted(x.keys()):
        v = x[k]
        if v is not None and v != "" and v != False:
            print(f"  {k}: {v}")
else:
    print("  未找到 session 87")

# 查所有 events 中 session_id=87
code, data = get("/api/v1/reports/events/sessions?limit=500")
evs = data.get("sessions", []) if isinstance(data, dict) else []
match_ev = [e for e in evs if e.get("session_id") == SID]
print(f"\n=== generation events (session_id={SID}) ===")
print(f"  找到 {len(match_ev)} 筆")
for e in match_ev:
    print(json.dumps(e, ensure_ascii=False, indent=2))

# headless jobs
code, data = get("/api/v1/reports/headless/jobs")
jobs = data.get("jobs", []) if isinstance(data, dict) else []
match_jobs = [j for j in jobs if j.get("session_id") == SID or SID in str(j.get("target_url",""))]
print(f"\n=== headless jobs (session {SID}) ===")
print(f"  全部 active jobs: {len(jobs)}, 符合: {len(match_jobs)}")
for j in match_jobs:
    print(json.dumps(j, ensure_ascii=False, indent=2, default=str))

# 查所有 failed jobs 看有沒有 鄭靜怡
failed_jobs = [j for j in jobs if j.get("status") == "failed"]
print(f"\n=== 最近 failed headless jobs ({len(failed_jobs)}) ===")
for j in failed_jobs[-10:]:
    print(f"  job={j.get('job_id')} session={j.get('session_id')} error={str(j.get('error',''))[:120]}")

# report list 詳細
code, data = get("/api/v1/reports/list")
reports = [r for r in data.get("reports",[]) if r.get("session_id") == SID]
print(f"\n=== report list session {SID} ===")
for r in reports:
    print(json.dumps(r, ensure_ascii=False, indent=2))

# 查 subjects
code, data = get("/api/v1/subjects?limit=500")
subjects = data.get("subjects", []) if isinstance(data, dict) else []
match_subj = [x for x in subjects if NAME in (x.get("name") or "")]
print(f"\n=== subjects ===")
for x in match_subj:
    print(json.dumps(x, ensure_ascii=False, indent=2, default=str))

# created_at 轉換
if match:
    ts = match[0].get("created_at")
    if ts:
        print(f"\n=== 時間 ===")
        print(f"  session created: {datetime.fromtimestamp(ts)}")

# firebase sync status if exists
code, data = get(f"/api/v1/admin/firebase-sync/status")
if code == 200:
    print(f"\n=== firebase sync ===")
    if isinstance(data, dict):
        pending = [x for x in data.get("pending", []) if x.get("session_id") == SID]
        failed = [x for x in data.get("failed", []) if x.get("session_id") == SID]
        print(f"  pending for sid87: {pending}")
        print(f"  failed for sid87: {failed}")
