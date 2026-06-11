"""
診斷 Railway 生產環境中邱心又的報告生成失敗原因
"""
import requests, json, urllib3
urllib3.disable_warnings()

BASE = "https://backend-production-2da61.up.railway.app"
NAME = "邱心又"

s = requests.Session()
s.verify = False

# 1. 登入
r = s.post(f"{BASE}/api/v1/auth/login", json={"phone":"0900000000","password":"admin123"}, timeout=10)
TOKEN = r.json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"
print(f"Logged in OK. Token: {TOKEN[:30]}...")

# 2. 查所有報告
r = s.get(f"{BASE}/api/v1/reports/list", timeout=20)
data = r.json()
reports = data.get("reports", data if isinstance(data, list) else [])
print(f"Total reports in production: {len(reports)}")

target = [rep for rep in reports if NAME in str(rep.get("subject_name",""))]
print(f"Reports for [{NAME}]: {len(target)}")

for rep in target:
    print("\n" + "="*60)
    for k,v in rep.items():
        print(f"  {k}: {v}")

# 3. 生成事件記錄
if target:
    for rep in target:
        sid = rep.get("session_id")
        rid = rep.get("report_id")
        print(f"\n--- Events for report_id={rid} session_id={sid} ---")
        # Try events endpoint
        r2 = s.get(f"{BASE}/api/v1/reports/events", params={"session_id": sid}, timeout=10)
        if r2.status_code == 200:
            evts = r2.json() if isinstance(r2.json(), list) else r2.json().get("events",[])
            print(f"Events count: {len(evts)}")
            for e in evts[-15:]:
                err = e.get('error_message') or ''
                print(f"  [{e.get('phase')}] {err[:120]} dur={e.get('duration_ms')}ms ts={e.get('created_at','')[:19]}")
        else:
            print(f"  events endpoint: {r2.status_code} {r2.text[:100]}")

        # Try diag
        r3 = s.get(f"{BASE}/api/v1/reports/diag", timeout=10)
        if r3.status_code == 200:
            diag = r3.json()
            print(f"\nDiag: {json.dumps(diag, ensure_ascii=False)[:300]}")

# 4. 顯示所有失敗報告
failed = [rep for rep in reports if rep.get("status") in ["failed","error","generating","pending"]]
print(f"\n--- All non-completed reports ({len(failed)}) ---")
for rep in failed:
    print(f"  report_id={rep.get('report_id')} session_id={rep.get('session_id')} "
          f"name={rep.get('subject_name')} status={rep.get('status')} "
          f"created={str(rep.get('created_at',''))[:16]}")
