"""
sync_all_to_firebase.py
~~~~~~~~~~~~~~~~~~~~~~~
把 PostgreSQL 中**所有**有 firebase_session_id 的 sessions，
同步報告 PDF 連結 (--reports) 和 EEG 逐秒資料 (--eeg) 到 Firebase。

用法（在 backend Console / Railway 執行）：
    python sync_all_to_firebase.py --reports --eeg
    python sync_all_to_firebase.py --reports          # 只同步報告
    python sync_all_to_firebase.py --eeg              # 只同步 EEG
    python sync_all_to_firebase.py --reports --eeg --dry-run
    python sync_all_to_firebase.py --reports --eeg --session 87
    python sync_all_to_firebase.py --reports --eeg --limit 20
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib3

import requests

urllib3.disable_warnings()

# ── Config ────────────────────────────────────────────────────────────────────
RAILWAY_BASE       = "https://backend-production-2da61.up.railway.app"
RAILWAY_PHONE      = "0900000000"
RAILWAY_PWD        = "admin123"

CF_BASE            = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
FIREBASE_API_KEY   = os.getenv("FIREBASE_API_KEY",   "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ")
FIREBASE_EMAIL     = os.getenv("FIREBASE_SYNC_EMAIL", "migration@returntohealthtw.com")
FIREBASE_PASSWORD  = os.getenv("FIREBASE_SYNC_PASSWORD", "MigrateEEG@2026")

GCS_BUCKET  = "brainwave-child-reports"
EEG_BATCH   = 50   # 每批上傳筆數

_REPORT_TYPE_MAP = {
    "adult":        "adult_vip",
    "child":        "child_vip",
    "parent_child": "parent_child",
    "marital":      "marital",
    "teen":         "child_vip",
    "life_script":  "adult_vip",
}

# ── Auth ──────────────────────────────────────────────────────────────────────
_fb_token = ""
_fb_token_exp = 0.0


def _firebase_token() -> str:
    global _fb_token, _fb_token_exp
    if time.time() < _fb_token_exp and _fb_token:
        return _fb_token
    r = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
        json={"email": FIREBASE_EMAIL, "password": FIREBASE_PASSWORD, "returnSecureToken": True},
        verify=False, timeout=15,
    )
    if r.status_code != 200:
        print(f"[ERROR] Firebase 登入失敗: {r.status_code} {r.text[:200]}")
        sys.exit(1)
    d = r.json()
    _fb_token = d["idToken"]
    _fb_token_exp = time.time() + int(d.get("expiresIn", 3600)) - 120
    return _fb_token


def _fb_headers() -> dict:
    return {"Authorization": f"Bearer {_firebase_token()}", "Content-Type": "application/json"}


# ── PostgreSQL ────────────────────────────────────────────────────────────────
def fetch_sessions(limit: int = 0, only_sid: int = 0) -> list[dict]:
    """取所有有 firebase_session_id 的 sessions"""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("[ERROR] 環境變數 DATABASE_URL 未設定")
        sys.exit(1)
    import sqlalchemy as sa
    engine = sa.create_engine(db_url, pool_pre_ping=True)
    with engine.connect() as conn:
        q = """
            SELECT s.session_id,
                   s.firebase_session_id,
                   s.firebase_subject_id,
                   s.mbti,
                   s.bagua,
                   sub.name AS subject_name
            FROM sessions s
            LEFT JOIN subjects sub ON s.subject_id = sub.id
            WHERE s.firebase_session_id IS NOT NULL
              AND s.firebase_session_id != ''
            ORDER BY s.session_id ASC
        """
        if only_sid:
            q = q.replace("ORDER BY", f"AND s.session_id = {int(only_sid)} ORDER BY")
        if limit:
            q += f" LIMIT {int(limit)}"
        rows = conn.execute(sa.text(q)).mappings().all()
    return [dict(r) for r in rows]


# ── Railway helpers ───────────────────────────────────────────────────────────
_rw_session: requests.Session | None = None


def _railway_session() -> requests.Session:
    global _rw_session
    if _rw_session:
        return _rw_session
    s = requests.Session()
    s.verify = False
    tok = s.post(f"{RAILWAY_BASE}/api/v1/auth/login",
                 json={"phone": RAILWAY_PHONE, "password": RAILWAY_PWD},
                 timeout=15).json().get("token", "")
    s.headers["Authorization"] = f"Bearer {tok}"
    _rw_session = s
    return s


# ── GCS URL strip ─────────────────────────────────────────────────────────────
def _strip_signed(url: str):
    """去除 GCS Signed URL 簽名參數，回傳 (gcs_path, base_url)"""
    if not url:
        return None, None
    from urllib.parse import urlparse, unquote, quote
    parsed = urlparse(url)
    try:
        decoded = unquote(parsed.path, errors="replace")
        encoded = quote(decoded, safe="/")
        base_url = f"{parsed.scheme}://{parsed.netloc}{encoded}"
    except Exception:
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    raw_path = unquote(parsed.path, errors="replace")
    prefix = f"/{GCS_BUCKET}/"
    gcs_path = raw_path[len(prefix):] if raw_path.startswith(prefix) else raw_path.lstrip("/")
    return gcs_path, base_url


# ── A. 同步報告 PDF ────────────────────────────────────────────────────────────
def sync_report(row: dict, dry_run: bool) -> str:
    """同步一筆 session 的報告，回傳 'ok' / 'skip' / 'fail'"""
    rw_sid = row["session_id"]
    fb_sid = row["firebase_session_id"]
    rw = _railway_session()

    sr = rw.get(f"{RAILWAY_BASE}/api/v1/eeg/sessions/{rw_sid}/stats", timeout=20)
    if sr.status_code != 200:
        print(f"    [WARN] Railway stats API 失敗 session={rw_sid}: {sr.status_code}")
        return "skip"

    d = sr.json()
    status   = d.get("report_status")
    pdf_url  = d.get("report_url")
    rtype    = d.get("report_type") or "adult"

    if status != "completed" or not pdf_url:
        return "skip"

    gcs_path, base_url = _strip_signed(pdf_url)
    report_type = _REPORT_TYPE_MAP.get(rtype, "session")

    eeg   = d.get("eeg_stats") or {}
    bands = eeg.get("bands_avg") or {}

    def bv(k):  return float(bands.get(k) or 0)
    total = sum(bv(k) for k in ["delta","theta","low_alpha","high_alpha",
                                 "low_beta","high_beta","low_gamma","high_gamma"]) or 1

    payload = {
        "sessionId":    fb_sid,
        "reportType":   report_type,
        "pdfUrl":       base_url,
        "sourceApp":    "railway_sync_all",
        "alphaAvg":     round((bv("low_alpha") + bv("high_alpha")) / total * 100, 2),
        "betaAvg":      round((bv("low_beta")  + bv("high_beta"))  / total * 100, 2),
        "thetaAvg":     round(bv("theta")  / total * 100, 2),
        "deltaAvg":     round(bv("delta")  / total * 100, 2),
        "attentionAvg": float(eeg.get("attention_percentage") or 0),
        "extraData": {
            "gcsBucket":        GCS_BUCKET,
            "gcsPath":          gcs_path,
            "railwaySessionId": rw_sid,
        },
    }
    if row.get("mbti"):
        payload["mbtiType"] = row["mbti"]
    if row.get("bagua"):
        payload["baguaType"] = row["bagua"]
    if row.get("firebase_subject_id"):
        payload["subjectId"] = row["firebase_subject_id"]

    if dry_run:
        print(f"    [DRY] 報告: type={report_type} gcs={gcs_path[:50]}")
        return "ok"

    r2 = requests.post(f"{CF_BASE}/reports/store",
                       json=payload, headers=_fb_headers(), verify=False, timeout=20)
    if r2.status_code in (200, 201):
        return "ok"
    print(f"    [ERROR] 報告 PATCH {r2.status_code}: {r2.text[:200]}")
    return "fail"


# ── B. 同步 EEG 逐秒資料 ──────────────────────────────────────────────────────
def _raw_to_ratio(v, total):
    return round(float(v) / total * 100, 4) if total > 0 else 0.0


def _build_features(caps: list) -> list:
    out = []
    for c in caps:
        d   = float(c.get("delta",      0) or 0)
        th  = float(c.get("theta",      0) or 0)
        la  = float(c.get("low_alpha",  0) or 0)
        ha  = float(c.get("high_alpha", 0) or 0)
        lb  = float(c.get("low_beta",   0) or 0)
        hb  = float(c.get("high_beta",  0) or 0)
        lg  = float(c.get("low_gamma",  0) or 0)
        hg  = float(c.get("high_gamma", 0) or 0)
        total = d + th + la + ha + lb + hb + lg + hg or 1.0

        ts_ms = c.get("captured_at") or 0
        try:
            ts_iso = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(int(ts_ms) / 1000))
        except Exception:
            ts_iso = "2026-01-01T00:00:00.000Z"

        out.append({
            "timestamp":       ts_iso,
            "windowSec":       1.0,
            "deltaRatio":      _raw_to_ratio(d,  total),
            "thetaRatio":      _raw_to_ratio(th, total),
            "alphaRatio":      _raw_to_ratio(la + ha, total),
            "betaRatio":       _raw_to_ratio(lb + hb, total),
            "gammaRatio":      _raw_to_ratio(lg + hg, total),
            "lowAlphaRatio":   _raw_to_ratio(la, total),
            "highAlphaRatio":  _raw_to_ratio(ha, total),
            "lowBetaRatio":    _raw_to_ratio(lb, total),
            "highBetaRatio":   _raw_to_ratio(hb, total),
            "lowGammaRatio":   _raw_to_ratio(lg, total),
            "highGammaRatio":  _raw_to_ratio(hg, total),
            "attentionIndex":  float(c.get("attention",  0) or 0),
            "relaxationIndex": float(c.get("meditation", 0) or 0),
            "signalQuality":   max(0.0, round((100 - float(c.get("good_signal", 200) or 200)) / 100 * 100, 1)),
            "isBaseline":      bool(c.get("is_baseline", 0)),
            "seqNum":          int(c.get("seq_num", 0) or 0),
        })
    return out


def sync_eeg(row: dict, dry_run: bool) -> str:
    """同步一筆 session 的 EEG 逐秒資料，回傳 'ok' / 'skip' / 'fail'"""
    rw_sid = row["session_id"]
    fb_sid = row["firebase_session_id"]
    rw = _railway_session()

    caps_r = rw.get(f"{RAILWAY_BASE}/api/v1/sessions/{rw_sid}/captures", timeout=30)
    if caps_r.status_code != 200:
        print(f"    [WARN] captures API 失敗 session={rw_sid}: {caps_r.status_code}")
        return "skip"

    caps = caps_r.json().get("captures", [])
    if not caps:
        return "skip"

    features = _build_features(caps)

    if dry_run:
        print(f"    [DRY] EEG: {len(features)} 筆逐秒資料")
        return "ok"

    for i in range(0, len(features), EEG_BATCH):
        batch = features[i : i + EEG_BATCH]
        r2 = requests.post(
            f"{CF_BASE}/eeg/batch",
            json={"sessionId": fb_sid, "features": batch},
            headers=_fb_headers(), verify=False, timeout=30,
        )
        if r2.status_code not in (200, 201):
            print(f"    [ERROR] EEG batch {i//EEG_BATCH+1} 失敗 {r2.status_code}: {r2.text[:150]}")
            return "fail"
        time.sleep(0.1)

    return "ok"


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports",  action="store_true", help="同步報告 PDF 連結")
    parser.add_argument("--eeg",      action="store_true", help="同步 EEG 逐秒資料")
    parser.add_argument("--dry-run",  action="store_true", help="只列出，不寫入")
    parser.add_argument("--limit",    type=int, default=0, help="最多處理幾筆")
    parser.add_argument("--session",  type=int, default=0, help="只處理指定 session_id")
    args = parser.parse_args()

    if not args.reports and not args.eeg:
        parser.error("請指定 --reports 和/或 --eeg")

    print("=" * 65)
    print(f"Firebase 全量同步  reports={args.reports}  eeg={args.eeg}  dry={args.dry_run}")
    print("=" * 65)

    # 登入
    print(f"[Firebase] 登入中...")
    _firebase_token()
    print(f"[Firebase] ✅ 登入成功")
    print(f"[Railway ] 登入中...")
    _railway_session()
    print(f"[Railway ] ✅ 登入成功\n")

    sessions = fetch_sessions(limit=args.limit, only_sid=args.session)
    print(f"找到 {len(sessions)} 筆有 firebase_session_id 的 sessions\n")

    r_ok = r_skip = r_fail = 0
    e_ok = e_skip = e_fail = 0

    for row in sessions:
        sid = row["session_id"]
        name = row.get("subject_name") or "?"
        print(f"session={sid} ({name})  fb={row['firebase_session_id'][:16]}...")

        if args.reports:
            res = sync_report(row, args.dry_run)
            if res == "ok":
                r_ok += 1;   print(f"  ✅ 報告 同步成功")
            elif res == "skip":
                r_skip += 1; print(f"  ⏭ 報告 跳過（無 completed 報告）")
            else:
                r_fail += 1; print(f"  ❌ 報告 同步失敗")

        if args.eeg:
            res = sync_eeg(row, args.dry_run)
            if res == "ok":
                e_ok += 1;   print(f"  ✅ EEG   同步成功")
            elif res == "skip":
                e_skip += 1; print(f"  ⏭ EEG   跳過（無逐秒資料）")
            else:
                e_fail += 1; print(f"  ❌ EEG   同步失敗")

        time.sleep(0.15)

    print()
    print("=" * 65)
    if args.reports:
        print(f"[報告] 成功 {r_ok}  跳過 {r_skip}  失敗 {r_fail}")
    if args.eeg:
        print(f"[EEG ] 成功 {e_ok}  跳過 {e_skip}  失敗 {e_fail}")
    print("=" * 65)


if __name__ == "__main__":
    main()
