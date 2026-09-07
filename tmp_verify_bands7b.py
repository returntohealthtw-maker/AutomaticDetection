import sys, requests, urllib3
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
h = {'Authorization': 'Bearer '+token}

print("=== 用 /reports/regenerate-preview 查單一 session 的 bands_7 ===")
# 用 stats 看 braindna_result
for sid in [122, 123, 87, 89]:
    st = requests.get(BASE+f'/eeg/sessions/{sid}/stats', headers=h, verify=False, timeout=30)
    if not st.ok:
        print(f"  session #{sid}: {st.status_code}")
        continue
    d = st.json()
    bdna = d.get('braindna_result') or {}
    print(f"  session #{sid} [{d.get('subject_name')}] _source={d.get('bdna_source','?')}")
    print(f"    stress={bdna.get('stress')} balance={bdna.get('balance')} energy={bdna.get('energy')}")
    print(f"    bands={bdna.get('bands')}")

print()
print("=== 直接呼叫 brainwave 資料（用 subject overview 帶 limit=3）===")
ov = requests.get(BASE+'/reports/all-subjects-overview?limit=3', headers=h, verify=False, timeout=90)
if ov.ok:
    for s in ov.json().get('subjects', [])[:3]:
        bw = s.get('latest_brainwave') or {}
        b7 = bw.get('bands_7') or {}
        src = bw.get('_source', '?')
        name = s.get('name', '?')
        vals = [v for v in b7.values() if v is not None]
        if not vals:
            print(f"  {name}: bands_7 空")
            continue
        ok = '✅' if max(vals) <= 200 else '❌'
        print(f"  {name} src={src}: theta={b7.get('theta','?'):.1f} hiAlpha={b7.get('alpha_high','?'):.1f} "
              f"max={max(vals):.1f} {ok}")
else:
    print(f"  FAIL: {ov.status_code} {ov.text[:100]}")
