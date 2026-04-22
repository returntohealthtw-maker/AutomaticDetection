"""
企業／機構名稱：前端下拉只顯示 is_active=1；
新增／啟用請走管理 API（需 ADMIN_SECRET）。
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from app.core.database import get_db
from app.core import models
from app.core.config import settings

router = APIRouter(prefix="/api/v1", tags=["企業名單"])


class CompanyItem(BaseModel):
    company_id: int
    name: str


class CompanyCreate(BaseModel):
    name: str
    admin_secret: str
    is_active: int = 1


def _check_admin(secret: str):
    if not settings.ADMIN_SECRET or secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="管理授權失敗")


@router.get("/companies", response_model=List[CompanyItem])
def list_active_companies(db: DbSession = Depends(get_db)):
    """顧問 App 下拉：僅回傳已啟用的企業"""
    rows = (
        db.query(models.Company)
        .filter(models.Company.is_active == 1)
        .order_by(models.Company.name)
        .all()
    )
    return [CompanyItem(company_id=r.company_id, name=r.name) for r in rows]


@router.post("/admin/companies", response_model=CompanyItem)
def admin_create_company(body: CompanyCreate, db: DbSession = Depends(get_db)):
    """後端管理：新增企業並可設定啟用（未在清單的機構由此開啟）"""
    _check_admin(body.admin_secret)
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name 不可為空")
    import time
    c = models.Company(name=name, is_active=body.is_active, created_at=int(time.time() * 1000))
    db.add(c)
    db.commit()
    db.refresh(c)
    return CompanyItem(company_id=c.company_id, name=c.name)


class CompanyToggle(BaseModel):
    company_id: int
    is_active: int
    admin_secret: str


@router.patch("/admin/companies/toggle", response_model=CompanyItem)
def admin_toggle_company(body: CompanyToggle, db: DbSession = Depends(get_db)):
    _check_admin(body.admin_secret)
    c = db.query(models.Company).filter(models.Company.company_id == body.company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="找不到企業")
    c.is_active = 1 if body.is_active else 0
    db.commit()
    db.refresh(c)
    return CompanyItem(company_id=c.company_id, name=c.name)
