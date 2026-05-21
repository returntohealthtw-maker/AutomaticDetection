"""
報告生成核心邏輯

- format_brainwave_data(): 把 EEG 數據格式化成 prompt 用的文字
- generate_one_section(): 生成單一節（同步、立即回傳）
- start_full_report(): 啟動背景任務生成完整報告（多節）
- get_job(): 查詢生成進度
"""
from __future__ import annotations
import json
import os
import time
import uuid
import threading
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from .report_chapters import (
    get_chapters,
    count_sections,
    ch_zh,
    sec_zh,
)
from .report_prompts import LIFE_SCRIPT_SYSTEM_PROMPT, build_section_prompt
from . import gemini_client

logger = logging.getLogger(__name__)

# 報告存放位置
REPORTS_DIR = Path("generated_reports")
REPORTS_DIR.mkdir(exist_ok=True)

# 任務記憶體存放
_jobs: Dict[str, Dict[str, Any]] = {}
_jobs_lock = threading.Lock()


# ──────────────────────────────────────────────────────────────────────────
# 資料格式化
# ──────────────────────────────────────────────────────────────────────────
def format_brainwave_data(report_json: Dict[str, Any]) -> str:
    """
    把 routers/analysis.py 回傳的 report_json 格式化成文字
    （給 Gemini prompt 使用）
    """
    if not report_json:
        return "（無腦波數據）"

    lines: List[str] = []
    lines.append(f"  整體分數：{report_json.get('overall_score', 'N/A')}")
    lines.append(f"  心智顏色：{report_json.get('mind_color_name', 'N/A')}（{report_json.get('mind_color_character', '')}）")
    lines.append(f"  八卦類型：{report_json.get('bagua_name', 'N/A')}")
    lines.append(f"  MBTI：{report_json.get('mbti', 'N/A')} {report_json.get('mbti_zh', '')}")
    lines.append(f"  專注度：{report_json.get('attention_percentage', 'N/A')}%")
    lines.append(f"  放鬆度：{report_json.get('meditation_percentage', 'N/A')}%")
    lines.append(f"  身心平衡：{report_json.get('mind_balance', 'N/A')}")
    lines.append(f"  腦力指數：{report_json.get('mind_energy', 'N/A')}")
    lines.append(f"  壓力指數：{report_json.get('mind_stress', 'N/A')}")
    lines.append("  腦波七大指標：")
    bands = report_json.get("bands", []) or []
    for b in bands:
        lines.append(f"    {b.get('name', '')}：{b.get('value', 'N/A')}%")
    return "\n".join(lines)


def _demo_brainwave_data() -> Dict[str, Any]:
    """測試用的腦波數據（seed=42 跑出的範例）"""
    return {
        "overall_score": 53,
        "mind_color_name": "綠腦人",
        "mind_color_character": "努力工作的建築師",
        "bagua_name": "坎",
        "mbti": "INTP",
        "mbti_zh": "邏輯學家",
        "attention_percentage": 87,
        "meditation_percentage": 60,
        "mind_balance": 57,
        "mind_energy": 43,
        "mind_stress": 51,
        "bands": [
            {"name": "Delta 深度休息",   "value": 28},
            {"name": "Theta 直覺能力",   "value": 66},
            {"name": "High Alpha 氣血飽滿", "value": 56},
            {"name": "Low Alpha 內在安定",  "value": 49},
            {"name": "High Beta 高度專注",  "value": 95},
            {"name": "Low Beta 邏輯分析",   "value": 100},
            {"name": "Mid Gamma 觀察環境",  "value": 50},
            {"name": "Low Gamma 慈悲柔軟",  "value": 50},
        ],
    }


