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
        # 沒分 low/high 就同時存入 low_* 與 high_*（讓 _session_to_brainwave_data 平均後不會減半）
        low_alpha    = _i(bands.get("alpha")),
        high_alpha   = _i(bands.get("alpha")),
        low_beta     = _i(bands.get("beta")),
        high_beta    = _i(bands.get("beta")),
        low_gamma    = _i(bands.get("gamma")),
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

    stats = {
        "sample_count":           n,
        "attention_percentage":   avg("attention"),
        "meditation_percentage":  avg("meditation"),
        "bands_avg": {
            "delta": avg("delta"),
            "theta": avg("theta"),
            "alpha": round((avg("low_alpha") + avg("high_alpha")) / 2),
            "beta":  round((avg("low_beta")  + avg("high_beta"))  / 2),
            "gamma": round((avg("low_gamma") + avg("high_gamma")) / 2),
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
            "report_status": (rep.status if rep else None),
            "report_url":    (rep.pdf_url if rep else None),
            "report_variant":(getattr(rep, "variant", None) if rep else None),
        })
    return {"ok": True, "count": len(out), "sessions": out}
