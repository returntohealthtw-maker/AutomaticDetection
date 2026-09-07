"""
BrainDNA 參數校正前後對照驗證腳本
- 從 Railway 拉多位受測者的逐秒 captures
- 同時用舊/新兩組 CAP + PROP_RANGE 計算分數
- 印出個體對照表，確認新參數是否產生足夠個體差異
"""
import sys, io, math, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "https://backend-production-2da61.up.railway.app/api/v1"

# ── 登入取 token ──────────────────────────────────────────────
r = requests.post(f"{BASE}/auth/login", json={"phone": "0900000000", "password": "admin123"})
d = r.json(); token = d.get("access_token") or d.get("token", "")
h = {"Authorization": f"Bearer {token}"}
print(f"登入: {'OK' if token else 'FAIL'}\n")

# ── 取 session 列表，選有逐秒資料的 ──────────────────────────
sessions_r = requests.get(f"{BASE}/eeg/sessions?limit=120", headers=h).json()
sessions = sessions_r if isinstance(sessions_r, list) else sessions_r.get("sessions", [])

# 只取 total_captures >= 30 的（有逐秒資料才有意義）
cands = [s for s in sessions if (s.get("total_captures") or 0) >= 30]
print(f"總 sessions: {len(sessions)}，有逐秒資料(≥30筆): {len(cands)}")

# ── 演算法工具函式 ─────────────────────────────────────────────
RAW_KEYS = ["r_delta","r_theta","r_lalpha","r_halpha","r_lbeta","r_hbeta","r_lgamma","r_hgamma"]
WIN = 30

def clamp(v, cap): return max(0.0, min(float(v), cap))

def prop_range(value, l1, l2):
    if l1 > l2 or l1 < 0 or value <= 0: return 0.0
    if value >= l2: return 1.0
    if value <= l1: return (value / l1) * 0.5
    return (value - l1) / (l2 - l1) * 0.5 + 0.5

def calc_scores(rows, cap, pr):
    """rows: list of dict with r_delta..r_hgamma"""
    MIN_DELTA = 30000
    # フィルタ: delta が低すぎる秒は除外
    rows = [r for r in rows if r.get("r_delta", 0) >= MIN_DELTA]
    if len(rows) < 5:
        return None

    # Best 30s window（lgamma proportionRange 評分最高）
    n = len(rows)
    num_win = math.ceil(n / WIN)
    lg_l1, lg_l2 = pr["r_lgamma"]
    best_idx, best_score = 0, -1.0
    for w in range(num_win):
        s, e = w * WIN, min((w + 1) * WIN, n)
        ps, vs = 0.0, 0
        for row in rows[s:e]:
            tot = sum(row.get(k, 0) for k in RAW_KEYS)
            if tot > 0:
                ps += clamp(row["r_lgamma"], cap["r_lgamma"]) / tot
                vs += 1
        if vs > 0:
            sc = prop_range(ps / vs, lg_l1, lg_l2)
            if sc > best_score:
                best_score, best_idx = sc, w

    win_rows = rows[best_idx * WIN: (best_idx + 1) * WIN]

    # 各頻段佔比 → proportionRange 評分
    prop_sum = {k: 0.0 for k in RAW_KEYS}
    valid = 0
    for row in win_rows:
        tot = sum(row.get(k, 0) for k in RAW_KEYS)
        if tot > 0:
            for k in RAW_KEYS:
                prop_sum[k] += clamp(row.get(k, 0), cap[k]) / tot
            valid += 1
    if valid == 0:
        return None

    scores = {}
    labels = {"r_delta":"delta","r_theta":"theta","r_lalpha":"lalpha","r_halpha":"halpha",
              "r_lbeta":"lbeta","r_hbeta":"hbeta","r_lgamma":"lgamma","r_hgamma":"hgamma"}
    raw_props = {}
    for k in RAW_KEYS:
        p = prop_sum[k] / valid
        raw_props[labels[k]] = round(p * 100, 1)
        l1, l2 = pr[k]
        scores[labels[k]] = round(prop_range(p, l1, l2) * 100, 1)
    return scores, raw_props, valid

# ── 兩組參數 ──────────────────────────────────────────────────
CAP_OLD = {"r_delta":98000,"r_theta":98000,"r_lalpha":50000,"r_halpha":50000,
           "r_lbeta":50000,"r_hbeta":50000,"r_lgamma":10000,"r_hgamma":10000}
PR_OLD  = {"r_delta":(0.60,0.80),"r_theta":(0.15,0.30),"r_lalpha":(0.10,0.20),
           "r_halpha":(0.10,0.20),"r_lbeta":(0.05,0.10),"r_hbeta":(0.05,0.10),
           "r_lgamma":(0.03,0.06),"r_hgamma":(0.03,0.06)}

CAP_NEW = {"r_delta":500000,"r_theta":200000,"r_lalpha":50000,"r_halpha":50000,
           "r_lbeta":50000,"r_hbeta":50000,"r_lgamma":25000,"r_hgamma":20000}
