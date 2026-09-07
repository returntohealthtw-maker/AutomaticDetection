import requests, sys, json
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r0 = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, timeout=10, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}'}

# 直接取 session 113 的 all captures
rc = requests.get(f'{BASE}/api/v1/sessions/113/captures', headers=H, timeout=20, verify=False)
caps = rc.json().get('captures', [])
print(f'Session 113 captures 筆數: {len(caps)}')

# 統計各頻段值域
bands = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
for b in bands:
    vals = [c.get(b, 0) for c in caps]
    n100 = sum(1 for v in vals if v == 100)
    nraw = sum(1 for v in vals if v > 1000)
    nsmall = sum(1 for v in vals if 0 < v <= 200)
    avg = sum(vals)/len(vals) if vals else 0
    print(f'{b:12s}: avg={avg:.0f} max={max(vals)} min={min(vals)} | =100筆:{n100} >1000筆:{nraw} 0-200筆:{nsmall}')

# 前3筆和最後3筆
print('\n前3筆:')
for c in caps[:3]:
    print(f'  seq={c["seq_num"]}: d={c["delta"]} th={c["theta"]} ha={c["high_alpha"]} la={c["low_alpha"]} hb={c["high_beta"]} lb={c["low_beta"]} hg={c["high_gamma"]} lg={c["low_gamma"]}')
print('最後3筆:')
for c in caps[-3:]:
    print(f'  seq={c["seq_num"]}: d={c["delta"]} th={c["theta"]} ha={c["high_alpha"]} la={c["low_alpha"]} hb={c["high_beta"]} lb={c["low_beta"]} hg={c["high_gamma"]} lg={c["low_gamma"]}')
