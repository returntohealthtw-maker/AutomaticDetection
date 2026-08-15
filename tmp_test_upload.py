import sys, requests, urllib3, time
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

print("=== 1. 測試 /sessions/upload 是否正常 ===")
import datetime
now_ts = int(time.time())
captures = []
for i in range(5):
    captures.append({
        "seq_num": i, "captured_at": now_ts + i,
        "is_baseline": 0, "good_signal": 0,
        "attention": 55, "meditation": 45,
        "delta": 250000, "theta": 120000,
        "low_alpha": 30000, "high_alpha": 20000,
        "low_beta": 15000, "high_beta": 12000,
        "low_gamma": 8000, "high_gamma": 3000
    })
body = {
    "subject_name": "測試upload",
    "consultant_name": "admin",
    "report_type": "life_script",
    "subject_age": 40,
    "subject_gender": "F",
    "session_duration": 5,
    "total_captures": 5,
    "captures": captures
}
resp = requests.post(BASE+'/sessions/upload', json=body, verify=False, timeout=15)
print(f"  HTTP {resp.status_code}")
try:
    j = resp.json()
    print(f"  session_id={j.get('session_id')} message={j.get('message','')}")
    if resp.status_code != 200:
        print(f"  detail={j.get('detail','')}")
        print(f"  full={j}")
except:
    print(f"  body={resp.text[:400]}")

print()
print("=== 2. 查詢 Railway health ===")
h2 = requests.get(BASE.replace('/api/v1','')+'/health', verify=False, timeout=8).json()
print(f"  status={h2.get('status')} db={h2.get('db','?')}")
