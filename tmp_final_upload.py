import requests, urllib3, time
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
now_s = int(time.time())  # 秒格式（正確）

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=10)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 正確：captured_at 用秒（~1753927000），不是毫秒（~1753927000000）
caps = [{'seq_num':i,'is_baseline':0,'captured_at': now_s + i,
         'good_signal':0,'attention':65,'meditation':58,
         'delta':200000,'theta':80000,'low_alpha':30000,'high_alpha':20000,
         'low_beta':15000,'high_beta':12000,'low_gamma':8000,'high_gamma':3000,'feedback':0}
        for i in range(179)]

r1 = requests.post(BASE+'/sessions/upload', json={
    "subject_name":"最終驗證","consultant_name":"系統管理員",
    "subject_age":35,"subject_gender":"male","report_type":"adult",
    "is_success":True,"captures":caps
}, verify=False, timeout=30)
print(f"status={r1.status_code}")
if r1.ok:
    d = r1.json()
    print(f"✅ session_id={d.get('session_id')} captures_saved={d.get('captures_saved')} firebase={d.get('firebase_sync_ok')}")
else:
    print(f"❌ {r1.text[:100]}")
