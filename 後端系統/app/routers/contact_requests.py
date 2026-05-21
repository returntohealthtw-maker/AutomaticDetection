"""
顧問帳號申請 / 管理員審核

⚠️ 重要：本模組從 v2 開始把資料存進 PostgreSQL `contact_requests` 表，
不再使用 backend/contact_requests.json 本地檔（Railway 重新部署會清空）。

API：
  POST  /api/v1/contact-requests                     新增申請（公開）
  GET   /api/v1/contact-requests                     列出全部
  GET   /api/v1/contact-requests?status=pending      依狀態過濾
  POST  /api/v1/contact-requests/{id}/approved       核准（回傳預設密碼）
  POST  /api/v1/contact-requests/{id}/rejected       拒絕

  POST  /api/v1/contact-requests/_migrate-from-json  [一次性] 把舊 JSON 檔匯入 DB
"""
import os
import json
import time
import secrets
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core import models as M
from app.core.database import get_db
from app.routers.auth import hash_password

router = APIRouter(prefix="/api/v1/contact-requests", tags=["顧問帳號申請"])


# ─── 舊 JSON 檔路徑（僅 migrate-from-json 使用） ─────────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))  # backend/
_LEGACY_JSON = os.path.join(_DATA_DIR, "contact_requests.json")


# ─── 資料模型 ────────────────────────────────────────────────────────────────

class ContactRequestIn(BaseModel):
    id: Optional[str] = None
    name: str
    phone: str
    email: str
    org_type: Optional[str] = ""     # 加盟商 / 直營商 / 工作人員 / 代理商 / 專案人員 / 其他
    org: Optional[str] = ""          # 單位名稱
    role_label: Optional[str] = ""   # 顯示用（含「其他」自填）
    ref: Optional[str] = ""
    note: Optional[str] = ""


# ─── helpers ────────────────────────────────────────────────────────────────

def _fmt_ts(ts) -> Optional[str]:
    """把 TIMESTAMP / datetime 轉成 ISO-like 字串（沿用舊版格式 `%Y-%m-%dT%H:%M:%S`）"""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%dT%H:%M:%S")
    return str(ts)


def _to_dict(row: M.ContactRequest) -> dict:
    """把 DB row 轉成跟舊版 JSON 一樣的回傳格式（前端不用改）"""
    return {
        "id":               row.id,
        "name":             row.name or "",
        "phone":            row.phone or "",
        "email":            row.email or "",
        "org_type":         row.org_type or "",
        "org":              row.org or "",
        "role_label":       row.role_label or "",
        "ref":              row.ref or "",
        "note":             row.note or "",
        "status":           row.status or "pending",
        "createdAt":        _fmt_ts(row.created_at),
        "handledAt":        _fmt_ts(row.handled_at),
        "initial_password": row.initial_password,
        "consultant_id":    row.consultant_id,
        "note_admin":       row.note_admin,
    }


def _new_req_id() -> str:
    return "REQ" + format(int(time.time() * 1000), "X")


# ─── API 端點 ────────────────────────────────────────────────────────────────

