"""
分潤規則 & 收益查詢 API

端點：
- GET  /api/v1/share-rules          回傳目前分潤規則 JSON（不需 auth）
- PUT  /api/v1/share-rules          儲存分潤規則（需 admin token）
- GET  /api/v1/earnings?month=YYYY-MM  依真實付款紀錄 + 規則計算分潤（需 auth）
"""
from __future__ import annotations
import json
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core import models as M
from app.core.database import get_db
from app.routers.auth import require_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["分潤規則"])

RULE_SET_KEY = "default"

# ── 各產品售價（與前端 _PRODUCTS 對應）───────────────────────────────────────
_PRODUCT_PRICES = {
    "life_trial":     3000,
    "life_full":      5000,
    "life_vip":      12000,
    "child_trial":    3000,
    "child_full":     5000,
    "child_vip":     12000,
    "relation":       8000,
    "up_trial_full":  2000,
    "up_full_vip":    7000,
    "up_trial_vip":   9000,
    "test_1":            1,
}

_ROLES = ["franchise", "direct", "agent", "project", "staff"]
_BASE_PCT = {"franchise": 25, "direct": 20, "agent": 18, "project": 15, "staff": 5}


def _default_rules() -> dict:
    rules = {}
    for key, price in _PRODUCT_PRICES.items():
        rules[key] = {
            "mode": "pct",
            "pct_byRole":    {r: _BASE_PCT[r] for r in _ROLES},
            "amount_byRole": {r: round(price * _BASE_PCT[r] / 100) for r in _ROLES},
        }
    return rules


def _load_rules(db: Session) -> dict:
    row = db.query(M.ShareRuleSet).filter_by(rule_set_key=RULE_SET_KEY).first()
    if not row:
        return _default_rules()
    try:
        stored = json.loads(row.rules_json)
        # 補齊缺少的產品
        defaults = _default_rules()
        for k, v in defaults.items():
            if k not in stored:
                stored[k] = v
            else:
                for sub in ("pct_byRole", "amount_byRole"):
                    if sub not in stored[k]:
                        stored[k][sub] = v[sub]
                    else:
                        for r in _ROLES:
                            if r not in stored[k][sub]:
                                stored[k][sub][r] = v[sub][r]
        return stored
    except Exception:
        return _default_rules()


# ── GET /api/v1/share-rules ───────────────────────────────────────────────────
@router.get("/share-rules")
def get_share_rules(db: Session = Depends(get_db)):
    """回傳目前分潤規則（不需登入）"""
    rules = _load_rules(db)
    row = db.query(M.ShareRuleSet).filter_by(rule_set_key=RULE_SET_KEY).first()
    return {
        "ok":         True,
        "rules":      rules,
        "updated_by": row.updated_by if row else None,
        "updated_at": row.updated_at if row else None,
    }


# ── PUT /api/v1/share-rules ───────────────────────────────────────────────────
class PutRulesIn(BaseModel):
    rules: dict


@router.put("/share-rules")
def put_share_rules(
    payload: PutRulesIn,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """儲存分潤規則（需 admin 或有效 token）"""
    user = require_user(authorization, db)
    # 允許 role 或 org_type 符合（相容舊帳號：org_type=專案人員/工作人員 但 role=consultant）
    _ALLOWED_ROLES     = {"admin", "project", "staff"}
    _ALLOWED_ORG_TYPES = {"專案人員", "工作人員"}
    if user.role not in _ALLOWED_ROLES and (user.org_type or "") not in _ALLOWED_ORG_TYPES:
        raise HTTPException(403, "僅管理員、專案人員或工作人員可修改分潤規則")

    row = db.query(M.ShareRuleSet).filter_by(rule_set_key=RULE_SET_KEY).first()
    if row is None:
        row = M.ShareRuleSet(
            rule_set_key=RULE_SET_KEY,
            rules_json=json.dumps(payload.rules, ensure_ascii=False),
            updated_by=user.name,
            updated_at=int(time.time()),
        )
        db.add(row)
    else:
        row.rules_json  = json.dumps(payload.rules, ensure_ascii=False)
        row.updated_by  = user.name
        row.updated_at  = int(time.time())
    db.commit()
    return {"ok": True, "message": "分潤規則已儲存", "updated_by": user.name}


# ── GET /api/v1/earnings ──────────────────────────────────────────────────────
@router.get("/earnings")
def get_earnings(
    month: Optional[str] = Query(None, description="格式 YYYY-MM，不填 = 本月"),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    依真實付款紀錄計算分潤。
    month 格式：2026-05
    回傳：逐筆明細 + 按顧問分組匯總 + 全公司總額
    """
    require_user(authorization, db)

    # 計算月份起訖 Unix timestamp
    import datetime
    if month:
        try:
            y, m = int(month[:4]), int(month[5:7])
        except Exception:
            raise HTTPException(400, "month 格式錯誤，請用 YYYY-MM")
    else:
        now = datetime.datetime.utcnow()
        y, m = now.year, now.month

    start_dt = datetime.datetime(y, m, 1, 0, 0, 0)
    if m == 12:
        end_dt = datetime.datetime(y + 1, 1, 1, 0, 0, 0)
    else:
        end_dt = datetime.datetime(y, m + 1, 1, 0, 0, 0)
    start_ts = int(start_dt.timestamp())
    end_ts   = int(end_dt.timestamp())

    # 查詢已付款紀錄
    payments = (
        db.query(M.Payment)
        .filter(
            M.Payment.status == "paid",
            M.Payment.paid_at >= start_ts,
            M.Payment.paid_at < end_ts,
        )
        .order_by(M.Payment.paid_at.desc())
        .all()
    )

    rules = _load_rules(db)

    # 建立顧問 org_type 快取（避免 N+1）
    consultant_cache: dict[str, str] = {}
    all_consultants = db.query(M.Consultant).all()
    for c in all_consultants:
        consultant_cache[c.name] = c.org_type or "franchise"

    items = []
    by_consultant: dict[str, dict] = {}
    total = 0

    for p in payments:
        role = consultant_cache.get(p.consultant_name or "", "franchise")
        prod_rule = rules.get(p.report_type)
        if prod_rule:
            mode = prod_rule.get("mode", "pct")
            if mode == "amount":
                share = prod_rule.get("amount_byRole", {}).get(role, 0)
                rule_text = f"固定 NT${share:,}"
            else:
                pct = prod_rule.get("pct_byRole", {}).get(role, 0)
                share = round(p.amount * pct / 100)
                rule_text = f"{pct}% × NT${p.amount:,}"
        else:
            share = 0
            rule_text = "未設定規則"

        total += share
        consultant_key = p.consultant_name or "(未知)"
        if consultant_key not in by_consultant:
            by_consultant[consultant_key] = {
                "consultant": consultant_key,
                "role": role,
                "total_share": 0,
                "order_count": 0,
            }
        by_consultant[consultant_key]["total_share"] += share
        by_consultant[consultant_key]["order_count"] += 1

        items.append({
            "payment_id":      p.payment_id,
            "paid_at":         p.paid_at,
            "consultant_name": p.consultant_name,
            "subject_name":    p.subject_name,
            "report_type":     p.report_type,
            "amount":          p.amount,
            "role":            role,
            "share":           share,
            "rule_text":       rule_text,
        })

    return {
        "ok":            True,
        "month":         f"{y:04d}-{m:02d}",
        "total_share":   total,
        "by_consultant": sorted(by_consultant.values(), key=lambda x: -x["total_share"]),
        "items":         items,
    }
