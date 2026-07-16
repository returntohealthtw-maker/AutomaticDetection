"""
sync_missing_sessions_to_firebase.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
把 Railway PostgreSQL 中「沒有 firebase_session_id」的 sessions
逐筆建立到 Firebase，並把 firebase_session_id 回寫到 PostgreSQL。

用法（在後端系統目錄執行）：
    python sync_missing_sessions_to_firebase.py [--dry-run] [--limit N]

環境變數（或直接在下方 CONFIG 設定）：
    DATABASE_URL          PostgreSQL 連線字串
    FIREBASE_SERVICE_KEY  Firebase 服務金鑰（X-Service-Key 標頭）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import httpx
import sqlalchemy as sa

# ── CONFIG ──────────────────────────────────────────────────────────────────
FIREBASE_API_BASE    = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
FIREBASE_SERVICE_KEY = os.getenv("FIREBASE_SERVICE_KEY", "86pjyXNhJ1PFDEBiIMukV2WxK4QvYZ97qemHLrbG3wngdUfA")
DATABASE_URL         = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    print("[ERROR] 請設定環境變數 DATABASE_URL（Railway PostgreSQL 連線字串）")
    sys.exit(1)

_hx = httpx.Client(timeout=20.0)


def _headers():
    return {"X-Service-Key": FIREBASE_SERVICE_KEY, "Content-Type": "application/json"}


def fetch_sessions_without_fb(engine, limit: int = 0) -> list[dict]:
    """取所有沒有 firebase_session_id 的 completed sessions"""
    q = """
        SELECT session_id, subject_name, subject_gender, subject_birthday,
               subject_age, consultant_name, report_type, status,
               start_time, end_time, created_at,
               mind_stress, mind_balance, mind_energy, mind_color,
               overall_score, mbti, bagua,
               qeeg_scores_json
        FROM sessions
        WHERE (firebase_session_id IS NULL OR firebase_session_id = '')
          AND status IN ('completed', 'failed')
        ORDER BY session_id
    """
    if limit:
        q += f" LIMIT {limit}"
    with engine.connect() as conn:
        rows = conn.execute(sa.text(q)).fetchall()
    return [dict(zip(
        ['session_id','subject_name','subject_gender','subject_birthday',
         'subject_age','consultant_name','report_type','status',
         'start_time','end_time','created_at',
         'mind_stress','mind_balance','mind_energy','mind_color',
         'overall_score','mbti','bagua','qeeg_scores_json'],
        r
    )) for r in rows]


def create_firebase_session(row: dict) -> str | None:
    """POST /sessions 建立 Firebase session，回傳 firebase_session_id 或 None"""
    # 決定報告對象
    report_type = row.get('report_type') or 'life_script'
    # 組 payload
    payload: dict = {
        "subjectName":     row['subject_name'] or '未知',
        "consultantName":  row.get('consultant_name') or '',
        "reportType":      report_type,
        "deviceType":      "android",
        "sessionSource":   "railway_migration",
    }
    if row.get('subject_gender'):
        payload['subjectGender'] = row['subject_gender']
    if row.get('subject_birthday'):
        bd = row['subject_birthday']
        payload['subjectBirthday'] = bd.isoformat() if hasattr(bd, 'isoformat') else str(bd)
    if row.get('subject_age'):
        payload['subjectAge'] = row['subject_age']

    # 用 start_time 做為 createdAt
    if row.get('start_time'):
        st = row['start_time']
        payload['createdAt'] = st.isoformat() if hasattr(st, 'isoformat') else str(st)

    resp = _hx.post(f"{FIREBASE_API_BASE}/sessions", headers=_headers(), json=payload)
    if resp.status_code in (200, 201):
        data = resp.json()
        fb_id = data.get('sessionId') or data.get('id') or data.get('firebase_session_id')
        return fb_id
    print(f"  [ERROR] POST /sessions 失敗 {resp.status_code}: {resp.text[:200]}")
    return None


def patch_firebase_session_with_bdna(firebase_session_id: str, row: dict):
    """把 BrainDNA / QEEG 結果 PATCH 到 Firebase session"""
    _COLOR_MAP = {0: "orange", 1: "green", 2: "blue", 3: "yellow"}
    patch: dict = {}

    if row.get("mind_stress") is not None:
        patch["mindStress"] = row["mind_stress"]
    if row.get("mind_balance") is not None:
        patch["mindBalance"] = row["mind_balance"]
    if row.get("mind_energy") is not None:
        patch["mindEnergy"] = row["mind_energy"]
    if row.get("mind_color") is not None:
        patch["mindColor"] = _COLOR_MAP.get(row["mind_color"], str(row["mind_color"]))
    if row.get("overall_score") is not None:
        patch["overallScore"] = row["overall_score"]
    if row.get("mbti"):
        patch["mbti"] = row["mbti"]
    if row.get("bagua"):
        patch["bagua"] = row["bagua"]

    qeeg_raw = row.get("qeeg_scores_json")
    if qeeg_raw:
        try:
            qeeg = json.loads(qeeg_raw) if isinstance(qeeg_raw, str) else qeeg_raw
            ab = qeeg.get("ability_scores", {})
            if ab:
                patch["qeegAbilities"] = {k: round(v["score"]) for k, v in ab.items() if isinstance(v, dict)}
            flags = qeeg.get("report_flags", [])
            if flags:
                patch["qeegFlags"] = {f["flag"]: True for f in flags if isinstance(f, dict) and f.get("flag")}
        except Exception:
            pass

    if patch:
        patch["analysisStatus"] = "completed"
        resp = _hx.patch(f"{FIREBASE_API_BASE}/sessions/{firebase_session_id}",
                         headers=_headers(), json=patch)
        if resp.status_code not in (200, 201, 204):
            print(f"  [WARN] PATCH bdna 失敗 {resp.status_code}: {resp.text[:100]}")


def save_firebase_session_id_to_db(engine, session_id: int, firebase_session_id: str):
    """把 firebase_session_id 回寫到 PostgreSQL"""
    with engine.begin() as conn:
        conn.execute(sa.text(
            "UPDATE sessions SET firebase_session_id = :fb_id WHERE session_id = :sid"
        ), {"fb_id": firebase_session_id, "sid": session_id})


def main():
    parser = argparse.ArgumentParser(description="同步缺少 firebase_session_id 的 sessions 到 Firebase")
    parser.add_argument("--dry-run", action="store_true", help="只顯示，不實際寫入")
    parser.add_argument("--limit", type=int, default=0, help="處理前 N 筆（預設全部）")
    args = parser.parse_args()

    engine = sa.create_engine(DATABASE_URL, pool_pre_ping=True)
    sessions = fetch_sessions_without_fb(engine, args.limit)
    print(f"找到 {len(sessions)} 筆沒有 firebase_session_id 的 sessions")

    if args.dry_run:
        for row in sessions:
            print(f"  [DRY] session_id={row['session_id']} {row['subject_name']} type={row['report_type']}")
        return

    ok = fail = 0
    for row in sessions:
        sid = row['session_id']
        name = row['subject_name']
        print(f"  處理 session_id={sid} {name} ...", end=" ")

        # 建立 Firebase session
        fb_id = create_firebase_session(row)
        if not fb_id:
            print("FAIL (建立 Firebase session 失敗)")
            fail += 1
            continue

        # 回寫 firebase_session_id
        save_firebase_session_id_to_db(engine, sid, fb_id)

        # PATCH BrainDNA/QEEG 結果
        patch_firebase_session_with_bdna(fb_id, row)

        print(f"OK → fb_sid={fb_id[:8]}")
        ok += 1
        time.sleep(0.3)  # 避免 rate limit

    print(f"\n同步結果：OK={ok} FAIL={fail}")
    print("\n完成！請重新執行 backfill_payments_reports_firebase.py 來同步付款資料。")


if __name__ == "__main__":
    main()
