"""
顧問帳號申請 / 管理員審核

簡易實作：以 JSON 檔案儲存於 backend/contact_requests.json
（多機部署時改用資料庫）。

API：
  POST  /api/v1/contact-requests                     新增申請
  GET   /api/v1/contact-requests                     列出全部
  GET   /api/v1/contact-requests?status=pending      依狀態過濾
  POST  /api/v1/contact-requests/{id}/approved       核准（會回傳預設密碼）
  POST  /api/v1/contact-requests/{id}/rejected       拒絕
"""
import os
import json
import time
import secrets
from typing import Optional
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core import models as M
from app.core.database import get_db
from app.routers.auth import hash_password

router = APIRouter(prefix="/api/v1/contact-requests", tags=["顧問帳號申請"])

# ─── 儲存位置 ────────────────────────────────────────────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.dirname(os.path.dirname(_THIS_DIR))  # backend/
_DATA_FILE = os.path.join(_DATA_DIR, "contact_requests.json")
_lock = Lock()


def _load() -> list[dict]:
    if not os.path.exists(_DATA_FILE):
        return []
    try:
        with open(_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(arr: list[dict]) -> None:
    with open(_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(arr, f, ensure_ascii=False, indent=2)


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


class ContactRequestOut(ContactRequestIn):
    status: str = "pending"          # pending / approved / rejected
    createdAt: str
    handledAt: Optional[str] = None
    initial_password: Optional[str] = None


# ─── API 端點 ────────────────────────────────────────────────────────────────

@router.post("", response_model=ContactRequestOut)
def create_request(req: ContactRequestIn):
    with _lock:
        arr = _load()
        rid = req.id or ("REQ" + format(int(time.time() * 1000), "X"))
        # 防重複 id
        if any(r.get("id") == rid for r in arr):
            rid = rid + secrets.token_hex(2).upper()
        item = {
            **req.model_dump(),
            "id": rid,
            "status": "pending",
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "handledAt": None,
            "initial_password": None,
        }
        arr.insert(0, item)
        _save(arr)
        return item


@router.get("")
def list_requests(status: Optional[str] = None):
    arr = _load()
    if status:
        arr = [r for r in arr if r.get("status") == status]
    return arr


@router.post("/{req_id}/approved", response_model=ContactRequestOut)
def approve(req_id: str, db: Session = Depends(get_db)):
    with _lock:
        arr = _load()
        for r in arr:
            if r.get("id") != req_id:
                continue

            phone = (r.get("phone") or "").strip().replace("-", "").replace(" ", "")
            name  = (r.get("name")  or "").strip()
            email = (r.get("email") or "").strip()

            if not phone or not name or not email:
                raise HTTPException(status_code=400, detail="申請資料不完整，無法建立帳號")

            # 防止覆蓋既有顧問帳號
            existing = db.query(M.Consultant).filter(M.Consultant.phone == phone).first()
            if existing:
                # 若帳號已存在，僅標記為已核准，不重設密碼
                r["status"] = "approved"
                r["handledAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                r["consultant_id"] = existing.consultant_id
                r["initial_password"] = None
                r["note_admin"] = "該手機已有顧問帳號，僅標記為已核准（未建立新帳號 / 未重設密碼）"
                _save(arr)
                return r

            # 產生 8 碼初始密碼（demo 用；正式環境應寄信並要求首次登入立刻修改）
            initial_pw = secrets.token_urlsafe(6)
            consultant = M.Consultant(
                name          = name,
                phone         = phone,
                email         = email,
                password_hash = hash_password(initial_pw),
                role          = "consultant",
                org_type      = r.get("org_type") or "",
                org           = r.get("org") or "",
                is_active     = 1,
            )
            db.add(consultant)
            db.commit()
            db.refresh(consultant)

            r["status"] = "approved"
            r["handledAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            r["initial_password"] = initial_pw
            r["consultant_id"]    = consultant.consultant_id
            _save(arr)
            # TODO：以 Email 寄送 phone + initial_password
            return r
    raise HTTPException(status_code=404, detail="申請編號不存在")


@router.post("/{req_id}/rejected", response_model=ContactRequestOut)
def reject(req_id: str):
    with _lock:
        arr = _load()
        for r in arr:
            if r.get("id") == req_id:
                r["status"] = "rejected"
                r["handledAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                _save(arr)
                return r
    raise HTTPException(status_code=404, detail="申請編號不存在")
