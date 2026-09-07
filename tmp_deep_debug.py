"""
Session #60 深度 Debug：逐秒追蹤每個環節
1. 原始 raw 值分佈
2. 每秒比例計算 (capped/uncapped_total)
3. EMG 雜訊偵測
4. 對照 BrainDNA 族群統計
5. 完整流程逐步追蹤（選窗前 → 選窗後 → 最終結果）
"""
import json, math, urllib3, requests, statistics
urllib3.disable_warnings()

BASE = "https://backend-production-2da61.up.railway.app"
r = requests.post(f"{BASE}/api/v1/auth/login",
                  json={"phone":"0900000000","password":"admin123"},
                  verify=False, timeout=15)
token = r.json().get("token","")
hdrs = {"Authorization": f"Bearer {token}"}

# ── 取得兩個 session 做對比 ──────────────────────────────────────────────────
def get_raw(sid):
    resp = requests.get(f"{BASE}/api/admin/raw-export/{sid}",
                        headers=hdrs, verify=False, timeout=30)
    return resp.json().get("raw_arrays", {})

print("取得 Session #57（正常值）和 #60（異常值）的逐秒資料...")
raw57 = get_raw(57)
raw60 = get_raw(60)
n57 = len(raw57.get("r_lalpha") or [])
n60 = len(raw60.get("r_lalpha") or [])
print(f"  Session 57: {n57} 秒  |  Session 60: {n60} 秒\n")

CAP = dict(r_delta=98000, r_theta=98000, r_lalpha=50000, r_halpha=50000,
           r_lbeta=50000,  r_hbeta=50000,  r_lgamma=10000, r_hgamma=10000)
PROP_RANGE = dict(
    r_delta=(0.60,0.80), r_theta=(0.15,0.30),
    r_lalpha=(0.10,0.20), r_halpha=(0.10,0.20),
    r_lbeta=(0.05,0.10),  r_hbeta=(0.05,0.10),
    r_lgamma=(0.03,0.06), r_hgamma=(0.03,0.06),
)
KEYS = list(CAP.keys())

def clamp(v, cap): return min(float(v), cap)

def proportion_range(v, l1, l2):
    if v <= 0: return 0.0
    if v >= l2: return 1.0
    if v <= l1: return (v/l1)*0.5
    return (v-l1)/(l2-l1)*0.5 + 0.5

def bandto100(raw):
    if raw <= 0: return 0.0
    return min(100.0, max(0.0, math.log10(raw+1)/6.0*100.0))

# ═══════════════════════════════════════════════════════════════════════════════
# 步驟 1：原始值分佈
# ═══════════════════════════════════════════════════════════════════════════════
print("═" * 70)
print("步驟 1：原始 raw 值分佈（全部秒數）")
print("─" * 70)

# BrainDNA 族群統計（log10 空間，來自 evaluationReport.py DATA_STATS）
POP_STATS = {
    "r_delta":  (5.298, 0.542), "r_theta":  (4.725, 0.441),
    "r_lalpha": (4.073, 0.424), "r_halpha": (4.090, 0.377),
    "r_lbeta":  (4.026, 0.404), "r_hbeta":  (4.089, 0.393),
    "r_lgamma": (3.757, 0.426), "r_hgamma": (3.753, 0.629),
}
NAMES = dict(r_delta="Delta",r_theta="Theta",r_lalpha="LowAlpha",r_halpha="HighAlpha",
             r_lbeta="LowBeta",r_hbeta="HighBeta",r_lgamma="LowGamma",r_hgamma="HighGamma")

print(f"{'頻段':<12}{'族群均值':>12}{'Sess57均值':>12}{'57 z分數':>10}{'Sess60均值':>12}{'60 z分數':>10}{'CAP':>10}")
print("-" * 80)
for k in KEYS:
    arr57 = [v for v in (raw57.get(k) or []) if v > 0]
    arr60 = [v for v in (raw60.get(k) or []) if v > 0]
    pop_m, pop_s = POP_STATS[k]
    pop_raw = 10**pop_m
    m57 = statistics.mean(arr57) if arr57 else 0
    m60 = statistics.mean(arr60) if arr60 else 0
    z57 = (math.log10(m57)-pop_m)/pop_s if m57 > 0 else 0
    z60 = (math.log10(m60)-pop_m)/pop_s if m60 > 0 else 0
    flag60 = " ⚠ OUTLIER" if abs(z60) > 2.0 else ""
    print(f"{NAMES[k]:<12}{pop_raw:>12,.0f}{m57:>12,.0f}{z57:>+10.2f}{m60:>12,.0f}{z60:>+10.2f}{CAP[k]:>10,}{flag60}")

