"""
backfill_firebase.py
~~~~~~~~~~~~~~~~~~~~
把 PostgreSQL 中有 BrainDNA / QEEG 結果但 Firebase 還沒有的 session，
逐筆 PATCH 到 Firebase sessions collection。

使用方式（在後端系統目錄執行）：
    python backfill_firebase.py [--dry-run] [--limit 50]

參數：
    --dry-run   只列出要補的 session，不實際寫入
    --limit N   只處理前 N 筆（預設全部）
    --session N 只處理指定 session_id

認證：優先使用環境變數 FIREBASE_SERVICE_KEY；未設定時 fallback Bearer Token
"""
import argparse
import json
import os
import sys
import time

import httpx

# ── 設定 ────────────────────────────────────────────────────────────────────
RAILWAY_DB_URL    = os.getenv("DATABASE_URL", "")
FIREBASE_API_BASE = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
FIREBASE_SERVICE_KEY   = os.getenv("FIREBASE_SERVICE_KEY", "86pjyXNhJ1PFDEBiIMukV2WxK4QvYZ97qemHLrbG3wngdUfA")
FIREBASE_API_KEY       = os.getenv("FIREBASE_API_KEY", "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ")
FIREBASE_SYNC_EMAIL    = os.getenv("FIREBASE_SYNC_EMAIL", "migration@returntohealthtw.com")
FIREBASE_SYNC_PASSWORD = os.getenv("FIREBASE_SYNC_PASSWORD", "MigrateEEG@2026")

_cached_token = ""
_token_expires_at = 0.0


def _get_headers():
    """優先 X-Service-Key，fallback Bearer Token"""
    global _cached_token, _token_expires_at
    if FIREBASE_SERVICE_KEY:
        return {"X-Service-Key": FIREBASE_SERVICE_KEY, "Content-Type": "application/json"}
    # Bearer Token fallback
    if time.time() >= _token_expires_at or not _cached_token:
        r = httpx.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
            json={"email": FIREBASE_SYNC_EMAIL, "password": FIREBASE_SYNC_PASSWORD, "returnSecureToken": True},
            timeout=15,
        )
        if r.status_code == 200:
            d = r.json()
            _cached_token = d["idToken"]
            _token_expires_at = time.time() + int(d.get("expiresIn", 3600)) - 120
        else:
            print(f"[ERROR] Firebase 登入失敗: {r.status_code} {r.text[:200]}")
            return {}
    return {"Authorization": f"Bearer {_cached_token}", "Content-Type": "application/json"}


def _build_patch(row: dict) -> dict:
    """從 PostgreSQL row 組出 Firebase PATCH body"""
    patch: dict = {}

    # mindColor: PostgreSQL 存整數(0-3)，Firebase 要求字串
    _COLOR_MAP = {0: "orange", 1: "green", 2: "blue", 3: "yellow"}

    # ── BrainDNA ────────────────────────────────────────────────────────────
    if row.get("mind_stress") is not None:
        patch["mindStress"]   = row["mind_stress"]
    if row.get("mind_balance") is not None:
        patch["mindBalance"]  = row["mind_balance"]
    if row.get("mind_energy") is not None:
        patch["mindEnergy"]   = row["mind_energy"]
    if row.get("mind_color") is not None:
        patch["mindColor"]    = _COLOR_MAP.get(row["mind_color"], str(row["mind_color"]))
    if row.get("overall_score") is not None:
        patch["overallScore"] = row["overall_score"]
    if row.get("mbti"):
        patch["mbti"]         = row["mbti"]
    if row.get("bagua"):
        patch["bagua"]        = row["bagua"]
    if row.get("bdna_mode"):
        patch["bdnaMode"]     = row["bdna_mode"]

    # ── QEEG ────────────────────────────────────────────────────────────────
    qeeg_raw = row.get("qeeg_scores_json")
    if qeeg_raw:
        try:
            qeeg = json.loads(qeeg_raw) if isinstance(qeeg_raw, str) else qeeg_raw
            ab = qeeg.get("ability_scores", {})
            if ab:
                patch["qeegAbilities"] = {k: round(v["score"]) for k, v in ab.items() if isinstance(v, dict)}
            ci = qeeg.get("composite_indices", {})
            if ci:
                patch["qeegComposites"] = {k: round(v["score"]) for k, v in ci.items() if isinstance(v, dict)}
            flags = qeeg.get("report_flags", [])
            if flags:
                patch["qeegFlags"] = [f["flag"] for f in flags]
            sq = qeeg.get("signal_quality", {})
            if sq.get("quality_grade"):
                patch["qeegSignalGrade"] = sq["quality_grade"]
            patch["qeegVersion"] = qeeg.get("calculation_version", "")
            # 8-band 分數
            bf = qeeg.get("band_features", {}).get("Fp1", {})
            if bf:
                band_scores = {
                    band: round(info.get("score_0_100", 0))
                    for band, info in bf.items()
                    if isinstance(info, dict) and info.get("score_0_100") is not None
                }
                if band_scores:
                    patch["qeegBandScores"] = band_scores
        except Exception as e:
            print(f"  [WARN] qeeg_scores_json 解析失敗 session={row['session_id']}: {e}")

    # ── 狀態標記 ────────────────────────────────────────────────────────────
    if patch:
        patch["analysisStatus"] = "completed"

    return patch


