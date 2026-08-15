"""
BrainDNA vs QEEG 對比驗證腳本
同一筆 session 同時用兩種演算法計算，並排顯示結果
"""
import sys, io, os, math, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from services.qeeg_pipeline import run_qeeg_pipeline
from services.braindna_algorithms import compute_all

BASE = "https://backend-production-2da61.up.railway.app/api/v1"

# ── 登入 ───────────────────────────────────────────────────────
r = requests.post(f"{BASE}/auth/login", json={"phone": "0900000000", "password": "admin123"})
d = r.json(); token = d.get("access_token") or d.get("token", "")
h = {"Authorization": f"Bearer {token}"}
print(f"登入: {'OK' if token else 'FAIL'}\n")

# ── 取 sessions ────────────────────────────────────────────────
sessions = requests.get(f"{BASE}/eeg/sessions?limit=120", headers=h).json()
if isinstance(sessions, dict): sessions = sessions.get("sessions", [])
cands = [s for s in sessions if (s.get("total_captures") or 0) >= 30]
print(f"有逐秒資料的 sessions: {len(cands)}\n")

# ── 逐一計算 ──────────────────────────────────────────────────
results = []
MAX = 12
for sess in cands[:MAX]:
    sid  = sess.get("session_id") or sess.get("id")
    name = (sess.get("subject_name") or "?")[:6]
    caps_r = requests.get(f"{BASE}/sessions/{sid}/captures", headers=h).json()
    caps   = caps_r.get("captures", [])

    # 轉成 raw_arrays 格式（排除 baseline）
    raw = {k: [] for k in ["r_delta","r_theta","r_lalpha","r_halpha",
                            "r_lbeta","r_hbeta","r_lgamma","r_hgamma","attn","medi"]}
    for c in caps:
        if c.get("is_baseline", 0): continue
        raw["r_delta"].append(c.get("delta",0) or 0)
        raw["r_theta"].append(c.get("theta",0) or 0)
        raw["r_lalpha"].append(c.get("low_alpha",0) or 0)
        raw["r_halpha"].append(c.get("high_alpha",0) or 0)
        raw["r_lbeta"].append(c.get("low_beta",0) or 0)
        raw["r_hbeta"].append(c.get("high_beta",0) or 0)
        raw["r_lgamma"].append(c.get("low_gamma",0) or 0)
        raw["r_hgamma"].append(c.get("high_gamma",0) or 0)
        raw["attn"].append(c.get("attention",0) or 0)
        raw["medi"].append(c.get("meditation",0) or 0)

    if len(raw["r_delta"]) < 10:
        print(f"  #{sid} ({name}) 資料不足，跳過")
        continue

    # ── BrainDNA ──
    bdna = compute_all(raw, is_child=False)
    bdna_bands = bdna.get("bands", {}) if bdna else {}

    # ── QEEG ──
    age = 35  # 預設年齡（無法從 session 取得時用 35）
    qeeg = run_qeeg_pipeline(
        raw_arrays   = raw,
        captures     = None,
        subject_info = {"name": name, "age": age, "sex": "male"},
    )
    qeeg_ab  = qeeg.get("ability_scores", {})  if qeeg else {}
    qeeg_bf  = (qeeg.get("band_features", {}).get("Fp1", {}) if qeeg else {})

    results.append({
        "id": sid, "name": name, "n": len(raw["r_delta"]),
        "bdna": bdna_bands,
        "qeeg_ab": qeeg_ab,
        "qeeg_bf": qeeg_bf,
        "qeeg_quality": qeeg.get("signal_quality", {}).get("quality_grade", "?") if qeeg else "?"
    })
    print(f"  #{sid} ({name}) done  "
          f"BDNA delta={bdna_bands.get('delta',0):.0f}  "
          f"QEEG focus={qeeg_ab.get('focus',{}).get('score',0):.0f}")

# ── 印出對照表 ─────────────────────────────────────────────────
BDNA_FIELDS = ["delta","theta","low_alpha","high_alpha","low_beta","high_beta","low_gamma","high_gamma"]
BDNA_LABELS = ["delta","theta","lAlpha","hAlpha","lBeta","hBeta","lGamma","hGamma"]
AB_FIELDS   = ["intuition","energy","relaxation","focus","logic","awareness","empathy"]
AB_LABELS   = ["直覺","活力","放鬆","專注","邏輯","覺察","同理"]

print("\n" + "="*140)
print("【BrainDNA 頻段分數（0~100，中位數=50）】")
print(f"{'ID':>4} {'姓名':>6} {'n':>4}  " + "  ".join(f"{b:>7}" for b in BDNA_LABELS))
print("-"*90)
for r in results:
    vals = "  ".join(f"{r['bdna'].get(k,0):>7.0f}" for k in BDNA_FIELDS)
    print(f"{r['id']:>4} {r['name']:>6} {r['n']:>4}  {vals}")

print("\n" + "="*140)
print("【QEEG 七大能力分數（0~100，Z-score sigmoid 轉換）】")
print(f"{'ID':>4} {'姓名':>6} {'品質':>4}  " + "  ".join(f"{b:>7}" for b in AB_LABELS))
print("-"*90)
for r in results:
    vals = "  ".join(f"{r['qeeg_ab'].get(k,{}).get('score',0):>7.0f}" for k in AB_FIELDS)
    print(f"{r['id']:>4} {r['name']:>6} {r['qeeg_quality']:>4}  {vals}")

print("\n" + "="*140)
print("【QEEG 頻段 Z-score 分數（sigmoid 轉換後 0~100，50=族群平均）】")
BF_KEYS = ["delta","theta","low_alpha","high_alpha","low_beta","high_beta","low_gamma","high_gamma"]
print(f"{'ID':>4} {'姓名':>6}  " + "  ".join(f"{b:>7}" for b in BDNA_LABELS))
print("-"*90)
for r in results:
    vals = "  ".join(f"{r['qeeg_bf'].get(k,{}).get('score_0_100',0):>7.0f}" for k in BF_KEYS)
    print(f"{r['id']:>4} {r['name']:>6}  {vals}")

# ── 統計 ─────────────────────────────────────────────────────
import statistics
if len(results) >= 2:
    print("\n── 個體差異統計（stdev 越大=個體差異越明顯）──")
    print(f"  {'演算法':12} {'頻段/能力':12}  stdev  range")
    for band, label in zip(BDNA_FIELDS, BDNA_LABELS):
        vals = [r["bdna"].get(band, 0) for r in results]
        sd = statistics.stdev(vals); rng = max(vals)-min(vals)
        print(f"  {'BrainDNA':12} {label:12}  {sd:5.1f}  {rng:.0f}")
    for key, label in zip(AB_FIELDS, AB_LABELS):
        vals = [r["qeeg_ab"].get(key,{}).get("score",0) for r in results]
        sd = statistics.stdev(vals); rng = max(vals)-min(vals)
        print(f"  {'QEEG能力':12} {label:12}  {sd:5.1f}  {rng:.0f}")

print("\n完成。")
