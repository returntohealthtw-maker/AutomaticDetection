import requests, sys
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}', 'Content-Type': 'application/json'}

# 確認 Railway 服務可用
print("Railway 服務確認：")
for ep in ['/api/v1/eeg/sessions', '/api/v1/reports/sessions/110/regenerate']:
    try:
        rv = requests.get(f'{BASE}{ep}', headers=H, timeout=8, verify=False) if 'GET' in ep else None
        print(f"  GET {ep}: OK")
    except Exception as e:
        print(f"  {ep}: {e}")

# 查 report job hl-05d705b645b7
JOB = 'hl-05d705b645b7'
print(f"\n查 job {JOB}:")
rj = requests.get(f'{BASE}/api/v1/report-gen/pdf/{JOB}', headers=H, timeout=10, verify=False)
print(f"  HTTP {rj.status_code}: {rj.text[:200]}")

# 查 report 128 狀態（直接查 report table）
print("\n查 session 110 所有 report 資訊：")
r2 = requests.get(f'{BASE}/api/v1/eeg/sessions/110/stats', headers=H, timeout=15, verify=False)
d = r2.json()
print(f"  report_status: {d.get('report_status')}")
print(f"  report_url: {d.get('report_url','')[:80] or '(空)'}")
print(f"  qeeg_abilities: {d.get('qeeg_abilities')}")

# 嘗試強制重置狀態並重新生成
print("\n嘗試強制重置 report 狀態...")
# 先查 jobs list
rlist = requests.get(f'{BASE}/api/v1/report-gen/jobs', headers=H, timeout=10, verify=False)
print(f"  jobs list: HTTP {rlist.status_code} - {rlist.text[:200]}")
