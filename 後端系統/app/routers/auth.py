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

from fastapi import APIRouter, Depends, Header, HTTPException, Query
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

def _to_halfwidth(s: str) -> str:
    """
    將全形 ASCII 字元（U+FF01 ~ U+FF5E）轉成對應的半形（U+0021 ~ U+007E），
    並把「全形空格 U+3000 / 不換行空格 U+00A0」也視為一般空格。
    用來避免使用者在中文輸入法下打出全形數字／字母（看起來一樣、實際不同碼點）
    而導致比對失敗。
    """
    if not s:
        return ""
    out = []
    for ch in s:
        code = ord(ch)
        if 0xFF01 <= code <= 0xFF5E:
            out.append(chr(code - 0xFEE0))
        elif ch in ("\u3000", "\u00A0"):
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def _phone_normalize(p: str) -> str:
    return (
        _to_halfwidth(p or "")
        .strip()
        .replace("-", "")
        .replace(" ", "")
    )


def _has_pending_initial_password(db: Session, consultant_id: int) -> bool:
    """
    判斷使用者是否仍使用「申請審核時系統發的初始密碼」。
    判斷依據：contact_requests 表內，consultant_id 對應的列上還留有 initial_password。
    /auth/change-password 成功會清掉這欄；此時這個函式就會回 False。

    用途：登入後決定要不要強制彈出「修改密碼」對話框。
    （admin / demo 帳號是用 bootstrap 建的，沒有對應的 ContactRequest，
      所以回 False，不會被打擾。）
    """
    if not consultant_id:
        return False
    return (
        db.query(M.ContactRequest)
        .filter(
            M.ContactRequest.consultant_id == consultant_id,
            M.ContactRequest.initial_password.isnot(None),
            M.ContactRequest.initial_password != "",
        )
        .first()
        is not None
    )


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
    # 密碼也順手把全形 ASCII 轉半形，避免使用者在中文輸入法下打出
    # `ｄｅｍｏ１２３` 卻一直登不進去（與肉眼看到的 demo123 不同碼點）。
    password = _to_halfwidth(req.password or "")
    user = (
        db.query(M.Consultant)
        .filter(M.Consultant.phone == phone, M.Consultant.is_active == 1)
        .first()
    )
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    token = create_token({"cid": user.consultant_id, "role": user.role})
    return {
        "token":                token,
        "consultant_id":        user.consultant_id,
        "name":                 user.name,
        "role":                 user.role,
        "org_type":             user.org_type or "",
        "org":                  user.org or "",
        "email":                user.email or "",
        "phone":                user.phone,
        "must_change_password": _has_pending_initial_password(db, user.consultant_id),
    }


