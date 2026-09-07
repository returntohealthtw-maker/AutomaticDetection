import sys, requests, urllib3, datetime, time
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 1. 確認 /sessions/upload 現在是否正常（用真實大小180筆）
print("=== 測試180筆 upload ===")
now_ts = int(time.time())
caps = []
import random
for i in range(180):
    caps.append({
        "seq_num": i, "captured_at": now_ts + i,
        "is_baseline": 0, "good_signal": 0,
        "attention": random.randint(40,70), "meditation": random.randint(30,60),
        "delta": random.randint(150000, 300000),
        "theta": random.randint(80000, 180000),
        "low_alpha": random.randint(20000, 60000),
        "high_alpha": random.randint(15000, 40000),
        "low_beta":  random.randint(10000, 25000),
        "high_beta":  random.randint(8000, 20000),
        "low_gamma": random.randint(3000, 12000),
        "high_gamma": random.randint(2000, 8000),
    })
body = {
    "subject_name": "鄭靜怡",
    "consultant_name": "admin",
    "report_type": "life_script",
    "subject_age": 49,
    "subject_gender": "F",
    "session_duration": 180,
    "total_captures": 180,
    "captures": caps
}
resp = requests.post(BASE+'/sessions/upload', json=body, verify=False, timeout=30)
print(f"  HTTP {resp.status_code}")
try:
    j = resp.json()
    print(f"  session_id={j.get('session_id')} message={j.get('message','')}")
    if resp.status_code != 200:
        print(f"  ERROR: {j}")
except:
    print(f"  body={resp.text[:400]}")

# 2. 查最新 sessions
print()
sl = requests.get(BASE+'/eeg/sessions?limit=200', headers=h, verify=False, timeout=15)
all_s = sl.json().get('sessions', [])
print(f"總 sessions: {len(all_s)}")
for s in all_s[:5]:
    ca = s.get('created_at', 0)
    try: dt = datetime.datetime.fromtimestamp(int(ca)).strftime('%m/%d %H:%M')
    except: dt = str(ca)
    print(f"  #{s.get('session_id')} {(s.get('subject_name') or '?'):12s} {dt} captures={s.get('total_captures','?')}")

# 3. 查 health
health = requests.get(BASE.replace('/api/v1','') + '/health', verify=False, timeout=8)
print(f"\n/health: HTTP {health.status_code}")
try: print(f"  {health.json()}")
except: print(f"  {health.text[:100]}")
