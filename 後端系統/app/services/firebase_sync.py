"""
firebase_sync.py
~~~~~~~~~~~~~~~~
將 ThinkGear 原始腦波陣列（180 筆/次）同步到外部 Firebase 腦波資料庫。

目標 API：
  https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api
  （見 D:/Write program/Database/ToOtherProject/API_INTEGRATION_GUIDE.md）

認證方式（優先順序）：
  1. X-Service-Key header：環境變數 FIREBASE_SERVICE_KEY（Railway 內部 service key）
  2. Firebase Bearer Token：用 FIREBASE_API_KEY + FIREBASE_SYNC_EMAIL + FIREBASE_SYNC_PASSWORD
     透過 Firebase Auth REST API 取得 id_token，自動快取並在到期前刷新。

資料轉換：
  ThinkGear raw 值（0 ~ 16,777,215）→ bandTo100 正規化 → 比例（ratio）
  每筆 sample 會計算各頻段占總功率的百分比，寫入 lowAlphaRatio、thetaRatio 等欄位。
"""

import asyncio
import logging
import math
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional

import httpx

logger = logging.getLogger(__name__)

FIREBASE_API_BASE = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api/api"
SOURCE_APP = "BrainReport-LUKE"

# ── 認證環境變數 ──────────────────────────────────────────────────────────────

# 方法 1：X-Service-Key（最優先）
FIREBASE_SERVICE_KEY = os.getenv("FIREBASE_SERVICE_KEY", "")

# 方法 2：Firebase User Auth（備用）
FIREBASE_API_KEY      = os.getenv("FIREBASE_API_KEY",      "AIzaSyBc-ZEcT8fvyn-dBZ0Bhm5IsakncVp1ngQ")
FIREBASE_SYNC_EMAIL   = os.getenv("FIREBASE_SYNC_EMAIL",   "migration@returntohealthtw.com")
FIREBASE_SYNC_PASSWORD = os.getenv("FIREBASE_SYNC_PASSWORD", "MigrateEEG@2026")

# ── Token 快取（模組級別，避免每次 API call 都重新登入）────────────────────────
_cached_token: str = ""
_token_expires_at: float = 0.0


def _refresh_bearer_token() -> str:
    """
    用 Firebase email/password 取得 id_token，並快取至到期前 120 秒。
    使用同步 httpx（在 asyncio 事件迴圈外呼叫時安全）。
    """
    global _cached_token, _token_expires_at
    import httpx as _httpx
    try:
        resp = _httpx.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
            f"?key={FIREBASE_API_KEY}",
            json={
                "email": FIREBASE_SYNC_EMAIL,
                "password": FIREBASE_SYNC_PASSWORD,
                "returnSecureToken": True,
            },
            timeout=15.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            _cached_token = data["idToken"]
            expires_in = int(data.get("expiresIn", 3600))
            _token_expires_at = time.time() + expires_in - 120  # 提前 2 分鐘刷新
            logger.info("[Firebase] Bearer token 取得成功，有效至 %s",
                        datetime.fromtimestamp(_token_expires_at + 120).strftime("%H:%M:%S"))
            return _cached_token
        else:
            logger.error("[Firebase] Firebase 登入失敗 %s: %s", resp.status_code, resp.text[:200])
            return ""
    except Exception as e:
        logger.error("[Firebase] Firebase 登入例外: %s", e)
        return ""


def _get_auth_headers(force_bearer: bool = False) -> dict:
    """
    取得正確的認證 header。
    優先使用 X-Service-Key；若 force_bearer=True 或未設定，改用 Firebase Bearer Token。
    """
    global _cached_token, _token_expires_at

    if FIREBASE_SERVICE_KEY and not force_bearer:
        return {
            "X-Service-Key": FIREBASE_SERVICE_KEY,
            "Content-Type":  "application/json",
        }

    # Firebase Bearer Token 備用
    if not (FIREBASE_API_KEY and FIREBASE_SYNC_EMAIL and FIREBASE_SYNC_PASSWORD):
        logger.warning("[Firebase] 既無 FIREBASE_SERVICE_KEY 也無 Firebase 登入憑證，無法同步")
        return {}

    if time.time() >= _token_expires_at or not _cached_token:
        _refresh_bearer_token()

    if not _cached_token:
        return {}

    return {
        "Authorization": f"Bearer {_cached_token}",
        "Content-Type":  "application/json",
    }


def _needs_bearer_fallback(status_code: int) -> bool:
    """401/403 時嘗試用 Bearer Token 替代 X-Service-Key。"""
    return status_code in (401, 403) and bool(FIREBASE_SERVICE_KEY)


def _band_to_100(raw: float) -> float:
    """ThinkGear raw → 0-100 正規化（與 Android bandTo100 完全一致）"""
    if raw <= 0:
        return 0.0
    return min(100.0, max(0.0, math.log10(raw + 1) / 6.0 * 100.0))


