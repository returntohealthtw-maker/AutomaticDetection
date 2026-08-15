import requests, sys, json
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r0 = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, timeout=10, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}'}

# 查逐秒原始數據（看 response 結構）
rc = requests.get(f'{BASE}/api/v1/sessions/113/captures', headers=H, timeout=15, verify=False)
print(f'captures status: {rc.status_code}')
raw = rc.json()
print(f'captures type: {type(raw)}')
if isinstance(raw, dict):
    print(f'captures keys: {list(raw.keys())}')
    caps = raw.get('captures', raw.get('data', []))
elif isinstance(raw, list):
    caps = raw
else:
    caps = []
print(f'captures 筆數: {len(caps)}')
if caps:
    c0 = caps[0]
    print(f'第1筆: {json.dumps(c0, ensure_ascii=False, default=str)[:500]}')
    # delta
    for field in ['delta','r_delta','Delta']:
        if field in c0:
            deltas = [c.get(field, 0) for c in caps[:10]]
            print(f'前10筆 {field}: {deltas}')
            break

# qeeg_abilities 是怎麼算的？
print('\n=== qeeg_scores_json ===')
r2 = requests.get(f'{BASE}/api/v1/eeg/sessions/113/stats', headers=H, timeout=15, verify=False)
d2 = r2.json()
print(json.dumps(d2, ensure_ascii=False, default=str, indent=2)[:2000])
