#!/usr/bin/env python3
"""
resync_to_firebase.py
=====================
將 Railway 生產資料庫中「尚未同步到 Firebase」的 sessions 補同步。

用法：
    python resync_to_firebase.py

功能：
  1. 讀取 Firebase 現有受測者 / session 清單（避免重複建立）
  2. 連到 Railway API 取得所有 sessions 及其 eeg_captures
  3. 對每個不在 Firebase 的 session 執行同步
  4. 輸出同步報告
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests
import urllib3

urllib3.disable_warnings()
sys.stdout.reconfigure(encoding="utf-8")

# ── Config ──────────────────────────────────────────────────────────────────

RAILWAY_BASE  = "https://backend-production-2da61.up.railway.app"
RAILWAY_PHONE = "0900000000"
RAILWAY_PWD   = "admin123"

FIREBASE_API_BASE = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
FIREBASE_API_KEY      = "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ"
FIREBASE_SYNC_EMAIL   = "migration@returntohealthtw.com"
FIREBASE_SYNC_PASSWORD = "MigrateEEG@2026"

SOURCE_APP = "BrainReport-LUKE"

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("resync.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ── Firebase Auth ─────────────────────────────────────────────────────────────

class TokenManager:
    def __init__(self):
        self._token = ""
        self._expires_at = 0.0

    def get_headers(self) -> dict:
        if time.time() >= self._expires_at or not self._token:
            self._refresh()
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    def _refresh(self):
        r = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
            json={"email": FIREBASE_SYNC_EMAIL, "password": FIREBASE_SYNC_PASSWORD, "returnSecureToken": True},
            timeout=15, verify=False
        )
        if r.status_code != 200:
            raise RuntimeError(f"Firebase 登入失敗: {r.text[:200]}")
        data = r.json()
        self._token = data["idToken"]
        self._expires_at = time.time() + int(data.get("expiresIn", 3600)) - 120
        log.info("✅ Firebase token 取得（有效至 %s）",
                 datetime.fromtimestamp(self._expires_at + 120).strftime("%H:%M:%S"))


token_mgr = TokenManager()


def fb_get(path: str) -> Tuple[int, dict]:
    r = requests.get(f"{FIREBASE_API_BASE}{path}", headers=token_mgr.get_headers(),
                     timeout=20, verify=False)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text}


def fb_post(path: str, body: dict) -> Tuple[int, dict]:
    r = requests.post(f"{FIREBASE_API_BASE}{path}", headers=token_mgr.get_headers(),
                      json=body, timeout=30, verify=False)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text}


def fb_patch(path: str, body: dict) -> Tuple[int, dict]:
    r = requests.patch(f"{FIREBASE_API_BASE}{path}", headers=token_mgr.get_headers(),
                       json=body, timeout=20, verify=False)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text}


# ── Railway API ──────────────────────────────────────────────────────────────

class RailwayClient:
    def __init__(self):
        self.sess = requests.Session()
        self.sess.verify = False
        r = self.sess.post(f"{RAILWAY_BASE}/api/v1/auth/login",
                           json={"phone": RAILWAY_PHONE, "password": RAILWAY_PWD}, timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"Railway 登入失敗: {r.text[:200]}")
        tok = r.json().get("token", "")
        self.sess.headers["Authorization"] = f"Bearer {tok}"
        log.info("✅ Railway 登入成功")

    def list_sessions(self, limit: int = 100) -> List[dict]:
        r = self.sess.get(f"{RAILWAY_BASE}/api/v1/eeg/sessions?limit={limit}", timeout=20)
        if r.status_code != 200:
            log.error("Railway sessions 失敗 %s", r.text[:200])
            return []
        data = r.json()
        return data.get("sessions") or data.get("data") or (data if isinstance(data, list) else [])

    def get_captures(self, session_id: int) -> List[dict]:
        r = self.sess.get(f"{RAILWAY_BASE}/api/v1/sessions/{session_id}/captures", timeout=30)
        if r.status_code != 200:
            log.warning("  captures %s 失敗: %s", session_id, r.text[:100])
            return []
        data = r.json()
        return data.get("captures") or []

    def get_eeg_stats(self, session_id: int) -> dict:
        r = self.sess.get(f"{RAILWAY_BASE}/api/v1/eeg/sessions/{session_id}/stats", timeout=20)
        if r.status_code == 200:
            return r.json().get("eeg_stats") or {}
        return {}


# ── EEG Feature Conversion ────────────────────────────────────────────────────

def captures_to_features(captures: List[dict]) -> List[dict]:
    """bandTo100 captures → Firebase EEG features"""
    features = []
    for cap in captures:
        d  = float(cap.get("delta",      0) or 0)
        th = float(cap.get("theta",      0) or 0)
        la = float(cap.get("low_alpha",  0) or 0)
        ha = float(cap.get("high_alpha", 0) or 0)
        lb = float(cap.get("low_beta",   0) or 0)
        hb = float(cap.get("high_beta",  0) or 0)
        lg = float(cap.get("low_gamma",  0) or 0)
        hg = float(cap.get("high_gamma", 0) or 0)
        attn = float(cap.get("attention",   0) or 0)
        medi = float(cap.get("meditation",  0) or 0)

        total = d + th + la + ha + lb + hb + lg + hg
        if total == 0:
            continue

        def pct(v): return round(v / total * 100, 2)

        captured_ms = int(cap.get("captured_at") or 0)
        if captured_ms > 0:
            # Railway stores seconds, not ms
            try:
                ts = datetime.fromtimestamp(captured_ms, tz=timezone.utc).isoformat()
            except Exception:
                ts = datetime.now(timezone.utc).isoformat()
        else:
            ts = datetime.now(timezone.utc).isoformat()

        feat: dict = {
            "timestamp":       ts,
            "windowSec":       1.0,
            "deltaRatio":      pct(d),
            "thetaRatio":      pct(th),
            "alphaRatio":      pct(la + ha),
            "betaRatio":       pct(lb + hb),
            "gammaRatio":      pct(lg + hg),
            "lowAlphaRatio":   pct(la),
            "highAlphaRatio":  pct(ha),
            "lowBetaRatio":    pct(lb),
            "highBetaRatio":   pct(hb),
            "lowGammaRatio":   pct(lg),
            "highGammaRatio":  pct(hg),
        }
        if attn > 0:
            feat["attentionIndex"]  = round(attn / 100.0, 4)
        if medi > 0:
            feat["meditationIndex"] = round(medi / 100.0, 4)
        features.append(feat)
    return features


def bands_avg_to_features(bands_avg: dict, session_time: int) -> List[dict]:
    """EEG stats bands_avg（單筆聚合）→ Firebase EEG features"""
    d  = float(bands_avg.get("delta",      0) or 0)
    th = float(bands_avg.get("theta",      0) or 0)
    la = float(bands_avg.get("low_alpha",  0) or 0)
    ha = float(bands_avg.get("high_alpha", 0) or 0)
    lb = float(bands_avg.get("low_beta",   0) or 0)
    hb = float(bands_avg.get("high_beta",  0) or 0)
    lg = float(bands_avg.get("low_gamma",  0) or 0)
    hg = float(bands_avg.get("high_gamma", 0) or 0)
    attn = float(bands_avg.get("attention",   0) or 0)
    medi = float(bands_avg.get("meditation",  0) or 0)

    total = d + th + la + ha + lb + hb + lg + hg
    if total == 0:
        return []

    def pct(v): return round(v / total * 100, 2)

    try:
        ts = datetime.fromtimestamp(session_time, tz=timezone.utc).isoformat()
    except Exception:
        ts = datetime.now(timezone.utc).isoformat()

    feat: dict = {
        "timestamp":       ts,
        "windowSec":       1.0,
        "deltaRatio":      pct(d),
        "thetaRatio":      pct(th),
        "alphaRatio":      pct(la + ha),
        "betaRatio":       pct(lb + hb),
        "gammaRatio":      pct(lg + hg),
        "lowAlphaRatio":   pct(la),
        "highAlphaRatio":  pct(ha),
        "lowBetaRatio":    pct(lb),
        "highBetaRatio":   pct(hb),
        "lowGammaRatio":   pct(lg),
        "highGammaRatio":  pct(hg),
    }
    if attn > 0:
        feat["attentionIndex"]  = round(attn / 100.0, 4)
    if medi > 0:
        feat["meditationIndex"] = round(medi / 100.0, 4)
    return [feat]


# ── Sync one session ──────────────────────────────────────────────────────────

def sync_session(railway_sess: dict, railway: RailwayClient,
                 subject_map: Dict[str, str]) -> bool:
    sid = railway_sess.get("session_id")
    name = railway_sess.get("subject_name") or "未知"
    log.info("▶ session %s: %s", sid, name)

    # 1. 建立或查找受測者
    subject_key = name
    fb_subject_id = subject_map.get(subject_key)
    if not fb_subject_id:
        status, data = fb_post("/users/subjects", {
            "name": name,
            "gender": "other",
            "relationship": "個案",
            "notes": f"Railway session_id={sid}",
        })
        if status in (200, 201):
            fb_subject_id = data.get("subjectId") or data.get("id")
            subject_map[subject_key] = fb_subject_id
            log.info("  ✅ 受測者建立: %s → %s", name, fb_subject_id)
        else:
            log.warning("  ⚠ 受測者建立失敗 %s: %s", status, data)

    # 2. 建立 Firebase Session
    start_time = railway_sess.get("start_time") or 0
    status, data = fb_post("/sessions", {
        "sourceApp":    SOURCE_APP,
        "deviceType":   "ThinkGear",
        "samplingRate": 1,
        "platform":     "android",
        "subjectId":    fb_subject_id,
        "metadata": {
            "railway_session_id": sid,
            "subject_name":       name,
        },
    })
    if status not in (200, 201):
        log.error("  ✗ Firebase session 建立失敗 %s: %s", status, data)
        return False

    fb_session_id = data.get("sessionId") or data.get("id")
    log.info("  ✅ Firebase session 建立: %s", fb_session_id)

    # 3. 取得腦波特徵
    captures = railway.get_captures(sid)
    if len(captures) > 1:
        features = captures_to_features(captures)
        source = f"{len(captures)} captures"
    else:
        eeg_stats = railway.get_eeg_stats(sid)
        bands_avg = eeg_stats.get("bands_avg") or {}
        if captures and not bands_avg:
            # 單筆 capture（聚合記錄）
            features = captures_to_features(captures)
            source = "1 aggregate capture"
        elif bands_avg:
            features = bands_avg_to_features(bands_avg, start_time)
            source = "bands_avg aggregate"
        else:
            features = []
            source = "empty"

    log.info("  EEG 來源: %s → %d 筆特徵", source, len(features))

    # 4. 批次上傳 EEG
    total_uploaded = 0
    if features:
        for i in range(0, len(features), 100):
            batch = features[i:i + 100]
            status2, data2 = fb_post("/eeg/batch", {
                "sessionId": fb_session_id,
                "sourceApp": SOURCE_APP,
                "features":  batch,
            })
            if status2 in (200, 201):
                total_uploaded += len(batch)
            else:
                log.error("  ✗ EEG 批次上傳失敗 %s: %s", status2, data2)
                break

    log.info("  ✅ EEG 上傳 %d 筆", total_uploaded)

    # 5. 標記完成
    fb_patch(f"/sessions/{fb_session_id}", {
        "status":      "completed",
        "endedAt":     datetime.now(timezone.utc).isoformat(),
        "durationSec": max(total_uploaded, 1),
    })

    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("Firebase 補同步腳本啟動")
    log.info("=" * 60)

    # 登入 Firebase
    token_mgr.get_headers()

    # 登入 Railway
    railway = RailwayClient()

    # 取得 Firebase 現有受測者（建 subject_map 避免重複）
    status, fb_subjects_data = fb_get("/users/subjects?limit=100")
    fb_subjects = fb_subjects_data.get("subjects") or []
    subject_map: Dict[str, str] = {
        s.get("name", ""): s.get("id") or s.get("subjectId", "")
        for s in fb_subjects
        if s.get("name")
    }
    log.info("Firebase 現有受測者: %d 位", len(subject_map))

    # 取得 Firebase 現有 sessions（透過 metadata.railway_session_id 比對）
    status2, fb_sessions_data = fb_get("/sessions?limit=200")
    fb_sessions = fb_sessions_data.get("sessions") or []
    synced_railway_ids = set()
    for fs in fb_sessions:
        meta = fs.get("metadata") or {}
        r_id = meta.get("railway_session_id")
        if r_id:
            synced_railway_ids.add(str(r_id))
    log.info("Firebase 已同步 Railway session: %d 個", len(synced_railway_ids))

    # 取得 Railway 所有 sessions
    railway_sessions = railway.list_sessions(limit=200)
    log.info("Railway 總 sessions: %d", len(railway_sessions))

    # 找出未同步的 sessions
    missing = [
        s for s in railway_sessions
        if str(s.get("session_id")) not in synced_railway_ids
    ]
    log.info("需要補同步: %d 個 sessions", len(missing))
    for m in missing:
        log.info("  ► session %s: %s", m.get("session_id"), m.get("subject_name"))

    if not missing:
        log.info("✅ 所有 sessions 已同步，無需補充")
        return

    # 開始補同步
    ok_count = 0
    fail_count = 0
    for sess in missing:
        try:
            if sync_session(sess, railway, subject_map):
                ok_count += 1
            else:
                fail_count += 1
        except Exception as e:
            log.error("  ✗ session %s 例外: %s", sess.get("session_id"), e)
            fail_count += 1
        time.sleep(0.5)  # 避免 rate limit

    log.info("=" * 60)
    log.info("補同步完成：成功 %d，失敗 %d", ok_count, fail_count)
    log.info("=" * 60)

    # 輸出摘要
    report = {
        "timestamp": datetime.now().isoformat(),
        "missing_sessions": len(missing),
        "synced_ok": ok_count,
        "synced_fail": fail_count,
        "sessions": [{"session_id": s["session_id"], "subject_name": s.get("subject_name")} for s in missing],
    }
    with open("resync_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log.info("報告已寫入 resync_report.json")


if __name__ == "__main__":
    main()
