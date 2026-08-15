import requests, json, urllib3
urllib3.disable_warnings()

BASE = 'https://backend-production-2da61.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'phone':'0900000000','password':'admin123'}, verify=False)
token = r.json().get('token') or r.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}

for sid in [87, 88, 89, 90, 91]:
    r2 = requests.get(f'{BASE}/api/v1/sessions/{sid}/captures', headers=headers, verify=False)
    if r2.status_code != 200:
        print(f'Session {sid}: 不存在或無法取得 ({r2.status_code})')
        continue
    caps = r2.json().get('captures', [])
    if not caps:
        print(f'Session {sid}: 無 captures')
        continue
    # 取前 5 筆
    print(f'\n=== Session {sid} (總{len(caps)}筆) ===')
    for c in caps[:5]:
        la = c['low_alpha']
        ha = c['high_alpha']
        lb = c['low_beta']
        hb = c['high_beta']
        lg = c['low_gamma']
        hg = c['high_gamma']
        same_alpha = '同' if la == ha else '不同'
        same_beta  = '同' if lb == hb else '不同'
        same_gamma = '同' if lg == hg else '不同'
        print(f"  seq={c['seq_num']:3d} | alpha({same_alpha}) L={la} H={ha} | beta({same_beta}) L={lb} H={hb} | gamma({same_gamma}) L={lg} H={hg}")
