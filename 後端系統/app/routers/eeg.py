"""
腦波檢測：採集完成後寫入 DB
- 一次採集 = 1 個 Session (sessions table)
- 統計值寫入 1 筆 EegCapture（seq_num=0，平均統計），有 raw_arrays 時同步展開為逐秒 N 筆
- 原始 180 筆陣列（raw_arrays）同步雙寫到 PostgreSQL（逐秒 EegCapture）及 Firebase
"""
from typing import Optional
import asyncio
import time

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import logging

from app.core import models as M
from app.core.database import get_db
from app.routers.auth import require_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/eeg", tags=["腦波檢測"])


# ─── Pydantic ────────────────────────────────────────────────────────────────

class EegStatsIn(BaseModel):
    # 受測者基本資料（必填）
    subject_name:     str
    subject_birthday: str = ""          # YYYY-MM-DD
    subject_gender:   str = ""
    subject_age:      Optional[int] = None
    subject_id:       Optional[int] = None  # 若已存在 subjects table

    # 報告分類
    report_type:      str = "adult"     # adult / child
    order_id:         Optional[str] = None
    paid_amount:      Optional[int] = None

    # 採集摘要
    sample_count:           int = 0
    attention_percentage:   int = 0     # 0-100
    meditation_percentage:  int = 0

    # 頻帶平均值（支援兩種格式，均可選填）
    #
    # 格式 A — 5-band 合併（舊版相容）：
    #   { delta, theta, alpha, beta, gamma }
    #   → high_alpha = low_alpha = alpha（無法區分 High/Low）
    #
    # 格式 B — 8-band 完整（ThinkGear 原始輸出，推薦）：
    #   { delta, theta, low_alpha, high_alpha,
    #                   low_beta,  high_beta,
    #                   low_gamma, high_gamma }
    #   → High / Low 儲存各自的真實值
    #
    # 兩種格式可混用：未提供個別 high/low 的頻帶自動退回合併值。
    bands_avg: dict = Field(default_factory=dict)

    # 原始逐秒陣列（可選，約 180 筆/次）
    # 用途：Firebase 腦波資料庫同步 & 未來 MBTI 時間窗重新分析
    # 格式：{ attn, medi, r_delta, r_theta, r_lalpha, r_halpha,
    #         r_lbeta, r_hbeta, r_lgamma, r_hgamma }
    raw_arrays: Optional[dict] = None


class EegStatsOut(BaseModel):
    ok: bool
    session_id: int
    capture_id: int
    msg: str = ""
    firebase_sync_ok: bool = False
    firebase_session_id: Optional[str] = None
    captures_saved: int = 1


# ─── 端點 ─────────────────────────────────────────────────────────────────────