@router.post("")
def create_request(req: ContactRequestIn, db: Session = Depends(get_db)):
    rid = (req.id or "").strip() or _new_req_id()
    # 防重複 id
    if db.query(M.ContactRequest).filter(M.ContactRequest.id == rid).first():
        rid = rid + secrets.token_hex(2).upper()

    row = M.ContactRequest(
        id          = rid,
        name        = req.name or "",
        phone       = req.phone or "",
        email       = req.email or "",
        org_type    = req.org_type or "",
        org         = req.org or "",
        role_label  = req.role_label or "",
        ref         = req.ref or "",
        note        = req.note or "",
        status      = "pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


@router.get("")
def list_requests(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(M.ContactRequest)
    if status:
        q = q.filter(M.ContactRequest.status == status)
    q = q.order_by(M.ContactRequest.created_at.desc())
    return [_to_dict(r) for r in q.all()]


@router.post("/{req_id}/approved")
def approve(req_id: str, db: Session = Depends(get_db)):
    row = db.query(M.ContactRequest).filter(M.ContactRequest.id == req_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="申請編號不存在")

    phone = (row.phone or "").strip().replace("-", "").replace(" ", "")
    name  = (row.name  or "").strip()
    email = (row.email or "").strip()

    if not phone or not name or not email:
        raise HTTPException(status_code=400, detail="申請資料不完整，無法建立帳號")

    # 防止覆蓋既有顧問帳號
    existing = db.query(M.Consultant).filter(M.Consultant.phone == phone).first()
    if existing:
        row.status            = "approved"
        row.handled_at        = datetime.utcnow()
        row.consultant_id     = existing.consultant_id
        row.initial_password  = None
        row.note_admin        = "該手機已有顧問帳號，僅標記為已核准（未建立新帳號 / 未重設密碼）"
        db.commit()
        db.refresh(row)
        return _to_dict(row)

    # 產生 8 碼初始密碼（demo 用；正式環境應寄信並要求首次登入立刻修改）
    initial_pw = secrets.token_urlsafe(6)
    consultant = M.Consultant(
        name          = name,
        phone         = phone,
        email         = email,
        password_hash = hash_password(initial_pw),
        role          = "consultant",
        org_type      = row.org_type or "",
        org           = row.org or "",
        is_active     = 1,
    )
    db.add(consultant)
    db.flush()  # 取得 consultant_id

    row.status            = "approved"
    row.handled_at        = datetime.utcnow()
    row.consultant_id     = consultant.consultant_id
    row.initial_password  = initial_pw
    db.commit()
    db.refresh(row)
    # TODO：以 Email 寄送 phone + initial_password
    return _to_dict(row)


@router.post("/{req_id}/rejected")
def reject(req_id: str, db: Session = Depends(get_db)):
    row = db.query(M.ContactRequest).filter(M.ContactRequest.id == req_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="申請編號不存在")
    row.status     = "rejected"
    row.handled_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _to_dict(row)


# ─── 一次性匯入舊版 JSON（若還存在）─────────────────────────────────────────

@router.post("/_migrate-from-json")
def migrate_from_json(db: Session = Depends(get_db)):
    """
    把 backend/contact_requests.json 一次性匯入 DB。

    - 若 JSON 檔不存在 → 回 {migrated: 0, reason: "no legacy json file"}
    - 已存在於 DB（同 id）→ 跳過、不覆蓋
    - 匯入成功後保留 JSON 檔（自行決定要不要刪掉）
    """
    if not os.path.exists(_LEGACY_JSON):
        return {"ok": True, "migrated": 0, "skipped": 0, "reason": "no legacy json file"}

    try:
        with open(_LEGACY_JSON, "r", encoding="utf-8") as f:
            arr = json.load(f) or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法解析 JSON：{e}")

    migrated = 0
    skipped  = 0
    for r in arr:
        rid = (r.get("id") or "").strip()
        if not rid:
            continue
        if db.query(M.ContactRequest).filter(M.ContactRequest.id == rid).first():
            skipped += 1
            continue

        # 解析時間字串（舊版用 strftime("%Y-%m-%dT%H:%M:%S")）
        def _parse(ts):
            if not ts:
                return None
            try:
                return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
            except Exception:
                return None

        row = M.ContactRequest(
            id               = rid,
            name             = r.get("name") or "",
            phone            = r.get("phone") or "",
            email            = r.get("email") or "",
            org_type         = r.get("org_type") or "",
            org              = r.get("org") or "",
            role_label       = r.get("role_label") or "",
            ref              = r.get("ref") or "",
            note             = r.get("note") or "",
            status           = r.get("status") or "pending",
            note_admin       = r.get("note_admin") or None,
            consultant_id    = r.get("consultant_id"),
            initial_password = r.get("initial_password"),
            created_at       = _parse(r.get("createdAt")),
            handled_at       = _parse(r.get("handledAt")),
        )
        db.add(row)
        migrated += 1
    db.commit()
    return {"ok": True, "migrated": migrated, "skipped": skipped}
