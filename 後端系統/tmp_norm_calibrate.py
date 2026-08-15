"""
用現有的 sessions 資料計算各頻段相對功率均值/標準差，
用於校準 normative_database.json 的 ThinkGear 適配值。
"""
import sys, requests, json, warnings, math
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/api/v1/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

BANDS = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']

per_session_avg = {}  # {session_id: {band: avg_rel_power}}

# 查有 raw_arrays_json 的 sessions (87, 88, 89)
for sid in [87, 88, 89]:
    r2 = s.get(f'{BASE}/api/v1/sessions/{sid}/captures', params={'limit': 200})
    data = r2.json()
    caps = data.get('captures', data if isinstance(data, list) else [])
    if not caps:
        print(f"session {sid}: 無 captures")
        continue
    
    # 篩選 raw 值（delta > 1000 代表 raw）
    raw_caps = [c for c in caps if c.get('delta', 0) > 1000]
    if not raw_caps:
        print(f"session {sid}: 無 raw 資料（delta<=1000）")
        continue
    
    print(f"\n=== session {sid} ({len(raw_caps)} raw caps) ===")
    
    # 計算每秒相對功率
    rel_lists = {b: [] for b in BANDS}
    for cap in raw_caps:
        vals = {b: float(cap.get(b, 0) or 0) for b in BANDS}
        total = sum(vals.values())
        if total <= 0:
            continue
        for b in BANDS:
            rel_lists[b].append(vals[b] / total)
    
    # 計算均值與標準差
    result = {}
    for b in BANDS:
        arr = rel_lists[b]
        if not arr:
            continue
        mean_rel = sum(arr) / len(arr)
        log_vals = [math.log(v + 1e-8) for v in arr]
        log_mean = sum(log_vals) / len(log_vals)
        log_sd = (sum((x - log_mean)**2 for x in log_vals) / len(log_vals)) ** 0.5
        result[b] = {'rel_mean': round(mean_rel, 4), 'log_mean': round(log_mean, 3), 'log_sd': round(log_sd, 3)}
        print(f"  {b:12s}: rel={mean_rel:.3f}  log_mean={log_mean:.3f}  log_sd={log_sd:.3f}")
    
    per_session_avg[sid] = result

# 計算跨 session 的整體均值
print("\n=== 跨 session 整體均值（ThinkGear 校準建議）===")
all_sessions = list(per_session_avg.values())
if all_sessions:
    combined = {}
    for b in BANDS:
        vals_rel = [sess[b]['rel_mean'] for sess in all_sessions if b in sess]
        vals_log_mean = [sess[b]['log_mean'] for sess in all_sessions if b in sess]
        vals_log_sd = [sess[b]['log_sd'] for sess in all_sessions if b in sess]
        if vals_rel:
            combined[b] = {
                'rel_mean': round(sum(vals_rel)/len(vals_rel), 4),
                'log_mean': round(sum(vals_log_mean)/len(vals_log_mean), 3),
                'log_sd': round(sum(vals_log_sd)/len(vals_log_sd), 3)
            }
    
    print("建議的 ThinkGear 常模（用於更新 normative_database.json）:")
    for b in BANDS:
        if b in combined:
            c = combined[b]
            print(f'  "{b}": {{"log_mean": {c["log_mean"]}, "log_sd": {c["log_sd"]}, "rel_mean": {c["rel_mean"]}}}')
