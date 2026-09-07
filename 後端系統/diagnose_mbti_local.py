"""
從 eeg_stats 取得腦波統計並在本地用最新演算法計算 MBTI。
"""
import sys, io, requests, json, urllib3, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.algorithms import (
    build_mbti_payload, compute_averages, compute_mbti_group_scoring,
    _calc_mind_color, BandAverages,
    _MC_ORANGE, _MC_GREEN, _MC_BLUE, _MC_YELLOW,
)

BASE  = "https://backend-production-2da61.up.railway.app"
s = requests.Session(); s.verify = False
TOKEN = s.post(f"{BASE}/api/v1/auth/login",
               json={"phone":"0900000000","password":"admin123"}, timeout=10
               ).json().get("token","")
s.headers["Authorization"] = f"Bearer {TOKEN}"

all_sess = s.get(f"{BASE}/api/v1/eeg/sessions", timeout=15).json().get("sessions", [])
seen = {}; recent = []
for sess in sorted(all_sess, key=lambda x: x.get("created_at",""), reverse=True):
    name = sess.get("subject_name") or "Unknown"
    sid  = sess.get("session_id") or sess.get("id")
    if name not in seen and sid:
        seen[name] = True
        recent.append({"name": name, "sid": sid})
    if len(recent) >= 3:
        break

MC_NAMES = {_MC_ORANGE:"橙", _MC_GREEN:"綠", _MC_BLUE:"藍", _MC_YELLOW:"黃"}

for item in recent:
    name = item["name"]
    sid  = item["sid"]
    print(f"\n{'='*65}")
    print(f"  受測者：{name}  │  Session ID: {sid}")
    print('='*65)

    rs = s.get(f"{BASE}/api/v1/eeg/sessions/{sid}/stats", timeout=15).json()
    eeg = rs.get("eeg_stats") or {}
    if not eeg:
        print("  ⚠ 無 eeg_stats")
        print("  Keys:", list(rs.keys()))
        print("  raw:", json.dumps(rs, ensure_ascii=False)[:400])
        continue

    print(f"  eeg_stats keys: {list(eeg.keys())}")

    def _g(d, *keys, default=0.0):
        for k in keys:
            if k in d:
                v = d[k]
                return float(v) if v is not None else default
        return default

    avg = BandAverages(
        delta      = _g(eeg, "delta"),
        theta      = _g(eeg, "theta"),
        low_alpha  = _g(eeg, "low_alpha", "lowAlpha"),
        high_alpha = _g(eeg, "high_alpha", "highAlpha"),
        low_beta   = _g(eeg, "low_beta", "lowBeta"),
        high_beta  = _g(eeg, "high_beta", "highBeta"),
        low_gamma  = _g(eeg, "low_gamma", "lowGamma"),
        high_gamma = _g(eeg, "high_gamma", "highGamma"),
        attention  = _g(eeg, "attention"),
        meditation = _g(eeg, "meditation"),
        sample_count = int(_g(eeg, "sample_count", default=0)),
    )

    print(f"  腦波均值：la={avg.low_alpha:.1f} th={avg.theta:.1f} ha={avg.high_alpha:.1f}")
    print(f"            hb={avg.high_beta:.1f} lb={avg.low_beta:.1f} lg={avg.low_gamma:.1f} hg={avg.high_gamma:.1f}")

    mc = _calc_mind_color(avg.high_alpha, avg.low_alpha,
                          avg.high_beta,  avg.low_beta,
                          avg.low_gamma,  avg.high_gamma)
    print(f"  心靈色彩（平均值）：{MC_NAMES[mc]}")

    # Try to get captures via diag endpoint
    rd = s.get(f"{BASE}/api/v1/reports/diag/mbti/{sid}", timeout=15)
    captures_list = []
    if rd.status_code == 200:
        mbti_resp = rd.json()
        captures_list = mbti_resp.get("captures") or []
        print(f"  Captures from diag: {len(captures_list)}")

    payload = build_mbti_payload(avg, captures_list if captures_list else None)
    primary = payload.get("mbti_primary")
    secs    = payload.get("mbti_secondaries", [])
    profs   = payload.get("mbti_profiles", [])

    print(f"\n  ✅ 主性格：{primary}  (卦位：{payload.get('mbti_bagua_name','')})")
    if secs:
        for sec in secs:
            print(f"     次性格：{sec['mbti']}  {sec['strength']}%  ({sec['reason']})")
    else:
        print("     (無達 15% 門檻次性格 → 性格特質高度集中)")

    print(f"\n  完整評分分布：")
    for p in profs[:6]:
        pct = int(p.get("pct", 0))
        bar = '█' * (pct // 5)
        print(f"    {p.get('type','?'):4s} {pct:3d}%  {bar}")
