"""
正確計算 inter-individual SD：
1. 先取每個 session 的每秒平均（session-level mean）
2. 用 session-level mean 計算跨人 SD
這才是 normative SD（而非每秒內部波動 SD）
"""
import sys, requests, json, warnings, math
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
s = requests.Session()
s.verify = False
r = s.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'})
token = r.json().get('access_token','')
s.headers['Authorization'] = f'Bearer {token}'

BANDS = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']

# 取每個 session 的 session-level log mean（先取每秒 relative power，再取 log，再平均）
def session_log_rel_mean(sid):
    r2 = s.get(f'{BASE}/sessions/{sid}/captures', params={'limit': 200})
    caps = r2.json().get('captures', [])
    raw_caps = [c for c in caps if c.get('delta', 0) > 1000]
    if not raw_caps:
        return None
    log_vals = {b: [] for b in BANDS}
    for cap in raw_caps:
        vals = {b: float(cap.get(b, 0) or 0) for b in BANDS}
        total = sum(vals.values())
        if total <= 0: continue
        for b in BANDS:
            rel = vals[b] / total
            log_vals[b].append(math.log(rel + 1e-8))
    # session-level log mean per band
    return {b: sum(log_vals[b])/len(log_vals[b]) if log_vals[b] else None for b in BANDS}

print("計算各 session 的 session-level log mean...")
sess_means = {}
for sid in [88, 89]:
    m = session_log_rel_mean(sid)
    if m:
        sess_means[sid] = m
        print(f"\nSession {sid}:")
        for b in BANDS:
            print(f"  {b:<14} log_mean = {m[b]:.4f}  rel_mean = {math.exp(m[b]):.4f}")

if len(sess_means) >= 2:
    print("\n=== 跨 session inter-individual 統計 ===")
    all_vals = list(sess_means.values())
    print(f"受測者數: {len(all_vals)}")
    print(f"\n建議的 normative_database.json 更新值（inter-individual SD）:")
    inter_individual = {}
    for b in BANDS:
        vs = [v[b] for v in all_vals if v[b] is not None]
        mean = sum(vs) / len(vs)
        if len(vs) >= 2:
            sd = math.sqrt(sum((x-mean)**2 for x in vs) / (len(vs)-1))
        else:
            sd = 0.35  # fallback to literature
        # 學術建議最小 SD（防止 n=2 造成 SD 接近 0 的特定頻段）
        # 文獻 inter-individual SD 通常在 0.30-0.50 (Teplan 2002, Nunez 2006)
        lit_min = 0.30  # 最小保底
        lit_max = 0.50  # 最大上限（避免過小差異）
        sd_clamped = max(lit_min, min(lit_max, sd))
        inter_individual[b] = {'log_mean': round(mean, 3), 'log_sd': round(sd_clamped, 3)}
        print(f'  "{b}": {{"log_mean": {round(mean,3)}, "log_sd": {round(sd_clamped,3)},  # raw_sd={round(sd,3)}"}}')

    print("\n=== 用新 SD 模擬 Session 88 vs 89 的 qEEG Z-scores ===")
    for sid in [88, 89]:
        if sid not in sess_means: continue
        print(f"\nSession {sid}:")
        for b in BANDS:
            m_val = sess_means[sid][b]
            norm = inter_individual[b]
            z = (m_val - norm['log_mean']) / norm['log_sd']
            # sigmoid(0.9*z)
            score = 100.0 / (1.0 + math.exp(-0.9 * z))
            print(f"  {b:<14} log={m_val:.3f}  z={z:+.2f}  score={score:.1f}")
