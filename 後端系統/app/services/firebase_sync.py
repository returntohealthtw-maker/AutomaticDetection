"""
firebase_sync.py
~~~~~~~~~~~~~~~~
將 ThinkGear 原始腦波陣列（180 筆/次）同步到外部 Firebase 腦波資料庫。

目標 API：
  https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api
  （見 D:/Write program/Database/ToOtherProject/API_INTEGRATION_GUIDE.md）

認證方式：
  X-Service-Key header，對應 Firebase Cloud Functions 的 INTERNAL_SERVICE_KEY
  本服務從環境變數 FIREBASE_SERVICE_KEY 讀取金鑰。

資料轉換：
  ThinkGear raw 值（0 ~ 16,777,215）→ bandTo100 正規化 → 比例（ratio）
  每筆 sample 會計算各頻段占總功率的百分比，寫入 lowAlphaRatio、thetaRatio 等欄位。
"""

import asyncio
import logging
import math
import os
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional

import httpx

logger = logging.getLogger(__name__)

FIREBASE_API_BASE = "https://asia-east1-gen-lang-client-0435688289.cloudfunctions.net/api"
FIREBASE_SERVICE_KEY = os.getenv("FIREBASE_SERVICE_KEY", "")
SOURCE_APP = "BrainReport-LUKE"


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
            "deltaPower":      raw_d  or None,
            "thetaPower":      raw_th or None,
            "alphaPower":      (raw_la + raw_ha) or None,
            "betaPower":       (raw_lb + raw_hb) or None,
            "gammaPower":      (raw_lg + raw_hg) or None,
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


async def sync_to_firebase(
    subject_name: str,
    session_id: int,
    raw_arrays: dict,
    session_start: Optional[datetime] = None,
    braindna_result: Optional[dict] = None,
) -> bool:
    """
    非同步將 180 筆原始腦波資料同步到 Firebase 腦波資料庫。

    流程：
      1. POST /api/sessions → 取得 firebase_session_id
      2. POST /api/eeg/batch（每批最多 100 筆，分批上傳）→ 存入 Firestore + BigQuery
      3. PATCH /api/sessions/{id} → 標記 completed

    返回 True 表示成功，False 表示失敗（不拋例外，避免影響主流程）。
    """
    if not FIREBASE_SERVICE_KEY:
        logger.warning("[Firebase] FIREBASE_SERVICE_KEY 未設定，跳過同步")
        return False

    if not raw_arrays:
        logger.warning("[Firebase] raw_arrays 為空，跳過同步")
        return False

    if session_start is None:
        session_start = datetime.now(timezone.utc)

    headers = {
        "X-Service-Key": FIREBASE_SERVICE_KEY,
        "Content-Type":  "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # ── 1. 建立 Firebase Session ─────────────────────────────────────
            sess_resp = await client.post(
                f"{FIREBASE_API_BASE}/sessions",
                headers=headers,
                json={
                    "sourceApp":    SOURCE_APP,
                    "deviceType":   "ThinkGear",
                    "samplingRate": 1,
                    "platform":     "android",
                    "metadata": {
                        "railway_session_id": session_id,
                        "subject_name":       subject_name,
                    },
                },
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
            # BrainDNA 聚合結果（與 PostgreSQL Session 欄位格式完全一致）
            if braindna_result and braindna_result.get("valid"):
                patch_body.update({
                    "mindStress":   braindna_result.get("stress"),
                    "mindBalance":  braindna_result.get("balance"),
                    "mindEnergy":   braindna_result.get("energy"),
                    "mindColor":    braindna_result.get("color"),
                    "overallScore": braindna_result.get("overall_score"),
                    "mbti":         braindna_result.get("mbti"),
                    "bagua":        braindna_result.get("bagua"),
                })
                patch_body = {k: v for k, v in patch_body.items() if v is not None}
            await client.patch(
                f"{FIREBASE_API_BASE}/sessions/{fb_session_id}",
                headers=headers,
                json=patch_body,
            )

            return True

    except Exception as exc:
        logger.exception("[Firebase] 同步例外: %s", exc)
        return False


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
) -> bool:
    """
    將 Android 上傳路徑（/sessions/upload）的 180 筆 EegCapture 同步到 Firebase。

    captures 中為 ThinkGear bandTo100 值（0~100），直接計算相對比例後上傳。
    回傳 True 表示成功，False 表示失敗（不拋例外）。
    """
    if not FIREBASE_SERVICE_KEY:
        logger.warning("[Firebase] FIREBASE_SERVICE_KEY 未設定，跳過 Android captures 同步")
        return False

    if not captures:
        logger.warning("[Firebase] captures 為空，跳過同步")
        return False

    headers = {
        "X-Service-Key": FIREBASE_SERVICE_KEY,
        "Content-Type":  "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. 建立 Firebase Session
            sess_resp = await client.post(
                f"{FIREBASE_API_BASE}/sessions",
                headers=headers,
                json={
                    "sourceApp":    SOURCE_APP,
                    "deviceType":   "ThinkGear",
                    "samplingRate": 1,
                    "platform":     "android",
                    "metadata": {
                        "railway_session_id": session_id,
                        "subject_name":       subject_name,
                        "data_format":        "bandTo100",
                    },
                },
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

            # 3. 標記 Session completed
            await client.patch(
                f"{FIREBASE_API_BASE}/sessions/{fb_session_id}",
                headers=headers,
                json={
                    "status":   "completed",
                    "endedAt":  datetime.now(timezone.utc).isoformat(),
                    "durationSec": len(features),
                },
            )

            return True

    except Exception as exc:
        logger.exception("[Firebase] Android captures 同步例外: %s", exc)
        return False
