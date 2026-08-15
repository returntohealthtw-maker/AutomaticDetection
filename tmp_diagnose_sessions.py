"""
診斷 session 104, 105 的 BrainDNA 計算過程
直接呼叫 Railway API 取 180 筆原始資料，逐步顯示每個頻段的
實際均值、CAP 設定、截斷比例、proportionRange 輸出
"""
import sys, io, json, statistics, requests, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
urllib3.disable_warnings()

RAILWAY_BASE = "https://backend-production-2da61.up.railway.app"
TARGET_SESSIONS = [104, 105]

CAP = {
    "r_delta":  500_000,
    "r_theta":  200_000,
    "r_lalpha":  50_000,
    "r_halpha":  50_000,
    "r_lbeta":   50_000,
    "r_hbeta":   50_000,
    "r_lgamma":  25_000,
    "r_hgamma":  20_000,
}
PROP_RANGE = {
    "r_delta":  (0.44, 0.60),
    "r_theta":  (0.13, 0.19),
    "r_lalpha": (0.035, 0.065),
    "r_halpha": (0.030, 0.060),
    "r_lbeta":  (0.028, 0.055),
    "r_hbeta":  (0.050, 0.110),
    "r_lgamma": (0.033, 0.075),
    "r_hgamma": (0.022, 0.055),
}
RAW_KEYS = ["r_delta", "r_theta", "r_lalpha", "r_halpha",
            "r_lbeta", "r_hbeta", "r_lgamma", "r_hgamma"]
LABEL = {
    "r_delta":  "Delta",
    "r_theta":  "Theta",
    "r_lalpha": "Low α",
    "r_halpha": "High α",
    "r_lbeta":  "Low β",
    "r_hbeta":  "High β",
    "r_lgamma": "Low γ",
    "r_hgamma": "High γ",
}

def clamp(v, c):
    return max(0.0, min(float(v), c))

def prop_range(value, l1, l2):
    if l1 > l2 or l1 < 0 or value <= 0: return 0.0
    if value >= l2: return 1.0
    if value <= l1: return (value / l1) * 0.5
    return (value - l1) / (l2 - l1) * 0.5 + 0.5

# ── Railway 登入 ──────────────────────────────────────────────────────────────
s = requests.Session(); s.verify = False
tok = s.post(f"{RAILWAY_BASE}/api/v1/auth/login",
             json={"phone": "0900000000", "password": "admin123"}, timeout=15).json().get("token","")
s.headers["Authorization"] = f"Bearer {tok}"
print("✅ Railway 登入成功\n")

for sid in TARGET_SESSIONS:
    print("=" * 65)
    print(f"Session #{sid}")
    print("=" * 65)

    # 取 180 筆逐秒資料
    r = s.get(f"{RAILWAY_BASE}/api/v1/sessions/{sid}/captures", timeout=30)
    if r.status_code != 200:
        print(f"  ❌ captures API 失敗: {r.status_code}")
        continue

    caps = r.json().get("captures", [])
    print(f"  筆數: {len(caps)}")
    if not caps:
        print("  ❌ 無資料"); continue

    # 過濾低品質（delta < 30K）
    MIN_DELTA = 30_000
    DB_KEY = {"r_delta":"delta","r_theta":"theta","r_lalpha":"low_alpha",
              "r_halpha":"high_alpha","r_lbeta":"low_beta","r_hbeta":"high_beta",
              "r_lgamma":"low_gamma","r_hgamma":"high_gamma"}

    def get_val(cap, key):
        return float(cap.get(DB_KEY[key], 0) or 0)

    good_caps = [c for c in caps if get_val(c, "r_delta") >= MIN_DELTA]
    print(f"  有效筆數（delta≥30K）: {len(good_caps)}/{len(caps)}")

    if len(good_caps) < 10:
        print("  ⚠ 有效資料不足，改用全部資料")
        good_caps = caps

    # 分析原始值域
    print(f"\n{'頻段':<10} {'原始均值':>12} {'原始最大值':>12} {'CAP':>10} {'截斷率%':>8}")
    print("-" * 55)
    raw_arrays = {}
    for k in RAW_KEYS:
        vals = [get_val(c, k) for c in good_caps]
        raw_arrays[k] = vals
        avg = statistics.mean(vals)
        mx  = max(vals)
        cap = CAP[k]
        clamped = sum(1 for v in vals if v >= cap)
        print(f"  {LABEL[k]:<8} {avg:>12,.0f} {mx:>12,.0f} {cap:>10,} {clamped/len(vals)*100:>7.1f}%")

    # 依 BrainDNA 演算法計算佔比（每秒各自算再平均）
    n = len(good_caps)
    prop_sums = {k: 0.0 for k in RAW_KEYS}
    for i in range(n):
        # 分母：未截斷原始值之和
        uncapped_total = sum(get_val(good_caps[i], k) for k in RAW_KEYS)
        if uncapped_total == 0: continue
        for k in RAW_KEYS:
            capped_v = clamp(get_val(good_caps[i], k), CAP[k])
            prop_sums[k] += capped_v / uncapped_total
    props = {k: prop_sums[k] / n for k in RAW_KEYS}

    print(f"\n{'頻段':<10} {'平均佔比':>10} {'level1':>8} {'level2':>8} {'得分':>6}")
    print("-" * 50)
    for k in RAW_KEYS:
        p = props[k]
        l1, l2 = PROP_RANGE[k]
        score = round(prop_range(p, l1, l2) * 100)
        flag = " ← 極端" if score >= 95 or score <= 5 else ""
        print(f"  {LABEL[k]:<8} {p*100:>9.2f}%  {l1*100:>6.1f}%  {l2*100:>6.1f}%  {score:>5}{flag}")

    print()
