import requests, urllib3, random, time, sys, datetime
sys.stdout.reconfigure(encoding='utf-8')
urllib3.disable_warnings()
BASE = 'https://backend-production-2da61.up.railway.app/api/v1'

# 等版本上線
for i in range(24):
    try:
        ver = requests.get(BASE + '/app/version', verify=False, timeout=8).json()
        hv = ver.get('html_version', '')
        print(f'[{i}] html_version={hv}')
        if hv == '2026.07.30.10':
            break
    except Exception as e:
        print(f'[{i}] wait: {e}')
    time.sleep(5)
else:
    print('ERROR: version not deployed yet')
    sys.exit(1)

r = requests.post(BASE+'/auth/login', json={'phone':'0900000000','password':'admin123'}, verify=False, timeout=8)
token = r.json().get('token','')
h = {'Authorization': 'Bearer '+token}

# 模擬 APP 採集完成後的 save-stats（含 raw_arrays）
n = 180
random.seed(777)
raw = {k: [] for k in ['attn','medi','r_delta','r_theta','r_lalpha','r_halpha','r_lbeta','r_hbeta','r_lgamma','r_hgamma','r_good_signal']}
for i in range(n):
    raw['attn'].append(random.randint(40, 80))
    raw['medi'].append(random.randint(40, 80))
    raw['r_delta'].append(random.randint(100000, 250000))
    raw['r_theta'].append(random.randint(40000, 90000))
    raw['r_lalpha'].append(random.randint(10000, 25000))
    raw['r_halpha'].append(random.randint(8000, 20000))
    raw['r_lbeta'].append(random.randint(6000, 15000))
    raw['r_hbeta'].append(random.randint(5000, 12000))
    raw['r_lgamma'].append(random.randint(3000, 8000))
    raw['r_hgamma'].append(random.randint(2000, 5000))
    raw['r_good_signal'].append(0)

payload = {
    'subject_name': '_e2e_save_stats_verify',
    'subject_birthday': '1990-01-01',
    'subject_gender': 'F',
    'subject_age': 36,
    'report_type': 'life_script',
    'sample_count': n,
    'attention_percentage': 55,
    'meditation_percentage': 60,
    'bands_avg': {
        'delta': 50, 'theta': 40, 'low_alpha': 30, 'high_alpha': 28,
        'low_beta': 25, 'high_beta': 22, 'low_gamma': 18, 'high_gamma': 15,
    },
    'raw_arrays': raw,
}
resp = requests.post(BASE+'/eeg/save-stats', headers=h, json=payload, verify=False, timeout=60)
print(f'\nsave-stats HTTP {resp.status_code}')
print(resp.text[:500])
if resp.status_code != 200:
    sys.exit(1)
d = resp.json()
sid = d.get('session_id')
print(f'session_id={sid} firebase={d.get("firebase_session_id")} sync={d.get("firebase_sync_ok")}')

# 確認 sessions 列表看得到
sl = requests.get(BASE+'/eeg/sessions?limit=20', headers=h, verify=False, timeout=15).json()
all_s = sl.get('sessions', [])
found = next((s for s in all_s if s.get('session_id') == sid), None)
print(f'\n在 sessions 列表找到: {found is not None}')
if found:
    print(f"  name={found.get('subject_name')} captures={found.get('total_captures')}")

# overview 是否能看到（skip_firebase 路徑）
ao = requests.get(BASE+'/reports/all-subjects-overview', headers=h, verify=False, timeout=30)
print(f'overview HTTP {ao.status_code}')
if ao.status_code == 200:
    data = ao.json()
    subjects = data if isinstance(data, list) else data.get('subjects', data.get('data', []))
    hit = [s for s in subjects if isinstance(s, dict) and 'e2e_save_stats' in str(s.get('name',''))]
    print(f'overview 命中筆數: {len(hit)}')
    for s in hit[:3]:
        print(f"  name={s.get('name')} latest_session={s.get('latest_session_id')}")
