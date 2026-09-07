import requests, urllib3
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/sessions/upload', json={
    "subject_name":"驗證測試","subject_age":30,"subject_gender":"male",
    "report_type":"adult","consultant_name":"系統管理員",
    "captures":[{"seq_num":i,"delta":200000,"theta":80000,"low_alpha":30000,
                 "high_alpha":20000,"low_beta":15000,"high_beta":12000,
                 "low_gamma":8000,"high_gamma":3000,"good_signal":0,
                 "attention":60,"meditation":55,"is_baseline":0} for i in range(10)]
}, verify=False, timeout=15)
print(r.status_code, r.text[:300])
