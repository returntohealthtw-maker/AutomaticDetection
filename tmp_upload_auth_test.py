import requests, urllib3, time
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
now_ts = int(time.time())

# 登入取得 token
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=10)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

def mc(i):
    return {'seq_num':i,'is_baseline':0,'captured_at':now_ts*1000+i*1000,
            'good_signal':0,'attention':65,'meditation':58,
            'delta':200000,'theta':80000,'low_alpha':30000,'high_alpha':20000,
            'low_beta':15000,'high_beta':12000,'low_gamma':8000,'high_gamma':3000,'feedback':0}

caps = [mc(i) for i in range(179)]

print("【測試1】有 auth header + life_script（模擬顧問 APP）")
r1 = requests.post(BASE+'/sessions/upload', json={
    "subject_name":"上傳驗證測試",
    "consultant_name":"系統管理員",
    "subject_age": 35, "subject_gender": "male",
    "report_type": "life_script",
    "is_success": True,
    "captures": caps
}, headers=h, verify=False, timeout=30)
print(f"  status={r1.status_code}")
if r1.ok:
    d = r1.json()
    print(f"  ✅ session_id={d.get('session_id')} captures_saved={d.get('captures_saved')} firebase={d.get('firebase_sync_ok')}")
else:
    print(f"  ❌ {r1.text[:100]}")

print()
print("【測試2】無 auth header（模擬 Android APP 的真實方式）")
r2 = requests.post(BASE+'/sessions/upload', json={
    "subject_name":"無Auth上傳測試",
    "consultant_name":"測試顧問",
    "subject_age": 35, "subject_gender": "male",
    "report_type": "adult",
    "is_success": True,
    "captures": caps
}, verify=False, timeout=30)
print(f"  status={r2.status_code}")
if r2.ok:
    d = r2.json()
    print(f"  ✅ session_id={d.get('session_id')} captures_saved={d.get('captures_saved')} firebase={d.get('firebase_sync_ok')}")
else:
    print(f"  ❌ {r2.text[:100]}")
