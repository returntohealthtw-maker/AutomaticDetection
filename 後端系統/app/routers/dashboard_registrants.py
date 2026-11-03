"""
總後台儀表板專用：顧問帳號（註冊者）與使用狀況。

GET /api/v1/dashboard/registrants
  驗證：header  X-Dashboard-Key  必須等於環境變數 DASHBOARD_API_KEY（未設定時一律拒絕）。
  回傳：所有顧問帳號 + 尚未建立帳號的待審核申請（contact_requests.status = pending）。
  不含密碼雜湊、初始密碼。

POST /api/v1/dashboard/registrants/{id}/profile
  修改顧問帳號／待審核申請的個人資料（姓名、手機、Email、單位類型、單位）。同一個 X-Dashboard-Key 驗證。
"""
import hmac
import os
import re
import unicodedata
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
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


# ── 修改註冊者個人資料（總後台儀表板用）──────────────────────────────────────
class ProfileUpdate(BaseModel):
    """只更新有帶的欄位。display_name 對應顧問姓名；org_type／org 為單位類型與單位名稱。"""
    display_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    org_type: Optional[str] = None
    org: Optional[str] = None


_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


def _clean(value, limit: int) -> str:
    s = unicodedata.normalize("NFKC", str(value if value is not None else ""))
    s = re.sub(r"[\x00-\x1f\x7f<>]", "", s)
    return re.sub(r"\s+", " ", s).strip()[:limit]


def _validate_profile(body: ProfileUpdate, *, email_required: bool) -> dict:
    """回傳整理後的欄位（只含有帶的）；格式不對丟 400。"""
    out = {}
    given = body.model_dump(exclude_unset=True) if hasattr(body, "model_dump") else body.dict(exclude_unset=True)
    for k, v in given.items():
        if k == "display_name":
            s = _clean(v, 50)
            if not s:
                raise HTTPException(status_code=400, detail="姓名不能空白")
        elif k == "phone":
            s = re.sub(r"[\s\-]", "", _clean(v, 30))
            if not re.fullmatch(r"\d{8,15}", s):
                raise HTTPException(status_code=400, detail="手機號碼只能是 8～15 位數字")
        elif k == "email":
            s = _clean(v, 120).lower()
            if (s or email_required) and not _EMAIL_RE.match(s):
                raise HTTPException(status_code=400, detail="Email 格式不正確")
        elif k == "org_type":
            s = _clean(v, 50)
        else:  # org
            s = _clean(v, 100)
        out[k] = s
    if not out:
        raise HTTPException(status_code=400, detail="沒有要修改的欄位")
    return out


@router.post("/registrants/{registrant_id}/profile")
def update_registrant_profile(
    registrant_id: str,
    body: ProfileUpdate,
    x_dashboard_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """修改顧問帳號（registrant_id 為數字）或尚未核准的申請（registrant_id 為 REQ 開頭）的個人資料。

    顧問姓名改變時，同步更新 sessions.consultant_name：系統是用「姓名」把檢測紀錄對回顧問的
    （顧問只能看自己的檢測、報告），不同步的話改名後會看不到過去的紀錄。
    """
    _check_key(x_dashboard_key)

    if registrant_id.isdigit():
        c = db.query(M.Consultant).filter(M.Consultant.consultant_id == int(registrant_id)).first()
        if not c:
            raise HTTPException(status_code=404, detail="找不到顧問帳號")
        fields = _validate_profile(body, email_required=False)
        if "phone" in fields and fields["phone"] != c.phone:
            dup = db.query(M.Consultant).filter(
                M.Consultant.phone == fields["phone"], M.Consultant.consultant_id != c.consultant_id).first()
            if dup:
                raise HTTPException(status_code=409, detail="此手機號碼已被其他顧問帳號使用")
        changed = []
        old_name = c.name
        for key, attr in (("display_name", "name"), ("phone", "phone"), ("email", "email"),
                          ("org_type", "org_type"), ("org", "org")):
            if key in fields and (getattr(c, attr) or "") != fields[key]:
                setattr(c, attr, fields[key] if (fields[key] or attr in ("name", "phone")) else None)
                changed.append(key)
        if "display_name" in changed and old_name:
            db.query(M.Session).filter(M.Session.consultant_name == old_name).update(
                {M.Session.consultant_name: c.name}, synchronize_session=False)
        db.commit()
        return {"ok": True, "changed": changed}

    r = db.query(M.ContactRequest).filter(M.ContactRequest.id == registrant_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="找不到註冊者")
    fields = _validate_profile(body, email_required=True)
    changed = []
    for key, attr in (("display_name", "name"), ("phone", "phone"), ("email", "email"),
                      ("org_type", "org_type"), ("org", "org")):
        if key in fields and (getattr(r, attr) or "") != fields[key]:
            setattr(r, attr, fields[key])
            changed.append(key)
    db.commit()
    return {"ok": True, "changed": changed}
