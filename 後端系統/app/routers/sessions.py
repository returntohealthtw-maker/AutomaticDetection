"""
腦波數據接收 API
Android 手機檢測完成後呼叫此 API 上傳數據
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session as DbSession
from pydantic import BaseModel
from typing import List, Optional
import time
import uuid

from app.core.database import get_db
from app.core import models
from app.core.config import settings
from app.services.algorithms import compute_averages, compute_all_indices, compute_mbti
from app.services.report_generator import generate_report_async
from app.routers.monitor import broadcast

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
    client_view_url: Optional[str] = None  # 客戶掃描 QR 開啟的五段摘要頁


# ─── API 端點 ────────────────────────────────────────────────────────────────

@router.post("/sessions/upload", response_model=SessionResponse)
async def upload_session(
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
        start_time       = req.start_time or int(time.time() * 1000),
        end_time         = req.end_time   or int(time.time() * 1000),
        total_captures   = len(req.captures),
        status           = 1 if req.is_success else 2,
        failure_reason   = req.failure_reason,
        created_at       = int(time.time() * 1000)
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

    # 4. 廣播到監控儀表板（即時顯示）
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

    # 5. 背景執行：計算演算法 + 生成 PDF + 傳送 LINE
    if req.is_success and len(req.captures) >= 150:
        background_tasks.add_task(
            generate_report_async,
            report_id  = report.report_id,
            session_id = session.session_id
        )

    base = (settings.PUBLIC_APP_BASE_URL or "").rstrip("/")
    client_url = f"{base}/api/v1/public/client/{qr_token}" if base else None

    return SessionResponse(
        session_id       = session.session_id,
        report_id        = report.report_id,
        message          = "數據已接收，報告生成中",
        captures_saved   = len(req.captures),
        client_view_url  = client_url,
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


@router.get("/reports/{report_id}/status")
def get_report_status(report_id: int, db: DbSession = Depends(get_db)):
    """查詢報告生成狀態（Android 可輪詢）"""
    report = db.query(models.Report).filter(
        models.Report.report_id == report_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="報告不存在")
    base = (settings.PUBLIC_APP_BASE_URL or "").rstrip("/")
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