@router.get("/me")
def me(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    user = require_user(authorization, db)
    return {
        "consultant_id":        user.consultant_id,
        "name":                 user.name,
        "role":                 user.role,
        "org_type":             user.org_type or "",
        "org":                  user.org or "",
        "email":                user.email or "",
        "phone":                user.phone,
        "must_change_password": _has_pending_initial_password(db, user.consultant_id),
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
    if req.new_password == req.old_password:
        raise HTTPException(status_code=400, detail="新密碼不可與舊密碼相同")
    user.password_hash = hash_password(req.new_password)

    # 清掉 ContactRequest.initial_password，避免「重新寄送歡迎信」把舊密碼又寄出去
    # 也讓下次登入時 must_change_password 回 false（不再彈出對話框）
    db.query(M.ContactRequest).filter(
        M.ContactRequest.consultant_id == user.consultant_id,
        M.ContactRequest.initial_password.isnot(None),
    ).update({"initial_password": None}, synchronize_session=False)

    db.commit()
    return {"ok": True}


@router.get("/consultants")
def list_consultants(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    取得所有顧問帳號清單（admin 才能用）。
    用於後台「顧問清單」分頁，方便清點 DB 內實際存在的帳號。
    回傳不含 password_hash。
    """
    require_admin(authorization, db)
    rows = (
        db.query(M.Consultant)
        .order_by(M.Consultant.consultant_id.asc())
        .all()
    )
    return [
        {
            "consultant_id": r.consultant_id,
            "name":          r.name,
            "phone":         r.phone,
            "email":         r.email or "",
            "role":          r.role or "consultant",
            "org_type":      r.org_type or "",
            "org":           r.org or "",
            "is_active":     int(r.is_active or 0),
            "created_at":    r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
            "updated_at":    r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else None,
        }
        for r in rows
    ]


def _count_active_admins(db: Session) -> int:
    return (
        db.query(M.Consultant)
        .filter(M.Consultant.role == "admin", M.Consultant.is_active == 1)
        .count()
    )


@router.patch("/consultants/{cid}/toggle-active")
def toggle_consultant_active(
    cid: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    停用 / 啟用顧問帳號（admin only）。
    is_active 1 ↔ 0 切換。停用後該手機無法登入。

    安全限制：
      - 不可停用自己（避免管理員把自己鎖住）
      - 不可停用「最後一個 active admin」（避免後台失控）
    """
    admin_user = require_admin(authorization, db)
    target = db.query(M.Consultant).filter(M.Consultant.consultant_id == cid).first()
    if not target:
        raise HTTPException(status_code=404, detail="顧問帳號不存在")
    if target.consultant_id == admin_user.consultant_id:
        raise HTTPException(status_code=400, detail="不可停用自己的帳號")

    new_active = 0 if (target.is_active or 0) == 1 else 1
    if new_active == 0 and target.role == "admin":
        # 將要停用的是 admin → 確認還有別的 active admin
        if _count_active_admins(db) <= 1:
            raise HTTPException(status_code=400, detail="不可停用最後一個 active 管理員")

    target.is_active = new_active
    db.commit()
    db.refresh(target)
    return {
        "ok":            True,
        "consultant_id": target.consultant_id,
        "name":          target.name,
        "is_active":     int(target.is_active or 0),
        "action":        "enabled" if new_active == 1 else "disabled",
    }


class AdminResetPasswordRequest(BaseModel):
    new_password: str


@router.patch("/consultants/{cid}/reset-password")
def admin_reset_password(
    cid: int,
    req: AdminResetPasswordRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    管理員強制重設指定顧問的密碼（admin only）。
    不需要舊密碼，重設後同時清除「初始密碼待更換」標記。
    """
    require_admin(authorization, db)
    target = db.query(M.Consultant).filter(M.Consultant.consultant_id == cid).first()
    if not target:
        raise HTTPException(status_code=404, detail="顧問帳號不存在")
    new_pw = (req.new_password or "").strip()
    if len(new_pw) < 6:
        raise HTTPException(status_code=400, detail="新密碼至少 6 碼")

    target.password_hash = hash_password(new_pw)
    # 清除初始密碼標記，讓顧問下次登入不再強制彈出修改對話框
    db.query(M.ContactRequest).filter(
        M.ContactRequest.consultant_id == cid,
        M.ContactRequest.initial_password.isnot(None),
    ).update({"initial_password": None}, synchronize_session=False)
    db.commit()
    return {"ok": True, "consultant_id": cid, "name": target.name}


@router.delete("/consultants/{cid}")
def delete_consultant(
    cid: int,
    confirm: int = Query(0, description="必須帶 ?confirm=1 才會真的刪除"),
    purge_requests: int = Query(
        1,
        description="1=同時刪除對應的申請紀錄（預設，避免名單不同步）/ 0=保留申請紀錄成孤兒",
    ),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    永久刪除顧問帳號（admin only，不可逆）。

    關聯資料處理：
      - subjects.consultant_id → NULL（受測者紀錄保留，只是失去歸屬）
      - contact_requests       → 預設「同時刪除」(purge_requests=1)，
                                 避免「顧問清單」與「已核准名單」不同步。
                                 若想保留申請歷史，請傳 ?purge_requests=0。

    安全限制：
      - 必須帶 ?confirm=1（防誤觸）
      - 不可刪除自己
      - 不可刪除最後一個 active admin
    """
    admin_user = require_admin(authorization, db)
    if confirm != 1:
        raise HTTPException(
            status_code=400,
            detail="未確認刪除，請於 URL 加上 ?confirm=1",
        )
    target = db.query(M.Consultant).filter(M.Consultant.consultant_id == cid).first()
    if not target:
        raise HTTPException(status_code=404, detail="顧問帳號不存在")
    if target.consultant_id == admin_user.consultant_id:
        raise HTTPException(status_code=400, detail="不可刪除自己的帳號")

    if target.role == "admin" and int(target.is_active or 0) == 1:
        if _count_active_admins(db) <= 1:
            raise HTTPException(status_code=400, detail="不可刪除最後一個 active 管理員")

    snapshot = {
        "consultant_id": target.consultant_id,
        "name":          target.name,
        "phone":         target.phone,
        "email":         target.email or "",
        "role":          target.role or "consultant",
        "org_type":      target.org_type or "",
        "org":           target.org or "",
    }

    purged_request_ids: list = []
    if purge_requests == 1:
        related = (
            db.query(M.ContactRequest)
            .filter(M.ContactRequest.consultant_id == target.consultant_id)
            .all()
        )
        for r in related:
            purged_request_ids.append(r.id)
            db.delete(r)

    db.delete(target)
    db.commit()
    return {
        "ok":                   True,
        "deleted":              snapshot,
        "purged_request_ids":   purged_request_ids,
        "purged_request_count": len(purged_request_ids),
    }


@router.post("/bootstrap")
def bootstrap(db: Session = Depends(get_db)):
    """
    一次性初始化：當 consultants 表為空時，建立：
      ① admin 帳號     → 手機 0900000000 / 密碼 admin123
      ② demo 加盟商顧問 → 手機 0900000001 / 密碼 demo123   / 名字 示範顧問   / org_type 加盟商
      ③ demo 直營商顧問 → 手機 0900000002 / 密碼 direct123 / 名字 示範直營商 / org_type 直營商
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
    demo_franchise = M.Consultant(
        name          = "示範顧問",
        phone         = "0900000001",
        password_hash = hash_password("demo123"),
        email         = "demo@example.com",
        role          = "consultant",
        org_type      = "加盟商",
        org           = "示範加盟店",
        is_active     = 1,
    )
    demo_direct = M.Consultant(
        name          = "示範直營商",
        phone         = "0900000002",
        password_hash = hash_password("direct123"),
        email         = "direct@example.com",
        role          = "consultant",
        org_type      = "直營商",
        org           = "示範直營店",
        is_active     = 1,
    )
    db.add_all([admin, demo_franchise, demo_direct])
    db.commit()
    return {
        "ok": True,
        "created": [
            {"name": "系統管理員",   "phone": "0900000000", "password": "admin123",  "role": "admin",      "org_type": "工作人員"},
            {"name": "示範顧問",     "phone": "0900000001", "password": "demo123",   "role": "consultant", "org_type": "加盟商"},
            {"name": "示範直營商",   "phone": "0900000002", "password": "direct123", "role": "consultant", "org_type": "直營商"},
        ],
        "hint": "請立即登入並使用 /change-password 修改密碼",
    }


@router.post("/bootstrap-direct-demo")
def bootstrap_direct_demo(db: Session = Depends(get_db)):
    """
    補建直營商 demo 帳號（給已經 bootstrap 過、但還沒有直營商帳號的舊資料庫用）。
    只在直營商帳號不存在時才會新增；已存在就回 409。
    """
    exists = (
        db.query(M.Consultant)
        .filter(M.Consultant.phone == "0900000002")
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="直營商 demo 帳號已存在")
    demo_direct = M.Consultant(
        name          = "示範直營商",
        phone         = "0900000002",
        password_hash = hash_password("direct123"),
        email         = "direct@example.com",
        role          = "consultant",
        org_type      = "直營商",
        org           = "示範直營店",
        is_active     = 1,
    )
    db.add(demo_direct)
    db.commit()
    return {
        "ok": True,
        "created": {
            "name": "示範直營商", "phone": "0900000002",
            "password": "direct123", "org_type": "直營商",
        },
    }
