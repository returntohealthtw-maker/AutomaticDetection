"""
總後台儀表板專用：顧問帳號（註冊者）與使用狀況。

GET /api/v1/dashboard/registrants
  驗證：header  X-Dashboard-Key  必須等於環境變數 DASHBOARD_API_KEY（未設定時一律拒絕）。
  回傳：所有顧問帳號 + 尚未建立帳號的待審核申請（contact_requests.status = pending）。
  不含密碼雜湊、初始密碼。
"""
import hmac
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import models as M
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/dashboard", tags=["總後台"])


def _check_key(given: Optional[str]) -> None:
    expected = os.environ.get("DASHBOARD_API_KEY", "")
    if not expected or not hmac.compare_digest((given or "").encode(), expected.encode()):
        raise HTTPException(status_code=403, detail="forbidden")


def _iso(dt) -> Optional[str]:
    return dt.isoformat() if isinstance(dt, datetime) else (str(dt) if dt else None)


def _epoch_iso(v) -> Optional[str]:
    try:
        return datetime.utcfromtimestamp(int(v)).isoformat() + "Z" if v else None
    except Exception:
        return None


@router.get("/registrants")
def registrants(x_dashboard_key: Optional[str] = Header(None), db: Session = Depends(get_db)):
    _check_key(x_dashboard_key)

    consultants = db.query(M.Consultant).order_by(M.Consultant.consultant_id.desc()).all()

    # 使用狀況：各顧問建立的受測者數、執行過的檢測場次數與最近一次
    subj_cnt = dict(
        db.query(M.Subject.consultant_id, func.count(M.Subject.subject_id))
        .group_by(M.Subject.consultant_id).all()
    )
    sess_rows = (
        db.query(M.Session.consultant_name, func.count(M.Session.session_id), func.max(M.Session.created_at))
        .group_by(M.Session.consultant_name).all()
    )
    sess_by_name = {n: (c, last) for n, c, last in sess_rows if n}

    out = []
    for c in consultants:
        n_sess, last_sess = sess_by_name.get(c.name, (0, None))
        out.append({
            "user_id": c.consultant_id,
            "phone": c.phone,
            "display_name": c.name,
            "email": c.email or "",
            "subject_name": "",
            "subject_birthday": "",
            "role": c.role or "consultant",
            "org_type": c.org_type or "",
            "org": c.org or "",
            "status": "approved" if int(c.is_active or 0) == 1 else "disabled",
            "is_active": int(c.is_active or 0) == 1,
            "created_at": _iso(c.created_at),
            "last_login": None,                      # 此系統不記錄登入時間
            "analysis_count": int(n_sess or 0),      # 執行過的檢測場次
            "last_analysis_at": _epoch_iso(last_sess),
            "contact_count": int(subj_cnt.get(c.consultant_id, 0) or 0),   # 建立的受測者數
            "connection_count": 0, "group_count": 0, "data_request_count": 0, "analysis_rehits": 0,
        })

    # 尚未核准、還沒有顧問帳號的申請
    pend = (
        db.query(M.ContactRequest)
        .filter(M.ContactRequest.status == "pending")
        .order_by(M.ContactRequest.created_at.desc()).all()
    )
    for r in pend:
        out.append({
            "user_id": r.id,
            "phone": r.phone, "display_name": r.name, "email": r.email or "",
            "subject_name": "", "subject_birthday": "",
            "role": "申請中", "org_type": r.org_type or "", "org": r.org or "",
            "status": "pending", "is_active": False,
            "created_at": _iso(r.created_at), "last_login": None,
            "analysis_count": 0, "last_analysis_at": None, "contact_count": 0,
            "connection_count": 0, "group_count": 0, "data_request_count": 0, "analysis_rehits": 0,
        })
    return {"app": "automaticdetection", "count": len(out), "registrants": out}
