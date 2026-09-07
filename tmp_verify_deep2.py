"""
1. 查看 regenerate 500 的根本原因（查 Railway 日誌）
2. 查看 job hl-82c9c13eb45b 的進度（個人報告再生成）
3. 查看 report #130 的 client_summary 完整內容
"""
import sys, requests, urllib3, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

print("=" * 60)
print("1. 個人報告 job hl-82c9c13eb45b 的狀態")
print("=" * 60)
jr = requests.get(BASE+'/reports/job-status/hl-82c9c13eb45b', headers=h, verify=False)
print(f"  Status: {jr.status_code}")
print(f"  Body: {jr.text[:300]}")

print()
print("=" * 60)
print("2. Report #135 最新狀態")
print("=" * 60)
rr = requests.get(BASE+'/reports/diag/report/135', headers=h, verify=False)
print(f"  {rr.json()}")

print()
print("=" * 60)
print("3. Report #130 client_summary 完整內容")
print("=" * 60)
# Use direct DB check via diag endpoint
rr130 = requests.get(BASE+'/reports/diag/report/130', headers=h, verify=False)
print(f"  {rr130.json()}")
# Try to get client_summary via another way
rr130s = requests.get(BASE+'/reports/session/112/signed-url?report_id=130', headers=h, verify=False)
if rr130s.ok:
    d = rr130s.json()
    print(f"  gcs_path: {d.get('gcs_path')}")

print()
print("=" * 60)
print("4. regenerate 500 詳細錯誤 - 嘗試帶 accept:application/json header")
print("=" * 60)
h2 = dict(h)
h2['Accept'] = 'application/json'
rgen = requests.post(BASE+'/reports/sessions/112/regenerate', json={'report_id': 130}, headers=h2, verify=False)
print(f"  Status: {rgen.status_code}")
print(f"  Headers: content-type={rgen.headers.get('content-type')}")
print(f"  Body: {rgen.text[:500]}")

print()
print("=" * 60)
print("5. orchestrator debug - marital URL 是否設定正確")
print("=" * 60)
orch_r = requests.get(BASE+'/reports/orchestrator-status', headers=h, verify=False)
print(f"  Status: {orch_r.status_code}")
print(f"  Body: {orch_r.text[:500]}")
