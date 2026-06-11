"""
報告生成 API

端點：
- POST /api/v1/report-gen/test-section   ← 立即生成單節（同步）
- POST /api/v1/report-gen/start          ← 啟動完整背景生成
- GET  /api/v1/report-gen/status/{id}    ← 輪詢進度
- GET  /api/v1/report-gen/stream/{id}    ← SSE 即時進度
- GET  /api/v1/report-gen/result/{id}    ← 取已完成報告
- GET  /api/v1/report-gen/chapters       ← 列出章節結構（給前端 UI 用）
- GET  /api/v1/report-gen/health         ← 檢查 Gemini key 狀態
"""
from __future__ import annotations
import json
import time
import logging
from typing import Optional, List, Dict, Any

from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.services import ai_report as report_generator
from app.services import gemini_client
from app.services import email_sender
from app.services import report_orchestrator
from app.services.report_chapters import get_chapters, count_sections
from app.core.database import get_db
from app.core import models as M

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/report-gen", tags=["report-gen"])

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _bw_from_session(db: DbSession, session_id: int) -> Optional[Dict[str, Any]]:
    """從 EegCapture 重建 brainwave_data，供 brainwave_data 為空時自動補充。

    重要：
      - 必須帶 sample_count（前端 / validator 會檢查 ≥ 30）
      - 不能用 `x or 50` 假裝有資料（會把 0 變 50 → 全部 50% bug）
      - 0 / None 用實際讀到的 capture 行數推 sample_count
    """
    caps = db.query(M.EegCapture).filter(
        M.EegCapture.session_id == session_id,
        M.EegCapture.is_baseline == 0,
    ).all()
    if not caps:
        caps = db.query(M.EegCapture).filter(
            M.EegCapture.session_id == session_id
        ).all()
    if not caps:
        return None
    n = len(caps)

    def avg_nz(attr):
        """只把『非 None』的值納入平均，避免被 NULL 拉低到 0"""
        vals = [getattr(c, attr, None) for c in caps]
        vals = [v for v in vals if v is not None]
        if not vals:
            return None
        return round(sum(vals) / len(vals), 2)

    def pair_avg(lo_attr, hi_attr):
        a = avg_nz(lo_attr); b = avg_nz(hi_attr)
        if a is None and b is None: return None
        if a is None: return b
        if b is None: return a
        return round((a + b) / 2, 2)

    # 如果 EegCapture 表是空殼（seq_num=0 那種 deduped 平均），sample_count 應該用 session.total_captures
    sess = db.query(M.Session).filter(M.Session.session_id == session_id).first()
    sample_count = (sess.total_captures if (sess and sess.total_captures) else n) or n

    lo_al = avg_nz("low_alpha");  hi_al = avg_nz("high_alpha")
    lo_be = avg_nz("low_beta");   hi_be = avg_nz("high_beta")
    lo_ga = avg_nz("low_gamma");  hi_ga = avg_nz("high_gamma")

    bw = {
        "attention_percentage":  avg_nz("attention"),
        "meditation_percentage": avg_nz("meditation"),
        "sample_count":          int(sample_count),
        "bands_avg": {
            # 5-band 合併（向下相容）
            "delta": avg_nz("delta"),
            "theta": avg_nz("theta"),
            "alpha": pair_avg("low_alpha", "high_alpha"),
            "beta":  pair_avg("low_beta",  "high_beta"),
            "gamma": pair_avg("low_gamma", "high_gamma"),
            # 8-band 真實子頻帶（優先帶出，避免 headless_renderer 用 ×0.9/×1.1 估算）
            "low_alpha":  lo_al, "high_alpha": hi_al,
            "low_beta":   lo_be, "high_beta":  hi_be,
            "low_gamma":  lo_ga, "high_gamma": hi_ga,
        },
    }
    return bw


@router.get("/pdf/{job_id}")
def get_pdf(job_id: str):
    """下載外部報告系統生成並存好的 PDF"""
    # 防 path traversal
    if "/" in job_id or "\\" in job_id or ".." in job_id:
        raise HTTPException(400, "非法 job_id")
    path = REPORTS_DIR / f"{job_id}.pdf"
    if not path.exists():
        raise HTTPException(404, "找不到報告檔案")
    return FileResponse(str(path), media_type="application/pdf",
                        filename=f"{job_id}.pdf")