def _raw_arrays_to_features(raw_arrays: dict, session_start: datetime) -> list[dict]:
    """
    將各頻段 raw 陣列轉換為 Firebase /api/eeg/batch 所需的 features 列表。

    每個索引 i 代表第 i 秒的樣本，轉換邏輯：
      1. raw → bandTo100（0-100 正規化）
      2. 計算各頻段占總功率比例（ratio）
      3. 保存原始 raw 值作為 *Power 欄位（供潛意識音頻生成專案用）
    """
    attn    = raw_arrays.get("attn",     [])
    medi    = raw_arrays.get("medi",     [])
    r_delta = raw_arrays.get("r_delta",  [])
    r_theta = raw_arrays.get("r_theta",  [])
    r_la    = raw_arrays.get("r_lalpha", [])
    r_ha    = raw_arrays.get("r_halpha", [])
    r_lb    = raw_arrays.get("r_lbeta",  [])
    r_hb    = raw_arrays.get("r_hbeta",  [])
    r_lg    = raw_arrays.get("r_lgamma", [])
    r_hg    = raw_arrays.get("r_hgamma", [])

    n = max(len(attn), len(r_theta), len(r_la))
    if n == 0:
        return []

    features = []
    for i in range(n):
        def _get(arr, idx): return arr[idx] if idx < len(arr) else 0

        raw_d  = _get(r_delta, i)
        raw_th = _get(r_theta, i)
        raw_la = _get(r_la,    i)
        raw_ha = _get(r_ha,    i)
        raw_lb = _get(r_lb,    i)
        raw_hb = _get(r_hb,    i)
        raw_lg = _get(r_lg,    i)
        raw_hg = _get(r_hg,    i)

        # bandTo100 正規化
        b_d  = _band_to_100(raw_d)
        b_th = _band_to_100(raw_th)
        b_la = _band_to_100(raw_la)
        b_ha = _band_to_100(raw_ha)
        b_lb = _band_to_100(raw_lb)
        b_hb = _band_to_100(raw_hb)
        b_lg = _band_to_100(raw_lg)
        b_hg = _band_to_100(raw_hg)

        # 相對功率比例（各頻段 / 總功率 × 100）
        total = b_d + b_th + b_la + b_ha + b_lb + b_hb + b_lg + b_hg
        def ratio(v): return round(v / total * 100, 2) if total > 0 else 0.0

        ts = (session_start + timedelta(seconds=i)).isoformat()

        feat = {
            "timestamp":       ts,
            "windowSec":       1.0,
            # 原始 raw 值（絕對功率，供潛意識音頻生成演算法使用）
            # 合併頻段（向下相容）
            "deltaPower":      raw_d  or None,
            "thetaPower":      raw_th or None,
            "alphaPower":      (raw_la + raw_ha) or None,
            "betaPower":       (raw_lb + raw_hb) or None,
            "gammaPower":      (raw_lg + raw_hg) or None,
            # 分頻功率（BrainDNA 佔比演算法必要欄位）
            "lowAlphaPower":   raw_la or None,
            "highAlphaPower":  raw_ha or None,
            "lowBetaPower":    raw_lb or None,
            "highBetaPower":   raw_hb or None,
            "lowGammaPower":   raw_lg or None,
            "highGammaPower":  raw_hg or None,
            # 相對比例（0-100 %）
            "deltaRatio":      ratio(b_d),
            "thetaRatio":      ratio(b_th),
            "alphaRatio":      ratio(b_la + b_ha),
            "betaRatio":       ratio(b_lb + b_hb),
            "gammaRatio":      ratio(b_lg + b_hg),
            # 細分頻段比例（MBTI 時間窗分析核心欄位）
            "lowAlphaRatio":   ratio(b_la),
            "highAlphaRatio":  ratio(b_ha),
            "lowBetaRatio":    ratio(b_lb),
            "highBetaRatio":   ratio(b_hb),
            "lowGammaRatio":   ratio(b_lg),
            "highGammaRatio":  ratio(b_hg),
            # 衍生指數
            "attentionIndex":  _get(attn, i) / 100.0 if i < len(attn) else None,
            "meditationIndex": _get(medi, i) / 100.0 if i < len(medi) else None,
        }
        # 移除 None 值（Firebase schema 允許 optional，但避免多餘欄位）
        feat = {k: v for k, v in feat.items() if v is not None}
        features.append(feat)

    return features


_MIND_COLOR_MAP = {0: "orange", 1: "green", 2: "blue", 3: "yellow"}

def _color_to_str(v) -> Optional[str]:
    """mindColor 整數(0-3) → Firebase 要求的字串；已是字串直接回傳"""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    return _MIND_COLOR_MAP.get(int(v), str(v))


