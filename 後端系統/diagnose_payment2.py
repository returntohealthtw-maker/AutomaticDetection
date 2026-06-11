# -*- coding: utf-8 -*-
"""
診斷劉秦惠的付款與報告關聯 (UTF-8)
"""
import requests, json, urllib3, sys
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE = "https://backend-production-2da61.up.railway.app"
NAME = "劉秦惠"

s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=10
               ).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"
print("Logged in OK")

# 1. 所有報告
r = s.get(f"{BASE}/api/v1/reports/list", timeout=20)
reports = r.json().get("reports", [])
target_rep = [rep for rep in reports if NAME in str(rep.get("subject_name",""))]
print(f"\n[Reports for {NAME}]: {len(target_rep)} 份")
for rep in target_rep:
    print(f"  report_id={rep.get('report_id')} session_id={rep.get('session_id')} "
          f"status={rep.get('status')} kind={rep.get('report_kind')} "
          f"created={str(rep.get('created_at',''))[:19]}")
    print(f"  pdf={str(rep.get('pdf_url',''))[:60]}")

# 2. 付款記錄（全部找劉秦惠）
r3 = s.get(f"{BASE}/api/v1/payments/my", params={"limit":200}, timeout=15)
payments = r3.json().get("payments", [])
target_pay = [p for p in payments if NAME in str(p.get("subject_name",""))]
print(f"\n[Payments for {NAME}]: {len(target_pay)} 筆")
for p in target_pay:
    print(f"\n  payment_id={p.get('payment_id')} order_id={p.get('order_id')} "
          f"type={p.get('report_type')} amount={p.get('amount')}")
    print(f"  status={p.get('status')} session_id={p.get('session_id')} "
          f"paid_at={str(p.get('paid_at',''))[:19]}")
    print(f"  consultant={p.get('consultant_name')} subject_email={p.get('subject_email')}")

# 3. Sessions（透過 reports 的 session_id 去查）
if target_rep:
    for rep in target_rep:
        sid = rep.get("session_id")
        if sid:
            rs = s.get(f"{BASE}/api/v1/sessions/{sid}", timeout=10)
            if rs.status_code == 200:
                sess = rs.json()
                print(f"\n[Session {sid}]")
                print(f"  captures={sess.get('total_captures')} "
                      f"status={sess.get('status')} "
                      f"report_type={sess.get('report_type')}")
                print(f"  created_at={sess.get('created_at')} "
                      f"start_time={sess.get('start_time')}")
                print(f"  consultant={sess.get('consultant_name')}")

# 4. 找 payment 和 session 的關聯
print(f"\n[Payment <-> Session 關聯分析]")
# Check if payment has session_id
if target_pay:
    for p in target_pay:
        sid = p.get("session_id")
        print(f"  payment {p.get('payment_id')} -> session_id={sid}")
        if sid:
            rs = s.get(f"{BASE}/api/v1/sessions/{sid}", timeout=10)
            print(f"    session status: {rs.status_code}")
        else:
            print(f"    payment has NO session_id linked")

# 5. 看看有幾份報告是相同 subject 但不同 session
print(f"\n[All reports summary]")
for rep in target_rep:
    r_events = s.get(f"{BASE}/api/v1/reports/events/sessions",
                     params={"session_id": rep.get("session_id")}, timeout=10)
