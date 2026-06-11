# -*- coding: utf-8 -*-
"""
清理生產環境的重複 session 43，並關聯付款 102 到 session 42
"""
import requests, json, urllib3, sys
urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8')

BASE = "https://backend-production-2da61.up.railway.app"
s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=10
               ).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"
print("Logged in OK")

# 1. 刪除 session 43（重複、無報告、資料不完整）
print("\n[1] 刪除重複 session 43...")
r1 = s.delete(f"{BASE}/api/v1/admin/sessions/43", timeout=10)
print(f"  DELETE session 43: {r1.status_code} {r1.text[:200]}")

# 2. 關聯付款 102 到 session 42
print("\n[2] 關聯付款 102 → session 42...")
r2 = s.post(f"{BASE}/api/v1/admin/payments/102/link-session",
            params={"session_id": 42}, timeout=10)
print(f"  POST link payment: {r2.status_code} {r2.text[:200]}")

# 3. 驗證結果
print("\n[3] 驗證結果...")
r3 = s.get(f"{BASE}/api/v1/sessions/42", timeout=8)
print(f"  Session 42: {r3.status_code} {r3.text[:100]}")
r4 = s.get(f"{BASE}/api/v1/sessions/43", timeout=8)
print(f"  Session 43: {r4.status_code} {r4.text[:80]} (should be 404)")

# 確認 reports
r5 = s.get(f"{BASE}/api/v1/reports/list", timeout=20)
reports = r5.json().get("reports", [])
liu_reps = [rep for rep in reports if "劉素惠" in str(rep.get("subject_name",""))]
print(f"\n  劉素惠報告數: {len(liu_reps)} (應為 1)")
for rep in liu_reps:
    print(f"    report {rep.get('report_id')} session={rep.get('session_id')} status={rep.get('status')}")
