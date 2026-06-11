"""
診斷劉秦惠的付款與報告關聯
"""
import requests, json, urllib3
urllib3.disable_warnings()

BASE = "https://backend-production-2da61.up.railway.app"
NAME = "劉秦惠"

s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=10
               ).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"
print("Logged in OK")

# 1. 找所有報告
r = s.get(f"{BASE}/api/v1/reports/list", timeout=20)
reports = r.json().get("reports", [])
target = [rep for rep in reports if NAME in str(rep.get("subject_name",""))]
print(f"\n[Reports for {NAME}]: {len(target)} 份")
for rep in target:
    print(f"\n  report_id={rep.get('report_id')} session_id={rep.get('session_id')} "
          f"status={rep.get('status')} kind={rep.get('report_kind')} "
          f"created={str(rep.get('created_at',''))[:19]}")
    print(f"  consultant={rep.get('consultant')} pdf={str(rep.get('pdf_url',''))[:60]}")

# 2. 找所有 sessions
r2 = s.get(f"{BASE}/api/v1/eeg/sessions", timeout=15)
sess_data = r2.json()
sessions_list = sess_data if isinstance(sess_data, list) else sess_data.get("sessions", sess_data.get("items", []))
target_sess = [x for x in sessions_list if NAME in str(x.get("subject_name",""))]
print(f"\n[Sessions for {NAME}]: {len(target_sess)} 筆")
for ss in target_sess:
    print(f"  session_id={ss.get('session_id')} status={ss.get('status')} "
          f"captures={ss.get('total_captures')} type={ss.get('report_type')} "
          f"created={ss.get('created_at')}")

# 3. 找付款記錄
r3 = s.get(f"{BASE}/api/v1/payments/my", timeout=10)
print(f"\n[My payments] {r3.status_code}: {r3.text[:200]}")

r4 = s.get(f"{BASE}/api/v1/payments/admin/paid-not-detected", timeout=10)
print(f"\n[Paid but no session] {r4.status_code}: {r4.text[:300]}")

# 4. 找 subjects
r5 = s.get(f"{BASE}/api/v1/subjects", timeout=15)
subj_data = r5.json()
subjects = subj_data if isinstance(subj_data, list) else subj_data.get("items", [])
target_subj = [x for x in subjects if NAME in str(x.get("name",""))]
print(f"\n[Subjects for {NAME}]: {len(target_subj)}")
for subj in target_subj:
    print(json.dumps(subj, ensure_ascii=False, indent=2)[:400])
