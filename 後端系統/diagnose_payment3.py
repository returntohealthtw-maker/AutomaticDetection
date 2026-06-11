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

# 找郭逸榛做過的所有檢測
print("=== 所有 Sessions (找郭逸榛相關) ===")
r = s.get(f"{BASE}/api/v1/eeg/sessions", timeout=20)
sess_data = r.json()
all_sess = sess_data if isinstance(sess_data, list) else sess_data.get("sessions", sess_data.get("items", []))
print(f"Total sessions: {len(all_sess)}")
guozhen_sess = [x for x in all_sess if "郭逸榛" in str(x.get("consultant_name","")) or "劉" in str(x.get("subject_name",""))]
for ss in guozhen_sess:
    print(f"  session {ss.get('session_id')} | {ss.get('subject_name')} | consultant={ss.get('consultant_name')} | captures={ss.get('total_captures')} | created={ss.get('created_at')}")

# 找所有報告
print("\n=== 所有 Reports (找郭逸榛相關) ===")
r2 = s.get(f"{BASE}/api/v1/reports/list", timeout=20)
reports = r2.json().get("reports", [])
print(f"Total reports: {len(reports)}")
guozhen_rep = [x for x in reports if "郭逸榛" in str(x.get("consultant","")) or "劉" in str(x.get("subject_name",""))]
for rep in guozhen_rep:
    print(f"  report {rep.get('report_id')} | {rep.get('subject_name')} | session={rep.get('session_id')} | status={rep.get('status')} | kind={rep.get('report_kind')} | created={str(rep.get('created_at',''))[:19]}")

# 找所有付款
print("\n=== 所有 Payments (找劉相關) ===")
r3 = s.get(f"{BASE}/api/v1/payments/my", timeout=15)
payments = r3.json().get("payments", [])
print(f"Total payments: {len(payments)}")
liu_pays = [p for p in payments if "劉" in str(p.get("subject_name","")) or "郭逸榛" in str(p.get("consultant_name",""))]
for p in liu_pays:
    print(f"  pay {p.get('payment_id')} | {p.get('subject_name')} | order={p.get('order_id')} | status={p.get('status')} | session_id={p.get('session_id')} | type={p.get('report_type')} | paid={str(p.get('paid_at',''))[:16]}")

# 找 subjects
print("\n=== Subjects (找劉) ===")
r4 = s.get(f"{BASE}/api/v1/subjects", timeout=15)
subj_data = r4.json()
subjects = subj_data if isinstance(subj_data, list) else subj_data.get("items", subj_data.get("subjects",[]))
liu_subj = [x for x in subjects if "劉" in str(x.get("name",""))]
for subj in liu_subj:
    print(f"  subject {subj.get('subject_id')} | {subj.get('name')} | sessions={subj.get('session_count','')} | reports={subj.get('report_count','')}")
    print(f"    email={subj.get('email')} | phone={subj.get('phone')} | consultant_id={subj.get('consultant_id')}")
