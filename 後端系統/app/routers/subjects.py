"""
受測者主檔 CRUD

存 Postgres / SQLite，跨裝置共用。

API：
  GET    /api/v1/subjects             列出所有受測者（最新排在前）
  GET    /api/v1/subjects?q=陳         依姓名 / Email / 手機 模糊搜尋
  POST   /api/v1/subjects             新增（若 email+name 重複則回傳已有的）
  GET    /api/v1/subjects/{id}        單筆
  PUT    /api/v1/subjects/{id}        更新
  DELETE /api/v1/subjects/{id}        刪除
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core import models as M

router = APIRouter(prefix="/api/v1/subjects", tags=["受測者"])


# ─── Pydantic 模型 ────────────────────────────────────────────────────────────

class SubjectIn(BaseModel):
    name: str
    birth_date: str                # YYYY-MM-DD
    gender: str                    # 男 / 女 / 其他
    occupation: Optional[str] = ""
    email: str
    phone: str
    medical_history: Optional[str] = ""
    medications: Optional[str] = ""


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _serialize(s: M.Subject) -> dict:
    return {
        "subject_id":       s.subject_id,
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


# ─── 端點 ────────────────────────────────────────────────────────────────────

@router.get("")
def list_subjects(
    q: Optional[str] = Query(None, description="關鍵字（姓名 / Email / 手機）"),
    db: Session = Depends(get_db),
):
    query = db.query(M.Subject)
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
def create_subject(req: SubjectIn, db: Session = Depends(get_db)):
    _validate(req)

    # 防重複：相同 email + name → 直接回傳已有的（避免前端按多次造成多筆）
    existing = db.query(M.Subject).filter(
        M.Subject.email == req.email.strip(),
        M.Subject.name == req.name.strip(),
    ).first()
    if existing:
        return _serialize(existing)

    s = M.Subject(
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
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    s = db.query(M.Subject).filter(M.Subject.subject_id == subject_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="受測者不存在")
    return _serialize(s)


@router.put("/{subject_id}")
def update_subject(subject_id: int, req: SubjectIn, db: Session = Depends(get_db)):
    _validate(req)
    s = db.query(M.Subject).filter(M.Subject.subject_id == subject_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="受測者不存在")

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
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    s = db.query(M.Subject).filter(M.Subject.subject_id == subject_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="受測者不存在")
    db.delete(s)
    db.commit()
    return {"ok": True}
