import requests, sys
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}'}

TARGETS = [111,110,109,108,107,106,105,104,103,102,101,100,99,98,97,96,95,94,93,92,90,89]
done, gen, failed, other = [], [], [], []
for sid in TARGETS:
    rs = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=15, verify=False)
    d = rs.json()
    st   = d.get('report_status','?')
    name = d.get('subject_name','?')
    url  = bool(d.get('report_url'))
    if st == 'completed' and url:
        done.append((sid, name))
    elif st == 'generating':
        gen.append((sid, name))
    elif st == 'failed':
        failed.append((sid, name))
    else:
        other.append((sid, name, st))

print(f"✅ 完成 ({len(done)} 個): {[f'{s}_{n}' for s,n in done]}")
print(f"⏳ 生成中 ({len(gen)} 個): {[f'{s}_{n}' for s,n in gen]}")
print(f"❌ 失敗 ({len(failed)} 個): {[f'{s}_{n}' for s,n in failed]}")
if other:
    print(f"其他: {other}")
