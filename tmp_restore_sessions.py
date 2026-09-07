"""
1. 查詢 Playwright 實際狀態
2. 若 headless 失敗，把 session 110/111 的 report 狀態復原
"""
import requests, sys, json
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}', 'Content-Type': 'application/json'}

# 嘗試各診斷端點
print("=== 診斷端點 ===")
for ep in ['/api/v1/report-gen/diag', '/api/v1/monitor/system-info',
           '/api/v1/monitor/headless-diag', '/api/v1/monitor/report-diag']:
    try:
        rv = requests.get(f'{BASE}{ep}', headers=H, timeout=8, verify=False)
        print(f"  {ep}: HTTP {rv.status_code} → {rv.text[:200]}")
    except Exception as e:
        print(f"  {ep}: {e}")

# 查 report 128（session 110）與 report 129（session 111）的目前狀態
print("\n=== 目前 report 狀態 ===")
for sid in [110, 111]:
    r2 = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=15, verify=False)
    d = r2.json()
    print(f"  session {sid}: status={d.get('report_status')}  url={bool(d.get('report_url'))}")

# 嘗試重置 report 狀態（用 monitor 端點）
print("\n=== 嘗試透過 monitor 批次重算重置 ===")
# 查是否有 reset_report_status 端點
for ep in ['/api/v1/monitor/reset-report-status',
           '/api/v1/monitor/fix-stuck-reports',
           '/api/v1/monitor/reports/reset']:
    try:
        rv = requests.post(f'{BASE}{ep}', headers=H, json={'session_ids': [110, 111]}, timeout=8, verify=False)
        print(f"  {ep}: HTTP {rv.status_code} → {rv.text[:100]}")
    except Exception as e:
        print(f"  {ep}: {e}")

# 最直接：用 db 端點 patch
# 嘗試 PATCH /api/v1/reports/sessions/{sid}/status
print("\n=== 嘗試 PATCH report status ===")
for sid, old_status in [(110, 'generating'), (111, 'generating')]:
    for ep in [f'/api/v1/reports/sessions/{sid}/status',
               f'/api/v1/monitor/sessions/{sid}/report-status']:
        try:
            rv = requests.patch(f'{BASE}{ep}', headers=H,
                                json={'status': 'failed'}, timeout=8, verify=False)
            print(f"  PATCH {ep}: HTTP {rv.status_code} → {rv.text[:100]}")
            if rv.status_code in [200, 204]:
                break
        except Exception as e:
            print(f"  PATCH {ep}: {e}")
