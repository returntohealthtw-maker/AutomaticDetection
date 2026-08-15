import sys, time, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=10)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

results = []
checks = [
    ("health",          "GET", "https://backend-production-2da61.up.railway.app/health", None),
    ("app/version",     "GET", BASE+'/app/version', None),
    ("session list",    "GET", BASE+'/eeg/sessions', None),
    ("session 87 stats","GET", BASE+'/eeg/sessions/87/stats', None),
    ("all-subjects-overview","GET", BASE+'/reports/all-subjects-overview', None),
    ("session upload test","POST", BASE+'/sessions/upload', {
        "subject_name":"驗證測試","subject_age":30,"subject_gender":"male",
        "report_type":"adult","consultant_name":"系統管理員",
        "captures":[{"seq_num":i,"delta":200000,"theta":80000,"low_alpha":30000,
                     "high_alpha":20000,"low_beta":15000,"high_beta":12000,
                     "low_gamma":8000,"high_gamma":3000,"good_signal":0,
                     "attention":60,"meditation":55,"is_baseline":0} for i in range(10)]
    }),
]

print("="*55)
print("完整端點驗證")
print("="*55)
for name, method, url, body in checks:
    t0 = time.time()
    try:
        if method == "GET":
            rr = requests.get(url, headers=h, verify=False, timeout=30)
        else:
            rr = requests.post(url, json=body, verify=False, timeout=15)
        elapsed = time.time()-t0
        ok = "✅" if rr.ok else "❌"
        print(f"  {ok} {name}: {rr.status_code} ({elapsed:.1f}s)")
    except Exception as e:
        elapsed = time.time()-t0
        print(f"  ❌ {name}: 超時/錯誤 ({elapsed:.1f}s)")

print()
print("版本:", requests.get(BASE+'/app/version', headers=h, verify=False, timeout=5).json().get('html_version'))
print("="*55)
