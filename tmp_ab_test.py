import requests, urllib3, time
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
now_s = int(time.time())

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=10)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 完全複製 tmp_check_now.py 的成功格式
def mc(i):
    return {'seq_num':i,'is_baseline':False,'captured_at':1785400000+i*1000,
            'good_signal':0,'attention':65,'meditation':58,
            'delta':200000,'theta':80000,'low_alpha':30000,'high_alpha':20000,
            'low_beta':15000,'high_beta':12000,'low_gamma':8000,'high_gamma':3000,'feedback':0}
caps = [mc(i) for i in range(179)]

print("【A】完全複製已知成功格式 (含 auth headers)")
ra = requests.post(BASE+'/sessions/upload', json={
    "subject_name":"A驗證","consultant_name":"系統管理員",
    "subject_age":49,"subject_gender":"女","report_type":"life_script","is_success":True,"captures":caps
}, headers=h, verify=False, timeout=30)
print(f"  {ra.status_code} → {ra.text[:100] if not ra.ok else ra.json().get('session_id')}")

print()
caps2 = [{'seq_num':i,'is_baseline':False,'captured_at':1785400000+i*1000,
          'good_signal':0,'attention':65,'meditation':58,
          'delta':200000,'theta':80000,'low_alpha':30000,'high_alpha':20000,
          'low_beta':15000,'high_beta':12000,'low_gamma':8000,'high_gamma':3000,'feedback':0}
         for i in range(179)]
print("【B】同格式，無 auth headers")
rb = requests.post(BASE+'/sessions/upload', json={
    "subject_name":"B驗證","consultant_name":"系統管理員",
    "subject_age":49,"subject_gender":"女","report_type":"life_script","is_success":True,"captures":caps2
}, verify=False, timeout=30)
print(f"  {rb.status_code} → {rb.text[:100] if not rb.ok else rb.json().get('session_id')}")