# ─── Pydantic Schemas ────────────────────────────────────────────────────
class TestSectionRequest(BaseModel):
    chapter_num:    int  = Field(1, ge=1, le=13)
    section_num:    int  = Field(1, ge=1, le=4)
    subject_name:   str  = "受測者"
    report_type:    str  = "life_script"  # life_script / child / parent_child / marital
    variant:        str  = "full"          # trial / full / vip
    brainwave_data: Optional[Dict[str, Any]] = None  # 沒給就用 demo 資料


class StartRequest(BaseModel):
    subject_name:         str  = "受測者"
    subject_age:          Optional[int] = None
    subject_gender:       Optional[str] = ""
    subject_id:           Optional[int] = None        # 🔑 受測者主檔 FK，避免報告變孤兒
    report_type:          str  = "life_script"
    variant:              str  = "full"
    brainwave_data:       Optional[Dict[str, Any]] = None
    subject_email:        Optional[str] = None       # 完成後自動寄到此 email（None = 不寄）
    chapters_to_generate: Optional[List[int]] = None  # 只生成這些章節（None = 全部）
    use_external:         Optional[bool] = None       # None = 自動判斷（外部設了就用），True/False = 強制
    session_id:           Optional[int] = None        # 從 /eeg/save-stats 拿到的 session_id，外部完成後可 callback
    extra:                Optional[Dict[str, Any]] = None  # 關係報告用：wife_session_id / members 等多人資料


class ChaptersQuery(BaseModel):
    report_type: str = "life_script"
    variant:     str = "full"


# ─── Endpoints ───────────────────────────────────────────────────────────
@router.get("/health")
def health():
    """檢查 Gemini key 與相關設定狀態（含詳細診斷，但不會洩露金鑰本身）"""
    import os
    from app.core.config import settings as _s

    # 1. 直接從環境變數讀
    env_key = os.environ.get("GEMINI_API_KEY", "")
    env_key_clean = env_key.strip()

    # 2. 從 pydantic settings 讀
    settings_key = getattr(_s, "GEMINI_API_KEY", "") or ""
    settings_key_clean = settings_key.strip()

    # 3. 找出所有名稱包含 GEMINI 的 env var（只顯示名稱、不顯示值）
    gemini_related_env_names = sorted(
        name for name in os.environ.keys() if "GEMINI" in name.upper()
    )

    # 4. 列出所有「應該由 Railway 注入」的 env vars 名稱（用來判斷整體注入是否正常）
    interesting_prefixes = ("GEMINI", "GITHUB", "ECPAY", "DATABASE", "RAILWAY", "RESEND", "PORT", "USE_")
    railway_visible_names = sorted(
        name for name in os.environ.keys()
        if any(name.upper().startswith(p) for p in interesting_prefixes)
    )
    total_env_count = len(os.environ)

    def _diag(value: str) -> dict:
        """生出單一字串的診斷資訊（不洩露內容）"""
        if not value:
            return {"present": False, "length": 0}
        return {
            "present":            True,
            "length":             len(value),
            "starts_with":        value[:4] + "..." if len(value) >= 4 else value,
            "ends_with":          "..." + value[-4:] if len(value) >= 8 else "",
            "has_leading_space":  value != value.lstrip(),
            "has_trailing_space": value != value.rstrip(),
            "has_quotes":         value.startswith(('"', "'")) or value.endswith(('"', "'")),
            "looks_like_gemini":  value.lstrip("\"' ").startswith("AIza"),
            "is_placeholder":     value.strip().strip("\"'") == "your-gemini-api-key-here",
        }

    gmail_user = os.environ.get("GMAIL_USER", "") or _s.GMAIL_USER
    return {
        "gemini_key_set": gemini_client.key_is_set(),
        "model":          _s.GEMINI_TEXT_MODEL if gemini_client.key_is_set() else None,
        "mock_mode":      not gemini_client.key_is_set(),
        "email": {
            "configured": email_sender.is_configured(),
            "gmail_user": gmail_user[:3] + "..." + gmail_user.split("@")[-1] if "@" in gmail_user else "",
            "from_name":  os.environ.get("GMAIL_FROM_NAME", "") or _s.GMAIL_FROM_NAME,
        },
        "external_reports": report_orchestrator.diag(),
        "diagnostics": {
            "env_var":     _diag(env_key),
            "settings":    _diag(settings_key),
            "gemini_env_names_seen_by_python": gemini_related_env_names,
            "railway_injected_env_names":      railway_visible_names,
            "total_env_var_count":             total_env_count,
        },
    }