@router.post("/save-stats", response_model=EegStatsOut)
def save_eeg_stats(
    payload: EegStatsIn,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    採集完成後由前端 / APK 呼叫，把統計值寫入 DB
    回傳 session_id，可給後續報告生成關聯使用
    """
    user = require_user(authorization, db)

    # ── 後端品質門檻：拒絕無效腦波數據 ──────────────────────────────────────
    att = int(payload.attention_percentage or 0)
    med = int(payload.meditation_percentage or 0)
    bands_check = payload.bands_avg or {}
    bands_total = sum(int(v or 0) for v in bands_check.values()) if bands_check else 0

    if att == 0 and med == 0 and bands_total == 0:
        raise HTTPException(
            status_code=422,
            detail="腦波數值全為零，拒絕存入（電極未接觸或腦波儀未連線）"
        )
    if att <= 5 and med <= 5:
        raise HTTPException(
            status_code=422,
            detail=f"腦波品質不足（專注={att}、放鬆={med}），電極接觸極差，請重新配戴後重測"
        )
    # ─────────────────────────────────────────────────────────────────────────

    bands = payload.bands_avg or {}
    now_ts = int(time.time())

    # ── BrainDNA 算法：若有 raw_arrays，用佔比算法覆寫頻段值（最高精度）──────────
    import logging as _logging
    _bdna_log = _logging.getLogger("braindna")
    _bdna_result = None   # 儲存完整結果，稍後寫入 Session 欄位
    _bdna_mode = "fallback_no_raw"   # 預設：未提供 raw_arrays

    if payload.raw_arrays:
        # 確認 raw_arrays 資料量
        _arr_len = len(list(payload.raw_arrays.values())[0]) if payload.raw_arrays else 0
        _bdna_log.info(f"[BrainDNA] raw_arrays 收到，樣本數={_arr_len}")
        try:
            from app.services.braindna_algorithms import compute_all as _bdna_compute
            _is_child = (getattr(payload, "report_type", None) or "").lower() in ("child", "child_report") \
                        or (getattr(payload, "report_type", None) or "").lower().startswith("child_")
            _bdna_result = _bdna_compute(payload.raw_arrays, is_child=_is_child)
            _input_scale = _bdna_result.get("input_scale", "unknown")
            _bdna_log.info(f"[BrainDNA] 執行完成：valid={_bdna_result.get('valid')}, input_scale={_input_scale}, bands={_bdna_result.get('bands')}")

            if _bdna_result.get("valid") and _bdna_result.get("bands"):
                _b = _bdna_result["bands"]
                # 用 BrainDNA 佔比值覆寫，確保 High ≠ Low，與原始算法一致
                bands = dict(bands)  # 不改動原始物件
                for _k in ("delta", "theta", "low_alpha", "high_alpha",
                           "low_beta", "high_beta", "low_gamma", "high_gamma"):
                    if _b.get(_k) is not None:
                        bands[_k] = _b[_k]
                # alpha/beta/gamma 合併值同步更新
                bands["alpha"] = round((_b.get("low_alpha", 0) + _b.get("high_alpha", 0)) / 2)
                bands["beta"]  = round((_b.get("low_beta",  0) + _b.get("high_beta",  0)) / 2)
                bands["gamma"] = round((_b.get("low_gamma", 0) + _b.get("high_gamma", 0)) / 2)
                # 演算成功：記錄模式（raw=最高精度 / norm100=降級佔比）
                _bdna_mode = f"bdna_{_input_scale}"
            else:
                # 演算失敗：回退前端 bandTo100 平均值
                _bdna_mode = f"fallback_bdna_invalid_{_input_scale}"
                _bdna_log.warning(f"[BrainDNA] 演算失敗(valid=False)，退回前端 bandTo100 平均值。input_scale={_input_scale}")
        except Exception as _bdna_ex:
            _bdna_result = None
            _bdna_mode = "fallback_exception"
            _bdna_log.error(f"[BrainDNA] 算法例外，退回前端 bandTo100 平均值。錯誤：{_bdna_ex}", exc_info=True)
    else:
        _bdna_log.warning("[BrainDNA] 未收到 raw_arrays，使用前端 bandTo100 平均值（最低精度）")

    # 🔑 受測者 FK 解析（核心修正：避免報告變孤兒）
    # 1. 優先用前端傳來的 subject_id
    # 2. 若沒帶，依 (consultant_id + name + birth_date) 比對既存 Subject 記錄
    # 3. 仍找不到就 NULL（admin 可在「報告管理」事後手動關聯）
    resolved_subject_id = payload.subject_id
    if resolved_subject_id is None and payload.subject_name:
        try:
            q = db.query(M.Subject).filter(M.Subject.name == payload.subject_name)
            if user.role != "admin":
                q = q.filter(M.Subject.consultant_id == user.consultant_id)
            if payload.subject_birthday:
                q = q.filter(M.Subject.birth_date == payload.subject_birthday)
            cand = q.order_by(M.Subject.subject_id.desc()).first()
            if cand:
                resolved_subject_id = cand.subject_id
        except Exception:
            resolved_subject_id = None

    # 1. 建一個 Session（同時寫入 subject_id FK）
    sess = M.Session(
        consultant_name = user.name,
        subject_id      = resolved_subject_id,           # ← 新增 FK
        subject_name    = payload.subject_name,
        subject_birthday= payload.subject_birthday,
        subject_gender  = payload.subject_gender,
        subject_age     = payload.subject_age or 0,
        report_type     = payload.report_type,
        start_time      = now_ts,
        end_time        = now_ts,
        total_captures  = int(payload.sample_count or 0),
        status          = 1,  # 1=成功
        created_at      = now_ts,
        bdna_mode       = _bdna_mode,  # 記錄演算來源（bdna_raw / bdna_norm100 / fallback_*）
    )
    db.add(sess)
    db.flush()  # 拿到 session_id

    # 2. 寫一筆 EegCapture 當「平均統計」（seq_num=0）
    def _i(v):
        try:
            return int(v or 0)
        except Exception:
            return 0

    # 支援 8-band 格式：優先取個別 low_*/high_*，無則退回合併值（兩者相同）
    def _lo(band_key):
        """取 low_{band} 值；若無則用合併的 {band} 值"""
        lo = bands.get(f"low_{band_key}")
        return _i(lo if lo is not None else bands.get(band_key))

    def _hi(band_key):
        """取 high_{band} 值；若無則用合併的 {band} 值"""
        hi = bands.get(f"high_{band_key}")
        return _i(hi if hi is not None else bands.get(band_key))

    # BrainDNA 算術平均 MBTI 欄位（前端提供時儲存，否則 NULL）
    def _mbti_v(key):
        v = bands.get(key)
        return _i(v) if v is not None else None

    cap = M.EegCapture(
        session_id   = sess.session_id,
        seq_num      = 0,
        is_baseline  = 0,
        captured_at  = now_ts,
        good_signal  = 0,
        attention    = _i(payload.attention_percentage),
        meditation   = _i(payload.meditation_percentage),
        delta        = _i(bands.get("delta")),
        theta        = _i(bands.get("theta")),
        low_alpha    = _lo("alpha"),
        high_alpha   = _hi("alpha"),
        low_beta     = _lo("beta"),
        high_beta    = _hi("beta"),
        low_gamma    = _lo("gamma"),
        high_gamma   = _hi("gamma"),
        feedback     = 0,
        mbti_la      = _mbti_v("mbti_la"),
        mbti_theta   = _mbti_v("mbti_theta"),
    )
    db.add(cap)

    # ── BrainDNA 計算結果寫入 Session（與 Firebase 欄位格式完全一致）────────────
    if _bdna_result and _bdna_result.get("valid"):
        try:
            sess.mind_stress   = _bdna_result.get("stress")
            sess.mind_balance  = _bdna_result.get("balance")
            sess.mind_energy   = _bdna_result.get("energy")
            sess.mind_color    = _bdna_result.get("color")
            sess.overall_score = _bdna_result.get("overall_score")
            # MBTI / bagua：從 algorithms/report.py 快速推算
            try:
                from app.algorithms.report import generate_quick_mbti as _qmbti
                from app.services.braindna_algorithms import (
                    _select_best_window as _sbw,
                    MIN_DELTA_QUALITY as _MDQ,
                    _detect_input_scale as _scale_detect,
                )
                _mbti_scale = _bdna_result.get("input_scale", "raw")
                _mbti_cap = {k: 100 for k in ["r_delta","r_theta","r_lalpha","r_halpha","r_lbeta","r_hbeta","r_lgamma","r_hgamma"]} \
                            if _mbti_scale == "norm100" else None
                bw = _sbw(payload.raw_arrays, cap=_mbti_cap)
                import statistics as _stat
                _bw_delta = bw.get("r_delta") or []
                def _mean_raw(key):
                    arr = bw.get(key) or []
                    if _mbti_scale == "raw":
                        # raw 模式：排除 delta<MIN_DELTA_QUALITY 的低品質秒
                        valid = [v for j, v in enumerate(arr)
                                 if j < len(_bw_delta) and _bw_delta[j] >= _MDQ and v > 0]
                    else:
                        # norm100 模式：不套用 delta 品質過濾，直接取所有非零秒
                        valid = [v for v in arr if v > 0]
                    return _stat.mean(valid) if valid else (_stat.mean([v for v in arr if v > 0]) if arr else 0.0)
                mbti_result = _qmbti({
                    "lowAlpha":  _mean_raw("r_lalpha"),
                    "highAlpha": _mean_raw("r_halpha"),
                    "lowBeta":   _mean_raw("r_lbeta"),
                    "highBeta":  _mean_raw("r_hbeta"),
                    "lowGamma":  _mean_raw("r_lgamma"),
                    "midGamma":  _mean_raw("r_hgamma"),
                    "theta":     _mean_raw("r_theta"),
                    "delta":     _mean_raw("r_delta"),
                })
                sess.mbti  = mbti_result.get("mbti")
                sess.bagua = mbti_result.get("bagua")
            except Exception:
                pass
        except Exception:
            pass

    # ── 展開 raw_arrays 為逐秒 EegCapture 並存入 PostgreSQL ────────────────────
    _per_sec_saved = 1  # 至少包含 seq_num=0 的平均統計筆
    if payload.raw_arrays:
        import json as _json
        try:
            sess.raw_arrays_json = _json.dumps(payload.raw_arrays, ensure_ascii=False)
        except Exception:
            pass

        try:
            _ra = payload.raw_arrays
            _r_attn   = _ra.get("r_attn")   or _ra.get("attn")   or []
            _r_medi   = _ra.get("r_medi")   or _ra.get("medi")   or []
            _r_delta  = _ra.get("r_delta")  or []
            _r_theta  = _ra.get("r_theta")  or []
            _r_lalpha = _ra.get("r_lalpha") or []
            _r_halpha = _ra.get("r_halpha") or []
            _r_lbeta  = _ra.get("r_lbeta")  or []
            _r_hbeta  = _ra.get("r_hbeta")  or []
            _r_lgamma = _ra.get("r_lgamma") or []
            _r_hgamma = _ra.get("r_hgamma") or []
            _n = max(len(_r_delta), len(_r_theta), len(_r_lalpha))
            if _n > 1:
                def _gv(arr, i):
                    try: return int(arr[i] or 0)
                    except IndexError: return 0
                per_sec_caps = [
                    M.EegCapture(
                        session_id  = sess.session_id,
                        seq_num     = idx + 1,  # 逐秒從 1 開始，0 留給平均統計
                        is_baseline = 0,
                        captured_at = now_ts - (_n - idx),
                        good_signal = 0,
                        attention   = _gv(_r_attn,   idx),
                        meditation  = _gv(_r_medi,   idx),
                        delta       = _gv(_r_delta,  idx),
                        theta       = _gv(_r_theta,  idx),
                        low_alpha   = _gv(_r_lalpha, idx),
                        high_alpha  = _gv(_r_halpha, idx),
                        low_beta    = _gv(_r_lbeta,  idx),
                        high_beta   = _gv(_r_hbeta,  idx),
                        low_gamma   = _gv(_r_lgamma, idx),
                        high_gamma  = _gv(_r_hgamma, idx),
                        feedback    = 0,
                    )
                    for idx in range(_n)
                ]
                db.bulk_save_objects(per_sec_caps)
                _per_sec_saved = 1 + _n
                logger.info("[EEG] 逐秒 EegCapture 已寫入 %d 筆 (session=%d)", _n, sess.session_id)
        except Exception as _ex:
            logger.warning("[EEG] 展開 raw_arrays 逐秒資料失敗: %s", _ex)

    db.commit()

    # ── qEEG Z-score 演算（在 Firebase sync 前完成，結果一起寫入 Firebase）──────
    _qeeg_result = None
    if payload.raw_arrays:
        try:
            import json as _json2
            from app.services.qeeg_pipeline import run_qeeg_pipeline
            _qeeg_result = run_qeeg_pipeline(
                raw_arrays   = payload.raw_arrays,
                captures     = None,
                subject_info = {
                    "name": payload.subject_name,
                    "age":  payload.subject_age,
                    "sex":  payload.subject_gender or "",
                    "test_condition": "eyes_closed",
                }
            )
            if _qeeg_result:
                try:
                    _s = db.query(M.Session).filter(M.Session.session_id == sess.session_id).first()
                    if _s:
                        _s.qeeg_scores_json = _json2.dumps(_qeeg_result, ensure_ascii=False)
                        db.commit()
                    logger.info("[qEEG] session=%d 計算完成，flags=%s",
                                sess.session_id,
                                [f["flag"] for f in _qeeg_result.get("report_flags", [])])
                except Exception as _dbex:
                    logger.warning("[qEEG] 寫入 DB 失敗: %s", _dbex)
        except Exception as _qex:
            logger.warning("[qEEG] 演算例外 session=%d: %s", sess.session_id, _qex)

    # ── 同步雙寫 Firebase（攜帶 qEEG 摘要）────────────────────────────────────
    _fb_sync_ok = False
    _fb_session_id = None
    if payload.raw_arrays:
        from app.services.firebase_sync import sync_to_firebase
        from datetime import datetime, timezone
        session_start = datetime.fromtimestamp(now_ts, tz=timezone.utc)
        try:
            fb_sid = asyncio.run(sync_to_firebase(
                subject_name    = payload.subject_name,
                session_id      = sess.session_id,
                raw_arrays      = payload.raw_arrays,
                session_start   = session_start,
                braindna_result = _bdna_result,
                qeeg_result     = _qeeg_result,
            ))
            if fb_sid and fb_sid is not False:
                _fb_sync_ok = True
                _fb_session_id = str(fb_sid)
                if not sess.firebase_session_id:
                    sess.firebase_session_id = _fb_session_id
                    db.add(sess)
                    db.commit()
                logger.info("[Firebase] 同步成功 session=%d fb_sid=%s", sess.session_id, fb_sid)
            else:
                logger.warning("[Firebase] sync_to_firebase 回傳失敗 session=%d", sess.session_id)
        except Exception as _fb_ex:
            logger.error("[Firebase] 同步例外 session=%d: %s", sess.session_id, _fb_ex)

    return EegStatsOut(
        ok                  = True,
        session_id          = sess.session_id,
        capture_id          = cap.capture_id,
        msg                 = f"已記錄 {payload.subject_name} 的腦波統計 ({payload.sample_count} 筆，逐秒={_per_sec_saved-1})",
        firebase_sync_ok    = _fb_sync_ok,
        firebase_session_id = _fb_session_id,
        captures_saved      = _per_sec_saved,
    )


@router.get("/sessions/{session_id}/stats")
def get_session_stats(
    session_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    取得指定 Session 的腦波統計值（供「歷史紀錄」點開後填入結果頁用）。
    回傳格式與 _lastEegCapture 相同，前端可直接傳給 _renderResultsFromEeg。
    """
    user = require_user(authorization, db)

    sess = db.query(M.Session).filter(M.Session.session_id == session_id).first()
    if not sess:
        raise HTTPException(404, "Session 不存在")
    # 非 admin 只能看自己的
    if user.role != "admin" and sess.consultant_name != user.name:
        raise HTTPException(403, "無權限查看此 Session")

    caps = db.query(M.EegCapture).filter(
        M.EegCapture.session_id == session_id
    ).order_by(M.EegCapture.seq_num).all()

    if not caps:
        return {
            "ok": True, "session_id": session_id,
            "subject_name": sess.subject_name,
            "subject_age":  sess.subject_age,
            "eeg_stats": None,
        }

    # 平均（排除基線，全部都是基線就全用）
    det = [c for c in caps if c.is_baseline == 0] or list(caps)
    n = len(det)
    def avg(attr): return round(sum(getattr(c, attr, 0) or 0 for c in det) / n)

    lo_alpha = avg("low_alpha")
    hi_alpha = avg("high_alpha")
    lo_beta  = avg("low_beta")
    hi_beta  = avg("high_beta")
    lo_gamma = avg("low_gamma")
    hi_gamma = avg("high_gamma")

    # sample_count 使用 Session.total_captures（真實秒數），
    # 而不是 EegCapture DB 列數（新版 save-stats 只有 1 列）
    sample_count = sess.total_captures or n

    stats = {
        "sample_count":           sample_count,
        "attention_percentage":   avg("attention"),
        "meditation_percentage":  avg("meditation"),
        "bands_avg": {
            "delta":      avg("delta"),
            "theta":      avg("theta"),
            "alpha":      round((lo_alpha + hi_alpha) / 2),
            "beta":       round((lo_beta  + hi_beta)  / 2),
            "gamma":      round((lo_gamma + hi_gamma) / 2),
            # 保留真實 sub-band 欄位，讓下游（headless_renderer、orchestrator）
            # 可直接讀取而不必回退到 ×0.9/×1.1 估算
            "low_alpha":  lo_alpha,
            "high_alpha": hi_alpha,
            "low_beta":   lo_beta,
            "high_beta":  hi_beta,
            "low_gamma":  lo_gamma,
            "high_gamma": hi_gamma,
        },
        # 真實 High / Low（供 admin panel 顯示；若資料來自舊版 5-band 介面則兩值相同）
        "bands_7": {
            "theta":      avg("theta"),
            "alpha_high": hi_alpha,
            "alpha_low":  lo_alpha,
            "beta_high":  hi_beta,
            "beta_low":   lo_beta,
            "gamma_high": hi_gamma,
            "gamma_low":  lo_gamma,
        },
    }

    rep = db.query(M.Report).filter(M.Report.session_id == session_id).first()

    return {
        "ok":          True,
        "session_id":  session_id,
        "subject_name": sess.subject_name,
        "subject_age":  sess.subject_age,
        "subject_gender": sess.subject_gender,
        "report_type":  sess.report_type,
        "created_at":   sess.created_at,
        "eeg_stats":    stats,
        "bdna_mode":    getattr(sess, "bdna_mode", None),
        "firebase_session_id": getattr(sess, "firebase_session_id", None),
        "report_status": rep.status if rep else None,
        "report_url":    rep.pdf_url if rep else None,
        "email_sent":    rep.email_sent if rep else 0,
    }


@router.get("/sessions")
def list_my_sessions(
    limit: int = 50,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """列出此顧問所做過的檢測場次（依姓名比對；admin 看全部）

    回傳欄位含 report_status / report_url，供 APP「歷史紀錄」顯示。
    """
    user = require_user(authorization, db)
    q = db.query(M.Session)
    if user.role != "admin":
        q = q.filter(M.Session.consultant_name == user.name)
    rows = q.order_by(M.Session.session_id.desc()).limit(limit).all()

    session_ids = [s.session_id for s in rows]
    report_map = {}
    if session_ids:
        rep_rows = db.query(M.Report).filter(M.Report.session_id.in_(session_ids)).all()
        for r in rep_rows:
            report_map[r.session_id] = r

    out = []
    for s in rows:
        rep = report_map.get(s.session_id)
        out.append({
            "session_id":    s.session_id,
            "consultant":    s.consultant_name,
            "subject_name":  s.subject_name,
            "subject_age":   s.subject_age,
            "subject_gender":s.subject_gender,
            "report_type":   s.report_type,
            "report_audience": s.report_audience,
            "total_captures":s.total_captures,
            "created_at":    s.created_at,
            "status":        s.status,
            "failure_reason":s.failure_reason,
            "bdna_mode":           getattr(s, "bdna_mode", None),
            "firebase_session_id": getattr(s, "firebase_session_id", None),  # Firebase session UUID
            "report_status": (rep.status if rep else None),
            "report_url":    (rep.pdf_url if rep else None),
            "report_variant":(getattr(rep, "variant", None) if rep else None),
        })
    return {"ok": True, "count": len(out), "sessions": out}


@router.get("/admin/compare")
def admin_eeg_compare(
    limit: int = 20,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    【管理員】腦波比對診斷：列出最近 N 筆場次的全部腦波統計，
    方便逐一比較不同受測者的數值，確認是否真實差異。

    回傳欄位：
      session_id, subject_name, age, created_at,
      attention, meditation, delta, theta,
      low_alpha, high_alpha, low_beta, high_beta, low_gamma, high_gamma,
      sample_count
    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "需要管理員權限")

    # 取最近 limit 筆場次（含 EegCapture 統計筆，seq_num=0）
    sessions = (
        db.query(M.Session)
        .order_by(M.Session.session_id.desc())
        .limit(limit)
        .all()
    )
    session_ids = [s.session_id for s in sessions]
    if not session_ids:
        return {"ok": True, "rows": []}

    # 取每個場次的 seq_num=0 統計筆（即 eeg/save-stats 寫入的那筆平均值）
    caps = (
        db.query(M.EegCapture)
        .filter(
            M.EegCapture.session_id.in_(session_ids),
            M.EegCapture.seq_num == 0,
        )
        .all()
    )
    cap_map: dict = {c.session_id: c for c in caps}

    rows = []
    for s in sessions:
        c = cap_map.get(s.session_id)
        rows.append({
            "session_id":   s.session_id,
            "subject_name": s.subject_name,
            "age":          s.subject_age,
            "report_type":  s.report_type,
            "consultant":   s.consultant_name,
            "created_at":   s.created_at,
            "sample_count": s.total_captures,
            "attention":    c.attention    if c else None,
            "meditation":   c.meditation   if c else None,
            "delta":        c.delta        if c else None,
            "theta":        c.theta        if c else None,
            "low_alpha":    c.low_alpha    if c else None,
            "high_alpha":   c.high_alpha   if c else None,
            "low_beta":     c.low_beta     if c else None,
            "high_beta":    c.high_beta    if c else None,
            "low_gamma":    c.low_gamma    if c else None,
            "high_gamma":   c.high_gamma   if c else None,
        })
    return {"ok": True, "count": len(rows), "rows": rows}


@router.get("/admin/firebase-diag")
def admin_firebase_diag(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    【管理員】Firebase 同步診斷：
    確認 FIREBASE_SERVICE_KEY 是否設定，並測試能否連線到 Firebase API。
    """
    import os, httpx, asyncio

    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "需要管理員權限")

    key = os.environ.get("FIREBASE_SERVICE_KEY", "")
    result = {
        "firebase_key_set":    bool(key),
        "firebase_key_prefix": key[:6] + "..." if key else "(未設定)",
        "firebase_api_reachable": False,
        "firebase_api_status":    None,
        "firebase_api_error":     None,
    }

    if key:
        try:
            from app.services.firebase_sync import FIREBASE_API_BASE
            resp = httpx.get(
                f"{FIREBASE_API_BASE}/health",
                headers={"X-Service-Key": key},
                timeout=8.0,
            )
            result["firebase_api_reachable"] = True
            result["firebase_api_status"]    = resp.status_code
        except Exception as e:
            result["firebase_api_error"] = f"{type(e).__name__}: {str(e)[:200]}"

    return result
