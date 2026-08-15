import requests, urllib3, time, random, sys
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

# 模擬 Android 真實上傳：captured_at 用毫秒（System.currentTimeMillis）
now_ms = int(time.time() * 1000)
captures = []
random.seed(12345)
for i in range(180):
    captures.append({
        "seq_num": i, "is_baseline": False,
        "captured_at": now_ms - (180 - i) * 1000,  # 毫秒
        "good_signal": 0,
        "delta": random.randint(80000, 250000),
        "theta": random.randint(30000, 90000),
        "low_alpha": random.randint(8000, 25000),
        "high_alpha": random.randint(5000, 20000),
        "low_beta": random.randint(5000, 15000),
        "high_beta": random.randint(4000, 12000),
        "low_gamma": random.randint(2000, 8000),
        "high_gamma": random.randint(1000, 5000),
        "attention": 50, "meditation": 50,
    })

payload = {
    "consultant_name": "admin",
    "subject_name": "_android_ms_verify",
    "subject_birthday": "1990-01-01",
    "subject_gender": "F",
    "subject_age": 36,
    "report_type": "life_script",
    "start_time": now_ms - 180000,
    "end_time": now_ms,
    "total_captures": 180,
    "is_success": True,
    "failure_reason": "",
    "captures": captures,
}
r = requests.post(BASE + '/sessions/upload', json=payload, verify=False, timeout=60)
print(f'Android毫秒格式上傳: HTTP {r.status_code}')
print(r.text[:400])
