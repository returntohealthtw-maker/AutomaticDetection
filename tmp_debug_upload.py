import requests, urllib3, time, json
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app'
now_ts = int(time.time())

# 先確認今天早些時候是否也 500（郭以琳 session 上傳是 200 嗎？）
# 查最近的 session 以確認今天還有 200 的上傳紀錄
r = requests.post(BASE+'/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=10)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 查今天的 sessions（created today）
sr = requests.get(BASE+'/api/v1/eeg/sessions', headers=h, verify=False, timeout=10)
sessions = sr.json().get('sessions', [])
today_sessions = [s for s in sessions if str(s.get('created_at',''))[:8] >= '20260730']
print(f"今天的 sessions: {len(today_sessions)} 筆")
for s in today_sessions[:5]:
    print(f"  #{s.get('session_id')} {s.get('subject_name')} at={s.get('created_at')}")

# 測試：用最少需要欄位的上傳
print()
print("測試 upload（包含完整 headers 看是否有更好的錯誤信息）...")
r2 = requests.post(BASE+'/api/v1/sessions/upload', 
    json={
        "subject_name":"debug","subject_age":30,"subject_gender":"male",
        "report_type":"adult","consultant_name":"系統管理員",
        "is_success": True,
        "captures":[{"seq_num":i, "captured_at": now_ts + i,
                     "delta":200000,"theta":80000,"low_alpha":30000,
                     "high_alpha":20000,"low_beta":15000,"high_beta":12000,
                     "low_gamma":8000,"high_gamma":3000,"good_signal":0,
                     "attention":60,"meditation":55,"is_baseline":0} for i in range(10)]
    }, 
    verify=False, timeout=20,
    headers={'X-Railway-Debug': 'true'}
)
print(f"status={r2.status_code}")
print(f"body={r2.text[:500]}")
print(f"headers={dict(r2.headers)}")
