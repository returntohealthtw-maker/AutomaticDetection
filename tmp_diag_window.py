"""
Diagnostic: session #113 best window proportions (30s vs 90s)
"""
import sys, json, math, requests, warnings
warnings.filterwarnings("ignore")

BASE = "https://backend-production-2da61.up.railway.app"
s = requests.Session()
r = s.post(f"{BASE}/api/v1/auth/login", json={"phone": "0900000000", "password": "admin123"}, verify=False)
print("Login:", r.status_code)
token = r.json().get("access_token")
s.headers["Authorization"] = f"Bearer {token}"

r4 = s.get(f"{BASE}/api/v1/sessions/113/captures", verify=False)
print("Captures:", r4.status_code)
data = r4.json()
caps = data.get("captures") if isinstance(data, dict) else data
print(f"Records: {len(caps)}")

RAW_KEYS = ["r_delta","r_theta","r_lalpha","r_halpha","r_lbeta","r_hbeta","r_lgamma","r_hgamma"]
FIELD_MAP = {"r_delta":"delta","r_theta":"theta","r_lalpha":"low_alpha","r_halpha":"high_alpha",
             "r_lbeta":"low_beta","r_hbeta":"high_beta","r_lgamma":"low_gamma","r_hgamma":"high_gamma"}
LABELS = {"r_delta":"Delta","r_theta":"Theta","r_lalpha":"Low-a","r_halpha":"High-a",
          "r_lbeta":"Low-b","r_hbeta":"High-b","r_lgamma":"Low-g","r_hgamma":"High-g"}

raw = {}
for k in RAW_KEYS:
    raw[k] = [float(c.get(FIELD_MAP[k], 0) or 0) for c in caps]
raw["attn"] = [float(c.get("attention", 0) or 0) for c in caps]
raw["medi"] = [float(c.get("meditation", 0) or 0) for c in caps]

print("\n--- Full session average proportions (no CAP) ---")
avgs = {k: sum(raw[k])/max(len(raw[k]),1) for k in RAW_KEYS}
total_avg = sum(avgs.values())
for k in RAW_KEYS:
    print(f"  {LABELS[k]:8}: avg={avgs[k]:>10.0f}  prop={avgs[k]/total_avg*100:.2f}%")

CHILD_CAP = {"r_delta":400000,"r_theta":230000,"r_lalpha":50000,"r_halpha":50000,
             "r_lbeta":50000,"r_hbeta":50000,"r_lgamma":20000,"r_hgamma":20000}

CHILD_PR_6_9 = {"r_delta":(0.44,0.54),"r_theta":(0.17,0.21),
                "r_lalpha":(0.062,0.089),"r_halpha":(0.062,0.089),
                "r_lbeta":(0.065,0.095),"r_hbeta":(0.065,0.095),
                "r_lgamma":(0.025,0.055),"r_hgamma":(0.015,0.040)}

def clamp(v, cap): return max(0.0, min(float(v), cap))

def prop_range(val, l1, l2):
    if l1 > l2 or l1 < 0 or val <= 0: return 0.0
    if val >= l2: return 1.0
    if val <= l1: return (val / l1) * 0.5
    return (val - l1) / (l2 - l1) * 0.5 + 0.5

def select_best_window(raw, ws, cap, pr):
    n = len(raw["r_lalpha"])
    lg_cap = cap["r_lgamma"]
    pr_l1, pr_l2 = pr["r_lgamma"]
    best_idx = 0; best_score = -1.0; scores = []
    for i in range(math.ceil(n / ws)):
        s2 = i * ws; e2 = min(s2 + ws, n)
        ps = 0.0; valid = 0
        for j in range(s2, e2):
            row = {k: float(raw[k][j]) for k in RAW_KEYS}
            total = sum(row.values())
            if total > 0:
                ps += clamp(row["r_lgamma"], lg_cap) / total; valid += 1
        if valid > 0:
            sc = prop_range(ps/valid, pr_l1, pr_l2)
            scores.append((i, sc, ps/valid))
            if sc > best_score: best_score = sc; best_idx = i
    s2 = best_idx * ws; e2 = min(s2 + ws, n)
    win = {k: raw[k][s2:e2] for k in list(RAW_KEYS)+["attn","medi"]}
    return win, best_idx, scores

def compute_props(win, cap, pr):
    n = len(win["r_lalpha"]); prop_sum = {k: 0.0 for k in RAW_KEYS}; valid = 0
    MIN_DELTA = 30000
    for i in range(n):
        row = {k: float(win[k][i]) for k in RAW_KEYS}
        total = sum(row.values())
        if total <= 0 or row["r_delta"] < MIN_DELTA: continue
        for k in RAW_KEYS:
            prop_sum[k] += clamp(row[k], cap[k]) / total
        valid += 1
    if valid == 0: return None
    props = {k: prop_sum[k]/valid for k in RAW_KEYS}
    scores = {k: round(prop_range(props[k], *pr[k]) * 100) for k in RAW_KEYS}
    return props, scores, valid

for ws in [30, 90]:
    print(f"\n{'='*65}")
    print(f"  Best {ws}s window analysis")
    win, best_idx, all_scores = select_best_window(raw, ws, CHILD_CAP, CHILD_PR_6_9)
    print(f"  Selected window #{best_idx} (total {len(all_scores)} windows)")
    for idx, sc, p in all_scores:
        mark = " <- BEST" if idx == best_idx else ""
        print(f"    win#{idx}: lgamma={p*100:.2f}%  score={sc:.3f}{mark}")
    
    result = compute_props(win, CHILD_CAP, CHILD_PR_6_9)
    if result:
        props, scores, valid = result
        print(f"\n  Valid seconds in window: {valid}")
        print(f"\n  {'Band':8} {'Prop%':>8} {'L1':>7} {'L2':>7} {'Score':>6} {'Status'}")
        print(f"  {'-'*55}")
        for k in RAW_KEYS:
            l1, l2 = CHILD_PR_6_9[k]
            p = props[k]
            sc = scores[k]
            status = "OVER L2" if p >= l2 else ("OK" if p >= l1 else "BELOW L1")
            print(f"  {LABELS[k]:8} {p*100:>8.2f}% {l1*100:>6.1f}% {l2*100:>6.1f}% {sc:>5}  {status}")
        
        print(f"\n  Suggested new level2 (actual_prop x 1.5 for safety margin):")
        for k in RAW_KEYS:
            l1_curr = CHILD_PR_6_9[k][0]
            suggested_l2 = max(props[k] * 1.5, CHILD_PR_6_9[k][1])
            print(f"    {LABELS[k]:8}: actual={props[k]*100:.2f}%  -> suggested level2={suggested_l2:.4f} ({suggested_l2*100:.1f}%)")
