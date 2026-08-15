import requests, urllib3, time
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=10)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

print("測試 all-subjects-overview...")
t0 = time.time()
ov = requests.get(BASE+'/reports/all-subjects-overview', headers=h, verify=False, timeout=30)
elapsed = time.time()-t0
print(f"  status={ov.status_code} elapsed={elapsed:.1f}s")
if ov.ok:
    subs = ov.json().get('subjects', [])
    print(f"  subjects count={len(subs)}")
    for s in subs[:5]:
        bw = s.get('latest_brainwave') or {}
        b7 = bw.get('bands_7') or {}
        if not b7:
            print(f"  {s.get('name')}: bands_7 空")
            continue
        vals = [v for v in b7.values() if v is not None]
        src = bw.get('_source', '?')
        print(f"  {s.get('name')} src={src} max={max(vals):.1f} theta={b7.get('theta','?')}")
else:
    print(f"  FAIL: {ov.text[:100]}")
