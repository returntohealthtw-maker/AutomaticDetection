"""
受測者主檔 CRUD

權限規則：
  - 一般 consultant：只能 CRUD 自己 consultant_id 的受測者
  - admin：可看 / 改 / 刪所有受測者（含舊資料 consultant_id 為 NULL 的）

API：
  GET    /api/v1/subjects             列出（依登入身份過濾）
  GET    /api/v1/subjects?q=陳         模糊搜尋
  POST   /api/v1/subjects             新增（自動寫入 consultant_id）
  GET    /api/v1/subjects/{id}
  PUT    /api/v1/subjects/{id}
  DELETE /api/v1/subjects/{id}
"""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core import models as M
from app.core.database import get_db
from app.routers.auth import require_user

router = APIRouter(prefix="/api/v1/subjects", tags=["受測者"])


# ─── Pydantic 模型 ────────────────────────────────────────────────────────────

class SubjectIn(BaseModel):
    name: str
    birth_date: str
    gender: str
    occupation: Optional[str] = ""
    email: str
    phone: str
    medical_history: Optional[str] = ""
    medications: Optional[str] = ""


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _serialize(s: M.Subject) -> dict:
    return {
        "subject_id":       s.subject_id,
        "consultant_id":    s.consultant_id,
        "name":             s.name,
        "birth_date":       s.birth_date,
        "gender":           s.gender,
        "occupation":       s.occupation or "",
        "email":            s.email,
        "phone":            s.phone,
        "medical_history":  s.medical_history or "",
        "medications":      s.medications or "",
        "created_at":       s.created_at.isoformat() if s.created_at else None,
        "updated_at":       s.updated_at.isoformat() if s.updated_at else None,
    }


def _validate(req: SubjectIn) -> None:
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="姓名必填")
    if not req.birth_date or len(req.birth_date) != 10:
        raise HTTPException(status_code=400, detail="出生日期格式錯誤（須為 YYYY-MM-DD）")
    if req.gender not in ("男", "女", "其他"):
        raise HTTPException(status_code=400, detail="性別僅接受 男 / 女 / 其他")
    if not req.email.strip() or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Email 格式錯誤")
    if not req.phone.strip():
        raise HTTPException(status_code=400, detail="手機必填")


def _can_access(user: M.Consultant, s: M.Subject) -> bool:
    if user.role == "admin":
        return True
    return s.consultant_id == user.consultant_id


# ─── 端點 ────────────────────────────────────────────────────────────────────

@router.get("")
def list_subjects(
    q: Optional[str] = Query(None, description="關鍵字（姓名 / Email / 手機）"),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    user = require_user(authorization, db)

    query = db.query(M.Subject)
    if user.role != "admin":
        # 一般顧問只能看自己建的
        query = query.filter(M.Subject.consultant_id == user.consultant_id)

    if q:
        kw = f"%{q.strip()}%"
        query = query.filter(or_(
            M.Subject.name.like(kw),
            M.Subject.email.like(kw),
            M.Subject.phone.like(kw),
        ))

    rows = query.order_by(M.Subject.subject_id.desc()).all()
    return [_serialize(s) for s in rows]


@router.post("")
def create_subject(
    req: SubjectIn,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    user = require_user(authorization, db)
    _validate(req)

    # 防重複：同顧問下 email+name 相同 → 直接回傳已有的
    existing = (
        db.query(M.Subject)
        .filter(
            M.Subject.email == req.email.strip(),
            M.Subject.name == req.name.strip(),
            M.Subject.consultant_id == user.consultant_id,
        )
        .first()
    )
    if existing:
        return _serialize(existing)

    s = M.Subject(
        consultant_id   = user.consultant_id,
        name            = req.name.strip(),
        birth_date      = req.birth_date,
        gender          = req.gender,
        occupation      = (req.occupation or "").strip(),
        email           = req.email.strip(),
        phone           = req.phone.strip(),
        medical_history = (req.medical_history or "").strip() or None,
        medications     = (req.medications or "").strip() or None,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _serialize(s)


@router.get("/{subject_id}")
def get_subject(
    subject_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    user = require_user(authorization, db)
    s = db.query(M.Subject).filter(M.Subject.subject_id == subject_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="受測者不存在")
    if not _can_access(user, s):
        raise HTTPException(status_code=403, detail="無權限存取此受測者")
    return _serialize(s)


@router.put("/{subject_id}")
def update_subject(
    subject_id: int,
    req: SubjectIn,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    user = require_user(authorization, db)
    _validate(req)

    s = db.query(M.Subject).filter(M.Subject.subject_id == subject_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="受測者不存在")
    if not _can_access(user, s):
        raise HTTPException(status_code=403, detail="僅能修改自己建立的受測者")

    s.name            = req.name.strip()
    s.birth_date      = req.birth_date
    s.gender          = req.gender
    s.occupation      = (req.occupation or "").strip()
    s.email           = req.email.strip()
    s.phone           = req.phone.strip()
    s.medical_history = (req.medical_history or "").strip() or None
    s.medications     = (req.medications or "").strip() or None

    db.commit()
    db.refresh(s)
    return _serialize(s)


@router.delete("/{subject_id}")
def delete_subject(
    subject_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    user = require_user(authorization, db)
    s = db.query(M.Subject).filter(M.Subject.subject_id == subject_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="受測者不存在")
    if not _can_access(user, s):
        raise HTTPException(status_code=403, detail="僅能刪除自己建立的受測者")
    db.delete(s)
    db.commit()
    return {"ok": True}
