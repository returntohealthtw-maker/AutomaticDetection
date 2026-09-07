import sys, requests, urllib3, datetime
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

# 1. 後端健康狀態
health = requests.get(BASE.replace('/api/v1','')+'/health', verify=False, timeout=8)
print(f"後端健康狀態: {health.status_code} {health.json()}")

# 2. 模擬一筆真實上傳（測試 /sessions/upload 現在是否正常）
import time, random
random.seed(999)
now_s = int(time.time())

captures = []
for i in range(10):
    captures.append({
        "seq_num": i, "is_baseline": False,
        "captured_at": now_s - 180 + i,   # 秒（不是毫秒）
        "good_signal": 0,
        "delta":     random.randint(100000, 250000),
        "theta":     random.randint(30000, 80000),
        "low_alpha": random.randint(8000, 20000),
        "high_alpha": random.randint(5000, 15000),
        "low_beta":  random.randint(5000, 12000),
        "high_beta": random.randint(4000, 10000),
        "low_gamma": random.randint(2000, 6000),
        "high_gamma":random.randint(1000, 4000),
        "attention": random.randint(40, 80),
        "meditation":random.randint(40, 80),
    })

payload = {
    "subject_name": "_verify_upload_test",
    "report_type": "life_script",
    "consultant_name": "admin",
    "captures": captures,
}
resp = requests.post(BASE+'/sessions/upload', json=payload, verify=False, timeout=15)
print(f"\n上傳測試: HTTP {resp.status_code}")
if resp.status_code == 200:
    print(f"  session_id={resp.json().get('session_id')} ✅ 上傳正常")
else:
    print(f"  錯誤: {resp.text[:300]}")
