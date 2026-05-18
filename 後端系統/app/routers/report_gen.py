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

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services import ai_report as report_generator
from app.services import gemini_client
from app.services.report_chapters import get_chapters, count_sections

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/report-gen", tags=["report-gen"])


# ─── Pydantic Schemas ────────────────────────────────────────────────────
class TestSectionRequest(BaseModel):
    chapter_num:    int  = Field(1, ge=1, le=13)
    section_num:    int  = Field(1, ge=1, le=4)
    subject_name:   str  = "受測者"
    report_type:    str  = "life_script"  # life_script / child / parent_child / marital
    variant:        str  = "full"          # trial / full / vip
    brainwave_data: Optional[Dict[str, Any]] = None  # 沒給就用 demo 資料


class StartRequest(BaseModel):
    subject_name:   str  = "受測者"
    report_type:    str  = "life_script"
    variant:        str  = "full"
    brainwave_data: Optional[Dict[str, Any]] = None
    subject_email:  Optional[str] = None  # 將來給 Resend 用


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

    return {
        "gemini_key_set": gemini_client.key_is_set(),
        "model":          _s.GEMINI_TEXT_MODEL if gemini_client.key_is_set() else None,
        "mock_mode":      not gemini_client.key_is_set(),
        "diagnostics": {
            "env_var":     _diag(env_key),
            "settings":    _diag(settings_key),
            "gemini_env_names_seen_by_python": gemini_related_env_names,
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
def start_full(req: StartRequest):
    """啟動完整報告背景生成，立即回 job_id"""
    job_id = report_generator.start_full_report(
        subject_name=req.subject_name,
        report_type=req.report_type,
        variant=req.variant,
        brainwave_data=req.brainwave_data,
    )
    return {"ok": True, "job_id": job_id}


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