# ═══════════════════════════════════════════════════════════════════════════════
# 步驟 2：選出最佳視窗並追蹤比例計算
# ═══════════════════════════════════════════════════════════════════════════════
print()
print("═" * 70)
print("步驟 2：選最佳 30 秒視窗的 lowGamma 佔比（每視窗）")
print("─" * 70)

def calc_window_lgamma_prop(raw, start, end):
    prop_sum, valid = 0.0, 0
    n = end - start
    for i in range(start, min(end, len(raw.get("r_lalpha") or []))):
        row = {k: float((raw.get(k) or [0])[i] if i < len(raw.get(k) or []) else 0) for k in KEYS}
        total = sum(row.values())
        if total > 0:
            prop_sum += clamp(row["r_lgamma"], CAP["r_lgamma"]) / total
            valid += 1
    raw_prop = prop_sum/valid if valid else 0
    return raw_prop, proportion_range(raw_prop, 0.03, 0.06)

import math as _math
n60_windows = _math.ceil(n60/30)
print(f"Session #60 共 {n60} 秒 → {n60_windows} 個視窗")
best_score, best_idx = -1, 0
for wi in range(n60_windows):
    s, e = wi*30, (wi+1)*30
    prop, score = calc_window_lgamma_prop(raw60, s, e)
    marker = ""
    if score > best_score:
        best_score = score; best_idx = wi
        marker = " ← 目前選此"
    print(f"  視窗 {wi} (秒 {s:3d}~{min(e,n60)-1:3d}): lowGamma 佔比={prop*100:5.2f}%  PR分數={score:.3f}{marker}")

# ═══════════════════════════════════════════════════════════════════════════════
# 步驟 3：最佳視窗逐秒追蹤
# ═══════════════════════════════════════════════════════════════════════════════
print()
print("═" * 70)
bw_start = best_idx * 30
bw_end   = min(bw_start+30, n60)
print(f"步驟 3：最佳視窗（秒 {bw_start}~{bw_end-1}）逐秒比例計算")
print("─" * 70)
print(f"{'秒':>4}  {'delta原始':>12}  {'lgamma原始':>12}  {'uncap總和':>14}  "
      f"{'lgamma_capped':>14}  {'lgamma佔比%':>12}  {'total_b100':>10}")
print("-" * 90)

suspicious_secs = []
for i in range(bw_start, bw_end):
    row = {k: float((raw60.get(k) or [0])[i] if i < len(raw60.get(k) or []) else 0) for k in KEYS}
    uncap_total = sum(row.values())
    lg_capped = clamp(row["r_lgamma"], CAP["r_lgamma"])
    lg_prop = lg_capped / uncap_total * 100 if uncap_total > 0 else 0

    # bandTo100 各值加總（對照參考）
    b100_total = sum(bandto100(row[k]) for k in KEYS)

    flag = ""
    # EMG 雜訊偵測：(lowAlpha+highAlpha+lowBeta+highBeta) > 120,000 原始值
    ab_raw = row["r_lalpha"]+row["r_halpha"]+row["r_lbeta"]+row["r_hbeta"]
    if ab_raw > 120000:
        flag += " EMG?"
    if row["r_theta"] > 90000:
        flag += " theta高"
    if row["r_lgamma"] > 50000:
        flag += " lgamma極高"
    if flag:
        suspicious_secs.append(i)

    print(f"{i:4d}  {row['r_delta']:>12,.0f}  {row['r_lgamma']:>12,.0f}  {uncap_total:>14,.0f}  "
          f"{lg_capped:>14,.0f}  {lg_prop:>12.2f}%  {b100_total:>10.1f}{flag}")

# ═══════════════════════════════════════════════════════════════════════════════
# 步驟 4：最終計算結果追蹤
# ═══════════════════════════════════════════════════════════════════════════════
print()
print("═" * 70)
print("步驟 4：最佳視窗的最終 BrainDNA 佔比計算")
print("─" * 70)
print(f"{'頻段':<12}  {'原始平均':>12}  {'cap上限':>10}  {'capped平均':>12}  "
      f"{'原始佔比%':>12}  {'proportionRange':>16}  {'最終值':>8}")
print("-" * 88)

prop_sums = {k: 0.0 for k in KEYS}
valids = 0
per_sec_data = {k: [] for k in KEYS}
per_sec_totals = []

for i in range(bw_start, bw_end):
    row = {k: float((raw60.get(k) or [0])[i] if i < len(raw60.get(k) or []) else 0) for k in KEYS}
    uncap_total = sum(row.values())
    if uncap_total <= 0: continue
    per_sec_totals.append(uncap_total)
    for k in KEYS:
        prop_sums[k] += clamp(row[k], CAP[k]) / uncap_total
        per_sec_data[k].append(row[k])
    valids += 1