@router.get("/headless-diag")
def headless_diag(authorization: str = Header(None), db=Depends(get_db)):
    """完整診斷 headless Chromium 環境（admin 專用）。
    回傳：playwright 是否安裝、Chromium 路徑是否存在、能否成功啟動 browser。
    """
    from app.services.auth import require_user
    from app.services import headless_renderer
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "僅管理員可使用")

    info = headless_renderer.diag()

    # 嘗試真正啟動 Chromium（同步）
    launch_ok = False
    launch_err = None
    if info.get("playwright_installed"):
        try:
            import asyncio as _asyncio
            from playwright.async_api import async_playwright as _apw

            async def _try_launch():
                async with _apw() as pw:
                    b = await pw.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-setuid-sandbox",
                              "--disable-dev-shm-usage", "--disable-gpu"],
                    )
                    ver = b.version
                    await b.close()
                    return ver

            loop = _asyncio.new_event_loop()
            ver = loop.run_until_complete(_try_launch())
            loop.close()
            launch_ok = True
            info["chromium_version"] = ver
        except Exception as e:
            launch_err = f"{type(e).__name__}: {e}"
    info["launch_ok"]  = launch_ok
    info["launch_err"] = launch_err
    return {"ok": True, "diag": info}


@router.get("/active-jobs")
def active_headless_jobs():
    """列出目前在 Railway 背景執行的 headless Playwright 任務（含狀態 / 耗時 / session_id）。

    若清單是空的，表示目前沒有報告正在被 headless 渲染（可能已完成、失敗、或伺服器重啟後消失）。
    """
    from app.services import headless_renderer
    jobs = headless_renderer.list_jobs()
    now = time.time()
    result = []
    for j in jobs:
        started = j.get("started_at") or now
        elapsed_sec = int(now - started)
        result.append({
            "job_id":       j.get("job_id"),
            "report_type":  j.get("report_type"),
            "subject_name": j.get("subject_name"),
            "status":       j.get("status"),         # queued / running / completed / failed
            "elapsed_sec":  elapsed_sec,
            "elapsed_min":  round(elapsed_sec / 60, 1),
            "error":        j.get("error"),
            "vercel_url":   (j.get("vercel_url") or "")[:120],  # 截短，URL 很長
        })
    return {
        "ok":         True,
        "count":      len(result),
        "jobs":       result,
        "playwright": headless_renderer.is_available(),
        "note":       "伺服器重啟後 jobs 會清空（in-memory）。若清單是空的但 DB 仍顯示 generating，請點「⚠️ 重置卡住」再重新生成。"
    }


@router.get("/chapters")
def list_chapters(report_type: str = "life_script", variant: str = "full"):
    """列出章節結構，給前端 UI 顯示進度清單用"""
    chapters = get_chapters(report_type, variant)
    return {
        "report_type":    report_type,
        "variant":        variant,
        "total_sections": count_sections(chapters),
        "chapters":       chapters,
    }


