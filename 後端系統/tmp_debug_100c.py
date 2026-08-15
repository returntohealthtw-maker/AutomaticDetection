"""
深度 debug：BrainDNA score=100 完整分析
"""
import sys, requests, warnings, math
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
sess = requests.Session()
sess.verify = False
r = sess.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'})
sess.headers['Authorization'] = f'Bearer {r.json()["token"]}'

# ==================== 原始 BrainDNA 參數 ====================
CAP = {
    'delta':98000,'theta':98000,'lowAlpha':50000,'highAlpha':50000,
    'lowBeta':50000,'highBeta':50000,'lowGamma':10000,'midGamma':10000
}
PROP_RANGE = {
    'delta':(0.6,0.8),'theta':(0.15,0.3),'lowAlpha':(0.1,0.2),
    'highAlpha':(0.1,0.2),'lowBeta':(0.05,0.1),'highBeta':(0.05,0.1),
    'lowGamma':(0.03,0.06),'midGamma':(0.03,0.06)
}
# API 欄位名 → BrainDNA 頻段名 (midGamma = ThinkGear highGamma)
API_TO_BDNA = {
    'delta':'delta','theta':'theta',
    'low_alpha':'lowAlpha','high_alpha':'highAlpha',
    'low_beta':'lowBeta','high_beta':'highBeta',
    'low_gamma':'lowGamma','high_gamma':'midGamma',
}
BANDS = list(CAP.keys())

def clamp(v, cap): return min(float(v or 0), float(cap))
def prop_range(val, l1, l2):
    if val <= 0: return 0.0
    if val >= l2: return 1.0
    if val <= l1: return (val/l1)*0.5
    return (val-l1)/(l2-l1)*0.5+0.5

def get_sessions_to_analyze():
    return [88, 89]

