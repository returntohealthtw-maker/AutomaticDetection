"""
深度 debug：為什麼我們的 BrainDNA 會出現 100？
對比原始 evaluationReport.py 的每個步驟
"""
import sys, requests, json, warnings, math
sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

BASE = 'https://backend-production-2da61.up.railway.app/api/v1'
sess = requests.Session()
sess.verify = False
r = sess.post(f'{BASE}/auth/login', json={'phone':'0900000000','password':'admin123'})
sess.headers['Authorization'] = f'Bearer {r.json()["token"]}'

# 取 session 89 原始 180 筆資料
r2 = sess.get(f'{BASE}/sessions/89/captures', params={'limit': 200})
caps = r2.json().get('captures', [])
raw_caps = [c for c in caps if (c.get('delta') or 0) > 1000]
print(f"Session 89 原始 raw 筆數: {len(raw_caps)}")

# ==================== 原始 BrainDNA 參數 ====================
CAP = {
    'delta':98000,'theta':98000,'lowAlpha':50000,'highAlpha':50000,
    'lowBeta':50000,'highBeta':50000,'lowGamma':10000,'midGamma':10000
}
# 注意：原始用 midGamma，我們用 highGamma（ThinkGear 8 頻段對應）
# ThinkGear 的 highGamma 對應 BrainDNA 的 midGamma（30-100Hz 高 gamma）
BAND_MAP = {
    'delta':   'r_delta',
    'theta':   'r_theta',
    'lowAlpha':'r_lalpha',
    'highAlpha':'r_halpha',
    'lowBeta': 'r_lbeta',
    'highBeta':'r_hbeta',
    'lowGamma':'r_lgamma',
    'midGamma':'r_hgamma',   # ← ThinkGear highGamma = BrainDNA midGamma
}
PROP_RANGE = {
    'delta':(0.6,0.8),'theta':(0.15,0.3),'lowAlpha':(0.1,0.2),
    'highAlpha':(0.1,0.2),'lowBeta':(0.05,0.1),'highBeta':(0.05,0.1),
    'lowGamma':(0.03,0.06),'midGamma':(0.03,0.06)
}
BANDS = list(CAP.keys())

def clamp(v, cap): return min(float(v or 0), float(cap))
def prop_range(val, l1, l2):
    if val <= 0: return 0.0
    if val >= l2: return 1.0
    if val <= l1: return (val/l1)*0.5
    return (val-l1)/(l2-l1)*0.5+0.5

# ==================== filterBands (原始，被註解) ====================
THRESHOLD_THETA     = 90000   # theta > 90K → 噪聲行
THRESHOLD_ALPHA_BETA = 120000  # highAlpha+lowAlpha+highBeta+lowBeta > 120K → 噪聲行

def would_filter(cap_row):
    theta_raw = float(cap_row.get('r_theta') or 0)
    ab = (float(cap_row.get('r_halpha') or 0) + float(cap_row.get('r_lalpha') or 0) +
          float(cap_row.get('r_hbeta')  or 0) + float(cap_row.get('r_lbeta')  or 0))
    return theta_raw > THRESHOLD_THETA or ab > THRESHOLD_ALPHA_BETA

# ==================== 建 30 秒視窗 ====================
def build_windows(caps):
    windows = []
    tmp = []
    for c in caps:
        row = {b: float(c.get(BAND_MAP[b]) or 0) for b in BANDS}
        row['_cap'] = c
        tmp.append(row)
        if len(tmp) >= 30:
            windows.append(tmp)
            tmp = []
    if tmp: windows.append(tmp)
    return windows

windows = build_windows(raw_caps)
print(f"視窗數: {len(windows)} (每個 30 秒)")

# ==================== filterBands 分析 ====================
print("\n===== filterBands 分析（原始被註解掉的邏輯）=====")
filtered_count = sum(1 for c in raw_caps if would_filter(c))
print(f"若啟用 filterBands：{filtered_count}/{len(raw_caps)} 筆會被過濾 ({100*filtered_count/len(raw_caps):.1f}%)")

# 詳細原因
theta_filtered = sum(1 for c in raw_caps if (c.get('r_theta') or 0) > THRESHOLD_THETA)
ab_filtered = sum(1 for c in raw_caps if
    (float(c.get('r_halpha') or 0)+float(c.get('r_lalpha') or 0)+
     float(c.get('r_hbeta') or 0)+float(c.get('r_lbeta') or 0)) > THRESHOLD_ALPHA_BETA)
print(f"  theta > 90K: {theta_filtered} 筆")
print(f"  alphaBeta > 120K: {ab_filtered} 筆")

# ==================== calcBand：找最佳視窗 ====================
def calc_window_lgamma_score(window):
    """計算視窗的 lowGamma proportionRange 分數（用於選最佳視窗）"""
    # calcColumnSumArray：用原始值作分母
    col_sums = [sum(row[b] for b in BANDS) for row in window]
    # calcLowGamma：上限 10000，分子
    lgamma_capped = [clamp(row['lowGamma'], 10000) for row in window]
    # proportion = 每秒的 (capped/total) 平均
    props = []
    for i, (capped, total) in enumerate(zip(lgamma_capped, col_sums)):
        if total > 0:
            props.append(capped/total)
    prop_avg = sum(props)/len(props) if props else 0
    return prop_range(prop_avg, 0.03, 0.06)

