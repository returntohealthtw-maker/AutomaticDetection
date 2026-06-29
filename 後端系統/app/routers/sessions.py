"""
腦波數據接收 API
Android 手機檢測完成後呼叫此 API 上傳數據
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from sqlalchemy.orm import Session as DbSession
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import time
import uuid

from app.core.database import get_db
from app.core import models
from app.core.config import settings
from app.services.algorithms import compute_averages, compute_all_indices, compute_mbti
from app.services.report_generator import generate_report_async
from app.routers.monitor import broadcast
from app.routers.auth import require_user as get_current_user

router = APIRouter(prefix="/api/v1", tags=["腦波數據"])


# ─── Request / Response 資料模型 ─────────────────────────────────────────────

class CaptureItem(BaseModel):
    """單秒腦波擷取資料"""
    seq_num:     int
    is_baseline: int = 0
    captured_at: int         # Unix timestamp ms
    good_signal: int = 0
    attention:   int = 0
    meditation:  int = 0
    delta:       int = 0
    theta:       int = 0
    low_alpha:   int = 0
    high_alpha:  int = 0
    low_beta:    int = 0
    high_beta:   int = 0
    low_gamma:   int = 0
    high_gamma:  int = 0
    feedback:    int = 0

class UploadSessionRequest(BaseModel):
    """Android 上傳的完整場次資料"""
    consultant_name:  Optional[str] = None   # 執行檢測的顧問姓名
    subject_name:     str = ""
    subject_birthday: str = ""
    subject_gender:   str = "M"
    subject_age:      int = 0
    report_type:      str = "adult"   # adult / child
    report_audience:  str = "student"  # teacher / student（天賦報告範本）
    company_id:       Optional[int] = None
    notify_email:     Optional[str] = None
    line_user_id:     Optional[str] = None   # LINE 使用者 ID（選填）
    start_time:       int = 0
    end_time:         int = 0
    total_captures:   int = 0
    is_success:       bool = True
    failure_reason:   Optional[str] = None
    captures:         List[CaptureItem]

class SessionResponse(BaseModel):
    """上傳成功回應"""
    session_id:  int
    report_id:   int
    message:     str
    captures_saved: int
    client_view_url: Optional[str] = None
    firebase_sync_ok: bool = False
    firebase_session_id: Optional[str] = None


# ─── API 端點 ────────────────────────────────────────────────────────────────

@router.post("/sessions/upload", response_model=SessionResponse)
def upload_session(
    req: UploadSessionRequest,
    background_tasks: BackgroundTasks,
    db: DbSession = Depends(get_db)
):
    """
    【主要 API】Android 檢測完成後上傳全場腦波數據

    流程：
    1. 儲存場次資訊
    2. 儲存所有腦波擷取資料
    3. 觸發背景報告生成任務
    4. 回傳 session_id 和 report_id
    """

    if req.company_id is not None:
        co = (
            db.query(models.Company)
            .filter(
                models.Company.company_id == req.company_id,
                models.Company.is_active == 1,
            )
            .first()
        )
        if not co:
            raise HTTPException(status_code=400, detail="企業無效或未於後端啟用")

    aud = (req.report_audience or "student").lower()
    if aud not in ("teacher", "student"):
        aud = "student"

    # ── 防重複上傳：同一顧問 + 同受測者 + 相近擷取數，15 分鐘內只建一筆 ──
    # 原因：Android App 在網路逾時後可能自動重試，導致同一場測建兩筆 session
    DEDUP_WINDOW_S   = 15 * 60          # 15 分鐘（秒）
    DEDUP_CAPTURE_DELTA = 10            # 擷取數差距容忍值
    now_s = int(time.time())
    if req.subject_name and req.consultant_name and len(req.captures) >= 150:
        cutoff = now_s - DEDUP_WINDOW_S
        existing = (
            db.query(models.Session)
            .filter(
                models.Session.subject_name    == req.subject_name,
                models.Session.consultant_name == req.consultant_name,
                models.Session.created_at      >= cutoff,
                models.Session.status          == 1,   # 成功場次才算
            )
            .order_by(models.Session.session_id.desc())
            .first()
        )
        if existing and abs(existing.total_captures - len(req.captures)) <= DEDUP_CAPTURE_DELTA:
            # 找到重複場次，直接回傳已存在的結果
            rep = db.query(models.Report).filter(
                models.Report.session_id == existing.session_id
            ).first()
            base = (settings.PUBLIC_BASE_URL or "").rstrip("/")
            client_url = (
                f"{base}/api/v1/public/client/{rep.qr_token}" if (base and rep and rep.qr_token) else None
            )
            return SessionResponse(
                session_id       = existing.session_id,
                report_id        = rep.report_id if rep else 0,
                message          = "重複上傳，已回傳既有場次",
                captures_saved   = existing.total_captures,
                client_view_url  = client_url,
            )

    def _to_unix_s(ms_val: int) -> int:
        """Android App 傳來的是毫秒時間戳，PostgreSQL INTEGER 欄位只支援 32-bit (~2.1B)，
        需轉換成秒。若值已是秒（< 1e11）則直接返回。"""
        now_s = int(time.time())
        if not ms_val:
            return now_s
        return ms_val // 1000 if ms_val > 10_000_000_000 else ms_val

    # 1. 建立場次記錄
    session = models.Session(
        consultant_name  = req.consultant_name,
        subject_name     = req.subject_name,
        subject_birthday = req.subject_birthday,
        subject_gender   = req.subject_gender,
        subject_age      = req.subject_age,
        company_id       = req.company_id,
        report_type      = req.report_type,
        report_audience  = aud,
        start_time       = _to_unix_s(req.start_time),
        end_time         = _to_unix_s(req.end_time),
        total_captures   = len(req.captures),
        status           = 1 if req.is_success else 2,
        failure_reason   = req.failure_reason,
        created_at       = int(time.time())
    )
    db.add(session)
    db.flush()  # 取得 session_id

    # 2. 批次儲存腦波擷取資料
    capture_objects = [
        models.EegCapture(
            session_id  = session.session_id,
            seq_num     = c.seq_num,
            is_baseline = c.is_baseline,
            captured_at = c.captured_at,
            good_signal = c.good_signal,
            attention   = c.attention,
            meditation  = c.meditation,
            delta       = c.delta,
            theta       = c.theta,
            low_alpha   = c.low_alpha,
            high_alpha  = c.high_alpha,
            low_beta    = c.low_beta,
            high_beta   = c.high_beta,
            low_gamma   = c.low_gamma,
            high_gamma  = c.high_gamma,
            feedback    = c.feedback
        )
        for c in req.captures
    ]
    db.bulk_save_objects(capture_objects)

    # 3. 建立報告待處理記錄（預先給 qr_token，檢測結束即可顯示 QR）
    qr_token = uuid.uuid4().hex
    notify = (req.notify_email or "").strip() or None
    report = models.Report(
        session_id   = session.session_id,
        status       = "pending",
        line_user_id = req.line_user_id,
        qr_token     = qr_token,
        notify_email = notify,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    import logging as _log
    _logger = _log.getLogger(__name__)

    # 4. qEEG Z-score 演算（在 Firebase sync 前完成，結果一起寫入 Firebase）
    _qeeg_result = None
    if req.is_success and len(req.captures) >= 30:
        try:
            import json as _json
            from app.services.qeeg_pipeline import run_qeeg_pipeline
            _qeeg_result = run_qeeg_pipeline(
                raw_arrays   = None,
                captures     = req.captures,
                subject_info = {
                    "name": req.subject_name,
                    "age":  req.subject_age,
                    "sex":  req.subject_gender or "",
                    "test_condition": "eyes_closed",
                }
            )
            if _qeeg_result:
                _s2 = db.query(models.Session).filter(
                    models.Session.session_id == session.session_id
                ).first()
                if _s2:
                    _s2.qeeg_scores_json = _json.dumps(_qeeg_result, ensure_ascii=False)
                    db.commit()
                _logger.info("[qEEG] Android session=%d 計算完成，flags=%s",
                             session.session_id,
                             [f["flag"] for f in _qeeg_result.get("report_flags", [])])
        except Exception as _qex:
            _logger.warning("[qEEG] Android session=%d 演算例外: %s", session.session_id, _qex)

    # 5. 同步雙寫 Firebase（攜帶 qEEG 摘要）
    _fb_sync_ok = False
    _fb_session_id = None
    try:
        from app.services.firebase_sync import sync_captures_to_firebase
        fb_sid = asyncio.run(sync_captures_to_firebase(
            subject_name = req.subject_name,
            session_id   = session.session_id,
            captures     = req.captures,
            qeeg_result  = _qeeg_result,
        ))
        if fb_sid and fb_sid is not False:
            _fb_sync_ok = True
            _fb_session_id = str(fb_sid)
            if not session.firebase_session_id:
                session.firebase_session_id = _fb_session_id
                db.add(session)
                db.commit()
            _logger.info("[Firebase] Android session %s 同步成功 fb_sid=%s",
                         session.session_id, fb_sid)
            # 完整 qEEG JSON → Firestore qeeg_analysis collection
            if _qeeg_result:
                try:
                    from app.services.firebase_sync import sync_qeeg_analysis_to_firestore
                    asyncio.run(sync_qeeg_analysis_to_firestore(
                        firebase_session_id = _fb_session_id,
                        qeeg_result         = _qeeg_result,
                        railway_session_id  = session.session_id,
                    ))
                except Exception as _qfs_ex:
                    _logger.warning("[qEEG Firestore] Android session=%d 寫入例外: %s",
                                    session.session_id, _qfs_ex)
        else:
            _logger.warning("[Firebase] Android session %s 同步回傳失敗", session.session_id)
    except Exception as _e:
        _logger.exception("[Firebase] Android session %s 同步例外: %s", session.session_id, _e)

    # 6. 廣播到監控儀表板（即時顯示）
    background_tasks.add_task(broadcast, "new_session", {
        "session_id":      session.session_id,
        "report_id":       report.report_id,
        "consultant_name": req.consultant_name,
        "subject_name":    req.subject_name,
        "subject_age":     req.subject_age,
        "report_type":     req.report_type,
        "captures":        len(req.captures),
        "is_success":      req.is_success,
        "status":          "success" if req.is_success else "failed",
    })

    # 7. 背景執行：計算演算法 + 生成 PDF + 傳送 LINE
    if req.is_success and len(req.captures) >= 150:
        background_tasks.add_task(
            generate_report_async,
            report_id  = report.report_id,
            session_id = session.session_id
        )

    base = (settings.PUBLIC_BASE_URL or "").rstrip("/")
    client_url = f"{base}/api/v1/public/client/{qr_token}" if base else None

    return SessionResponse(
        session_id          = session.session_id,
        report_id           = report.report_id,
        message             = "數據已接收，報告生成中",
        captures_saved      = len(req.captures),
        client_view_url     = client_url,
        firebase_sync_ok    = _fb_sync_ok,
        firebase_session_id = _fb_session_id,
    )


@router.get("/sessions-recent")
def get_recent_sessions(limit: int = 50, db: DbSession = Depends(get_db)):
    """取得最近場次（供儀表板初始載入）"""
    sessions = db.query(models.Session).order_by(
        models.Session.session_id.desc()
    ).limit(limit).all()

    result = []
    for s in sessions:
        report = db.query(models.Report).filter(
            models.Report.session_id == s.session_id
        ).first()
        result.append({
            "session_id":      s.session_id,
            "report_id":       report.report_id if report else None,
            "consultant_name": s.consultant_name,
            "subject_name":    s.subject_name,
            "subject_age":     s.subject_age,
            "report_type":     s.report_type,
            "captures":        s.total_captures,
            "is_success":      s.status == 1,
            "created_at":      s.created_at,
        })
    return result


@router.get("/sessions/{session_id}")
def get_session(session_id: int, db: DbSession = Depends(get_db)):
    """查詢場次資訊"""
    session = db.query(models.Session).filter(
        models.Session.session_id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="場次不存在")
    return session


@router.get("/sessions/{session_id}/captures")
def get_session_captures(session_id: int, db: DbSession = Depends(get_db)):
    """取得場次所有逐秒腦波擷取資料（供 Firebase 同步等用途）"""
    session = db.query(models.Session).filter(
        models.Session.session_id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="場次不存在")

    caps = (
        db.query(models.EegCapture)
        .filter(models.EegCapture.session_id == session_id)
        .order_by(models.EegCapture.seq_num)
        .all()
    )
    return {
        "session_id":  session_id,
        "total":       len(caps),
        "captures": [
            {
                "seq_num":     c.seq_num,
                "is_baseline": c.is_baseline,
                "captured_at": c.captured_at,
                "good_signal": c.good_signal,
                "attention":   c.attention,
                "meditation":  c.meditation,
                "delta":       c.delta,
                "theta":       c.theta,
                "low_alpha":   c.low_alpha,
                "high_alpha":  c.high_alpha,
                "low_beta":    c.low_beta,
                "high_beta":   c.high_beta,
                "low_gamma":   c.low_gamma,
                "high_gamma":  c.high_gamma,
                "feedback":    c.feedback,
            }
            for c in caps
        ],
    }


@router.get("/reports/{report_id}/status")
def get_report_status(report_id: int, db: DbSession = Depends(get_db)):
    """查詢報告生成狀態（Android 可輪詢）"""
    report = db.query(models.Report).filter(
        models.Report.report_id == report_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="報告不存在")
    base = (settings.PUBLIC_BASE_URL or "").rstrip("/")
    client_url = (
        f"{base}/api/v1/public/client/{report.qr_token}"
        if base and report.qr_token
        else None
    )
    return {
        "report_id":       report.report_id,
        "status":          report.status,
        "pdf_url":         report.pdf_url,
        "line_sent":       report.line_sent,
        "client_view_url": client_url,
    }


# ─── Admin 管理端點 ──────────────────────────────────────────────────────────

@router.delete("/admin/sessions/{session_id}")
def admin_delete_session(
    session_id: int,
    authorization: Optional[str] = Header(None),
    db: DbSession = Depends(get_db),
):
    """
    [Admin] 刪除場次及其所有腦波擷取資料、報告記錄。
    只允許 admin 或顧問刪除無報告 / 失敗的重複場次。
    """
    user = get_current_user(authorization, db)
    if not user:
        raise HTTPException(status_code=401, detail="未登入")

    sess = db.query(models.Session).filter(
        models.Session.session_id == session_id
    ).first()
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session #{session_id} 不存在")

    # 非 admin 只能刪除自己負責的場次
    if user.role != "admin" and sess.consultant_name != user.name:
        raise HTTPException(status_code=403, detail="無權刪除此場次")

    # 檢查是否有已完成的報告（有 PDF 的不允許刪除，避免誤操作）
    report = db.query(models.Report).filter(
        models.Report.session_id == session_id
    ).first()
    if report and report.status == "completed" and report.pdf_url:
        raise HTTPException(
            status_code=409,
            detail=f"Session #{session_id} 已有完成的報告，請先至報告管理刪除報告"
        )

    report_id = report.report_id if report else None
    # 刪除 report（如果有）
    if report:
        db.delete(report)
    # EegCapture 有 cascade delete，刪 session 時自動刪
    db.delete(sess)
    db.commit()

    return {
        "ok": True,
        "deleted_session_id": session_id,
        "deleted_report_id":  report_id,
        "message": f"Session #{session_id} 及其腦波資料已刪除",
    }


@router.post("/admin/payments/{payment_id}/link-session")
def admin_link_payment_session(
    payment_id: int,
    session_id: int,
    authorization: Optional[str] = Header(None),
    db: DbSession = Depends(get_db),
):
    """
    [Admin] 手動將付款記錄關聯到指定場次（修正付款-場次斷鏈問題）。
    """
    user = get_current_user(authorization, db)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="需要 admin 權限")

    pay = db.query(models.Payment).filter(
        models.Payment.payment_id == payment_id
    ).first() if hasattr(models, "Payment") else None

    if pay is None:
        # Try via raw query
        from sqlalchemy import text
        result = db.execute(
            text("UPDATE payments SET session_id=:sid WHERE payment_id=:pid"),
            {"sid": session_id, "pid": payment_id}
        )
        db.commit()
        return {"ok": True, "payment_id": payment_id, "session_id": session_id,
                "rows_updated": result.rowcount}

    pay.session_id = session_id
    db.commit()
    return {"ok": True, "payment_id": payment_id, "session_id": session_id}
