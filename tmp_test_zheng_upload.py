"""
測試 Android APP 真實上傳格式（帶 is_baseline、feedback 欄位）
同時確認 report_type 及 talent_report_kind 長度是否有問題
"""
import sys, requests, urllib3, json
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

# 確認 sessions 表 report_type 欄位長度（透過直接測試）
print("=== 欄位長度驗證 ===")
all_types = ['adult','child','life_script','life_trial','child_report','child_trial',
             'child_vip','child_full','life_vip','life_full','parent_child','marital']
for t in all_types:
    print(f"  '{t}' = {len(t)} 字")

print()
print("=== 最長的 talent_report_kind ===")
for rt in ['life_script', 'child_report', 'child_trial', 'parent_child']:
    for v in ['full', 'vip', 'trial']:
        kind = f"{rt}_{v}"
        flag = "⚠️ >32字" if len(kind) > 32 else "✅"
        print(f"  '{kind}' = {len(kind)} 字 {flag}")

print()
# 核心：模擬 Android APP 真實上傳（使用 is_baseline=False、feedback=0，
# 同時用真實格式的 report_type=life_script）
def mc(i):
    return {
        "seq_num": i, "is_baseline": False,
        "captured_at": 1785400000 + i * 1000,
        "good_signal": 0, "attention": 65, "meditation": 58,
        "delta": 200000, "theta": 80000,
        "low_alpha": 30000, "high_alpha": 20000,
        "low_beta": 15000, "high_beta": 12000,
        "low_gamma": 8000, "high_gamma": 3000,
        "feedback": 0
    }

caps = [mc(i) for i in range(179)]
payload = {
    "subject_name": "鄭靜怡_retest",
    "consultant_name": "系統管理員",
    "subject_age": 49,
    "subject_gender": "F",
    "subject_birthday": "1977-07-30",
    "report_type": "life_script",
    "report_audience": "student",
    "is_success": True,
    "captures": caps,
    "start_time": 1785400000000,
    "end_time": 1785580000000,
    "notify_email": "",
}
print("=== 模擬鄭靜怡真實上傳（life_script，179筆）===")
resp = requests.post(BASE+'/sessions/upload', json=payload, headers=h, verify=False, timeout=90)
print(f"  Status: {resp.status_code}")
print(f"  Body: {resp.text[:300]}")
