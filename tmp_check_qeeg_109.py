import requests, sys, json
requests.packages.urllib3.disable_warnings()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'https://backend-production-2da61.up.railway.app'
r0 = requests.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'}, timeout=10, verify=False)
H = {'Authorization': f'Bearer {r0.json()["token"]}'}

# 直接查 session 113 的 stats（含 bands_7 和 _source）
r = requests.get(f'{BASE}/api/v1/eeg/sessions/113/stats', headers=H, timeout=20, verify=False)
d = r.json()
print('=== eeg_stats 回傳 ===')
print(json.dumps(d, ensure_ascii=False, default=str, indent=2))

# 也計算本地 BrainDNA 的預期值（用 PostgreSQL captures 資料）
rc = requests.get(f'{BASE}/api/v1/sessions/113/captures', headers=H, timeout=20, verify=False)
caps = rc.json().get('captures', [])
print(f'\n=== 用 PostgreSQL captures 本地計算 BrainDNA ===')
print(f'共 {len(caps)} 筆')

# 手動模擬 BrainDNA 計算
CHILD_CAP = {'r_delta':400000,'r_theta':230000,'r_lalpha':50000,'r_halpha':50000,'r_lbeta':50000,'r_hbeta':50000,'r_lgamma':20000,'r_hgamma':20000}
CHILD_PROP_RANGE = {'r_delta':(0.35,0.55),'r_theta':(0.08,0.22),'r_lalpha':(0.015,0.060),'r_halpha':(0.015,0.060),'r_lbeta':(0.010,0.040),'r_hbeta':(0.020,0.070),'r_lgamma':(0.015,0.040),'r_hgamma':(0.010,0.030)}
KEY_MAP = {'r_delta':'delta','r_theta':'theta','r_lalpha':'low_alpha','r_halpha':'high_alpha','r_lbeta':'low_beta','r_hbeta':'high_beta','r_lgamma':'low_gamma','r_hgamma':'high_gamma'}
MIN_DELTA_Q = 30000

prop_sum = {k:0.0 for k in CHILD_CAP}
valid = 0
skipped = 0
for c in caps:
    d_val = float(c.get('delta',0) or 0)
    if d_val < MIN_DELTA_Q:
        skipped += 1
        continue
    raw_row = {k:float(c.get(v,0) or 0) for k,v in KEY_MAP.items()}
    total = sum(raw_row.values())
    if total <= 0: continue
    for k in CHILD_CAP:
        capped = min(raw_row[k], CHILD_CAP[k])
        prop_sum[k] += capped / total
    valid += 1

print(f'有效秒數: {valid}, 跳過(delta<30K): {skipped}')
print('\n預期 BrainDNA 計算結果:')
def pr(val, l1, l2):
    if val <= 0: return 0
    if val >= l2: return 100
    if val <= l1: return round((val/l1)*50)
    return round((val-l1)/(l2-l1)*50+50)

for k, (l1,l2) in CHILD_PROP_RANGE.items():
    avg_prop = prop_sum[k]/valid if valid else 0
    score = pr(avg_prop, l1, l2)
    fname = KEY_MAP[k]
    print(f'  {fname:12s}: prop={avg_prop:.4f} ({avg_prop*100:.1f}%) → score={score}')