NAME_OUT = dict(r_delta="delta",r_theta="theta",r_lalpha="low_alpha",r_halpha="high_alpha",
                r_lbeta="low_beta",r_hbeta="high_beta",r_lgamma="low_gamma",r_hgamma="high_gamma")
for k in KEYS:
    arr = per_sec_data[k]
    raw_mean = statistics.mean(arr) if arr else 0
    capped_mean = statistics.mean([clamp(v, CAP[k]) for v in arr]) if arr else 0
    raw_prop = prop_sums[k] / valids if valids else 0
    l1, l2 = PROP_RANGE[k]
    pr = proportion_range(raw_prop, l1, l2)
    final = round(pr * 100)
    thresholds = f"[{l1*100:.0f}%~{l2*100:.0f}%]"
    print(f"{NAME_OUT[k]:<12}  {raw_mean:>12,.0f}  {CAP[k]:>10,}  {capped_mean:>12,.0f}  "
          f"{raw_prop*100:>12.3f}%  {thresholds:>16}  {final:>8}")

avg_total = statistics.mean(per_sec_totals) if per_sec_totals else 0
print(f"\n  視窗內每秒 uncapped 總和：最小={min(per_sec_totals):,.0f}  最大={max(per_sec_totals):,.0f}  平均={avg_total:,.0f}")

# ═══════════════════════════════════════════════════════════════════════════════
# 步驟 5：Session 57 對照
# ═══════════════════════════════════════════════════════════════════════════════
print()
print("═" * 70)
print("步驟 5：Session #57（正常）最佳視窗對照")
print("─" * 70)
best57_score, best57_idx = -1, 0
n57_windows = _math.ceil(n57/30)
for wi in range(n57_windows):
    _, score = calc_window_lgamma_prop(raw57, wi*30, (wi+1)*30)
    if score > best57_score:
        best57_score = score; best57_idx = wi
bw57_s = best57_idx * 30; bw57_e = min(bw57_s+30, n57)
ps57, pt57 = {k:0.0 for k in KEYS}, []
v57 = 0
for i in range(bw57_s, bw57_e):
    row = {k: float((raw57.get(k) or [0])[i] if i < len(raw57.get(k) or []) else 0) for k in KEYS}
    ut = sum(row.values())
    if ut <= 0: continue
    for k in KEYS: ps57[k] += clamp(row[k], CAP[k]) / ut
    pt57.append(ut); v57 += 1

avg57 = statistics.mean(pt57) if pt57 else 0
print(f"  最佳視窗：秒 {bw57_s}~{bw57_e-1}  每秒平均 uncapped 總和：{avg57:,.0f}")
print(f"  Session #60 最佳視窗：秒 {bw_start}~{bw_end-1}  每秒平均 uncapped 總和：{avg_total:,.0f}")
print(f"\n  {'頻段':<12}  {'57最終值':>10}  {'60最終值':>10}  {'原因說明':>30}")
print("  " + "-" * 68)
for k in KEYS:
    r57 = prop_range57 = proportion_range(ps57[k]/v57 if v57 else 0, *PROP_RANGE[k])
    r60 = proportion_range(prop_sums[k]/valids if valids else 0, *PROP_RANGE[k])
    f57 = round(r57*100); f60 = round(r60*100)
    p57 = ps57[k]/v57*100 if v57 else 0
    p60 = prop_sums[k]/valids*100 if valids else 0
    reason = f"57佔比={p57:.2f}% 60佔比={p60:.2f}%"
    print(f"  {NAME_OUT[k]:<12}  {f57:>10}  {f60:>10}  {reason:>30}")

print()
print("═" * 70)
print("診斷結論")
print("─" * 70)
if suspicious_secs:
    print(f"  ⚠ 可疑秒數（EMG或訊號異常）：{suspicious_secs}")
else:
    print("  ✓ 最佳視窗內無明顯 EMG 尖峰（alpha+beta<120K，theta<90K）")

print(f"  每秒平均 uncapped 總和：Session57={avg57:,.0f}  Session60={avg_total:,.0f}")
ratio = avg57/avg_total if avg_total else 0
print(f"  分母比值：57是60的 {ratio:.1f} 倍")
print()
print("  → 根本原因：分母大小差異")
print(f"    Session 57 delta 主導分母（delta 均值 ≈ {statistics.mean([v for v in (raw57.get('r_delta') or []) if v>0]):,.0f}）")
print(f"    Session 60 delta 較小     （delta 均值 ≈ {statistics.mean([v for v in (raw60.get('r_delta') or []) if v>0]):,.0f}）")
print()
print("  → 是否有 EMG 問題？請看上方步驟 3 標記行")