# level1 = 族群中位數，level2 = 族群高分段（使一半人低於50、一半人高於50）
PR_NEW  = {"r_delta":(0.44,0.60),"r_theta":(0.13,0.19),"r_lalpha":(0.035,0.065),
           "r_halpha":(0.030,0.060),"r_lbeta":(0.028,0.055),"r_hbeta":(0.050,0.110),
           "r_lgamma":(0.033,0.075),"r_hgamma":(0.022,0.055)}

# ── 逐一拉資料並計算 ──────────────────────────────────────────
results = []
MAX_SESSIONS = 15  # 最多取 15 筆避免太慢
for sess in cands[:MAX_SESSIONS]:
    sid = sess.get("session_id") or sess.get("id")
    name = sess.get("subject_name", "?")[:6]
    caps_r = requests.get(f"{BASE}/sessions/{sid}/captures", headers=h).json()
    caps = caps_r.get("captures", [])

    # 轉成 r_delta ... 格式（只取 is_baseline=0）
    rows = []
    for c in caps:
        if c.get("is_baseline", 0) == 1:
            continue
        rows.append({
            "r_delta":  c.get("delta",      0) or 0,
            "r_theta":  c.get("theta",      0) or 0,
            "r_lalpha": c.get("low_alpha",  0) or 0,
            "r_halpha": c.get("high_alpha", 0) or 0,
            "r_lbeta":  c.get("low_beta",   0) or 0,
            "r_hbeta":  c.get("high_beta",  0) or 0,
            "r_lgamma": c.get("low_gamma",  0) or 0,
            "r_hgamma": c.get("high_gamma", 0) or 0,
        })
    if len(rows) < 5:
        print(f"  Session#{sid} ({name}) 資料不足，跳過")
        continue

    res_old = calc_scores(rows, CAP_OLD, PR_OLD)
    res_new = calc_scores(rows, CAP_NEW, PR_NEW)
    if not res_old or not res_new:
        continue

    old_s, _, _ = res_old
    new_s, raw_p, valid = res_new

    results.append({
        "id": sid, "name": name, "n": valid,
        "old": old_s, "new": new_s, "raw": raw_p,
        "delta_raw_mean": round(sum(r["r_delta"] for r in rows) / len(rows))
    })
    print(f"  Session#{sid} ({name}) n={valid}  delta均值={results[-1]['delta_raw_mean']:,}")

# ── 印出對照表 ────────────────────────────────────────────────
BANDS = ["delta","theta","lalpha","halpha","lbeta","hbeta","lgamma","hgamma"]

import statistics

# ── 印出各頻段實際佔比分布（供重新校正 PROP_RANGE 用）──────────────
ALL_LABELS = ["delta","theta","lalpha","halpha","lbeta","hbeta","lgamma","hgamma"]
print("\n" + "="*120)
print("各頻段實際佔比 (%, 新CAP後)  ← 用來確認 PROP_RANGE 設定是否合理")
print(f"{'ID':>4} {'姓名':>6} {'n':>4}  " + "  ".join(f"{b:>8}" for b in ALL_LABELS))
print("-"*120)
for r in results:
    vals = "  ".join(f"{r['raw'][b]:>7.1f}%" for b in ALL_LABELS)
    print(f"{r['id']:>4} {r['name']:>6} {r['n']:>4}  {vals}")

if results:
    print(f"  {'min':>8}  " + "  ".join(
        f"{min(r['raw'][b] for r in results):>7.1f}%" for b in ALL_LABELS))
    print(f"  {'max':>8}  " + "  ".join(
        f"{max(r['raw'][b] for r in results):>7.1f}%" for b in ALL_LABELS))
    print(f"  {'mean':>8}  " + "  ".join(
        f"{statistics.mean(r['raw'][b] for r in results):>7.1f}%" for b in ALL_LABELS))

# ── 新舊分數對照表 ────────────────────────────────────────────
print("\n" + "="*110)
print(f"{'ID':>4} {'姓名':>6} {'n':>4}  " +
      "".join(f"{'[舊]'+b:>9}" for b in ALL_LABELS) + "  |  " +
      "".join(f"{'[新]'+b:>9}" for b in ALL_LABELS))
print("-"*110)
for r in results:
    old_line = "".join(f"{r['old'][b]:>9.0f}" for b in ALL_LABELS)
    new_line = "".join(f"{r['new'][b]:>9.0f}" for b in ALL_LABELS)
    print(f"{r['id']:>4} {r['name']:>6} {r['n']:>4}  {old_line}  |  {new_line}")

# ── 統計個體差異 ──────────────────────────────────────────────
if len(results) >= 2:
    print("\n── 個體差異統計 ──")
    for tag, key in [("舊參數", "old"), ("新參數", "new")]:
        for b in ALL_LABELS:
            vals = [r[key][b] for r in results]
            mn, mx = min(vals), max(vals)
            sd = statistics.stdev(vals) if len(vals) > 1 else 0
            print(f"  [{tag}] {b:>7}: min={mn:>3.0f}  max={mx:>3.0f}  range={mx-mn:>3.0f}  stdev={sd:.1f}")

print("\n完成。range/stdev 越大代表個體差異越明顯。")