@router.post("/test-section")
def test_section(req: TestSectionRequest):
    """
    立即生成單一節（同步、阻塞）。給「測試生成」按鈕用。
    無 GEMINI_API_KEY 時自動回傳 mock 文字。

    回應約需 30~60 秒（Gemini 2.5 Pro），mock 模式立即回。
    """
    try:
        result = report_generator.generate_one_section(
            chapter_num=req.chapter_num,
            section_num=req.section_num,
            subject_name=req.subject_name,
            report_type=req.report_type,
            variant=req.variant,
            brainwave_data=req.brainwave_data,
        )
        return {"ok": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("test-section 失敗")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.post("/start")
def start_full(req: StartRequest, db: DbSession = Depends(get_db)):
    """啟動報告生成（自動依 report_type 路由到外部系統或內建 Gemini）

    優先序：
      1. use_external=True  → 一定用外部
      2. use_external=False → 一定用內建 Gemini
      3. None（預設）       → 若外部 URL 有設就走外部；否則走內建
    """
    # 若前端沒有傳 brainwave_data（或 bands_avg 為空），嘗試從 DB 重建
    bw = req.brainwave_data
    if req.session_id and (not bw or not (bw or {}).get("bands_avg")):
        try:
            db_bw = _bw_from_session(db, req.session_id)
            if db_bw:
                bw = db_bw
                logger.info("[report-gen/start] brainwave_data 缺失，已從 session_id=%d DB 補充: attn=%s",
                            req.session_id, bw.get("attention_percentage"))
        except Exception as e:
            logger.warning("[report-gen/start] DB 補充 brainwave_data 失敗: %s", e)

    # ─────────────────────────────────────────────────────────────────────
    # 🚨 硬擋：拒絕無效的報告生成請求（避免再產生「全部數據都是 50」的假報告）
    # 規則（任一不通過即拒絕）：
    #   1. 必須有 brainwave_data，且 sample_count >= 30
    #   2. 必須有 attention_percentage 或 bands_avg（其中之一非 0）
    # 這一步擋下：① 前端漏帶資料 ② 主程式被誤觸發 ③ 第三方測試呼叫
    # ─────────────────────────────────────────────────────────────────────
    def _is_valid_bw(d) -> tuple[bool, str]:
        if not d or not isinstance(d, dict):
            return False, "brainwave_data 缺失（None 或非物件）"
        sc = d.get("sample_count") or 0
        try:
            sc = int(sc)
        except Exception:
            sc = 0
        if sc < 30:
            return False, f"檢測樣本數不足（sample_count={sc}，至少需 30 筆即約 30 秒以上的有效檢測）"
        att = d.get("attention_percentage") or 0
        med = d.get("meditation_percentage") or 0
        bands = d.get("bands_avg") or {}
        bands_total = sum(int(v or 0) for v in bands.values()) if bands else 0
        if (int(att or 0) == 0) and (int(med or 0) == 0) and bands_total == 0:
            return False, "腦波數值全為零（疑似未真正接收到腦波儀資料）"
        return True, ""

    valid, why = _is_valid_bw(bw)
    if not valid:
        # 親子報告特例：若所有成員皆由 session_id 提供資料，第一人的腦波仍是必要的
        # 但允許關係報告（marital/parent_child）從 session_id 補充主成員腦波
        is_relation = req.report_type in ("marital", "parent_child")
        has_session_id = bool(req.session_id)
        if not (is_relation and has_session_id):
            logger.warning("[report-gen/start] 拒絕生成（資料不完整）: %s | session_id=%s | name=%s",
                           why, req.session_id, req.subject_name)
            raise HTTPException(
                status_code=400,
                detail={
                    "ok": False,
                    "code": "INVALID_BRAINWAVE",
                    "reason": why,
                    "message": "尚未採集到有效的腦波資料，無法生成報告。請使用腦波儀完成至少 30 秒的有效檢測後再試。",
                    "subject_name": req.subject_name,
                    "session_id": req.session_id,
                    "sample_count": (bw or {}).get("sample_count", 0),
                },
            )
        logger.info("[report-gen/start] 關係報告允許空腦波 (type=%s, session_id=%s), 將由成員 session_id 補充",
                    req.report_type, req.session_id)

    # 🔑 受測者真實姓名解析：若 subject_id 有傳，從 Subject 主檔取真名，避免 PDF 顯示「受測者」
    PLACEHOLDER_NAMES = {"受測者", "陳小明", "測試模式", "test", "Test", "TEST"}
    resolved_name = req.subject_name
    resolved_email = req.subject_email
    if req.subject_id:
        try:
            subj = db.query(M.Subject).filter(M.Subject.subject_id == req.subject_id).first()
            if subj:
                if not resolved_name or resolved_name in PLACEHOLDER_NAMES:
                    resolved_name = subj.name
                    logger.info("[report-gen/start] 用 subject_id=%s 反查真名: %s -> %s",
                                req.subject_id, req.subject_name, resolved_name)
                if not resolved_email:
                    resolved_email = subj.email
        except Exception as e:
            logger.warning("[report-gen/start] 反查 Subject 失敗: %s", e)

    use_ext = req.use_external
    if use_ext is None:
        use_ext = report_orchestrator.is_external_available(req.report_type)

    if use_ext:
        # ── 先建立一筆「pending」Report，讓 admin「報告管理」可立刻看到「⏳ 生成中」狀態 ──
        # 若 Vercel callback /reports/record 成功，會 UPDATE 這筆（不會重覆建）
        # 若失敗或 timeout，這筆仍會保留在 DB 供 admin 查找
        try:
            from sqlalchemy import func as _sqlfunc
            import json as _json

            existing_rep = None
            if req.session_id:
                existing_rep = db.query(M.Report).filter(
                    M.Report.session_id == req.session_id
                ).first()
            if existing_rep is None:
                # 🔑 解析 subject_id：前端有傳 → 直接用；否則從 session 反查
                resolved_sid = req.subject_id
                if resolved_sid is None and req.session_id:
                    try:
                        sess = db.query(M.Session).filter(
                            M.Session.session_id == req.session_id
                        ).first()
                        if sess and sess.subject_id:
                            resolved_sid = sess.subject_id
                    except Exception:
                        pass

                pending_summary = _json.dumps({
                    "subject_name": req.subject_name,
                    "subject_id": resolved_sid,
                    "source": "report-gen/start (pending)",
                }, ensure_ascii=False)
                pending_rep = M.Report(
                    session_id          = req.session_id,
                    subject_id          = resolved_sid,    # ← 雙保險 FK
                    status              = "generating",
                    pdf_url             = None,
                    notify_email        = req.subject_email or None,
                    email_sent          = 0,
                    talent_report_kind  = f"{req.report_type}_{req.variant}",
                    client_summary      = pending_summary,
                    completed_at        = None,
                )
                db.add(pending_rep)
                db.commit()
                logger.info("[report-gen/start] 建立 pending Report (session_id=%s, subject_id=%s, kind=%s_%s)",
                            req.session_id, resolved_sid, req.report_type, req.variant)
        except Exception as pe:
            logger.warning("[report-gen/start] 建立 pending Report 失敗: %s", pe)

        # ── 建立 extra，合併系統欄位與前端傳入的關係報告資料 ──────────────────────
        merged_extra: Dict[str, Any] = dict(req.extra or {})
        merged_extra["session_id"]  = req.session_id
        merged_extra["subject_id"]  = req.subject_id

        # 夫妻報告：若 extra 含 wife_session_id，自動從 DB 補充第二人腦波資料
        if req.report_type in ("marital",) and "wife_session_id" in merged_extra:
            wife_sid = merged_extra["wife_session_id"]
            if wife_sid and not merged_extra.get("wife_brainwave_data"):
                try:
                    wife_bw = _bw_from_session(db, int(wife_sid))
                    if wife_bw:
                        merged_extra["wife_brainwave_data"] = wife_bw
                        logger.info("[report-gen/start] 夫妻第二人腦波已從 session_id=%s 補充", wife_sid)
                except Exception as e:
                    logger.warning("[report-gen/start] 夫妻第二人腦波補充失敗: %s", e)

        # 親子報告：若 extra.members 含 session_id，自動補充各成員腦波資料
        if req.report_type == "parent_child" and merged_extra.get("members"):
            from app.services.report_orchestrator import _bw_to_metrics as _pc_bw_to_metrics
            enriched_members = []
            for m in merged_extra["members"]:
                m = dict(m)
                m_sid = m.get("session_id")
                if m_sid and m.get("present") and not m.get("data"):
                    try:
                        m_bw = _bw_from_session(db, int(m_sid))
                        if m_bw:
                            m["data"] = {
                                "concentration_pct": int(m_bw.get("attention_percentage") or 50),
                                "relaxation_pct":    int(m_bw.get("meditation_percentage") or 50),
                                "metrics":           _pc_bw_to_metrics(m_bw),
                            }
                            logger.info("[report-gen/start] 親子成員 %s 腦波已從 session_id=%s 補充",
                                        m.get("name", "?"), m_sid)
                    except Exception as e:
                        logger.warning("[report-gen/start] 親子成員腦波補充失敗 sid=%s: %s", m_sid, e)
                enriched_members.append(m)
            merged_extra["members"] = enriched_members

        result = report_orchestrator.trigger_external_report(
            report_type=req.report_type,
            subject_name=resolved_name,                # 🔑 用解析後的真名（不是 placeholder）
            subject_email=resolved_email or "",
            subject_age=req.subject_age,
            subject_gender=req.subject_gender or "",
            variant=req.variant,
            chapters_to_generate=req.chapters_to_generate,
            brainwave_data=bw,
            extra=merged_extra,
        )

        # ── 夫妻 / 親子 REST 模式：外部系統不回呼 /reports/record，主動寫 DB ──
        ext_mode = result.get("mode", "")
        if result.get("ok") and ext_mode in ("marital_rest", "parent_child_rest"):
            try:
                from sqlalchemy import func as sqlfunc
                import json as _json
                pdf_url   = result.get("result_url") or result.get("file_path") or ""
                rep_kind  = f"{req.report_type}_{req.variant}"
                summary   = _json.dumps({"subject_name": req.subject_name, "source": ext_mode}, ensure_ascii=False)

                existing = None
                if req.session_id:
                    existing = db.query(M.Report).filter(M.Report.session_id == req.session_id).first()

                if existing is None:
                    new_rep = M.Report(
                        session_id          = req.session_id,
                        status              = "completed",
                        pdf_url             = pdf_url,
                        notify_email        = req.subject_email or None,
                        email_sent          = 0,
                        talent_report_kind  = rep_kind,
                        client_summary      = summary,
                        completed_at        = sqlfunc.now(),
                    )
                    db.add(new_rep)
                else:
                    existing.pdf_url            = pdf_url
                    existing.status             = "completed"
                    existing.notify_email       = req.subject_email or existing.notify_email
                    existing.email_sent         = 0
                    existing.talent_report_kind = rep_kind
                    existing.completed_at       = sqlfunc.now()

                db.commit()
                logger.info("[report-gen/start] %s 報告已寫入 DB，session_id=%s", ext_mode, req.session_id)
            except Exception as db_err:
                logger.warning("[report-gen/start] 寫入 DB 失敗（%s）: %s", ext_mode, db_err)

        return {
            "ok":              result.get("ok", False),
            "mode":            "external",
            "external_mode":   result.get("mode"),         # headless / marital_rest / parent_child_rest / vite_prefill(fallback)
            "report_type":     req.report_type,
            "external_url":    result.get("external_url"),
            "external_job_id": result.get("external_job_id") or result.get("job_id"),
            "job_id":          result.get("job_id"),       # headless mode 用
            "status_url":      result.get("status_url"),
            "result_url":      result.get("result_url"),
            "redirect_url":    result.get("redirect_url"),  # vite_prefill fallback 用
            "note":            result.get("note"),
            "error":           result.get("error"),
        }

    # 內建 Gemini 生成（背景任務）→ 生 PDF → 上傳 GCS → 寄 email 連結
    job_id = report_generator.start_full_report(
        subject_name=resolved_name,                  # 🔑 用真名
        report_type=req.report_type,
        variant=req.variant,
        brainwave_data=bw,
        chapters_to_generate=req.chapters_to_generate,
        subject_email=resolved_email,
        subject_age=req.subject_age,
        subject_gender=req.subject_gender,
        session_id=req.session_id,
    )
    return {"ok": True, "mode": "internal", "job_id": job_id}


@router.get("/download/{job_id}.pdf")
def download_pdf(job_id: str):
    """下載已生成的 PDF（local fallback：當 GCS 未設或上傳失敗時用）"""
    from fastapi.responses import FileResponse
    import os
    path = f"generated_reports/{job_id}.pdf"
    if not os.path.isfile(path):
        raise HTTPException(404, "PDF 不存在或仍在生成中")
    return FileResponse(path, media_type="application/pdf",
                        filename=f"{job_id}.pdf")


@router.get("/status/{job_id}")
def status(job_id: str):
    """輪詢進度（fallback when SSE 不可用）"""
    job = report_generator.get_job(job_id)
    if not job:
        raise HTTPException(404, "找不到此 job")
    return {
        "job_id":              job_id,
        "status":              job.get("status"),
        "progress":            job.get("progress", 0),
        "completed_sections":  job.get("completed_sections", 0),
        "total_sections":      job.get("total_sections", 0),
        "current_chapter":     job.get("current_chapter", ""),
        "current_chapter_num": job.get("current_chapter_num"),
        "current_section":     job.get("current_section", ""),
        "current_section_num": job.get("current_section_num"),
        "chapters_list":       job.get("chapters_list", []),
        "error_message":       job.get("error_message", ""),
        "email_status":        job.get("email_status", "skipped"),
        "email_to":            job.get("email_to", ""),
        "email_from":          job.get("email_from", ""),
        "email_error":         job.get("email_error", ""),
        # 方案 C 新增：PDF/GCS 狀態
        "pdf_status":          job.get("pdf_status", "pending"),
        "pdf_url":             job.get("pdf_url"),
        "pdf_error":           job.get("pdf_error", ""),
        "subject_email":       job.get("subject_email", ""),
        "subject_name":        job.get("subject_name", ""),
        "session_id":          job.get("session_id"),
    }


@router.get("/stream/{job_id}")
def stream(job_id: str):
    """Server-Sent Events 即時進度"""
    def event_gen():
        deadline = time.time() + 60 * 60   # 1 小時上限
        last_completed = -1
        last_ping = time.time()
        PING_INTERVAL = 15

        while time.time() < deadline:
            job = report_generator.get_job(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                return

            cur_completed = job.get("completed_sections", 0)
            status_val    = job.get("status", "pending")

            if cur_completed != last_completed or status_val in ("completed", "error"):
                last_completed = cur_completed
                last_ping = time.time()
                payload = {
                    "status":              status_val,
                    "progress":            job.get("progress", 0),
                    "completed_sections":  cur_completed,
                    "total_sections":      job.get("total_sections", 0),
                    "current_chapter":     job.get("current_chapter", ""),
                    "current_chapter_num": job.get("current_chapter_num"),
                    "current_section":     job.get("current_section", ""),
                    "current_section_num": job.get("current_section_num"),
                    "chapters_list":       job.get("chapters_list", []),
                    "email_status":        job.get("email_status", "skipped"),
                    "email_to":            job.get("email_to", ""),
                    "email_error":         job.get("email_error", ""),
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            elif time.time() - last_ping >= PING_INTERVAL:
                yield ": ping\n\n"
                last_ping = time.time()

            if status_val in ("completed", "error"):
                return
            time.sleep(1.5)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )


@router.get("/result/{job_id}")
def result(job_id: str):
    """取已完成的報告（in-memory 優先，沒有則讀磁碟）"""
    job = report_generator.get_job(job_id)
    if job and job.get("status") == "completed":
        return {
            "job_id":       job_id,
            "subject_name": job.get("subject_name"),
            "report_type":  job.get("report_type"),
            "variant":      job.get("variant"),
            "chapters":     job.get("chapters_list", []),
            "results":      job.get("results", {}),
        }

    file = report_generator.REPORTS_DIR / f"{job_id}.json"
    if file.exists():
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    raise HTTPException(404, "報告不存在或尚未完成")


@router.post("/cancel/{job_id}")
def cancel(job_id: str):
    ok = report_generator.cancel_job(job_id)
    if not ok:
        raise HTTPException(404, "找不到此 job")
    return {"ok": True, "job_id": job_id}
