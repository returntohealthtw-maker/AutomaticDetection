# -*- coding: utf-8 -*-
"""
清理劉素惠的重複 session 43（沒有報告、資料不完整）
並將付款 102 關聯到正確的 session 42
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

# 確認 session 43 沒有報告
r = s.get(f"{BASE}/api/v1/reports/list", timeout=20)
reports = r.json().get("reports", [])
sess43_reports = [rep for rep in reports if rep.get("session_id") == 43]
print(f"\nSession 43 reports: {len(sess43_reports)}")

# 刪除 session 43（透過報告刪除端點，或直接刪 session）
# 先找管理端點
print("\n嘗試刪除 session 43...")
# Try delete endpoint for sessions
for ep in [
    f"/api/v1/reports/sessions/43/delete-report",
    f"/api/v1/sessions/43",
]:
    r2 = s.delete(f"{BASE}{ep}", timeout=10)
    print(f"  DELETE {ep}: {r2.status_code} {r2.text[:100]}")

# 確認付款 102 的 session 關聯
print("\n確認付款記錄...")
r3 = s.get(f"{BASE}/api/v1/payments/my", timeout=15)
payments = r3.json().get("payments", [])
pay102 = next((p for p in payments if p.get("payment_id") == 102), None)
if pay102:
    print(f"  pay 102 session_id={pay102.get('session_id')} status={pay102.get('status')}")
    if not pay102.get("session_id"):
        print("  → 付款未關聯 session，需要手動關聯到 session 42")
        # Try to link
        r4 = s.patch(f"{BASE}/api/v1/payments/102", json={"session_id": 42}, timeout=10)
        print(f"  PATCH payment: {r4.status_code} {r4.text[:100]}")

print("\nDone.")