def _build_qeeg_patch(qeeg_result: Optional[dict]) -> dict:
    """qEEG 結果 → Firebase PATCH 欄位（打平為輕量摘要，避免 Firestore document 過大）"""
    if not qeeg_result:
        return {}
    out: dict = {}
    ab = qeeg_result.get("ability_scores", {})
    if ab:
        out["qeegAbilities"] = {k: v.get("score") for k, v in ab.items()}
    ci = qeeg_result.get("composite_indices", {})
    if ci:
        out["qeegComposites"] = {k: v.get("score") for k, v in ci.items()}
    flags = qeeg_result.get("report_flags", [])
    if flags:
        # Firebase PATCH 要求 object，不接受 array
        out["qeegFlags"] = {f["flag"]: True for f in flags if isinstance(f, dict) and f.get("flag")}
    sq = qeeg_result.get("signal_quality", {})
    if sq:
        out["qeegSignalGrade"] = sq.get("quality_grade")
    # qeegVersion: Firebase PATCH 不接受，省略
    # ── 8 個頻段的 qEEG Z-score 0-100 分數（使用者昨天要求存入 Firebase 的欄位）──
    bf = qeeg_result.get("band_features", {}).get("Fp1", {})
    if bf:
        band_scores = {}
        for band in ["delta", "theta", "low_alpha", "high_alpha",
                     "low_beta", "high_beta", "low_gamma", "high_gamma"]:
            entry = bf.get(band)
            if entry and entry.get("score_0_100") is not None:
                band_scores[band] = round(entry["score_0_100"])
        if band_scores:
            out["qeegBandScores"] = band_scores
    return {k: v for k, v in out.items() if v is not None}


