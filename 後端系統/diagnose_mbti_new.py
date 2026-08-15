"""
用最新演算法計算資料庫最近 3 位受測者的 MBTI。
"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

import sqlite3
from app.services.algorithms import (
    build_mbti_payload, compute_averages,
    compute_mbti_group_scoring,
    _calc_mind_color, _MC_ORANGE, _MC_GREEN, _MC_BLUE, _MC_YELLOW,
)

DB_PATH = "D:/Write program/Database/ToOtherProject/eeg_dev.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# ── 取最近 3 個有腦波資料的 session ──────────────────────────────
sessions = conn.execute("""
    SELECT s.session_id, s.subject_name, s.created_at
    FROM sessions s
    WHERE s.session_id IN (
        SELECT DISTINCT session_id FROM eeg_captures LIMIT 9999
    )
    ORDER BY s.created_at DESC
    LIMIT 3
""").fetchall()

print(f"最近 3 個 session：")
for row in sessions:
    print(f"  [{row['session_id']}] {row['subject_name']} — {row['created_at']}")

MC_NAMES = {_MC_ORANGE: "橙", _MC_GREEN: "綠", _MC_BLUE: "藍", _MC_YELLOW: "黃"}

for sess in sessions:
    sid    = sess['session_id']
    sname  = sess['subject_name'] or f"(session {sid})"
    print(f"\n{'='*65}")
    print(f"  受測者：{sname}  │  Session ID: {sid}")
    print('='*65)

    captures_raw = conn.execute("""
        SELECT theta, low_alpha, high_alpha,
               low_beta, high_beta,
               low_gamma, high_gamma,
               attention, meditation, delta, good_signal
        FROM eeg_captures
        WHERE session_id = ?
        ORDER BY capture_id
    """, (sid,)).fetchall()

    if not captures_raw:
        print("  ⚠ 無腦波資料")
        continue

    captures = [dict(r) for r in captures_raw]
    n = len(captures)
    print(f"  資料筆數：{n}")

    # ── 基本統計 ───────────────────────────────────────────────────
    avg = compute_averages(captures)
    print(f"  lowAlpha 均值：{avg.low_alpha:.1f}   theta 均值：{avg.theta:.1f}")
    print(f"  highGamma 均值：{avg.high_gamma:.1f}  lowGamma 均值：{avg.low_gamma:.1f}")

    # ── MindColor 分布 ─────────────────────────────────────────────
    mc_count = {0:0, 1:0, 2:0, 3:0}
    for c in captures:
        mc = _calc_mind_color(
            c.get('high_alpha',0), c.get('low_alpha',0),
            c.get('high_beta',0),  c.get('low_beta',0),
            c.get('low_gamma',0),  c.get('high_gamma',0),
        )
        mc_count[mc] += 1
    mc_total = n
    print(f"  心靈色彩分布：" +
          "  ".join(f"{MC_NAMES[k]}:{mc_count[k]} ({mc_count[k]*100//mc_total}%)"
                   for k in [0,1,2,3]))

    # ── 群組評分 ──────────────────────────────────────────────────
    group_profiles = compute_mbti_group_scoring(captures)
    if group_profiles:
        print(f"\n  群組評分結果（所有有分類型）：")
        for p in group_profiles:
            bar = '█' * (p['pct'] // 5)
            print(f"    {p['type']:4s} {p['pct']:3d}%  {bar}")

    # ── 最終 payload ──────────────────────────────────────────────
    payload = build_mbti_payload(avg, captures)
    print(f"\n  ✅ 主性格：{payload['mbti_primary']}")
    secs = payload['mbti_secondaries']
    if secs:
        for s in secs:
            print(f"     次性格：{s['mbti']}  強度 {s['strength']}%  ({s['reason']})")
    else:
        print(f"     (無達門檻的次性格)")

conn.close()