def fetch_sessions(limit: int = 0, only_id: int = 0):
    """從 PostgreSQL 取需要補的 sessions"""
    import sqlalchemy as sa
    engine = sa.create_engine(RAILWAY_DB_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        q = """
            SELECT session_id, firebase_session_id,
                   mind_stress, mind_balance, mind_energy, mind_color,
                   overall_score, mbti, bagua, bdna_mode,
                   qeeg_scores_json, qeeg_band_scores_json
            FROM sessions
            WHERE firebase_session_id IS NOT NULL
              AND firebase_session_id != ''
              AND (
                    mind_stress IS NOT NULL
                 OR mbti IS NOT NULL
                 OR qeeg_scores_json IS NOT NULL
              )
        """
        params = {}
        if only_id:
            q += " AND session_id = :sid"
            params["sid"] = only_id
        q += " ORDER BY session_id DESC"
        if limit:
            q += f" LIMIT {int(limit)}"

        rows = conn.execute(sa.text(q), params).mappings().all()
        return [dict(r) for r in rows]


def patch_firebase(fb_sid: str, patch_body: dict, dry_run: bool) -> bool:
    """PATCH 一筆 Firebase session"""
    url = f"{FIREBASE_API_BASE}/sessions/{fb_sid}"
    if dry_run:
        return True
    headers = _get_headers()
    if not headers:
        print(f"  [ERROR] 無法取得認證 headers")
        return False
    try:
        resp = httpx.patch(url, headers=headers, json=patch_body, timeout=20)
        if resp.status_code not in (200, 204):
            print(f"  [ERROR] HTTP {resp.status_code}  URL={url}")
            print(f"  [ERROR] 回應: {resp.text[:300]}")
            return False
        return True
    except Exception as e:
        print(f"  [ERROR] PATCH 例外: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",  action="store_true", help="只列出，不寫入")
    parser.add_argument("--limit",    type=int, default=0, help="最多處理幾筆（0=全部）")
    parser.add_argument("--session",  type=int, default=0, help="只處理指定 session_id")
    args = parser.parse_args()

    if not RAILWAY_DB_URL:
        print("[ERROR] 環境變數 DATABASE_URL 未設定")
        sys.exit(1)

    print("=" * 60)
    print(f"PostgreSQL → Firebase 補譜  (dry_run={args.dry_run})")
    print("=" * 60)

    # 印出認證狀態方便除錯
    if FIREBASE_SERVICE_KEY:
        print(f"[AUTH] 使用 X-Service-Key: {FIREBASE_SERVICE_KEY[:8]}...{FIREBASE_SERVICE_KEY[-4:]}")
    else:
        print(f"[AUTH] 使用 Bearer Token (email={FIREBASE_SYNC_EMAIL})")

    # 快速測試認證：呼叫一個輕量 API
    try:
        h = _get_headers()
        test_resp = httpx.get(f"{FIREBASE_API_BASE}/sessions?limit=1", headers=h, timeout=10)
        print(f"[AUTH TEST] GET /sessions → HTTP {test_resp.status_code}")
        if test_resp.status_code not in (200, 201):
            print(f"[AUTH TEST] 回應: {test_resp.text[:200]}")
    except Exception as e:
        print(f"[AUTH TEST] 例外: {e}")
    print()

    sessions = fetch_sessions(limit=args.limit, only_id=args.session)
    print(f"找到 {len(sessions)} 筆需要補的 sessions（有 firebase_session_id 且有 BrainDNA/QEEG 結果）\n")

    ok_count = 0
    fail_count = 0

    for s in sessions:
        sid       = s["session_id"]
        fb_sid    = s["firebase_session_id"]
        patch     = _build_patch(s)

        if not patch:
            print(f"  session={sid}  fb={fb_sid[:16]}...  → 無欄位可補，跳過")
            continue

        fields = ", ".join(patch.keys())
        print(f"  session={sid}  fb={fb_sid[:20]}...  欄位: {fields}")

        if args.dry_run:
            ok_count += 1
            continue

        ok = patch_firebase(fb_sid, patch, dry_run=False)
        if ok:
            print(f"    ✅ PATCH 成功")
            ok_count += 1
        else:
            print(f"    ❌ PATCH 失敗")
            fail_count += 1
        time.sleep(0.2)  # 避免 rate limit

    print()
    print("=" * 60)
    if args.dry_run:
        print(f"[DRY RUN] 預計補 {ok_count} 筆")
    else:
        print(f"完成：成功 {ok_count} 筆，失敗 {fail_count} 筆")
    print("=" * 60)


if __name__ == "__main__":
    main()
