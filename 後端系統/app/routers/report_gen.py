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

from fastapi import APIRouter, Depends, HTTPException
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
    """從 EegCapture 重建 brainwave_data，供 brainwave_data 為空時自動補充。"""
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
    def avg(attr): return round(sum(getattr(c, attr, 0) or 0 for c in caps) / n)
    return {
        "attention_percentage":  avg("attention"),
        "meditation_percentage": avg("meditation"),
        "bands_avg": {
            "delta": avg("delta"),
            "theta": avg("theta"),
            "alpha": round((avg("low_alpha") + avg("high_alpha")) / 2),
            "beta":  round((avg("low_beta")  + avg("high_beta"))  / 2),
            "gamma": round((avg("low_gamma") + avg("high_gamma")) / 2),
        },
    }


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
    report_type:          str  = "life_script"
    variant:              str  = "full"
    brainwave_data:       Optional[Dict[str, Any]] = None
    subject_email:        Optional[str] = None       # 完成後自動寄到此 email（None = 不寄）
    chapters_to_generate: Optional[List[int]] = None  # 只生成這些章節（None = 全部）
    use_external:         Optional[bool] = None       # None = 自動判斷（外部設了就用），True/False = 強制
    session_id:           Optional[int] = None        # 從 /eeg/save-stats 拿到的 session_id，外部完成後可 callback


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

    use_ext = req.use_external
    if use_ext is None:
        use_ext = report_orchestrator.is_external_available(req.report_type)

    if use_ext:
        result = report_orchestrator.trigger_external_report(
            report_type=req.report_type,
            subject_name=req.subject_name,
            subject_email=req.subject_email or "",
            subject_age=req.subject_age,
            subject_gender=req.subject_gender or "",
            variant=req.variant,
            chapters_to_generate=req.chapters_to_generate,
            brainwave_data=bw,
            extra={"session_id": req.session_id},  # 給外部 React App 在 callback /reports/record 時帶上
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
    # 這是「方案 C」的核心：使用者下單後可以離開頁面，後端默默跑，完成寄信
    job_id = report_generator.start_full_report(
        subject_name=req.subject_name,
        report_type=req.report_type,
        variant=req.variant,
        brainwave_data=bw,
        chapters_to_generate=req.chapters_to_generate,
        subject_email=req.subject_email,
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