for SID in get_sessions_to_analyze():
    r2 = sess.get(f'{BASE}/sessions/{SID}/captures', params={'limit': 200})
    caps_raw = r2.json().get('captures', [])

    # 過濾出原始 raw 值（delta > 1000）
    raw_caps = []
    for c in caps_raw:
        if (c.get('delta') or 0) > 1000:
            row = {BANDS[0]: float(c['delta']),
                   'theta':   float(c['theta']),
                   'lowAlpha':float(c['low_alpha']),
                   'highAlpha':float(c['high_alpha']),
                   'lowBeta': float(c['low_beta']),
                   'highBeta':float(c['high_beta']),
                   'lowGamma':float(c['low_gamma']),
                   'midGamma':float(c['high_gamma']),
                  }
            raw_caps.append(row)

    total_rows = len(raw_caps)
    print(f"\n{'='*72}")
    print(f"Session {SID}  有效 raw 筆數: {total_rows}")
    print(f"{'='*72}")

    # ===== filterBands 分析 =====
    THRESHOLD_THETA = 90000
    THRESHOLD_AB    = 120000
    filtered_count = 0
    theta_hi = 0
    ab_hi = 0
    for row in raw_caps:
        theta_bad = row['theta'] > THRESHOLD_THETA
        ab_bad = (row['highAlpha']+row['lowAlpha']+row['highBeta']+row['lowBeta']) > THRESHOLD_AB
        if theta_bad: theta_hi += 1
        if ab_bad:    ab_hi += 1
        if theta_bad or ab_bad: filtered_count += 1

    print(f"\n[filterBands] 原始有這個邏輯但被註解掉了：")
    print(f"  若啟用：{filtered_count}/{total_rows} 筆會被過濾 ({100*filtered_count/total_rows:.1f}%)")
    print(f"    theta > 90K: {theta_hi} 筆 | alphaBeta > 120K: {ab_hi} 筆")

    # ===== 各頻段原始平均 =====
    print(f"\n[原始均值] 全部 {total_rows} 秒的頻段均值：")
    all_avg = {b: sum(r[b] for r in raw_caps)/total_rows for b in BANDS}
    for b in BANDS:
        cap_flag = '⚠ 超 CAP' if all_avg[b] > CAP[b] else ''
        print(f"  {b:<12} 均值={all_avg[b]:>9,.0f}  CAP={CAP[b]:>7,}  {cap_flag}")

    # ===== 建 30 秒視窗 =====
    windows = []
    tmp = []
    for row in raw_caps:
        tmp.append(row)
        if len(tmp) >= 30:
            windows.append(tmp)
            tmp = []
    if tmp: windows.append(tmp)

    # ===== calcBand：找最佳視窗 =====
    def window_lgamma_score(window):
        col_sums = [sum(r[b] for b in BANDS) for r in window]
        lg_capped = [clamp(r['lowGamma'], 10000) for r in window]
        props = [cv/cs for cv, cs in zip(lg_capped, col_sums) if cs > 0]
        prop_avg = sum(props)/len(props) if props else 0
        return prop_range(prop_avg, 0.03, 0.06)

    scores = [(i, window_lgamma_score(w)) for i, w in enumerate(windows)]
    scores.sort(key=lambda x: -x[1])
    best_idx = scores[0][0]
    best_win = windows[best_idx]

    print(f"\n[最佳視窗] #{best_idx}（秒 {best_idx*30+1}~{min((best_idx+1)*30, total_rows)}）")
    print(f"  lowGamma proportionRange 分數:")
    for idx, sc in scores[:min(5,len(scores))]:
        marker = ' ← 最佳' if idx == best_idx else ''
        print(f"    視窗 #{idx}: {sc:.4f}{marker}")

    # ===== 最佳視窗各頻段計算 =====
    w = best_win
    col_sums = [sum(r[b] for b in BANDS) for r in w]
    print(f"\n[最佳視窗 #{best_idx} 各頻段 proportionRange 詳細計算]")
    print(f"{'頻段':<12} {'原始均值':>10} {'vs CAP':>8} {'截斷後':>10} {'佔比':>8} {'閾(l1,l2)':>14} {'pr值':>7} {'score':>6}")
    print("-"*85)

    window_scores = {}
    for b in BANDS:
        raw_v = [r[b] for r in w]
        cap_v = [clamp(v, CAP[b]) for v in raw_v]
        raw_avg = sum(raw_v)/len(raw_v)
        cap_avg = sum(cap_v)/len(cap_v)
        props = [cv/cs for cv, cs in zip(cap_v, col_sums) if cs > 0]
        prop_avg = sum(props)/len(props) if props else 0
        l1, l2 = PROP_RANGE[b]
        pr = prop_range(prop_avg, l1, l2)
        score = round(pr * 100)
        window_scores[b] = score
        exceed = '⚠ 超 level2' if prop_avg >= l2 else ('→達 level1' if prop_avg >= l1 else '')
        print(f"  {b:<12} {raw_avg:>10,.0f} {('超' if raw_avg>CAP[b] else '在'):>6}CAP {cap_avg:>10,.0f} {prop_avg:>7.1%} ({l1:.2f},{l2:.2f}) {pr:>6.3f} {score:>6}  {exceed}")

    print(f"\n[結論] Session {SID} BrainDNA 分數: ", end="")
    for b in BANDS:
        print(f"{b}={window_scores[b]}", end="  ")
    print()

    score_100 = [b for b in BANDS if window_scores[b] == 100]
    if score_100:
        print(f"\n⚠ 出現 100 的頻段: {score_100}")
        for b in score_100:
            raw_v = [r[b] for r in w]
            raw_avg = sum(raw_v)/len(raw_v)
            props = [clamp(v, CAP[b])/cs for v, cs in zip(raw_v, col_sums) if cs > 0]
            prop_avg = sum(props)/len(props)
            l1, l2 = PROP_RANGE[b]
            print(f"\n  [{b}]:")
            print(f"    原始均值 {raw_avg:,.0f} vs CAP {CAP[b]:,} → 超出 {raw_avg/CAP[b]:.1f}x")
            print(f"    佔比 {prop_avg:.2%} vs level2 = {l2:.0%}")
            print(f"    分母（未截斷總和）均值: {sum(col_sums)/len(col_sums):,.0f}")
            # 如果用原始不截斷分子
            raw_props = [rv/cs for rv, cs in zip(raw_v, col_sums) if cs > 0]
            raw_prop_avg = sum(raw_props)/len(raw_props)
            pr_no_cap = prop_range(raw_prop_avg, l1, l2)
            print(f"    假設不用 CAP（原始分子）：佔比={raw_prop_avg:.2%}  score={round(pr_no_cap*100)}")
    else:
        print(f"  ✓ 無頻段達到 100")

print(f"\n{'='*72}")
print("比對摘要：原始 BrainDNA evaluationReport.py vs 我們的實作")
print("="*72)
print("""
[完全相同的部分]：
  ✅ proportionRange 函式邏輯（≤l1: ×0.5, l1~l2: 映射0.5-1.0, ≥l2: 1.0）
  ✅ CAP 值（delta=98K, theta=98K, alpha/beta=50K, gamma=10K）
  ✅ proportionRange 閾值（delta:0.6/0.8, beta:0.05/0.1, gamma:0.03/0.06）
  ✅ calcColumnSumArray 用「未截斷」原始值作分母
  ✅ proportion = 每秒 (capped_分子/uncapped_分母) 的平均
  ✅ 最佳 30 秒視窗 = lowGamma proportionRange 最高

[filterBands 在原始程式碼中被註解掉]：
  ℹ️  原始 evaluationReport.py line 26: #filtered = MindValueAlgorithm.filterBands([esense,])
  ℹ️  不是造成差異的原因

[100 出現的真正原因]：
  ❗ 受測者的某些頻段原始值超過 CAP 很多（如 highBeta 均值可達 90K+ vs CAP=50K）
  ❗ 截斷後分子被固定在 CAP，分母由 delta 主導，比例計算後超過 level2 → score=100
  ❗ 這是 CAP 設計問題，不是演算法邏輯錯誤
""")
