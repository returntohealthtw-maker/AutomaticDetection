import sys, time, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=10)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 先確認版本
vr = requests.get(BASE+'/app/version', headers=h, verify=False, timeout=10)
print(f"目前版本: {vr.json().get('html_version')}")

# 測試 all-subjects-overview 最多等 60 秒
print("測試 all-subjects-overview（最多等 60 秒）...")
t0 = time.time()
try:
    ov = requests.get(BASE+'/reports/all-subjects-overview', headers=h, verify=False, timeout=60)
    elapsed = time.time()-t0
    print(f"  status={ov.status_code} elapsed={elapsed:.1f}s")
    if ov.ok:
        subs = ov.json().get('subjects', [])
        print(f"  ✅ 成功！subjects={len(subs)}")
        for s in subs[:3]:
            bw = s.get('latest_brainwave') or {}
            print(f"    {s.get('name','?')}: src={bw.get('_source','?')}")
    else:
        print(f"  ❌ {ov.text[:100]}")
except Exception as e:
    elapsed = time.time()-t0
    print(f"  ❌ 超時/錯誤 after {elapsed:.1f}s: {e}")
