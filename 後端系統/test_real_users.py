"""
用生產環境三位使用者的真實腦波數據，本地用最新演算法計算 MBTI。
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.algorithms import (
    build_mbti_payload, BandAverages,
    compute_mbti_group_scoring,
    _calc_mind_color, _norm100_to_raw,
    _MC_ORANGE, _MC_GREEN, _MC_BLUE, _MC_YELLOW,
)

# ── 從生產環境 API 取到的真實 bands_avg 數據 ────────────────────
users = [
    {
        "name": "鄭小怡",
        "sid":  52,
        "la": 67, "th": 77, "ha": 67, "hb": 72, "lb": 67, "lg": 71, "hg": 68,
        "delta": 86, "at": 65, "md": 60,  # 估計 attention/meditation
        "n": 150,
    },
    {
        "name": "王筱琪",
        "sid":  49,
        "la": 69, "th": 79, "ha": 66, "hb": 72, "lb": 66, "lg": 70, "hg": 65,
        "delta": 83, "at": 65, "md": 60,
        "n": 150,
    },
    {
        "name": "紀羽珊",
        "sid":  48,
        "la": 69, "th": 79, "ha": 69, "hb": 65, "lb": 67, "lg": 59, "hg": 55,
        "delta": 89, "at": 65, "md": 60,
        "n": 150,
    },
]

MC_NAMES = {_MC_ORANGE:"橙(ORANGE)", _MC_GREEN:"綠(GREEN)", _MC_BLUE:"藍(BLUE)", _MC_YELLOW:"黃(YELLOW)"}

for u in users:
    la, th, ha, hb, lb, lg, hg = u["la"], u["th"], u["ha"], u["hb"], u["lb"], u["lg"], u["hg"]
    print(f"\n{'='*65}")
    print(f"  受測者：{u['name']}  │  Session: {u['sid']}")
    print('='*65)

    # raw 值
    raw_la = _norm100_to_raw(la)
    raw_th = _norm100_to_raw(th)
    raw_ha = _norm100_to_raw(ha)
    raw_hb = _norm100_to_raw(hb)
    raw_lb = _norm100_to_raw(lb)
    raw_lg = _norm100_to_raw(lg)
    raw_hg = _norm100_to_raw(hg)
    print(f"  歸一化 → la={la} th={th} ha={ha} hb={hb} lb={lb} lg={lg} hg={hg}")
    print(f"  raw    → la={raw_la:.0f} th={raw_th:.0f} ha={raw_ha:.0f} hb={raw_hb:.0f} lb={raw_lb:.0f} lg={raw_lg:.0f} hg={raw_hg:.0f}")

    # MindColor（用 raw 值）
    mc = _calc_mind_color(raw_ha, raw_la, raw_hb, raw_lb, raw_lg, raw_hg)
    gamma = raw_lg + raw_hg
    alpha = raw_la + raw_ha
    beta  = raw_lb + raw_hb
    f1 = gamma / alpha * 100 if alpha > 0 else 0
    f2 = gamma / beta  * 100 if beta  > 0 else 0
    print(f"  gamma/alpha ratio: {f1:.1f}  gamma/beta ratio: {f2:.1f}")
    print(f"  心靈色彩：{MC_NAMES[mc]}")

    # 模擬 150 筆 captures（使用相同平均值）
    captures = [
        {"low_alpha": la, "theta": th, "high_alpha": ha,
         "high_beta": hb, "low_beta": lb, "low_gamma": lg, "high_gamma": hg,
         "good_signal": 0}
    ] * u["n"]

    avg = BandAverages(
        delta=u["delta"], theta=th, low_alpha=la, high_alpha=ha,
        low_beta=lb, high_beta=hb, low_gamma=lg, high_gamma=hg,
        attention=u["at"], meditation=u["md"], sample_count=u["n"]
    )

    payload = build_mbti_payload(avg, captures)
    primary = payload.get("mbti_primary")
    secs    = payload.get("mbti_secondaries", [])
    profs   = payload.get("mbti_profiles", [])

    print(f"\n  ✅ 主性格：{primary}  (卦位：{payload.get('mbti_bagua_name','')})")
    if secs:
        for sec in secs:
            print(f"     次性格：{sec['mbti']}  強度 {sec['strength']}%  ({sec['reason']})")
    else:
        print("     (無達 15% 門檻次性格 → 性格特質高度集中)")

    print(f"\n  完整群組評分分布：")
    for p in profs[:6]:
        pct = int(p.get("pct", 0))
        bar = '█' * (pct // 5)
        print(f"    {p.get('type','?'):4s} {pct:3d}%  {bar}")
