"""
進一步隔離 child_report 500 的原因
"""
import sys, requests, urllib3, json, random
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

def make_capture(i):
    return {
        "seq_num": i, "is_baseline": False,
        "captured_at": 1785000000 + i * 1000,
        "good_signal": 0, "attention": 50, "meditation": 50,
        "delta": 200000, "theta": 80000,
        "low_alpha": 30000, "high_alpha": 20000,
        "low_beta": 15000, "high_beta": 12000,
        "low_gamma": 8000, "high_gamma": 3000,
        "feedback": 0
    }
captures = [make_capture(i) for i in range(179)]

tests = [
    ("child",          "郭A_test", "何綺晨", 7, "女", "student"),
    ("child_report",   "郭B_test", "何綺晨", 7, "女", "student"),  # 找 500
    ("child_vip",      "郭C_test", "何綺晨", 7, "女", "student"),
    ("child_trial",    "郭D_test", "何綺晨", 7, "女", "student"),
]

for rt, name, cons, age, gender, aud in tests:
    payload = {
        "subject_name": name, "consultant_name": cons,
        "subject_age": age, "subject_gender": gender,
        "report_type": rt, "report_audience": aud,
        "is_success": True, "captures": captures,
        "start_time": 1785000000000, "end_time": 1785180000000,
    }
    resp = requests.post(BASE+'/sessions/upload', json=payload, headers=h, verify=False, timeout=60)
    sid = resp.json().get('session_id') if resp.ok else 'N/A'
    print(f"  report_type={rt:15s} → {resp.status_code}  session_id={sid}")
    if resp.status_code != 200:
        print(f"    ERROR: {resp.text[:200]}")
