"""
模擬 APP 呼叫 /report-gen/start，找 500 原因
"""
import sys, requests, urllib3, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'}

# 模擬 APP 的 brainwave_data（有效的 179 筆分析結果）
brainwave_data = {
    "sample_count": 179,
    "attention_percentage": 65,
    "meditation_percentage": 58,
    "bands_avg": {
        "delta": 45, "theta": 38, "low_alpha": 52,
        "high_alpha": 48, "low_beta": 41, "high_beta": 35,
        "low_gamma": 28, "high_gamma": 22
    },
    "mind_stress": 45, "mind_balance": 62, "mind_energy": 55,
    "mind_color": 2, "mbti": "INTJ", "overall_score": 73
}

tests = [
    # (report_type, variant, session_id, subject_id, desc)
    ("life_script", "full",  None, 87,   "無session_id，有subject_id=87（鄭靜怡）"),
    ("life_script", "full",  97,   None, "有session_id=97，無subject_id"),
    ("life_script", "vip",   None, None, "無session_id無subject_id"),
    ("child",       "full",  None, 89,   "child+有subject_id=89（郭以琳）"),
    ("child_report","full",  None, 89,   "child_report+有subject_id=89"),
]

for rt, variant, sid, subj_id, desc in tests:
    payload = {
        "subject_name":   "鄭靜怡" if subj_id == 87 else ("郭以琳" if subj_id == 89 else "測試"),
        "subject_age":    49,
        "subject_gender": "女",
        "report_type":    rt,
        "variant":        variant,
        "session_id":     sid,
        "subject_id":     subj_id,
        "brainwave_data": brainwave_data,
        "chapters_to_generate": None,
    }
    resp = requests.post(BASE+'/report-gen/start', json=payload, headers=h, verify=False, timeout=30)
    ok = "✅" if resp.status_code < 400 else "❌"
    print(f"{ok} [{rt}/{variant}] session={sid} subject={subj_id}: {resp.status_code}")
    if resp.status_code >= 400:
        try:
            err = resp.json()
            print(f"   ERROR: {json.dumps(err, ensure_ascii=False)[:200]}")
        except:
            print(f"   RAW: {resp.text[:200]}")
    else:
        d = resp.json()
        print(f"   OK: mode={d.get('mode')} job_id={str(d.get('job_id',''))[:12]}")
