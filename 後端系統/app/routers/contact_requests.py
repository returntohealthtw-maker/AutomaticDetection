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

from sqlalchemy import or_

from app.core import models as M
from app.core.database import get_db
from app.routers.auth import hash_password
from app.services.email_sender import send_consultant_welcome_email, is_configured as email_is_configured

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


def _send_welcome(row: M.ContactRequest) -> dict:
    """
    寄發顧問歡迎信。回傳 dict 給前端顯示「寄信成功 / 失敗」。
    失敗時也會把錯誤訊息記到 row.note_admin，方便管理員看。
    """
    if not row.initial_password:
        return {"ok": False, "error": "initial_password 為空，無法寄送"}
    if not email_is_configured():
        msg = "GMAIL_USER / GMAIL_APP_PASSWORD 未設定（請至 Railway Variables）"
        row.note_admin = (row.note_admin or "") + f" [email skipped: {msg}]"
        return {"ok": False, "error": msg}

    try:
        result = send_consultant_welcome_email(
            to               = row.email or "",
            name             = row.name or "",
            phone            = row.phone or "",
            initial_password = row.initial_password,
            org_type         = row.org_type or "",
            org              = row.org or "",
        )
    except Exception as e:
        result = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    if result.get("ok"):
        row.note_admin = (row.note_admin or "") + f" [email sent to {row.email}]"
    else:
        row.note_admin = (row.note_admin or "") + f" [email failed: {result.get('error')}]"
    return result


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
    """
    核准申請。

    行為（v3 變更，避免「dup_phone 不寄信」造成名單不同步）：
      • 手機尚無顧問 → 建立新顧問 + 寄歡迎信
      • 手機已有顧問 → 「重設密碼 + 更新 email / name / 啟用 + 寄歡迎信」
        （核准 = 一定會給對方一組可用密碼 + 寄信，行為簡單可預期）

    若不想覆蓋既有帳號，請先用「拒絕」處理該申請，或先刪除既有顧問。
    """
    row = db.query(M.ContactRequest).filter(M.ContactRequest.id == req_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="申請編號不存在")

    phone = (row.phone or "").strip().replace("-", "").replace(" ", "")
    name  = (row.name  or "").strip()
    email = (row.email or "").strip()

    if not phone or not name or not email:
        raise HTTPException(status_code=400, detail="申請資料不完整，無法建立帳號")

    initial_pw = secrets.token_urlsafe(6)

    existing = db.query(M.Consultant).filter(M.Consultant.phone == phone).first()
    if existing:
        # ★ v3：不再跳過，改成「重設密碼 + 同步申請最新資料 + 重新啟用」
        existing.password_hash = hash_password(initial_pw)
        existing.email         = email or existing.email
        existing.name          = name or existing.name
        if (row.org_type or "").strip():
            existing.org_type = row.org_type
        if (row.org or "").strip():
            existing.org = row.org
        existing.is_active = 1
        consultant = existing
        note = f"既有顧問 #{existing.consultant_id}：已重設密碼、同步申請資料、重新啟用"
    else:
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
        note = f"建立新顧問 #{consultant.consultant_id}"

    row.status            = "approved"
    row.handled_at        = datetime.utcnow()
    row.consultant_id     = consultant.consultant_id
    row.initial_password  = initial_pw
    row.note_admin        = note
    db.commit()
    db.refresh(row)

    # ─── 寄發歡迎信（含帳號 + 初始密碼） ───────────────────────────────────
    email_status = _send_welcome(row)
    db.commit()           # 把 _send_welcome 寫到 row.note_admin 的結果存進 DB
    db.refresh(row)

    out = _to_dict(row)
    out["email_status"] = email_status
    return out


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


# ─── 重新寄送歡迎信（給寄信失敗、或申請人沒收到的情況）─────────────────────
@router.post("/{req_id}/resend-welcome-email")
def resend_welcome_email(req_id: str, db: Session = Depends(get_db)):
    row = db.query(M.ContactRequest).filter(M.ContactRequest.id == req_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="申請編號不存在")
    if row.status != "approved":
        raise HTTPException(status_code=400, detail="此申請尚未核准，無法寄送歡迎信")
    if not row.initial_password:
        raise HTTPException(
            status_code=400,
            detail="初始密碼已被使用者修改或清除，請改用密碼重設流程",
        )

    email_status = _send_welcome(row)
    db.commit()
    db.refresh(row)
    return {"email_status": email_status, "request": _to_dict(row)}


