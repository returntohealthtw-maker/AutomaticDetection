#!/usr/bin/env python3
"""
一次性歷史資料遷移腳本：SQLite → Firebase Cloud Functions API
========================================================================
用法：
    python migrate_to_firebase.py

需要先設定環境變數（或修改下方 CONFIG 區段）：
    FIREBASE_API_KEY   = Firebase Web API Key（專案設定 → 一般 → 網頁 API 金鑰）
    FIREBASE_EMAIL     = 遷移用帳號 email
    FIREBASE_PASSWORD  = 遷移用帳號密碼
    SQLITE_DB_PATH     = SQLite 資料庫路徑（預設自動偵測）

注意：
    - 腳本是「冪等」的：同一筆 session_id 重跑不會重複建立（API 會回 409 或覆蓋）
    - EEG 絕對值 → 比例換算：各頻帶 / 總和 × 100
    - 遷移完成後會產生 migration_report.json 紀錄結果
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
import urllib3
urllib3.disable_warnings()

# ─── CONFIG ─────────────────────────────────────────────────────────────────

FIREBASE_API_KEY  = os.environ.get("FIREBASE_API_KEY",  "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ")
FIREBASE_EMAIL    = os.environ.get("FIREBASE_EMAIL",    "migration@returntohealthtw.com")
FIREBASE_PASSWORD = os.environ.get("FIREBASE_PASSWORD", "MigrateEEG@2026")

API_BASE = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"

# Railway 生產環境 API（遷移來源之一）
RAILWAY_BASE  = "https://backend-production-2da61.up.railway.app"
RAILWAY_PHONE = "0900000000"
RAILWAY_PWD   = "admin123"

# 自動偵測 SQLite 路徑
_here = os.path.dirname(os.path.abspath(__file__))
_candidates = [
    os.environ.get("SQLITE_DB_PATH", ""),
    os.path.join(_here, "eeg_dev.db"),
    os.path.join(_here, "..", "Database", "ToOtherProject", "eeg_dev.db"),
    "D:/Write program/Database/ToOtherProject/eeg_dev.db",
]
SQLITE_DB_PATH = next((p for p in _candidates if p and os.path.isfile(p)), "")

# EEG 批次每次上傳筆數
EEG_BATCH_SIZE = 50

# ─── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("migration.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ─── Firebase Auth ───────────────────────────────────────────────────────────

class FirebaseTokenManager:
    """管理 Firebase ID Token，到期前自動重新取得。"""

    def __init__(self, api_key: str, email: str, password: str):
        self._api_key  = api_key
        self._email    = email
        self._password = password
        self._token: Optional[str] = None
        self._expires_at: float = 0.0

    def get_token(self) -> str:
        if time.time() < self._expires_at - 120:   # 提前 2 分鐘刷新
            return self._token  # type: ignore
        self._refresh()
        return self._token  # type: ignore

    def _refresh(self):
        url  = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self._api_key}"
        resp = requests.post(url, json={
            "email": self._email,
            "password": self._password,
            "returnSecureToken": True,
        }, timeout=15, verify=False)
        if resp.status_code != 200:
            raise RuntimeError(f"Firebase 登入失敗 {resp.status_code}: {resp.text}")
        data = resp.json()
        self._token     = data["idToken"]
        expires_in      = int(data.get("expiresIn", 3600))
        self._expires_at = time.time() + expires_in
        log.info("✅ Firebase 登入成功，Token 有效至 %s",
                 datetime.fromtimestamp(self._expires_at).strftime("%H:%M:%S"))


# ─── API Client ──────────────────────────────────────────────────────────────

class FirebaseApiClient:
    def __init__(self, token_mgr: FirebaseTokenManager):
        self._tm = token_mgr
        self._session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._tm.get_token()}",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, body: Dict) -> Tuple[int, Dict]:
        url  = f"{API_BASE}{path}"
        resp = self._session.post(url, json=body, headers=self._headers(), timeout=30, verify=False)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        return resp.status_code, data

    def _patch(self, path: str, body: Dict) -> Tuple[int, Dict]:
        url  = f"{API_BASE}{path}"
        resp = self._session.patch(url, json=body, headers=self._headers(), timeout=30, verify=False)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        return resp.status_code, data

    # ── Subject ──────────────────────────────────────────────────────────────

    def create_subject(self, name: str, birth_date: str, gender: str,
                       age: int, notes: str = "") -> Optional[str]:
        """建立受測者，回傳 Firebase subjectId。"""
        gender_map = {"M": "male", "F": "female", "m": "male", "f": "female",
                      "male": "male", "female": "female"}
        fb_gender = gender_map.get(gender, "other")
        payload: Dict[str, Any] = {
            "name":         name or "未知",
            "gender":       fb_gender,
            "relationship": "個案",
            "notes":        notes or "",
        }
        if birth_date:
            payload["birthDate"] = birth_date
        if age:
            pass  # Firebase 由 birthDate 計算 age，直接略過

        status, data = self._post("/users/subjects", payload)
        if status in (200, 201):
            subject_id = data.get("subjectId") or data.get("id")
            log.info("  ✅ 建立受測者 %s → subjectId=%s", name, subject_id)
            return subject_id
        log.warning("  ⚠ 建立受測者失敗 (%s): %s", status, data)
        return None

    # ── Session ───────────────────────────────────────────────────────────────

    def create_session(self, subject_id: Optional[str], device_type: str = "ThinkGear",
                       platform: str = "android") -> Optional[str]:
        """建立 Session，回傳 Firebase sessionId。"""
        payload: Dict[str, Any] = {
            "deviceType": device_type,
            "platform":   platform,
        }
        if subject_id:
            payload["subjectId"] = subject_id

        status, data = self._post("/sessions", payload)
        if status in (200, 201):
            session_id = data.get("sessionId") or data.get("id")
            log.info("    ✅ 建立 Session → sessionId=%s", session_id)
            return session_id
        log.warning("    ⚠ 建立 Session 失敗 (%s): %s", status, data)
        return None

    def complete_session(self, session_id: str, started_at: int,
                         ended_at: int, duration_sec: int):
        """結束 Session。"""
        payload: Dict[str, Any] = {
            "status":      "completed",
            "durationSec": duration_sec,
        }
        if ended_at:
            payload["endedAt"] = _ts_to_iso(ended_at)
        status, data = self._patch(f"/sessions/{session_id}", payload)
        if status not in (200, 201, 204):
            log.warning("    ⚠ 結束 Session 失敗 (%s): %s", status, data)

    # ── EEG Batch ─────────────────────────────────────────────────────────────

    def upload_eeg_batch(self, session_id: str,
                         features: List[Dict[str, Any]]) -> bool:
        """上傳 EEG 特徵批次（最多 EEG_BATCH_SIZE 筆）。"""
        payload = {"sessionId": session_id, "features": features}
        status, data = self._post("/eeg/batch", payload)
        if status in (200, 201):
            saved = data.get("message", "")
            log.info("      ✅ EEG 批次上傳 %d 筆：%s", len(features), saved)
            return True
        log.warning("      ⚠ EEG 批次上傳失敗 (%s): %s", status, data)
        return False

    # ── Report Store ──────────────────────────────────────────────────────────

    def store_report(self, session_id: Optional[str], subject_id: Optional[str],
                     report_type: str, pdf_url: str,
                     mbti_type: Optional[str] = None,
                     bagua_type: Optional[str] = None,
                     extra_data: Optional[Dict] = None) -> bool:
        """儲存報告 metadata。"""
        payload: Dict[str, Any] = {
            "reportType": report_type,
            "pdfUrl":     pdf_url,
        }
        if session_id:
            payload["sessionId"] = session_id
        if subject_id:
            payload["subjectId"] = subject_id
        if mbti_type:
            payload["mbtiType"] = mbti_type
        if bagua_type:
            payload["baguaType"] = bagua_type
        if extra_data:
            payload["extraData"] = extra_data

        status, data = self._post("/reports/store", payload)
        if status in (200, 201):
            log.info("    ✅ 報告 metadata 已儲存 (type=%s)", report_type)
            return True
        log.warning("    ⚠ 報告儲存失敗 (%s): %s", status, data)
        return False


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _ts_to_iso(ts: Any) -> str:
    """Unix timestamp（秒或毫秒）→ ISO 8601 UTC 字串。"""
    if not ts:
        return datetime.now(timezone.utc).isoformat()
    ts_int = int(ts)
    if ts_int > 10**12:          # 毫秒
        ts_int //= 1000
    try:
        dt = datetime.fromtimestamp(ts_int, tz=timezone.utc)
        return dt.isoformat()
    except (OSError, OverflowError):
        return datetime.now(timezone.utc).isoformat()


def _abs_to_ratios(cap: sqlite3.Row) -> Dict[str, Any]:
    """將 EegCapture 絕對值換算為各頻帶比例（%）。

    子頻帶：delta, theta, low_alpha, high_alpha, low_beta, high_beta,
             low_gamma, high_gamma
    合併頻帶：alpha = low_alpha + high_alpha, ...
    """
    c   = dict(cap)
    d   = c.get("delta",      0) or 0
    th  = c.get("theta",      0) or 0
    loa = c.get("low_alpha",  0) or 0
    hia = c.get("high_alpha", 0) or 0
    lob = c.get("low_beta",   0) or 0
    hib = c.get("high_beta",  0) or 0
    log_ = c.get("low_gamma", 0) or 0
    hig = c.get("high_gamma", 0) or 0

    total = d + th + loa + hia + lob + hib + log_ + hig
    if total == 0:
        return {}

    def pct(v: float) -> float:
        return round(v / total * 100, 2)

    feature: Dict[str, Any] = {
        "timestamp":       _ts_to_iso(c.get("captured_at")),
        "windowSec":       1.0,
        # 合併頻帶
        "deltaRatio":      pct(d),
        "thetaRatio":      pct(th),
        "alphaRatio":      pct(loa + hia),
        "betaRatio":       pct(lob + hib),
        "gammaRatio":      pct(log_ + hig),
        # 分頻子帶（7欄）
        "lowAlphaRatio":   pct(loa),
        "highAlphaRatio":  pct(hia),
        "lowBetaRatio":    pct(lob),
        "highBetaRatio":   pct(hib),
        "lowGammaRatio":   pct(log_),
        "highGammaRatio":  pct(hig),
        # 指數
        "attentionIndex":  float(c.get("attention")  or 0),
        "relaxationIndex": float(c.get("meditation") or 0),
        "signalQuality":   float(100 if (c.get("good_signal") == 0) else 50),
        # 方案B新增欄位
        "isBaseline":      bool(c.get("is_baseline", 0)),
        "seqNum":          int(c.get("seq_num", 0) or 0),
    }
    return feature


def _extract_mbti(client_summary: Optional[str]) -> Optional[str]:
    """從 client_summary JSON 中取出 MBTI 類型（如有）。"""
    if not client_summary:
        return None
    try:
        data = json.loads(client_summary)
        return data.get("mbti_type") or data.get("mbtiType")
    except Exception:
        return None


def _map_report_type(rt: str) -> str:
    """將 Railway 報告類型對應到 Firebase 合法值。"""
    mapping = {
        "adult":       "adult_vip",
        "child":       "child_vip",
        "adult_vip":   "adult_vip",
        "child_vip":   "child_vip",
        "marital":     "marital",
        "parent_child":"parent_child",
    }
    return mapping.get(str(rt).lower(), "session")


# ─── Railway → Firebase Migration ───────────────────────────────────────────

def migrate_railway(client: FirebaseApiClient) -> Dict[str, Any]:
    """從 Railway PostgreSQL（透過 API）遷移到 Firebase。"""
    import urllib3; urllib3.disable_warnings()
    rs = requests.Session(); rs.verify = False
    # Railway 登入
    tok = rs.post(f"{RAILWAY_BASE}/api/v1/auth/login",
                  json={"phone": RAILWAY_PHONE, "password": RAILWAY_PWD}, timeout=15
                  ).json().get("token", "")
    if not tok:
        raise RuntimeError("Railway 登入失敗，請確認帳號密碼")
    rs.headers["Authorization"] = f"Bearer {tok}"
    log.info("✅ Railway 登入成功")

    results: Dict[str, Any] = {
        "subjects_ok": 0, "subjects_fail": 0,
        "sessions_ok": 0, "sessions_fail": 0,
        "eeg_features_ok": 0, "eeg_features_fail": 0,
        "reports_ok": 0, "reports_fail": 0,
        "session_map": {}, "subject_map": {}, "errors": [],
    }

    # 取所有 sessions
    all_sess = rs.get(f"{RAILWAY_BASE}/api/v1/eeg/sessions", timeout=20).json().get("sessions", [])
    log.info("Railway sessions 總數：%d", len(all_sess))

    for sess in sorted(all_sess, key=lambda x: x.get("session_id", 0)):
        sid  = sess.get("session_id") or sess.get("id")
        name = sess.get("subject_name") or "未知"
        rtype = sess.get("report_type") or "adult"
        log.info("▶ Railway session_id=%s, 受測者=%s", sid, name)

        # 建立受測者
        subject_key = name
        fb_subject_id = results["subject_map"].get(subject_key)
        if not fb_subject_id:
            fb_subject_id = client.create_subject(
                name, sess.get("subject_birthday") or "",
                sess.get("subject_gender") or "M", sess.get("subject_age") or 0,
                notes=f"遷移自 Railway session_id={sid}"
            )
            if fb_subject_id:
                results["subjects_ok"] += 1
                results["subject_map"][subject_key] = fb_subject_id
            else:
                results["subjects_fail"] += 1

        # 建立 session
        fb_session_id = client.create_session(fb_subject_id, "ThinkGear", "android")
        if not fb_session_id:
            results["sessions_fail"] += 1
            results["errors"].append(f"Railway session {sid}: 建立 Firebase session 失敗")
            continue
        results["sessions_ok"] += 1
        results["session_map"][sid] = fb_session_id

        # 取 EEG stats / captures
        stats_r = rs.get(f"{RAILWAY_BASE}/api/v1/eeg/sessions/{sid}/stats", timeout=20).json()
        eeg_stats = stats_r.get("eeg_stats") or {}
        bands_avg = eeg_stats.get("bands_avg") or {}

        # 只有 bands_avg 時，上傳一筆代表性特徵
        if bands_avg:
            def bv(k): return float(bands_avg.get(k) or 0)
            d=bv("delta"); th=bv("theta"); la=bv("low_alpha"); ha=bv("high_alpha")
            lb=bv("low_beta"); hb=bv("high_beta"); lg=bv("low_gamma"); hg=bv("high_gamma")
            total = d+th+la+ha+lb+hb+lg+hg or 1
            def pct(v): return round(v/total*100, 2)
            n = eeg_stats.get("sample_count") or 1
            feat = {
                "timestamp":       _ts_to_iso(0),
                "windowSec":       1.0,
                "deltaRatio":      pct(d), "thetaRatio": pct(th),
                "alphaRatio":      pct(la+ha), "betaRatio": pct(lb+hb), "gammaRatio": pct(lg+hg),
                "lowAlphaRatio":   pct(la), "highAlphaRatio": pct(ha),
                "lowBetaRatio":    pct(lb), "highBetaRatio":  pct(hb),
                "lowGammaRatio":   pct(lg), "highGammaRatio": pct(hg),
                "attentionIndex":  float(bands_avg.get("attention") or 0),
                "relaxationIndex": float(bands_avg.get("meditation") or 0),
                "signalQuality":   95.0,
                # 方案B新增欄位（Railway bands_avg 為 session 平均，無逐筆序號）
                "isBaseline":      False,
                "seqNum":          0,
            }
            if client.upload_eeg_batch(fb_session_id, [feat]):
                results["eeg_features_ok"] += 1
            else:
                results["eeg_features_fail"] += 1

        # 完成 session
        client.complete_session(fb_session_id, 0, 0, 180)

        # 報告 metadata
        reps_r = rs.get(f"{RAILWAY_BASE}/api/v1/reports", timeout=20).json()
        reps = [r for r in (reps_r.get("reports") or []) if str(r.get("session_id")) == str(sid)
                and r.get("status") == "completed" and r.get("pdf_url")]
        for rep in reps:
            ok = client.store_report(
                session_id=fb_session_id, subject_id=fb_subject_id,
                report_type=_map_report_type(rep.get("talent_report_kind") or rtype),
                pdf_url=rep["pdf_url"],
                extra_data={"railway_session_id": sid, "railway_report_id": rep.get("report_id")},
            )
            results["reports_ok" if ok else "reports_fail"] += 1

        log.info("  ✔ Railway session %s → Firebase %s", sid, fb_session_id)

    return results


# ─── Migration Core ──────────────────────────────────────────────────────────

def migrate(db_path: str, client: FirebaseApiClient) -> Dict[str, Any]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    results: Dict[str, Any] = {
        "subjects_ok": 0, "subjects_fail": 0,
        "sessions_ok": 0, "sessions_fail": 0,
        "eeg_features_ok": 0, "eeg_features_fail": 0,
        "reports_ok": 0, "reports_fail": 0,
        "session_map": {},      # local session_id → firebase session_id
        "subject_map": {},      # local subject_key → firebase subject_id
        "errors": [],
    }

    # 1. 取得所有需要遷移的 sessions
    sessions = conn.execute("""
        SELECT * FROM sessions
        WHERE status = 1
        ORDER BY session_id
    """).fetchall()

    log.info("=" * 60)
    log.info("開始遷移：%d 筆 sessions", len(sessions))
    log.info("=" * 60)

    for sess in sessions:
        local_sid = sess["session_id"]
        name      = sess["subject_name"] or "未知"
        birth     = sess["subject_birthday"] or ""
        gender    = sess["subject_gender"] or "M"
        age       = sess["subject_age"] or 0
        rtype     = sess["report_type"] or "adult"

        log.info("▶ 處理 session_id=%d, 受測者=%s", local_sid, name)

        # ── Step 1: 建立受測者 ────────────────────────────────────────────
        subject_key = f"{name}|{birth}|{gender}"
        fb_subject_id = results["subject_map"].get(subject_key)
        if not fb_subject_id:
            fb_subject_id = client.create_subject(name, birth, gender, age,
                                                   notes=f"遷移自舊系統 session_id={local_sid}")
            if fb_subject_id:
                results["subjects_ok"] += 1
                results["subject_map"][subject_key] = fb_subject_id
            else:
                results["subjects_fail"] += 1
                results["errors"].append(f"session {local_sid}: 建立受測者失敗")
                # 繼續但 subject_id=None

        # ── Step 2: 建立 Session ──────────────────────────────────────────
        fb_session_id = client.create_session(
            subject_id=fb_subject_id,
            device_type="ThinkGear",
            platform="android",
        )
        if not fb_session_id:
            results["sessions_fail"] += 1
            results["errors"].append(f"session {local_sid}: 建立 Firebase session 失敗")
            continue

        results["sessions_ok"] += 1
        results["session_map"][local_sid] = fb_session_id

        # ── Step 3: 上傳 EEG Captures ────────────────────────────────────
        captures = conn.execute("""
            SELECT * FROM eeg_captures
            WHERE session_id = ?
            ORDER BY seq_num
        """, (local_sid,)).fetchall()

        features_buffer: List[Dict[str, Any]] = []
        ok_count = 0; fail_count = 0

        for cap in captures:
            feat = _abs_to_ratios(cap)
            if not feat:
                log.debug("  跳過空白 capture capture_id=%s", cap["capture_id"])
                continue
            features_buffer.append(feat)

            if len(features_buffer) >= EEG_BATCH_SIZE:
                if client.upload_eeg_batch(fb_session_id, features_buffer):
                    ok_count += len(features_buffer)
                else:
                    fail_count += len(features_buffer)
                    results["errors"].append(
                        f"session {local_sid}: EEG 批次上傳失敗 ({len(features_buffer)} 筆)")
                features_buffer = []

        # 上傳剩餘
        if features_buffer:
            if client.upload_eeg_batch(fb_session_id, features_buffer):
                ok_count += len(features_buffer)
            else:
                fail_count += len(features_buffer)
                results["errors"].append(
                    f"session {local_sid}: EEG 剩餘批次上傳失敗 ({len(features_buffer)} 筆)")

        results["eeg_features_ok"]   += ok_count
        results["eeg_features_fail"] += fail_count
        log.info("  EEG：成功 %d 筆，失敗 %d 筆", ok_count, fail_count)

        # ── Step 4: 結束 Session ──────────────────────────────────────────
        start_ts = sess["start_time"] or 0
        end_ts   = sess["end_time"]   or start_ts
        dur      = max(0, (end_ts - start_ts) // 1000 if end_ts > 10**12 else end_ts - start_ts)
        client.complete_session(fb_session_id, start_ts, end_ts, dur)

        # ── Step 5: 儲存報告 metadata ─────────────────────────────────────
        reports = conn.execute("""
            SELECT * FROM reports
            WHERE session_id = ? AND status = 'completed' AND pdf_url IS NOT NULL
        """, (local_sid,)).fetchall()

        for rep in reports:
            rep_dict = dict(rep)
            mbti = _extract_mbti(rep_dict.get("client_summary"))
            ok   = client.store_report(
                session_id  = fb_session_id,
                subject_id  = fb_subject_id,
                report_type = _map_report_type(rep_dict.get("talent_report_kind") or rtype),
                pdf_url     = rep_dict.get("pdf_url", ""),
                mbti_type   = mbti,
                extra_data  = {
                    "local_report_id": rep_dict.get("report_id"),
                    "local_session_id": local_sid,
                    "consultant_name":  rep_dict.get("consultant_name") or "",
                },
            )
            if ok:
                results["reports_ok"] += 1
            else:
                results["reports_fail"] += 1
                results["errors"].append(f"session {local_sid} report {rep['report_id']}: 儲存報告失敗")

        log.info("  ✔ session %d 完成 → Firebase session=%s", local_sid, fb_session_id)

    conn.close()
    return results


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  腦波歷史資料遷移工具  SQLite → Firebase")
    print("=" * 60 + "\n")

    # 驗證設定
    missing = []
    if not FIREBASE_API_KEY:
        missing.append("FIREBASE_API_KEY")
    if not FIREBASE_EMAIL:
        missing.append("FIREBASE_EMAIL")
    if not FIREBASE_PASSWORD:
        missing.append("FIREBASE_PASSWORD")
    if missing:
        print("❌ 缺少必要設定（請設定環境變數）：")
        for m in missing:
            print(f"   {m}")
        print("\n範例：")
        print('   set FIREBASE_API_KEY=AIzaSy...')
        print('   set FIREBASE_EMAIL=migration@example.com')
        print('   set FIREBASE_PASSWORD=yourpassword')
        sys.exit(1)

    if not SQLITE_DB_PATH:
        print("⚠ 未找到 SQLite 資料庫，將只遷移 Railway 生產資料")

    print(f"📁 SQLite 來源：{SQLITE_DB_PATH}")
    print(f"🌐 API Base：  {API_BASE}")
    print(f"📧 帳號：      {FIREBASE_EMAIL}\n")

    # 取得 Token
    try:
        token_mgr = FirebaseTokenManager(FIREBASE_API_KEY, FIREBASE_EMAIL, FIREBASE_PASSWORD)
        client    = FirebaseApiClient(token_mgr)
        # 預先觸發一次登入
        _ = token_mgr.get_token()
    except Exception as e:
        print(f"❌ Firebase 登入失敗：{e}")
        sys.exit(1)

    # 執行遷移
    t0 = time.time()
    all_results = []
    
    # 1. 先遷移 Railway 生產資料
    print("\n📡 第一步：遷移 Railway 生產資料...")
    try:
        r1 = migrate_railway(client)
        all_results.append(("Railway 生產資料", r1))
        print(f"  ✅ Railway 遷移完成：{r1['sessions_ok']} sessions, {r1['eeg_features_ok']} EEG 筆")
    except Exception as e:
        log.exception("Railway 遷移失敗")
        print(f"  ⚠ Railway 遷移失敗：{e}")

    # 2. 再遷移 SQLite 歷史資料
    if SQLITE_DB_PATH:
        print(f"\n💾 第二步：遷移 SQLite 歷史資料（{SQLITE_DB_PATH}）...")
        try:
            r2 = migrate(SQLITE_DB_PATH, client)
            all_results.append(("SQLite 歷史資料", r2))
            print(f"  ✅ SQLite 遷移完成：{r2['sessions_ok']} sessions, {r2['eeg_features_ok']} EEG 筆")
        except Exception as e:
            log.exception("SQLite 遷移失敗")
            print(f"  ⚠ SQLite 遷移失敗：{e}")
    else:
        print("\n💾 未找到 SQLite 資料庫，跳過歷史資料遷移")

    elapsed = time.time() - t0

    # 結果報告
    print("\n" + "=" * 60)
    print("  遷移完成！")
    print("=" * 60)
    for label, results in all_results:
        print(f"\n  【{label}】")
        print(f"  受測者：成功 {results['subjects_ok']} / 失敗 {results['subjects_fail']}")
        print(f"  Sessions：成功 {results['sessions_ok']} / 失敗 {results['sessions_fail']}")
        print(f"  EEG 特徵值：成功 {results['eeg_features_ok']} / 失敗 {results['eeg_features_fail']}")
        print(f"  報告 metadata：成功 {results['reports_ok']} / 失敗 {results['reports_fail']}")
        if results.get("errors"):
            for e in results["errors"][:5]:
                print(f"   ⚠ {e}")
    print(f"\n  總耗時：{elapsed:.1f} 秒")

    if results["errors"]:
        print(f"\n⚠ 共 {len(results['errors'])} 個錯誤：")
        for e in results["errors"][:20]:
            print(f"   - {e}")
        if len(results["errors"]) > 20:
            print(f"   ... 更多錯誤請查看 migration.log")

    # 儲存詳細報告
    report_path = "migration_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "elapsed_sec": round(elapsed, 1),
            "sources": [
                {
                    "label": label,
                    "summary": {k: v for k, v in results.items() if isinstance(v, int)},
                    "session_map": {str(k): v for k, v in results.get("session_map", {}).items()},
                    "errors": results.get("errors", []),
                }
                for label, results in all_results
            ],
        }, f, ensure_ascii=False, indent=2)
    print(f"\n📄 詳細報告已儲存：{report_path}")
    print("📝 完整日誌：migration.log\n")


if __name__ == "__main__":
    main()
