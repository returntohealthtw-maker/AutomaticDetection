"""
分析 session 89 的 BrainDNA best 30s window，
確認 high_beta=100 的原因（best window 中的 high_beta 佔比是否超過 0.10）
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

r2 = s.get(f'{BASE}/api/v1/sessions/89/captures', params={'limit': 200})
data = r2.json()
caps = data.get('captures', data if isinstance(data, list) else [])
raw_caps = [c for c in caps if c.get('delta', 0) > 1000]
raw_caps.sort(key=lambda c: c.get('seq_num', 0))

BANDS = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
RAW_KEYS = ['delta','theta','low_alpha','high_alpha','low_beta','high_beta','low_gamma','high_gamma']
CAP = {'delta': 2_000_000, 'theta': 2_000_000, 'low_alpha': 2_000_000, 'high_alpha': 2_000_000,
       'low_beta': 2_000_000, 'high_beta': 2_000_000, 'low_gamma': 2_000_000, 'high_gamma': 2_000_000}
_PROP_RANGE = {
    'delta': (0.60, 0.80), 'theta': (0.15, 0.30),
    'low_alpha': (0.10, 0.20), 'high_alpha': (0.10, 0.20),
    'low_beta': (0.05, 0.10), 'high_beta': (0.05, 0.10),
    'low_gamma': (0.03, 0.06), 'high_gamma': (0.03, 0.06),
}

def clamp(v, cap): return min(float(v), float(cap))

def proportionRange(value, level1, level2):
    if value >= level2: return 1.0
    if value <= level1: return value / level1 * 0.5
    return (value - level1) / (level2 - level1) * 0.5 + 0.5

def calc_window_score(window_caps):
    """BrainDNA 視窗評分（lowGamma proportionRange）"""
    n = len(window_caps)
    if n == 0: return 0.0
    lg_prop_sum = 0.0
    for cap in window_caps:
        vals = {b: float(cap.get(b, 0) or 0) for b in BANDS}
        uncapped_total = sum(vals[b] for b in BANDS)
        if uncapped_total <= 0: continue
        capped_lg = clamp(vals['low_gamma'], CAP['low_gamma'])
        lg_prop_sum += capped_lg / uncapped_total
    avg_lg_prop = lg_prop_sum / n
    l1, l2 = _PROP_RANGE['low_gamma']
    return proportionRange(avg_lg_prop, l1, l2)

def calc_band_score_from_window(window_caps, band):
    """計算指定頻段在視窗內的 proportionRange 分數"""
    n = len(window_caps)
    if n == 0: return 0.0
    prop_sum = 0.0
    for cap in window_caps:
        vals = {b: float(cap.get(b, 0) or 0) for b in BANDS}
        uncapped_total = sum(vals[b] for b in BANDS)
        if uncapped_total <= 0: continue
        capped_val = clamp(vals[band], CAP[band])
        prop_sum += capped_val / uncapped_total
    avg_prop = prop_sum / n
    l1, l2 = _PROP_RANGE[band]
    return proportionRange(avg_prop, l1, l2), avg_prop

# 枚舉所有 30s 視窗
WINDOW_SIZE = 30
best_score = -1
best_window_idx = -1
window_scores = []
for start in range(0, len(raw_caps), WINDOW_SIZE):
    window = raw_caps[start:start + WINDOW_SIZE]
    if len(window) < WINDOW_SIZE: continue
    score = calc_window_score(window)
    window_scores.append((start, score))
    if score > best_score:
        best_score = score
        best_window_idx = start

print(f"共 {len(raw_caps)} raw caps，{len(window_scores)} 個視窗")
print(f"\n所有視窗 lowGamma 分數：")
for start, score in window_scores:
    marker = "★ BEST" if start == best_window_idx else ""
    print(f"  視窗 {start:3d}-{start+WINDOW_SIZE-1:3d}: {score:.4f} {marker}")

if best_window_idx >= 0:
    best_window = raw_caps[best_window_idx:best_window_idx + WINDOW_SIZE]
    print(f"\n=== Best 30s window ({best_window_idx}-{best_window_idx+WINDOW_SIZE-1}) 各頻段分析 ===")
    for band in BANDS:
        score, avg_prop = calc_band_score_from_window(best_window, band)
        l1, l2 = _PROP_RANGE[band]
        final = round(score * 100)
        if final > 100: final = 100
        print(f"  {band:12s}: 平均佔比={avg_prop:.4f} (閾值 {l1}~{l2})  → proportionRange={score:.4f}  → BrainDNA分數={final}")
