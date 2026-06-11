"""
診斷指定受測者的報告生成失敗原因
"""
import sqlite3, json

DB = "D:/Write program/Database/ToOtherProject/eeg_dev.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

NAME = "邱心又"

print("=" * 60)
print(f"診斷：{NAME} 的報告生成狀況")
print("=" * 60)

# 找 sessions
sessions = conn.execute(
    "SELECT * FROM sessions WHERE subject_name LIKE ?", (f"%{NAME}%",)
).fetchall()
print(f"\n[Sessions] 找到 {len(sessions)} 筆")
for s in sessions:
    print(f"  session_id={s['session_id']} status={s['status']} "
          f"report_type={s['report_type']} captures={s['total_captures']} "
          f"created_at={s['created_at']}")

# 找 reports
if sessions:
    ids = tuple(s['session_id'] for s in sessions)
    placeholders = ",".join("?" * len(ids))
    reports = conn.execute(
        f"SELECT * FROM reports WHERE session_id IN ({placeholders})", ids
    ).fetchall()
    print(f"\n[Reports] 找到 {len(reports)} 筆")
    for r in reports:
        print(f"  report_id={r['report_id']} session_id={r['session_id']} "
              f"status={r['status']} pdf_url={str(r['pdf_url'])[:80] if r['pdf_url'] else 'NULL'}")

    # 找 events
    rep_ids = tuple(r['report_id'] for r in reports) if reports else ()
    if rep_ids:
        placeholders2 = ",".join("?" * len(rep_ids))
        events = conn.execute(
            f"""SELECT * FROM report_generation_events
                WHERE session_id IN ({placeholders})
                ORDER BY created_at DESC LIMIT 30""", ids
        ).fetchall()
        print(f"\n[Generation Events] 最近 {len(events)} 筆")
        for e in events:
            print(f"  [{e['phase']}] {e['error_message'] or ''} "
                  f"dur={e['duration_ms']}ms created_at={e['created_at']}")

# 找 eeg_captures
if sessions:
    for s in sessions:
        caps = conn.execute(
            "SELECT COUNT(*) as cnt, AVG(attention) as attn, AVG(meditation) as medi, "
            "AVG(low_alpha) as la, AVG(theta) as th "
            "FROM eeg_captures WHERE session_id=?", (s['session_id'],)
        ).fetchone()
        print(f"\n[EEG Captures] session {s['session_id']}: "
              f"count={caps['cnt']} attn={caps['attn']:.1f} medi={caps['medi']:.1f} "
              f"low_alpha={caps['la']:.1f} theta={caps['th']:.1f}")

conn.close()
