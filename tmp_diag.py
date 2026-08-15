import requests, sys, time
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}'}

# headless renderer 診斷
print("headless renderer 診斷：")
try:
    rd = requests.get(f'{BASE}/api/v1/report-gen/diag', headers=H, timeout=15, verify=False)
    print(f"  HTTP {rd.status_code}: {rd.text[:500]}")
except Exception as e:
    print(f"  diag 端點失敗: {e}")

# 查 active jobs
print("\nactive jobs：")
try:
    rj = requests.get(f'{BASE}/api/v1/report-gen/jobs', headers=H, timeout=15, verify=False)
    print(f"  HTTP {rj.status_code}: {rj.text[:300]}")
except Exception as e:
    print(f"  jobs 端點: {e}")

# 確認 sessions 111 目前狀態
print("\nsession 111 目前狀態：")
r3 = requests.get(f'{BASE}/api/v1/eeg/sessions/111/stats', headers=H, timeout=15, verify=False)
d = r3.json()
print(f"  status={d.get('report_status')}  url={'...' + (d.get('report_url') or '')[-25:] if d.get('report_url') else '(空)'}")