# ──────────────────────────────────────────────────────────────────────────
# 單節生成（同步、立即回傳）
# ──────────────────────────────────────────────────────────────────────────
def generate_one_section(
    chapter_num: int,
    section_num: int,
    subject_name: str,
    report_type: str = "life_script",
    variant: str = "full",
    brainwave_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    生成「第 X 章第 Y 節」的單一節內容，同步回傳。
    給 demo / 測試使用。
    """
    chapters = get_chapters(report_type, variant)
    chapter = next((c for c in chapters if c["num"] == chapter_num), None)
    if not chapter:
        raise ValueError(f"找不到第 {chapter_num} 章")
    section = next((s for s in chapter["sections"] if s["num"] == section_num), None)
    if not section:
        raise ValueError(f"第 {chapter_num} 章找不到第 {section_num} 節")

    bw = brainwave_data or _demo_brainwave_data()
    bw_str = format_brainwave_data(bw)

    prompt = build_section_prompt(
        subject_data_str=bw_str,
        chapter=chapter,
        section=section,
        subject_name=subject_name,
        variant=variant,
    )

    started_at = time.time()
    text = gemini_client.generate_text(
        prompt=prompt,
        system_instruction=LIFE_SCRIPT_SYSTEM_PROMPT,
        temperature=0.78,
        max_output_tokens=4096,
    )
    elapsed = round(time.time() - started_at, 1)

    return {
        "chapter_num": chapter_num,
        "chapter_title": chapter["title"],
        "chapter_icon": chapter["icon"],
        "section_num": section_num,
        "section_title": section["title"],
        "subject_name": subject_name,
        "report_type": report_type,
        "variant": variant,
        "text": text,
        "elapsed_sec": elapsed,
        "key_used": gemini_client.key_is_set(),
    }


# ──────────────────────────────────────────────────────────────────────────
# 完整報告（背景任務）
# ──────────────────────────────────────────────────────────────────────────
def _run_full_generation(
    job_id: str,
    subject_name: str,
    report_type: str,
    variant: str,
    brainwave_data: Dict[str, Any],
    chapters_to_generate: Optional[List[int]] = None,
    subject_email: Optional[str] = None,
):
    """背景 thread：依序生成所有節，可選擇只生成特定章節，生成完寄 email"""
    from . import email_sender  # 避免循環匯入

    job = _jobs[job_id]
    job["status"] = "running"
    job["started_at"] = time.time()

    try:
        chapters = get_chapters(report_type, variant)
        # 過濾出指定章節
        if chapters_to_generate:
            wanted = set(chapters_to_generate)
            chapters = [c for c in chapters if c["num"] in wanted]
        total = count_sections(chapters)
        job["total_sections"] = total
        job["chapters_list"] = [
            {"num": c["num"], "title": c["title"], "icon": c["icon"]} for c in chapters
        ]

        bw_str = format_brainwave_data(brainwave_data)
        completed = 0

        for chapter in chapters:
            if job.get("cancelled"):
                break
            job["current_chapter"] = chapter["title"]
            job["current_chapter_num"] = chapter["num"]

            for section in chapter["sections"]:
                if job.get("cancelled"):
                    break
                job["current_section"] = (
                    f"第{ch_zh(chapter['num'])}章・第{sec_zh(section['num'])}節：{section['title']}"
                )
                job["current_section_num"] = section["num"]

                prompt = build_section_prompt(
                    subject_data_str=bw_str,
                    chapter=chapter,
                    section=section,
                    subject_name=subject_name,
                    variant=variant,
                )

                try:
                    text = gemini_client.generate_text(
                        prompt=prompt,
                        system_instruction=LIFE_SCRIPT_SYSTEM_PROMPT,
                        temperature=0.78,
                        max_output_tokens=4096,
                    )
                except Exception as e:
                    text = f"（此節生成失敗：{type(e).__name__}: {str(e)[:100]}）"
                    logger.error("section %d_%d 失敗: %s", chapter["num"], section["num"], e)

                key = f"{chapter['num']}_{section['num']}"
                job["results"][key] = {
                    "text": text,
                    "chapter_num": chapter["num"],
                    "chapter_title": chapter["title"],
                    "chapter_icon": chapter["icon"],
                    "section_num": section["num"],
                    "section_title": section["title"],
                }

                completed += 1
                job["completed_sections"] = completed
                job["progress"] = int(completed / total * 100)

                # 避免 503 burst
                time.sleep(2)

        # 寫到磁碟
        try:
            payload = {
                "job_id":         job_id,
                "subject_name":   subject_name,
                "subject_email":  subject_email,
                "report_type":    report_type,
                "variant":        variant,
                "chapters":       job["chapters_list"],
                "results":        job["results"],
                "brainwave_data": brainwave_data,
                "created_at":     time.time(),
            }
            with open(REPORTS_DIR / f"{job_id}.json", "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            job["save_error"] = str(e)
            logger.error("save report failed: %s", e)

        # ── 生成 PDF + 上傳 GCS + 寫回 DB ────────────────────────────
        pdf_url = None
        if not job.get("cancelled"):
            try:
                from . import pdf_builder, gcs_uploader
                pdf_local = f"generated_reports/{job_id}.pdf"
                pdf_builder.render_report_pdf(
                    out_path=pdf_local,
                    subject_name=subject_name,
                    report_type=report_type,
                    variant=variant,
                    chapters_list=job["chapters_list"],
                    results=job["results"],
                    brainwave_data=brainwave_data,
                    subject_age=job.get("subject_age"),
                    subject_gender=job.get("subject_gender"),
                )
                job["pdf_status"] = "rendered"

                # 上傳 GCS（取 signed URL）
                from .pdf_builder import REPORTS_LABEL
                safe_name = (subject_name or "report").replace("/", "_").replace(" ", "_")
                object_name = f"reports/{report_type}_{variant}_{safe_name}_{job_id}.pdf"
                signed_url = gcs_uploader.upload_pdf(pdf_local, object_name)

                if signed_url:
                    pdf_url = signed_url
                    job["pdf_status"] = "uploaded"
                    job["pdf_url"] = pdf_url
                    logger.info("✅ PDF 已上傳 GCS → %s", object_name)
                else:
                    # GCS 沒設好 → 用主後端的下載端點
                    job["pdf_status"] = "local_only"
                    base = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
                    if base and not base.startswith("http"):
                        base = f"https://{base}"
                    pdf_url = f"{base}/api/v1/report-gen/download/{job_id}.pdf" if base else None
                    job["pdf_url"] = pdf_url
                    logger.warning("⚠ GCS 未設好，使用本地連結：%s", pdf_url)

                # 寫回 DB reports 表（若有 session_id）
                if pdf_url and job.get("session_id"):
                    try:
                        from app.core.database import SessionLocal
                        from app.core import models as M
                        db = SessionLocal()
                        try:
                            rep = db.query(M.Report).filter(
                                M.Report.session_id == job["session_id"]
                            ).first()
                            if rep:
                                rep.pdf_url = pdf_url
                                rep.status = "completed"
                                rep.notify_email = subject_email or rep.notify_email
                            else:
                                rep = M.Report(
                                    session_id=job["session_id"],
                                    pdf_url=pdf_url,
                                    status="completed",
                                    notify_email=subject_email,
                                )
                                db.add(rep)
                            db.commit()
                            logger.info("✅ DB reports 已更新 session_id=%s", job["session_id"])
                        finally:
                            db.close()
                    except Exception as e:
                        logger.exception("DB 更新失敗：%s", e)
            except Exception as e:
                job["pdf_status"] = "failed"
                job["pdf_error"] = f"{type(e).__name__}: {e}"
                logger.exception("PDF/GCS 流程例外")

        # ── 寄 Email（GCS 連結版；若沒 PDF URL 才退回全文版）─────────
        job["email_status"] = "skipped"
        if subject_email and not job.get("cancelled"):
            try:
                if pdf_url:
                    from .pdf_builder import REPORTS_LABEL
                    report_title = REPORTS_LABEL(report_type, variant)
                    email_result = email_sender.send_report_link_email(
                        to=subject_email,
                        subject_name=subject_name,
                        report_title=report_title,
                        pdf_url=pdf_url,
                        expires_days=7,
                    )
                else:
                    # 沒 PDF URL 時 fallback：寄全文版
                    merged_text_parts = []
                    first_chapter = job["chapters_list"][0] if job["chapters_list"] else None
                    for key, sec in job["results"].items():
                        merged_text_parts.append(
                            f"【第{sec['section_num']}節：{sec['section_title']}】\n\n{sec['text']}"
                        )
                    merged_text = "\n\n\n".join(merged_text_parts)
                    ch_title = (
                        f"第{first_chapter['num']}章：{first_chapter['title']}"
                        if first_chapter else "AI 分析報告"
                    )
                    ch_icon = (first_chapter or {}).get("icon", "📄")
                    email_result = email_sender.send_report_email(
                        to=subject_email,
                        subject_name=subject_name,
                        chapter_title=ch_title,
                        chapter_text=merged_text,
                        chapter_icon=ch_icon,
                    )

                if email_result.get("ok"):
                    job["email_status"] = "sent"
                    job["email_to"]     = subject_email
                    job["email_from"]   = email_result.get("from")
                    logger.info("✅ Email 寄出 → %s", subject_email)
                else:
                    job["email_status"] = "failed"
                    job["email_error"]  = email_result.get("error", "unknown")
                    logger.error("❌ Email 失敗：%s", email_result.get("error"))
            except Exception as e:
                job["email_status"] = "failed"
                job["email_error"]  = f"{type(e).__name__}: {e}"
                logger.exception("email 寄發例外")

        job["status"] = "completed"
        job["finished_at"] = time.time()

    except Exception as e:
        logger.exception("背景任務崩潰")
        job["status"] = "error"
        job["error_message"] = f"{type(e).__name__}: {e}"


def start_full_report(
    subject_name: str,
    report_type: str = "life_script",
    variant: str = "full",
    brainwave_data: Optional[Dict[str, Any]] = None,
    chapters_to_generate: Optional[List[int]] = None,
    subject_email: Optional[str] = None,
    subject_age: Optional[int] = None,
    subject_gender: Optional[str] = None,
    session_id: Optional[int] = None,
) -> str:
    """
    啟動報告背景生成，立即回傳 job_id

    Args:
        chapters_to_generate: 只生成這些章節（如 [1]）。None = 該 variant 全部章節
        subject_email:        生成完自動寄到此 email（None = 不寄）
        session_id:           EEG session_id，用於把 PDF URL 寫回 reports 表
    """
    bw = brainwave_data or _demo_brainwave_data()

    job_id = str(uuid.uuid4())
    chapters = get_chapters(report_type, variant)
    if chapters_to_generate:
        wanted = set(chapters_to_generate)
        chapters = [c for c in chapters if c["num"] in wanted]
    est = count_sections(chapters)

    with _jobs_lock:
        _jobs[job_id] = {
            "job_id":              job_id,
            "status":              "pending",
            "progress":            0,
            "completed_sections":  0,
            "total_sections":      est,
            "current_section":     "準備中…",
            "current_chapter":     "",
            "current_chapter_num": None,
            "current_section_num": None,
            "chapters_list":       [],
            "results":             {},
            "subject_name":        subject_name,
            "subject_age":         subject_age,
            "subject_gender":      subject_gender,
            "subject_email":       subject_email,
            "report_type":         report_type,
            "variant":             variant,
            "chapters_to_generate": chapters_to_generate,
            "email_status":        "pending" if subject_email else "skipped",
            "pdf_status":          "pending",
            "pdf_url":             None,
            "session_id":          session_id,
        }

    t = threading.Thread(
        target=_run_full_generation,
        args=(job_id, subject_name, report_type, variant, bw, chapters_to_generate, subject_email),
        daemon=True,
    )
    t.start()
    return job_id


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    return _jobs.get(job_id)


def cancel_job(job_id: str) -> bool:
    job = _jobs.get(job_id)
    if not job:
        return False
    job["cancelled"] = True
    return True
