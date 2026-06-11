# -*- coding: utf-8 -*-
import requests, json, urllib3, sys
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE = "https://backend-production-2da61.up.railway.app"
s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=10
               ).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"

# Session 42 vs 43 詳細比較
for sid in [42, 43]:
    r = s.get(f"{BASE}/api/v1/sessions/{sid}", timeout=10)
    print(f"\n[Session {sid}] status={r.status_code}")
    if r.status_code == 200:
        d = r.json()
        print(f"  subject_name={d.get('subject_name')} captures={d.get('total_captures')}")
        print(f"  start_time={d.get('start_time')} end_time={d.get('end_time')}")
        print(f"  created_at={d.get('created_at')} consultant={d.get('consultant_name')}")
        print(f"  report_type={d.get('report_type')} subject_id={d.get('subject_id')}")

# 所有報告（找 session 43 的）
r2 = s.get(f"{BASE}/api/v1/reports/list", timeout=20)
reports = r2.json().get("reports", [])
sess_42_reps = [rep for rep in reports if rep.get("session_id") == 42]
sess_43_reps = [rep for rep in reports if rep.get("session_id") == 43]
print(f"\n[Reports for session 42]: {len(sess_42_reps)}")
for rep in sess_42_reps:
    print(f"  report {rep.get('report_id')} status={rep.get('status')} kind={rep.get('report_kind')} created={str(rep.get('created_at',''))[:19]}")
print(f"\n[Reports for session 43]: {len(sess_43_reps)}")
for rep in sess_43_reps:
    print(f"  report {rep.get('report_id')} status={rep.get('status')} kind={rep.get('report_kind')}")

# 付款記錄時間分析
r3 = s.get(f"{BASE}/api/v1/payments/my", timeout=15)
payments = r3.json().get("payments", [])
target_pay = [p for p in payments if "劉" in str(p.get("subject_name",""))]
print(f"\n[Payment timeline]")
for p in target_pay:
    paid_ts = p.get('paid_at', 0)
    print(f"  pay {p.get('payment_id')} paid_at={paid_ts} ({paid_ts})")
    print(f"  session 42 created_at=1780732704 (diff from payment: {1780732704 - paid_ts}s)")
    print(f"  session 43 created_at=1780733012 (diff from payment: {1780733012 - paid_ts}s)")
    print(f"  session gap: {1780733012 - 1780732704}s = {(1780733012-1780732704)//60}min {(1780733012-1780732704)%60}s")

# EEG captures 樣本比較（前 5 筆）
r4 = s.get(f"{BASE}/api/v1/eeg/sessions/{42}/stats", timeout=10)
r5 = s.get(f"{BASE}/api/v1/eeg/sessions/{43}/stats", timeout=10)
print(f"\n[EEG stats session 42] {r4.status_code}: {r4.text[:200]}")
print(f"\n[EEG stats session 43] {r5.status_code}: {r5.text[:200]}")
