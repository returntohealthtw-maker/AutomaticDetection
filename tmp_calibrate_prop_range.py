"""
從 Railway 拉所有有 180 筆資料的 sessions，
計算每個頻段的實際佔比分佈，
找出 50th percentile（level1）和 90th percentile（level2）
"""
import sys, io, statistics, requests, urllib3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
urllib3.disable_warnings()

RAILWAY_BASE = "https://backend-production-2da61.up.railway.app"

CAP = {
    "r_delta":  500_000, "r_theta":  200_000,
    "r_lalpha":  50_000, "r_halpha":  50_000,
    "r_lbeta":   50_000, "r_hbeta":   50_000,
    "r_lgamma":  25_000, "r_hgamma":  20_000,
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

def calc_avg_props(good_caps):
    n = len(good_caps)
    prop_sums = {k: 0.0 for k in RAW_KEYS}
    for c in good_caps:
        uncapped_total = sum(get_val(c, k) for k in RAW_KEYS)
        if uncapped_total == 0: continue
        for k in RAW_KEYS:
            prop_sums[k] += clamp(get_val(c, k), CAP[k]) / uncapped_total
    return {k: prop_sums[k] / n for k in RAW_KEYS}

# ── Railway 登入 ──────────────────────────────────────────────────────────────
s = requests.Session(); s.verify = False
tok = s.post(f"{RAILWAY_BASE}/api/v1/auth/login",
             json={"phone": "0900000000", "password": "admin123"}, timeout=15).json().get("token","")
s.headers["Authorization"] = f"Bearer {tok}"
print("✅ Railway 登入成功")

# 取 session 清單
sessions_r = s.get(f"{RAILWAY_BASE}/api/v1/eeg/sessions?limit=200", timeout=20)
sessions = sessions_r.json().get("sessions", [])
print(f"共 {len(sessions)} 筆 sessions\n")

all_props = {k: [] for k in RAW_KEYS}
processed = []

for sess in sessions:
    sid = sess.get("id") or sess.get("session_id")
    name = sess.get("subject_name","?")
    r = s.get(f"{RAILWAY_BASE}/api/v1/sessions/{sid}/captures", timeout=30)
    if r.status_code != 200: continue
    caps = r.json().get("captures", [])
    if len(caps) < 30: continue  # 太少筆略過

    # 過濾低品質
    good = [c for c in caps if get_val(c,"r_delta") >= MIN_DELTA]
    if len(good) < 15: good = caps  # fallback

    props = calc_avg_props(good)

    # 只收 raw 模式（delta 均值 > 1000）
    delta_avg = statistics.mean([get_val(c,"r_delta") for c in good])
    if delta_avg <= 1000: continue

    for k in RAW_KEYS:
        all_props[k].append(props[k])
    processed.append((sid, name, props))
    print(f"  session={sid} ({name})  筆數={len(good)}  delta均值={delta_avg:,.0f}")

print(f"\n有效 sessions: {len(processed)} 筆\n")
print("=" * 70)
print(f"{'頻段':<10} {'min':>7} {'p25':>7} {'p50(L1)':>9} {'p75':>7} {'p90(L2)':>9} {'max':>7}")
print("-" * 70)
for k in RAW_KEYS:
    vals = sorted(all_props[k])
    n = len(vals)
    if n < 2:
        print(f"  {LABEL[k]:<8}  資料不足"); continue
    mn  = vals[0]
    p25 = vals[int(n*0.25)]
    p50 = vals[int(n*0.50)]
    p75 = vals[int(n*0.75)]
    p90 = vals[min(int(n*0.90), n-1)]
    mx  = vals[-1]
    print(f"  {LABEL[k]:<8} {mn*100:>6.1f}% {p25*100:>6.1f}% {p50*100:>8.1f}% {p75*100:>6.1f}% {p90*100:>8.1f}% {mx*100:>6.1f}%")

print()
print("建議更新 _PROP_RANGE（level1=p50, level2=p90）：")
print("_PROP_RANGE = {")
for k in RAW_KEYS:
    vals = sorted(all_props[k])
    n = len(vals)
    if n < 2: continue
    p50 = vals[int(n*0.50)]
    p90 = vals[min(int(n*0.90), n-1)]
    print(f'    "{k}": ({p50:.3f}, {p90:.3f}),  # {LABEL[k]}')
print("}")