async def sync_to_firebase(
    subject_name: str,
    session_id: int,
    raw_arrays: dict,
    session_start: Optional[datetime] = None,
    braindna_result: Optional[dict] = None,
    qeeg_result: Optional[dict] = None,
) -> Optional[str]:
    """
    非同步將 180 筆原始腦波資料同步到 Firebase 腦波資料庫。

    流程：
      1. POST /api/sessions → 取得 firebase_session_id
      2. POST /api/eeg/batch（每批最多 100 筆，分批上傳）→ 存入 Firestore + BigQuery
      3. PATCH /api/sessions/{id} → 標記 completed

    返回 firebase_session_id（字串）表示成功；None 表示失敗（不拋例外，避免影響主流程）。
    """
    # 優先使用 X-Service-Key（admin 權限，支援寫入 BrainDNA/QEEG 欄位）
    # 未設定時 fallback Bearer Token
    headers = _get_auth_headers(force_bearer=False)
    if not headers:
        logger.warning("[Firebase] 無可用認證憑證，跳過同步（設定 FIREBASE_SERVICE_KEY 或 FIREBASE_SYNC_EMAIL/PASSWORD）")
        return False

    if not raw_arrays:
        logger.warning("[Firebase] raw_arrays 為空，跳過同步")
        return False

    if session_start is None:
        session_start = datetime.now(timezone.utc)

    _sess_payload = {
        "sourceApp":    SOURCE_APP,
        "deviceType":   "ThinkGear",
        "samplingRate": 1,
        "platform":     "android",
        "metadata": {
            "railway_session_id": session_id,
            "subject_name":       subject_name,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # ── 1. 建立 Firebase Session ─────────────────────────────────────
            sess_resp = await client.post(
                f"{FIREBASE_API_BASE}/sessions",
                headers=headers,
                json=_sess_payload,
            )
            if sess_resp.status_code not in (200, 201):
                if _needs_bearer_fallback(sess_resp.status_code):
                    logger.warning("[Firebase] X-Service-Key 被拒（%s），切換 Bearer Token 重試...",
                                   sess_resp.status_code)
                    _refresh_bearer_token()
                    headers = _get_auth_headers(force_bearer=True)
                    if headers:
                        sess_resp = await client.post(
                            f"{FIREBASE_API_BASE}/sessions", headers=headers, json=_sess_payload
                        )
                if sess_resp.status_code not in (200, 201):
                    logger.error("[Firebase] 建立 session 失敗 %s: %s",
                                 sess_resp.status_code, sess_resp.text[:200])
                    return False

            fb_session_id = sess_resp.json().get("sessionId")
            if not fb_session_id:
                logger.error("[Firebase] 回應無 sessionId")
                return False

            logger.info("[Firebase] session 建立成功 fb_sid=%s", fb_session_id)

            # ── 2. 轉換並批次上傳 EEG 特徵值 ─────────────────────────────
            features = _raw_arrays_to_features(raw_arrays, session_start)
            if not features:
                logger.warning("[Firebase] 轉換後特徵值為空，跳過上傳")
                return False

            batch_size = 100   # Firebase schema 上限 100 筆/次
            total_uploaded = 0
            for i in range(0, len(features), batch_size):
                batch = features[i:i + batch_size]
                eeg_resp = await client.post(
                    f"{FIREBASE_API_BASE}/eeg/batch",
                    headers=headers,
                    json={
                        "sessionId": fb_session_id,
                        "sourceApp": SOURCE_APP,
                        "features":  batch,
                    },
                )
                if eeg_resp.status_code not in (200, 201):
                    logger.error("[Firebase] 上傳 EEG batch 失敗 %s: %s",
                                 eeg_resp.status_code, eeg_resp.text[:200])
                    return False
                total_uploaded += len(batch)

            logger.info("[Firebase] 已上傳 %d 筆 EEG 特徵值 → fb_sid=%s",
                        total_uploaded, fb_session_id)

            # ── 3. 標記 Session completed + 寫入 BrainDNA 計算結果 ───────────
            patch_body: dict = {
                "status":      "completed",
                "endedAt":     datetime.now(timezone.utc).isoformat(),
                "durationSec": len(features),
            }
            # BrainDNA 聚合結果
            if braindna_result and braindna_result.get("valid"):
                patch_body.update({
                    "mindStress":   braindna_result.get("stress"),
                    "mindBalance":  braindna_result.get("balance"),
                    "mindEnergy":   braindna_result.get("energy"),
                    "mindColor":    _color_to_str(braindna_result.get("color")),
                    "overallScore": braindna_result.get("overall_score"),
                    "mbti":         braindna_result.get("mbti"),
                    "bagua":        braindna_result.get("bagua"),
                })
            # qEEG Z-score 摘要（七大能力 + 複合指標 + flags）
            patch_body.update(_build_qeeg_patch(qeeg_result))
            patch_body = {k: v for k, v in patch_body.items() if v is not None}
            patch_resp = await client.patch(
                f"{FIREBASE_API_BASE}/sessions/{fb_session_id}",
                headers=headers,
                json=patch_body,
            )
            if patch_resp.status_code not in (200, 204):
                logger.warning("[Firebase] PATCH session 狀態非預期: %s", patch_resp.status_code)

            return fb_session_id

    except Exception as exc:
        logger.exception("[Firebase] 同步例外: %s", exc)
        return None


def _captures_to_features(captures: List[Any]) -> list:
    """
    將 Android 上傳的 180 筆 ThinkGear bandTo100 擷取值轉換為 Firebase EEG 特徵格式。

    captures 是 CaptureItem 或 EegCapture 物件列表；
    其中的 delta/theta/... 均為 ThinkGear bandTo100 值（0~100 scale）。
    直接用這些值計算相對功率比例，無需再做 bandTo100 轉換。
    """
    features = []
    for cap in captures:
        d  = float(getattr(cap, "delta",      0) or 0)
        th = float(getattr(cap, "theta",      0) or 0)
        la = float(getattr(cap, "low_alpha",  0) or 0)
        ha = float(getattr(cap, "high_alpha", 0) or 0)
        lb = float(getattr(cap, "low_beta",   0) or 0)
        hb = float(getattr(cap, "high_beta",  0) or 0)
        lg = float(getattr(cap, "low_gamma",  0) or 0)
        hg = float(getattr(cap, "high_gamma", 0) or 0)
        attn = float(getattr(cap, "attention",   0) or 0)
        medi = float(getattr(cap, "meditation",  0) or 0)

        total = d + th + la + ha + lb + hb + lg + hg

        def ratio(v: float) -> float:
            return round(v / total * 100, 2) if total > 0 else 0.0

        # captured_at 是毫秒 Unix timestamp
        captured_ms = int(getattr(cap, "captured_at", 0) or 0)
        if captured_ms > 0:
            ts = datetime.fromtimestamp(captured_ms / 1000.0, tz=timezone.utc).isoformat()
        else:
            ts = datetime.now(timezone.utc).isoformat()

        feat: dict = {
            "timestamp":       ts,
            "windowSec":       1.0,
            "deltaRatio":      ratio(d),
            "thetaRatio":      ratio(th),
            "alphaRatio":      ratio(la + ha),
            "betaRatio":       ratio(lb + hb),
            "gammaRatio":      ratio(lg + hg),
            "lowAlphaRatio":   ratio(la),
            "highAlphaRatio":  ratio(ha),
            "lowBetaRatio":    ratio(lb),
            "highBetaRatio":   ratio(hb),
            "lowGammaRatio":   ratio(lg),
            "highGammaRatio":  ratio(hg),
        }
        if attn > 0:
            feat["attentionIndex"]  = round(attn / 100.0, 4)
        if medi > 0:
            feat["meditationIndex"] = round(medi / 100.0, 4)

        features.append(feat)

    return features


async def sync_captures_to_firebase(
    subject_name: str,
    session_id: int,
    captures: List[Any],
    qeeg_result: Optional[dict] = None,
    braindna_result: Optional[dict] = None,
) -> Optional[str]:
    """
    將 Android 上傳路徑（/sessions/upload）的 180 筆 EegCapture 同步到 Firebase。

    captures 中為 ThinkGear bandTo100 值（0~100），直接計算相對比例後上傳。
    回傳 firebase_session_id（字串）表示成功；None 表示失敗（不拋例外）。
    """
    # 優先使用 X-Service-Key（admin 權限）；未設定時 fallback Bearer Token
    headers = _get_auth_headers(force_bearer=False)
    if not headers:
        logger.warning("[Firebase] 無可用認證憑證，跳過 Android captures 同步")
        return False

    if not captures:
        logger.warning("[Firebase] captures 為空，跳過同步")
        return False

    _sess_payload = {
        "sourceApp":    SOURCE_APP,
        "deviceType":   "ThinkGear",
        "samplingRate": 1,
        "platform":     "android",
        "metadata": {
            "railway_session_id": session_id,
            "subject_name":       subject_name,
            "data_format":        "bandTo100",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. 建立 Firebase Session
            sess_resp = await client.post(
                f"{FIREBASE_API_BASE}/sessions",
                headers=headers,
                json=_sess_payload,
            )
            if sess_resp.status_code not in (200, 201):
                if _needs_bearer_fallback(sess_resp.status_code):
                    logger.warning("[Firebase] X-Service-Key 被拒（%s），切換 Bearer Token...",
                                   sess_resp.status_code)
                    _refresh_bearer_token()
                    headers = _get_auth_headers(force_bearer=True)
                    if headers:
                        sess_resp = await client.post(
                            f"{FIREBASE_API_BASE}/sessions", headers=headers, json=_sess_payload
                        )
                if sess_resp.status_code not in (200, 201):
                    logger.error("[Firebase] Android 建立 session 失敗 %s: %s",
                                 sess_resp.status_code, sess_resp.text[:200])
                    return False

            fb_session_id = sess_resp.json().get("sessionId")
            if not fb_session_id:
                logger.error("[Firebase] Android session 回應無 sessionId")
                return False

            logger.info("[Firebase] Android session 建立成功 fb_sid=%s", fb_session_id)

            # 2. 轉換並批次上傳 180 筆特徵值
            features = _captures_to_features(captures)
            if not features:
                logger.warning("[Firebase] captures 轉換後為空，跳過上傳")
                return False

            batch_size = 100
            total_uploaded = 0
            for i in range(0, len(features), batch_size):
                batch = features[i:i + batch_size]
                eeg_resp = await client.post(
                    f"{FIREBASE_API_BASE}/eeg/batch",
                    headers=headers,
                    json={
                        "sessionId": fb_session_id,
                        "sourceApp": SOURCE_APP,
                        "features":  batch,
                    },
                )
                if eeg_resp.status_code not in (200, 201):
                    logger.error("[Firebase] Android EEG batch 失敗 %s: %s",
                                 eeg_resp.status_code, eeg_resp.text[:200])
                    return False
                total_uploaded += len(batch)

            logger.info("[Firebase] Android 已上傳 %d 筆 EEG → fb_sid=%s",
                        total_uploaded, fb_session_id)

            # 3. 標記 Session completed + BrainDNA + qEEG 摘要
            android_patch = {
                "status":      "completed",
                "endedAt":     datetime.now(timezone.utc).isoformat(),
                "durationSec": len(features),
            }
            # BrainDNA 結果（Android 路徑）
            if braindna_result and braindna_result.get("valid"):
                android_patch.update({
                    "mindStress":   braindna_result.get("stress"),
                    "mindBalance":  braindna_result.get("balance"),
                    "mindEnergy":   braindna_result.get("energy"),
                    "mindColor":    _color_to_str(braindna_result.get("mind_color")),
                    "overallScore": braindna_result.get("overall_score"),
                    "mbti":         braindna_result.get("mbti"),
                    "bagua":        braindna_result.get("bagua"),
                })
            android_patch.update(_build_qeeg_patch(qeeg_result))
            android_patch = {k: v for k, v in android_patch.items() if v is not None}
            patch_resp = await client.patch(
                f"{FIREBASE_API_BASE}/sessions/{fb_session_id}",
                headers=headers,
                json=android_patch,
            )
            if patch_resp.status_code not in (200, 204):
                logger.warning("[Firebase] Android PATCH session 狀態非預期: %s", patch_resp.status_code)

            return fb_session_id

    except Exception as exc:
        logger.exception("[Firebase] Android captures 同步例外: %s", exc)
        return None


# ── qEEG 完整分析結果存入 Firestore qeeg_analysis collection ──────────────────

FIRESTORE_BASE = "https://firestore.googleapis.com/v1/projects/gen-lang-client-0435688289/databases/(default)/documents"


def _to_firestore_value(v: Any) -> dict:
    """Python 值 → Firestore REST API 型別值"""
    if v is None:
        return {"nullValue": None}
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, str):
        return {"stringValue": v}
    if isinstance(v, list):
        return {"arrayValue": {"values": [_to_firestore_value(i) for i in v]}}
    if isinstance(v, dict):
        return {"mapValue": {"fields": {k: _to_firestore_value(vv) for k, vv in v.items()}}}
    return {"stringValue": str(v)}


def _dict_to_firestore_fields(d: dict) -> dict:
    return {k: _to_firestore_value(v) for k, v in d.items()}


async def sync_qeeg_analysis_to_firestore(
    firebase_session_id: str,
    qeeg_result: dict,
    railway_session_id: int,
) -> bool:
    """
    將完整 qEEG 分析結果存入 Firestore qeeg_analysis collection。
    文件 ID 使用 Firebase session ID，方便跨 collection 關聯查詢。

    Firestore path: qeeg_analysis/{firebase_session_id}
    """
    if not firebase_session_id or not qeeg_result:
        return False

    headers = _get_auth_headers(force_bearer=False)
    if not headers:
        logger.warning("[qEEG Firestore] 無認證憑證，跳過 qeeg_analysis 存入")
        return False

    # 在文件中加入 session 關聯 ID
    doc_data = dict(qeeg_result)
    doc_data["firebaseSessionId"]  = firebase_session_id
    doc_data["railwaySessionId"]   = railway_session_id
    doc_data["savedAt"]            = datetime.now(timezone.utc).isoformat()

    firestore_body = {"fields": _dict_to_firestore_fields(doc_data)}
    url = f"{FIRESTORE_BASE}/qeeg_analysis/{firebase_session_id}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                url,
                headers={**headers, "Content-Type": "application/json"},
                json=firestore_body,
            )
            if resp.status_code in (200, 201):
                logger.info("[qEEG Firestore] qeeg_analysis/%s 寫入成功", firebase_session_id)
                return True
            else:
                logger.warning("[qEEG Firestore] 寫入失敗 %s: %s",
                               resp.status_code, resp.text[:200])
                return False
    except Exception as exc:
        logger.exception("[qEEG Firestore] 寫入例外: %s", exc)
        return False


# ── 從 Firebase 讀取 180 筆特徵值（用於 BrainDNA 重新計算）──────────────────────

async def fetch_eeg_features(firebase_session_id: str) -> Optional[List[dict]]:
    """
    從 Firebase 讀取指定 session 的所有 EEG 特徵值（最多 200 筆）。

    端點：GET /eeg/{sessionId}?limit=200
    回傳特徵值列表；失敗或無資料時回傳 None。
    """
    headers = _get_auth_headers(force_bearer=False)
    if not headers:
        logger.warning("[Firebase] 無認證憑證，無法讀取 EEG 特徵值")
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{FIREBASE_API_BASE}/eeg/{firebase_session_id}",
                headers=headers,
                params={"limit": 200},
            )
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features") or data.get("data") or []
                logger.info("[Firebase] 讀取 fb_sid=%s 共 %d 筆特徵值",
                            firebase_session_id, len(features))
                return features if features else None
            else:
                logger.error("[Firebase] GET /eeg/%s 失敗 %s: %s",
                             firebase_session_id, resp.status_code, resp.text[:200])
                return None
    except Exception as exc:
        logger.exception("[Firebase] fetch_eeg_features 例外: %s", exc)
        return None


def firebase_features_to_raw_arrays(features: List[dict]) -> dict:
    """
    將 Firebase eeg_features 列表轉換為 BrainDNA compute_all() 所需的 raw_arrays 格式。

    優先使用各分頻功率（*Power）做原始值輸入（scale='raw'）；
    若無功率值，改用比例值（*Ratio，0-100）做輸入（scale='norm100'）。

    回傳格式：
    {
        "r_delta":  [float, ...],  # 每秒一個值
        "r_theta":  [float, ...],
        "r_lalpha": [float, ...],
        "r_halpha": [float, ...],
        "r_lbeta":  [float, ...],
        "r_hbeta":  [float, ...],
        "r_lgamma": [float, ...],
        "r_hgamma": [float, ...],
    }
    """
    # 按時間戳或序號排序，確保順序正確
    # Firestore timestamp 格式：{"_seconds": 1782625206, "_nanoseconds": 0}
    def _sort_key(f):
        ts = f.get("timestamp")
        if isinstance(ts, dict):
            return ts.get("_seconds", 0)
        if isinstance(ts, (int, float)):
            return ts
        # 字串 ISO 格式（備用）
        return str(ts or "")
    sorted_features = sorted(features, key=_sort_key)

    # 判斷是否有分頻功率欄位（Railway 新格式）或只有比例欄位
    has_sub_power = any(
        f.get("lowAlphaPower") or f.get("highAlphaPower")
        for f in sorted_features[:5]
    )

    r_delta  = []
    r_theta  = []
    r_lalpha = []
    r_halpha = []
    r_lbeta  = []
    r_hbeta  = []
    r_lgamma = []
    r_hgamma = []

    for f in sorted_features:
        if has_sub_power:
            # 使用原始 raw 功率值（供 scale='raw' BrainDNA）
            r_delta .append(float(f.get("deltaPower",     0) or 0))
            r_theta .append(float(f.get("thetaPower",     0) or 0))
            r_lalpha.append(float(f.get("lowAlphaPower",  0) or 0))
            r_halpha.append(float(f.get("highAlphaPower", 0) or 0))
            r_lbeta .append(float(f.get("lowBetaPower",   0) or 0))
            r_hbeta .append(float(f.get("highBetaPower",  0) or 0))
            r_lgamma.append(float(f.get("lowGammaPower",  0) or 0))
            r_hgamma.append(float(f.get("highGammaPower", 0) or 0))
        else:
            # 使用比例值（供 scale='norm100' BrainDNA）
            r_delta .append(float(f.get("deltaRatio",     0) or 0))
            r_theta .append(float(f.get("thetaRatio",     0) or 0))
            r_lalpha.append(float(f.get("lowAlphaRatio",  0) or 0))
            r_halpha.append(float(f.get("highAlphaRatio", 0) or 0))
            r_lbeta .append(float(f.get("lowBetaRatio",   0) or 0))
            r_hbeta .append(float(f.get("highBetaRatio",  0) or 0))
            r_lgamma.append(float(f.get("lowGammaRatio",  0) or 0))
            r_hgamma.append(float(f.get("highGammaRatio", 0) or 0))

    return {
        "r_delta":  r_delta,
        "r_theta":  r_theta,
        "r_lalpha": r_lalpha,
        "r_halpha": r_halpha,
        "r_lbeta":  r_lbeta,
        "r_hbeta":  r_hbeta,
        "r_lgamma": r_lgamma,
        "r_hgamma": r_hgamma,
    }


# ── 付款記錄同步到 Firebase Firestore payments collection ─────────────────────

_REPORT_TYPE_MAP = {
    "life_script":  "adult_vip",
    "adult":        "adult_vip",
    "child":        "child_vip",
    "child_report": "child_vip",
    "marital":      "marital",
    "parent_child": "parent_child",
}

def sync_payment_to_firebase(payment_row, firebase_session_id: str = "") -> bool:
    """
    將付款資訊同步到 Firebase。
    策略：
      1. 若提供 firebase_session_id → PATCH /sessions/{fb_sid}，把 paymentInfo 存進 session 文件
         （使用 CF API + Service Key，權限充足）
      2. 若無 firebase_session_id → 嘗試直接寫 Firestore payments collection
         （需 Firebase security rules 允許；生產環境可能因規則限制而失敗）

    payment_row：ORM Payment 物件或包含相同欄位的 dict。
    firebase_session_id：關聯的 Firebase session ID（可選，有則優先用）。
    """
    if not is_configured():
        return False
    try:
        def _get(obj, attr, default=None):
            return getattr(obj, attr, None) if not isinstance(obj, dict) else obj.get(attr, default)

        payment_id = _get(payment_row, "payment_id")
        if not payment_id:
            return False

        import time as _time
        import httpx as _hx

        payment_info = {
            "railwayPaymentId": payment_id,
            "orderId":          _get(payment_row, "order_id") or "",
            "consultantId":     _get(payment_row, "consultant_id"),
            "consultantName":   _get(payment_row, "consultant_name") or "",
            "subjectName":      _get(payment_row, "subject_name") or "",
            "subjectEmail":     _get(payment_row, "subject_email") or "",
            "reportType":       _get(payment_row, "report_type") or "",
            "amount":           int(_get(payment_row, "amount") or 0),
            "status":           _get(payment_row, "status") or "paid",
            "provider":         _get(payment_row, "provider") or "",
            "paymentMethod":    _get(payment_row, "payment_method") or "",
            "paidAt":           _get(payment_row, "paid_at"),
            "createdAt":        _get(payment_row, "created_at"),
            "syncedAt":         int(_time.time()),
        }
        payment_info = {k: v for k, v in payment_info.items() if v is not None and v != ""}

        # ── 策略 1：有 firebase_session_id → PATCH session metadata 寫入付款資訊 ────
        # CF API PATCH /sessions 不接受自定義欄位，但 metadata 欄位在 service key 環境下可用
        if firebase_session_id:
            headers = _get_auth_headers(force_bearer=False)
            if not headers:
                return False
            # 先嘗試 metadata（service key 環境），再嘗試 subjects 子欄位
            for patch_body in [
                {"metadata": {"paymentInfo": payment_info}},
                {"metadata": payment_info},
            ]:
                resp = _hx.patch(
                    f"{FIREBASE_API_BASE}/sessions/{firebase_session_id}",
                    headers=headers,
                    json=patch_body,
                    timeout=15.0,
                )
                if resp.status_code in (200, 201, 204):
                    logger.info("[Firebase] payment %s → session %s metadata 已寫入",
                                payment_id, firebase_session_id)
                    return True
                if resp.status_code == 400:
                    # 驗證失敗換下一個格式
                    logger.debug("[Firebase] PATCH metadata 格式不符，嘗試下一格式: %s", resp.text[:100])
                    continue
                # 其他錯誤（403/500 等）不重試
                logger.warning("[Firebase] PATCH session metadata 失敗 %s: %s",
                               resp.status_code, resp.text[:200])
                return False
            logger.warning("[Firebase] PATCH session 所有格式均失敗，payment %s", payment_id)
            return False

        # ── 策略 2：無 session → 直接寫 Firestore payments collection ────────
        headers = _get_auth_headers(force_bearer=True)
        if not headers:
            logger.warning("[Firebase] sync_payment_to_firebase: 無認證憑證")
            return False

        project = "gen-lang-client-0435688289"
        url = (
            f"https://firestore.googleapis.com/v1/projects/{project}"
            f"/databases/(default)/documents/payments/{payment_id}"
        )
        firestore_body = {"fields": _dict_to_firestore_fields(payment_info)}
        resp = _hx.patch(url, headers=headers, json=firestore_body, timeout=15.0)
        if resp.status_code in (200, 201):
            logger.info("[Firebase] payment %s 已寫入 Firestore payments", payment_id)
            return True
        else:
            logger.warning("[Firebase] sync_payment_to_firebase %s 失敗 %s: %s",
                           payment_id, resp.status_code, resp.text[:200])
            return False
    except Exception as exc:
        logger.warning("[Firebase] sync_payment_to_firebase 例外: %s", exc)
        return False


def sync_report_pdf_to_firebase(
    firebase_session_id: str,
    report_type: str,
    pdf_url: str,
    railway_session_id: int = 0,
) -> bool:
    """
    將報告 PDF 連結同步到 Firebase reports collection。
    使用 POST /reports/store CF 端點（需要 X-Service-Key）。
    同步失敗只記錄 warning，不影響主流程。
    """
    if not firebase_session_id or not pdf_url:
        return False
    if not is_configured():
        return False
    try:
        import httpx as _hx
        from datetime import datetime, timezone as _tz
        headers = _get_auth_headers(force_bearer=False)
        if not headers:
            return False

        fb_report_type = _REPORT_TYPE_MAP.get(report_type, "adult_vip")
        payload = {
            "sessionId":   firebase_session_id,
            "reportType":  fb_report_type,
            "pdfUrl":      pdf_url,
            "generatedAt": datetime.now(_tz.utc).isoformat(),
        }
        resp = _hx.post(
            f"{FIREBASE_API_BASE}/reports/store",
            headers=headers,
            json=payload,
            timeout=15.0,
        )
        if resp.status_code in (200, 201):
            logger.info("[Firebase] report pdf synced fb_sid=%s", firebase_session_id)
            return True
        else:
            logger.warning("[Firebase] sync_report_pdf_to_firebase fb_sid=%s 失敗 %s: %s",
                           firebase_session_id, resp.status_code, resp.text[:200])
            return False
    except Exception as exc:
        logger.warning("[Firebase] sync_report_pdf_to_firebase 例外: %s", exc)
        return False


# ── 佇列 API（供 main.py / report_gen.py / ai_report.py 呼叫）─────────────────

def is_configured() -> bool:
    """回傳 True 表示 Firebase 同步已設定（有 Service Key 或備用認證）。"""
    return bool(
        FIREBASE_SERVICE_KEY
        or (FIREBASE_API_KEY and FIREBASE_SYNC_EMAIL and FIREBASE_SYNC_PASSWORD)
    )


def enqueue(session_id: int, report_id: Optional[int] = None) -> None:
    """將 session 加入 firebase_sync_log 佇列（pending），等待排程補漏同步。

    若資料庫不可用或寫入失敗，僅記錄 warning，不拋例外，主流程不受影響。
    """
    try:
        from app.core.database import SessionLocal
        from app.core.models import FirebaseSyncLog
        db = SessionLocal()
        try:
            # 避免同一 session 重複入列
            existing = (
                db.query(FirebaseSyncLog)
                .filter(
                    FirebaseSyncLog.session_id == session_id,
                    FirebaseSyncLog.status.in_(["pending", "syncing", "synced"]),
                )
                .first()
            )
            if existing:
                logger.debug("[Firebase] session %s 已在佇列中（%s），跳過入列", session_id, existing.status)
                return
            log = FirebaseSyncLog(
                session_id  = session_id,
                report_id   = report_id,
                status      = "pending",
            )
            db.add(log)
            db.commit()
            logger.info("[Firebase] session %s 已加入同步佇列", session_id)
        finally:
            db.close()
    except Exception as e:
        logger.warning("[Firebase] enqueue 失敗（session %s）: %s", session_id, e)


MAX_RETRY = 5


def run_pending_syncs(SessionLocalFactory) -> None:
    """掃描 firebase_sync_log 中 pending/failed（retry < MAX_RETRY）的記錄並嘗試同步。

    設計為在背景 thread 或 APScheduler 中執行；失敗不影響主流程。
    """
    if not is_configured():
        return
    try:
        from app.core.models import FirebaseSyncLog, Session as SessionModel, EegCapture
        from datetime import datetime, timezone
        db = SessionLocalFactory()
        try:
            cutoff = datetime.now(timezone.utc)
            pending = (
                db.query(FirebaseSyncLog)
                .filter(
                    FirebaseSyncLog.status.in_(["pending", "failed"]),
                    FirebaseSyncLog.retry_count < MAX_RETRY,
                    (FirebaseSyncLog.next_retry_at == None)
                    | (FirebaseSyncLog.next_retry_at <= cutoff),
                )
                .limit(20)
                .all()
            )
            if not pending:
                return
            logger.info("[Firebase] 排程掃描：發現 %d 筆待同步", len(pending))
            for log in pending:
                log.status = "syncing"
                db.commit()
                try:
                    sess = db.query(SessionModel).filter(
                        SessionModel.session_id == log.session_id
                    ).first()
                    if not sess:
                        log.status = "failed"
                        log.last_error = "session not found"
                        db.commit()
                        continue

                    captures = (
                        db.query(EegCapture)
                        .filter(EegCapture.session_id == log.session_id)
                        .order_by(EegCapture.seq_num)
                        .all()
                    )
                    ok = asyncio.run(sync_captures_to_firebase(sess, captures))
                    if ok:
                        log.status   = "synced"
                        log.synced_at = datetime.now(timezone.utc)
                        log.last_error = None
                    else:
                        log.status = "failed"
                        log.retry_count += 1
                        # 指數退避：1 分、2 分、4 分、8 分、16 分
                        backoff_min = 2 ** log.retry_count
                        from datetime import timedelta
                        log.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=backoff_min)
                        log.last_error = "sync returned False"
                    db.commit()
                except Exception as e:
                    log.status = "failed"
                    log.retry_count += 1
                    log.last_error = str(e)[:500]
                    db.commit()
                    logger.warning("[Firebase] 排程同步 session %s 失敗: %s", log.session_id, e)
        finally:
            db.close()
    except Exception as e:
        logger.exception("[Firebase] run_pending_syncs 例外: %s", e)
