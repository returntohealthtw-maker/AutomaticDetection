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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
def approve(req_id: str):
    with _lock:
        arr = _load()
        for r in arr:
            if r.get("id") == req_id:
                r["status"] = "approved"
                r["handledAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                # 簡易產生 8 碼初始密碼（demo 用，正式版應加密儲存 + 寄信）
                r["initial_password"] = secrets.token_urlsafe(6)
                _save(arr)
                # TODO：在此呼叫實際寄信服務（SendGrid/SMTP）
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
