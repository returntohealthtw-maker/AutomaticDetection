"""
腦波檢測：採集完成後寫入 DB
- 一次採集 = 1 個 Session (sessions table)
- 統計值寫入 1 筆 EegCapture（seq_num=0），不存原始 sample
"""
from typing import Optional
import time

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core import models as M
from app.core.database import get_db
from app.routers.auth import require_user

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

    # 5 個 band 平均值 (0-100)
    bands_avg: dict = Field(default_factory=dict)
    # { delta, theta, alpha, beta, gamma }


class EegStatsOut(BaseModel):
    ok: bool
    session_id: int
    capture_id: int
    msg: str = ""


# ─── 端點 ─────────────────────────────────────────────────────────────────────

@router.post("/save-stats", response_model=EegStatsOut)
def save_eeg_stats(
    payload: EegStatsIn,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    採集完成後由前端 / APK 呼叫，把統計值寫入 DB
    回傳 session_id，可給後續報告生成關聯使用
    """
    user = require_user(authorization, db)

    bands = payload.bands_avg or {}
    now_ts = int(time.time())

    # 1. 建一個 Session
    sess = M.Session(
        consultant_name = user.name,
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
    )
    db.add(sess)
    db.flush()  # 拿到 session_id

    # 2. 寫一筆 EegCapture 當「平均統計」（seq_num=0）
    def _i(v):
        try:
            return int(v or 0)
        except Exception:
            return 0

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
        # 沒分 low/high 就一律放到 high_*
        low_alpha    = 0,
        high_alpha   = _i(bands.get("alpha")),
        low_beta     = 0,
        high_beta    = _i(bands.get("beta")),
        low_gamma    = 0,
        high_gamma   = _i(bands.get("gamma")),
        feedback     = 0,
    )
    db.add(cap)
    db.commit()

    return EegStatsOut(
        ok         = True,
        session_id = sess.session_id,
        capture_id = cap.capture_id,
        msg        = f"已記錄 {payload.subject_name} 的腦波統計 ({payload.sample_count} 筆)"
    )


@router.get("/sessions")
def list_my_sessions(
    limit: int = 50,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """列出此顧問所做過的檢測場次（依姓名比對；admin 看全部）"""
    user = require_user(authorization, db)
    q = db.query(M.Session)
    if user.role != "admin":
        q = q.filter(M.Session.consultant_name == user.name)
    rows = q.order_by(M.Session.session_id.desc()).limit(limit).all()
    out = []
    for s in rows:
        out.append({
            "session_id":    s.session_id,
            "consultant":    s.consultant_name,
            "subject_name":  s.subject_name,
            "subject_age":   s.subject_age,
            "subject_gender":s.subject_gender,
            "report_type":   s.report_type,
            "total_captures":s.total_captures,
            "created_at":    s.created_at,
            "status":        s.status,
        })
    return {"ok": True, "count": len(out), "sessions": out}
