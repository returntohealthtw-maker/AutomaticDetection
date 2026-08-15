"""
模擬兒童腦波上傳（child report type），找 500 原因
"""
import sys, requests, urllib3, json, random
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

# 模擬 180 筆兒童腦波擷取（類似 BrainLink 的值域）
def make_capture(i):
    return {
        "seq_num": i,
        "is_baseline": False,
        "captured_at": 1785000000 + i * 1000,
        "good_signal": 0,
        "attention": random.randint(30, 80),
        "meditation": random.randint(40, 70),
        "delta": random.randint(50000, 400000),
        "theta": random.randint(30000, 150000),
        "low_alpha": random.randint(10000, 80000),
        "high_alpha": random.randint(8000, 60000),
        "low_beta": random.randint(5000, 40000),
        "high_beta": random.randint(3000, 30000),
        "low_gamma": random.randint(1000, 20000),
        "high_gamma": random.randint(500, 10000),
        "feedback": 0
    }

captures = [make_capture(i) for i in range(179)]

print("=== 測試 1：兒童報告類型上傳 ===")
payload = {
    "subject_name": "郭以琳_test",
    "consultant_name": "何綺晨",
    "subject_age": 7,
    "subject_gender": "女",
    "subject_birthday": "2018-10-18",
    "report_type": "child",
    "report_audience": "student",
    "is_success": True,
    "captures": captures,
    "start_time": 1785000000000,
    "end_time": 1785180000000,
}
resp = requests.post(BASE+'/sessions/upload', json=payload, headers=h, verify=False, timeout=120)
print(f"  Status: {resp.status_code}")
print(f"  Body: {resp.text[:300]}")

print()
print("=== 測試 2：兒童報告 child_report 類型 ===")
payload2 = dict(payload)
payload2["report_type"] = "child_report"
payload2["subject_name"] = "郭以樂_test"
payload2["subject_gender"] = "男"
payload2["subject_age"] = 5
payload2["subject_birthday"] = "2021-02-26"
resp2 = requests.post(BASE+'/sessions/upload', json=payload2, headers=h, verify=False, timeout=120)
print(f"  Status: {resp2.status_code}")
print(f"  Body: {resp2.text[:300]}")
