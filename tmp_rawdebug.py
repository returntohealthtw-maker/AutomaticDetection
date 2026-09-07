import requests, json, urllib3
urllib3.disable_warnings()
r = requests.post('https://backend-production-2da61.up.railway.app/api/v1/auth/login',
    json={'phone':'0900000000','password':'admin123'}, timeout=15, verify=False)
token = r.json().get('token','')
H = {'Authorization': f'Bearer {token}'}

for sid in [57, 59, 60]:
    result = requests.get(f'https://backend-production-2da61.up.railway.app/api/admin/raw-debug/{sid}',
        headers=H, timeout=20, verify=False)
    print(f'=== Session {sid} (status {result.status_code}) ===')
    if result.status_code == 200:
        d = result.json()
        print('All 180s raw stats:')
        for k, v in (d.get('all_180s_raw_stats') or {}).items():
            mn = v.get("mean", 0)
            mx = v.get("max", 0)
            cap = v.get("cap", 0)
            pct = v.get("pct_at_cap", 0)
            print(f'  {k}: mean={mn}, max={mx}, cap={cap}, pct_at_cap={pct}%')
        print('Best 30s window:')
        for k, v in (d.get('best_30s_window_stats') or {}).items():
            mn = v.get("mean", 0)
            tot = v.get("avg_uncapped_total", 0)
            prop = v.get("avg_proportion_pct", 0)
            print(f'  {k}: mean={mn}, avg_total={tot}, proportion={prop}%')
    else:
        print(result.text[:300])
    print()
