import requests, json, warnings
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

r = requests.post(f'{BASE}/auth/login',
    json={'phone':'0900000000','password':'admin123'}, verify=False)
tok = r.json().get('token','')
print('Login:', r.status_code)
headers = {'Authorization': f'Bearer {tok}'}

# 取最新 sessions
r2 = requests.get(f'{BASE}/eeg/sessions', headers=headers, verify=False)
resp = r2.json()
# 處理兩種格式
if isinstance(resp, dict) and 'sessions' in resp:
    sessions = resp['sessions']
elif isinstance(resp, list):
    sessions = resp
else:
    sessions = []

# 依 session_id 排序取最新
sessions.sort(key=lambda x: x.get('session_id', x.get('id', 0)))
recent = sessions[-8:]
print(f'\n最新 {len(recent)} 筆 sessions:')
for s in recent:
    sid = s.get('session_id') or s.get('id')
    name = s.get('subject_name','?')
    created = str(s.get('created_at',''))[:19]
    print(f'  id={sid} name={name} created={created}')

# 看最新一筆
if recent:
    latest = recent[-1]
    sid = latest.get('session_id') or latest.get('id')
    subj = latest.get('subject_name','?')
    print(f'\n=== Session {sid} ({subj}) ===')

    # stats
    r3 = requests.get(f'{BASE}/eeg/sessions/{sid}/stats', headers=headers, verify=False)
    stats = r3.json()
    bands_avg = stats.get('bands_avg', {})
    print('bands_avg:')
    for k, v in bands_avg.items():
        print(f'  {k}: {v}')

    bdna = stats.get('braindna_scores') or stats.get('braindna') or {}
    print('\nBrainDNA scores:', json.dumps(bdna, ensure_ascii=False))

    # raw captures
    r4 = requests.get(f'{BASE}/sessions/{sid}/captures', headers=headers, verify=False)
    caps_data = r4.json()
    if isinstance(caps_data, dict) and 'captures' in caps_data:
        cap_list = caps_data['captures']
    elif isinstance(caps_data, list):
        cap_list = caps_data
    else:
        cap_list = []
        print('captures resp:', str(caps_data)[:300])

    print(f'\ncaptures 總筆數: {len(cap_list)}')
    if cap_list:
        fields = ['seq_num','delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
        print('前 3 筆:')
        for c in cap_list[:3]:
            print(' ', {k: c.get(k) for k in fields})

        print('\n各欄位 min/max/avg/unique:')
        for fld in ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']:
            vals = [c.get(fld) for c in cap_list if c.get(fld) is not None]
            if vals:
                unique = len(set(vals))
                print(f'  {fld}: min={min(vals):.0f}  max={max(vals):.0f}  avg={sum(vals)/len(vals):.1f}  unique_values={unique}')