# ─── 同步檢查 / 清理孤兒申請 ──────────────────────────────────────────────────

@router.get("/_sync-status")
def sync_status(db: Session = Depends(get_db)):
    """
    回傳「申請紀錄 vs 顧問帳號」的同步狀態，給管理員 UI 顯示用。

    每筆已核准的申請，會標記它對應的 consultant 是否還存在：
      - linked        ：有 consultant_id 而且查得到對應顧問
      - orphan_deleted：有 consultant_id 但對應顧問已被刪除（FK 已被 SET NULL）
      - orphan_null   ：consultant_id 為 NULL（FK 被 SET NULL 後的狀態）
      - dup_phone     ：原本就因為同手機已有帳號，未建立新顧問（這是正常情況）

    回傳：
      {
        approved_total: int,
        orphans:        int,   # orphan_deleted + orphan_null 加總
        items:          [...]  # 每筆狀態
      }
    """
    rows = (
        db.query(M.ContactRequest)
        .filter(M.ContactRequest.status == "approved")
        .order_by(M.ContactRequest.created_at.desc())
        .all()
    )

    items = []
    counts = {"linked": 0, "orphan_null": 0, "orphan_deleted": 0, "dup_phone": 0}
    for r in rows:
        is_dup = (r.note_admin or "").find("該手機已有顧問帳號") >= 0
        if r.consultant_id is None:
            state = "dup_phone" if is_dup else "orphan_null"
        else:
            c = db.query(M.Consultant).filter(
                M.Consultant.consultant_id == r.consultant_id
            ).first()
            state = "linked" if c else "orphan_deleted"
        counts[state] = counts.get(state, 0) + 1
        items.append({
            "id":            r.id,
            "name":          r.name or "",
            "phone":         r.phone or "",
            "consultant_id": r.consultant_id,
            "state":         state,
        })

    return {
        "approved_total": len(rows),
        "orphans":        counts["orphan_null"] + counts["orphan_deleted"],
        "dup_phone":      counts["dup_phone"],
        "linked":         counts["linked"],
        "unmatched":      counts["orphan_null"] + counts["orphan_deleted"] + counts["dup_phone"],
        "counts":         counts,
        "items":          items,
    }


@router.post("/_purge-orphans")
def purge_orphans(
    include_dup: int = 1,
    db: Session = Depends(get_db),
):
    """
    一次性清理「已核准但不對應任何 active 顧問」的申請：

    一定會刪：
      - orphan_null    （consultant_id=NULL 且非 dup_phone）
      - orphan_deleted （consultant_id 不為 NULL 但對應顧問已不存在）

    預設也會刪（讓兩個名單真正同步）：
      - dup_phone（同手機已有帳號，本次未建新顧問）

    若要保留 dup_phone 歷史紀錄，請傳 ?include_dup=0
    """
    rows = (
        db.query(M.ContactRequest)
        .filter(M.ContactRequest.status == "approved")
        .all()
    )
    deleted_ids = []
    breakdown = {"orphan_null": 0, "orphan_deleted": 0, "dup_phone": 0}

    for r in rows:
        is_dup = (r.note_admin or "").find("該手機已有顧問帳號") >= 0
        if r.consultant_id is None:
            if is_dup:
                if include_dup == 1:
                    deleted_ids.append(r.id)
                    breakdown["dup_phone"] += 1
                    db.delete(r)
            else:
                deleted_ids.append(r.id)
                breakdown["orphan_null"] += 1
                db.delete(r)
            continue
        c = db.query(M.Consultant).filter(
            M.Consultant.consultant_id == r.consultant_id
        ).first()
        if not c:
            deleted_ids.append(r.id)
            breakdown["orphan_deleted"] += 1
            db.delete(r)
    db.commit()
    return {
        "ok":            True,
        "deleted_count": len(deleted_ids),
        "deleted_ids":   deleted_ids,
        "breakdown":     breakdown,
    }


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
