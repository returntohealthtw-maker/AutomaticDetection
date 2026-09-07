"""
用新 PROP_RANGE 重新計算 session 104, 105 的各頻段分數
"""
import sys, io, statistics, requests, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
urllib3.disable_warnings()

RAILWAY_BASE = "https://backend-production-2da61.up.railway.app"
TARGET_SESSIONS = [104, 105]

CAP = {
    "r_delta":  500_000, "r_theta":  200_000,
    "r_lalpha":  50_000, "r_halpha":  50_000,
    "r_lbeta":   50_000, "r_hbeta":   50_000,
    "r_lgamma":  25_000, "r_hgamma":  20_000,
}

# ── 新校正後的 PROP_RANGE ──────────────────────────────────────────────────────
NEW_PROP_RANGE = {
    "r_delta":  (0.47, 0.60),
    "r_theta":  (0.14, 0.26),
    "r_lalpha": (0.040, 0.080),
    "r_halpha": (0.033, 0.080),
    "r_lbeta":  (0.028, 0.060),
    "r_hbeta":  (0.041, 0.100),
    "r_lgamma": (0.028, 0.070),
    "r_hgamma": (0.020, 0.060),
}
OLD_PROP_RANGE = {
    "r_delta":  (0.44, 0.60),
    "r_theta":  (0.13, 0.19),
    "r_lalpha": (0.035, 0.065),
    "r_halpha": (0.030, 0.060),
    "r_lbeta":  (0.028, 0.055),
    "r_hbeta":  (0.050, 0.110),
    "r_lgamma": (0.033, 0.075),
    "r_hgamma": (0.022, 0.055),
}
RAW_KEYS = ["r_delta","r_theta","r_lalpha","r_halpha","r_lbeta","r_hbeta","r_lgamma","r_hgamma"]
LABEL    = {"r_delta":"Delta","r_theta":"Theta","r_lalpha":"Low α","r_halpha":"High α",
            "r_lbeta":"Low β","r_hbeta":"High β","r_lgamma":"Low γ","r_hgamma":"High γ"}
DB_KEY   = {"r_delta":"delta","r_theta":"theta","r_lalpha":"low_alpha",
            "r_halpha":"high_alpha","r_lbeta":"low_beta","r_hbeta":"high_beta",
            "r_lgamma":"low_gamma","r_hgamma":"high_gamma"}
MIN_DELTA = 30_000

def clamp(v, c): return max(0.0, min(float(v), c))
def get_val(cap, key): return float(cap.get(DB_KEY[key], 0) or 0)
def prop_range(value, l1, l2):
    if l1 > l2 or l1 < 0 or value <= 0: return 0.0
    if value >= l2: return 1.0
    if value <= l1: return (value / l1) * 0.5
    return (value - l1) / (l2 - l1) * 0.5 + 0.5

s = requests.Session(); s.verify = False
tok = s.post(f"{RAILWAY_BASE}/api/v1/auth/login",
             json={"phone": "0900000000", "password": "admin123"}, timeout=15).json().get("token","")
s.headers["Authorization"] = f"Bearer {tok}"

for sid in TARGET_SESSIONS:
    r = s.get(f"{RAILWAY_BASE}/api/v1/sessions/{sid}/captures", timeout=30)
    caps = r.json().get("captures", [])
    good = [c for c in caps if get_val(c,"r_delta") >= MIN_DELTA]
    if len(good) < 15: good = caps
    n = len(good)

    prop_sums = {k: 0.0 for k in RAW_KEYS}
    for c in good:
        uncapped_total = sum(get_val(c, k) for k in RAW_KEYS)
        if uncapped_total == 0: continue
        for k in RAW_KEYS:
            prop_sums[k] += clamp(get_val(c, k), CAP[k]) / uncapped_total
    props = {k: prop_sums[k] / n for k in RAW_KEYS}

    name_map = {104: "鄭佳宜", 105: "李肯欣"}
    print(f"\n{'='*55}")
    print(f"Session #{sid}  {name_map.get(sid,'')}  有效筆數={n}")
    print(f"{'='*55}")
    print(f"{'頻段':<8} {'實測佔比':>8}  {'舊分數':>6}  {'新分數':>6}  {'變化':>6}")
    print("-" * 55)
    for k in RAW_KEYS:
        p = props[k]
        old_s = round(prop_range(p, *OLD_PROP_RANGE[k]) * 100)
        new_s = round(prop_range(p, *NEW_PROP_RANGE[k]) * 100)
        diff  = new_s - old_s
        flag  = " ✅" if abs(diff) > 5 else ""
        print(f"  {LABEL[k]:<7} {p*100:>7.2f}%   {old_s:>5}    {new_s:>5}   {diff:>+5}{flag}")