lgamma_scores = [(i, calc_window_lgamma_score(w)) for i, w in enumerate(windows)]
lgamma_scores.sort(key=lambda x: -x[1])
best_idx, best_score = lgamma_scores[0]
best_window = windows[best_idx]
print(f"\n===== 最佳視窗選擇 =====")
print(f"最佳視窗: #{best_idx} (秒 {best_idx*30+1}~{min((best_idx+1)*30, len(raw_caps))})")
print(f"lowGamma proportionRange 分數: {best_score:.4f}")
print("所有視窗 lowGamma 分數:")
for idx, sc in lgamma_scores[:5]:
    print(f"  視窗 #{idx}: {sc:.4f}")

# ==================== 最佳視窗的每個頻段詳細計算 ====================
print(f"\n===== 最佳視窗 (#{best_idx}) 各頻段詳細計算 =====")
w = best_window
col_sums = [sum(row[b] for b in BANDS) for row in w]

print(f"\n{'頻段':<12} {'原始均值':>12} {'截斷CAP':>10} {'截斷後均值':>12} {'佔比(分子/分母)':>16} {'proportionRange':>16} {'×100→score':>12}")
print("-"*100)

band_scores = {}
for b in BANDS:
    raw_vals   = [row[b] for row in w]
    cap_vals   = [clamp(v, CAP[b]) for v in raw_vals]
    raw_avg    = sum(raw_vals)/len(raw_vals)
    cap_avg    = sum(cap_vals)/len(cap_vals)

    # proportion = mean of per-second (capped/uncapped_total)
    props = []
    for i, (cv, total) in enumerate(zip(cap_vals, col_sums)):
        if total > 0:
            props.append(cv / total)
    prop_avg = sum(props)/len(props) if props else 0

    l1, l2 = PROP_RANGE[b]
    pr = prop_range(prop_avg, l1, l2)
    score = round(pr * 100)

    band_scores[b] = score
    capped_flag = '⚠ 被截斷' if raw_avg > CAP[b] else ''
    print(f"  {b:<12} {raw_avg:>12,.0f} {CAP[b]:>10,} {cap_avg:>12,.0f} {prop_avg:>14.1%}  ({l1:.2f},{l2:.2f}){pr:>10.3f}  {score:>10}  {capped_flag}")

print(f"\n===== 造成 100 的原因分析 =====")
for b, score in band_scores.items():
    if score == 100:
        raw_vals = [row[b] for row in w]
        raw_avg = sum(raw_vals)/len(raw_vals)
        cap_vals = [clamp(v, CAP[b]) for v in raw_vals]
        props = [cv/cs for cv, cs in zip(cap_vals, col_sums) if cs > 0]
        prop_avg = sum(props)/len(props)
        l1, l2 = PROP_RANGE[b]
        print(f"\n  [{b}] score=100 原因:")
        print(f"    原始均值 = {raw_avg:,.0f}  >  CAP = {CAP[b]:,}  → 截斷為 {CAP[b]:,}")
        print(f"    佔比 = {prop_avg:.2%}  >=  level2 = {l2:.0%}  → proportionRange = 1.0 → score = 100")
        # 看有多少秒超過 level2
        exceed_count = sum(1 for p in props if p >= l2)
        print(f"    此視窗 {len(props)} 秒中，有 {exceed_count} 秒佔比 >= {l2:.0%}")
        print(f"    若原始未被截斷（不用 CAP），佔比會是多少？")
        raw_props = [rv/cs for rv, cs in zip(raw_vals, col_sums) if cs > 0]
        raw_prop_avg = sum(raw_props)/len(raw_props)
        pr_raw = prop_range(raw_prop_avg, l1, l2)
        print(f"    原始佔比 = {raw_prop_avg:.2%}  → proportionRange = {pr_raw:.3f} → score = {round(pr_raw*100)}")

print(f"\n===== 結論 =====")
print(f"頻段分數: {dict((b,s) for b,s in band_scores.items())}")
print(f"出現 100 的頻段: {[b for b,s in band_scores.items() if s == 100]}")
print(f"\n出現 100 的主要原因：")
print(f"  1. CAP 值過低（highBeta CAP=50,000，但此受測者 highBeta 原始均值遠超 50,000）")
print(f"  2. 截斷後分子固定=50,000，若分母（delta主導的總值）不夠大，佔比就會超過 level2=10%")
print(f"  3. filterBands 在原始程式碼中已被註解掉，不是原因")
print(f"\n請問：這個受測者（楊女毓）的腦波是否為高 beta 活躍型（緊張/高度專注）？")
print(f"如果是，100 表示確實超出常模上限，並非演算法錯誤，而是 CAP/level2 閾值設計偏保守。")
