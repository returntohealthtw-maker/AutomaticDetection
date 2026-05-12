"""
顧問登入 / Token 驗證

- POST  /api/v1/auth/login        手機 + 密碼 → 回 token + 個人資料
- GET   /api/v1/auth/me           依 token 取目前登入者
- POST  /api/v1/auth/bootstrap    [一次性] 初始化 admin + demo consultant
- POST  /api/v1/auth/change-password   修改自己的密碼

簡易 HMAC-SHA256 token（非標準 JWT、但格式相容：base64url(json).sig）。
密碼採 SHA256 + per-row salt。
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core import models as M
from app.core.config import settings
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["驗證"])


# ─── 密碼雜湊 ────────────────────────────────────────────────────────────────

def hash_password(pw: str) -> str:
    salt = secrets.token_hex(8)
    h    = hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()
    return f"{salt}${h}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        salt, h = (stored or "").split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(
        hashlib.sha256((salt + pw).encode("utf-8")).hexdigest(),
        h,
    )


# ─── Token（HMAC-SHA256，類 JWT）─────────────────────────────────────────────

def _sign(body_b64: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        body_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_token(payload: dict, exp_seconds: int = 7 * 24 * 3600) -> str:
    body = dict(payload)
    body["exp"] = int(time.time()) + exp_seconds
    raw       = json.dumps(body, separators=(",", ":")).encode("utf-8")
    body_b64  = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    return f"{body_b64}.{_sign(body_b64)}"


def verify_token(token: str) -> Optional[dict]:
    try:
        body_b64, sig = token.split(".", 1)
        if not hmac.compare_digest(sig, _sign(body_b64)):
            return None
        pad = "=" * ((-len(body_b64)) % 4)
        body = json.loads(base64.urlsafe_b64decode(body_b64 + pad))
        if body.get("exp", 0) < time.time():
            return None
        return body
    except Exception:
        return None


# ─── 取得目前使用者 ───────────────────────────────────────────────────────────

def _phone_normalize(p: str) -> str:
    return (p or "").strip().replace("-", "").replace(" ", "")


def require_user(authorization: Optional[str], db: Session) -> M.Consultant:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="未登入")
    payload = verify_token(authorization[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="登入逾期或 token 無效")
    cid = payload.get("cid")
    user = (
        db.query(M.Consultant)
        .filter(M.Consultant.consultant_id == cid, M.Consultant.is_active == 1)
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="帳號已停用")
    return user


def require_admin(authorization: Optional[str], db: Session) -> M.Consultant:
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需管理員權限")
    return user


# ─── Pydantic 模型 ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    phone: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ─── 端點 ────────────────────────────────────────────────────────────────────

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    phone = _phone_normalize(req.phone)
    user = (
        db.query(M.Consultant)
        .filter(M.Consultant.phone == phone, M.Consultant.is_active == 1)
        .first()
    )
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    token = create_token({"cid": user.consultant_id, "role": user.role})
    return {
        "token":         token,
        "consultant_id": user.consultant_id,
        "name":          user.name,
        "role":          user.role,
        "org_type":      user.org_type or "",
        "org":           user.org or "",
        "email":         user.email or "",
        "phone":         user.phone,
    }


@router.get("/me")
def me(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    user = require_user(authorization, db)
    return {
        "consultant_id": user.consultant_id,
        "name":          user.name,
        "role":          user.role,
        "org_type":      user.org_type or "",
        "org":           user.org or "",
        "email":         user.email or "",
        "phone":         user.phone,
    }


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    user = require_user(authorization, db)
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="舊密碼錯誤")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密碼至少 6 碼")
    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"ok": True}


@router.post("/bootstrap")
def bootstrap(db: Session = Depends(get_db)):
    """
    一次性初始化：當 consultants 表為空時，建立：
      ① admin 帳號  → 手機 0900000000 / 密碼 admin123
      ② demo 顧問   → 手機 0900000001 / 密碼 demo123 / 名字 示範顧問
    用過一次後（表內有資料）就拒絕呼叫，避免被惡意覆蓋。
    """
    count = db.query(M.Consultant).count()
    if count > 0:
        raise HTTPException(status_code=409, detail="已初始化，本端點停用")

    admin = M.Consultant(
        name          = "系統管理員",
        phone         = "0900000000",
        password_hash = hash_password("admin123"),
        email         = "admin@example.com",
        role          = "admin",
        org_type      = "工作人員",
        org           = "總公司",
        is_active     = 1,
    )
    demo = M.Consultant(
        name          = "示範顧問",
        phone         = "0900000001",
        password_hash = hash_password("demo123"),
        email         = "demo@example.com",
        role          = "consultant",
        org_type      = "加盟商",
        org           = "示範分店",
        is_active     = 1,
    )
    db.add_all([admin, demo])
    db.commit()
    return {
        "ok": True,
        "created": [
            {"name": "系統管理員", "phone": "0900000000", "password": "admin123", "role": "admin"},
            {"name": "示範顧問",   "phone": "0900000001", "password": "demo123",  "role": "consultant"},
        ],
        "hint": "請立即登入並使用 /change-password 修改密碼",
    }
