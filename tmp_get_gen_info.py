import requests, sys, json
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
H = {'Authorization': f'Bearer {r.json()["token"]}'}

# 找出還在 generating 的 session
GEN_SIDS = [98,97,96,95,94,93,92,90,89]
info = []
for sid in GEN_SIDS:
    rs = requests.get(f'{BASE}/api/v1/eeg/sessions/{sid}/stats', headers=H, timeout=15, verify=False)
    d = rs.json()
    st = d.get('report_status','?')
    name = d.get('subject_name','?')
    age  = d.get('subject_age','?')
    rtype = d.get('report_type','?')
    print(f"sid={sid} {name} age={age} type={rtype} status={st}")
    info.append({'sid': sid, 'name': name, 'status': st})

print()
print(json.dumps(info, ensure_ascii=False, indent=2))
