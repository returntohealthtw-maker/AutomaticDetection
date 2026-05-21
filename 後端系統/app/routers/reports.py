"""
報告檔案管理：
  POST /api/v1/reports/record   外部 React App 完成後 callback，把 GCS URL 寫入 DB
  GET  /api/v1/reports/list     管理員後台用，列出所有報告 + 下載連結
  GET  /api/v1/reports/by-subject/{email}   依 email 查單一受測者的報告紀錄

注意：/record 由外部 Vercel 服務呼叫，使用 shared secret 認證
      （REPORTS_INGEST_SECRET env var）。若沒設則允許任何來源（僅開發用）。
"""
from typing import Optional, List
import time
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core import models as M
from app.core.database import get_db
from app.routers.auth import require_user

router = APIRouter(prefix="/api/v1/reports", tags=["報告管理"])

# 部署版本標記（每次 commit 改一次即可確認最新程式上線）
BUILD_VERSION = "planc-v15-timeout-45min"


@router.get("/diag/full")
def diag_full() -> dict:
    """檢查 GCS、Email Proxy、Headless renderer、部署版本"""
    from app.services import gcs_uploader, email_sender, headless_renderer
    gcs = gcs_uploader.diag()
    return {
        "build_version": BUILD_VERSION,
        "gcs": gcs,
        "vercel_email_proxy": email_sender._vercel_email_proxy(),
        "ingest_secret_set": bool(os.environ.get("REPORTS_INGEST_SECRET")),
        "headless": headless_renderer.diag(),
    }


@router.get("/headless/jobs")
def list_headless_jobs() -> dict:
    """列出所有 headless 任務（管理員觀察用）"""
    from app.services import headless_renderer
    return {
        "jobs": headless_renderer.list_jobs(),
        "active_count": sum(1 for j in headless_renderer.list_jobs() if j.get("status") == "running"),
    }


@router.get("/headless/job/{job_id}")
def get_headless_job(job_id: str) -> dict:
    """單一 headless 任務狀態"""
    from app.services import headless_renderer
    j = headless_renderer.get_job(job_id)
    if not j:
        raise HTTPException(404, "找不到 headless job")
    return j


@router.get("/diag/fontmap")
def diag_fontmap() -> dict:
    """直接看 reportlab 內部的 _ps2tt_map 是不是有 reportcjk，
    並嘗試手動註冊以捕捉真實例外。"""
    import glob, traceback
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.fonts import addMapping
    from reportlab.lib import fonts as rlfonts
    from app.services import pdf_builder

    out: dict = {
        "font_path": pdf_builder._find_cjk_font(),
        "fonts_dir_listing": sorted(glob.glob("/usr/share/fonts/**/*.ttc", recursive=True) +
                                    glob.glob("/usr/share/fonts/**/*.ttf", recursive=True) +
                                    glob.glob("/usr/share/fonts/**/*.otf", recursive=True))[:30],
    }

    # 嘗試逐一註冊看哪個成功
    candidates = []
    fp = pdf_builder._find_cjk_font()
    if fp:
        candidates.append((fp, 0))
        if fp.lower().endswith(".ttc"):
            for i in range(1, 8):
                candidates.append((fp, i))
    out["registration_attempts"] = []
    for (p, si) in candidates:
        try:
            name = f"diag_si{si}"
            pdfmetrics.registerFont(TTFont(name, p, subfontIndex=si))
            out["registration_attempts"].append({"path": p, "subfontIndex": si, "ok": True, "name": name})
        except Exception as e:
            out["registration_attempts"].append({"path": p, "subfontIndex": si, "ok": False,
                                                  "err": f"{type(e).__name__}: {e}"})

    pdf_builder._ensure_font_registered()
    out["_FONT_REGISTERED"] = pdf_builder._FONT_REGISTERED
    out["ps2tt_map_keys"]   = sorted(list(rlfonts._ps2tt_map.keys()))
    out["ps2tt_lookup_reportcjk"] = rlfonts._ps2tt_map.get("reportcjk")
    return out


@router.get("/diag/pdf")
def diag_pdf() -> dict:
    """直接呼叫 render_report_pdf 跑一個極小 sample，回傳完整 traceback。"""
    import traceback, tempfile
    from app.services import pdf_builder
    out_path = os.path.join(tempfile.gettempdir(), "_diag_test.pdf")
    try:
        sample = {
            "1_1": {
                "chapter_num": 1, "section_num": 1,
                "section_title": "測試節", "text": "這是測試。Hello world.",
            }
        }
        chapters = [{"num": 1, "title": "測試章", "icon": "📄"}]
        result = pdf_builder.render_report_pdf(
            out_path=out_path,
            subject_name="測試者",
            report_type="life_script",
            variant="trial",
            chapters_list=chapters,
            results=sample,
            brainwave_data={"attention_percentage": 70},
        )
        size = os.path.getsize(result)
        return {"ok": True, "size_bytes": size, "font_path": pdf_builder._find_cjk_font()}
    except Exception as e:
        return {
            "ok": False,
            "font_path": pdf_builder._find_cjk_font(),
            "error_type": type(e).__name__,
            "error_msg": str(e),
            "traceback": traceback.format_exc(),
        }


# ─── Schemas ─────────────────────────────────────────────────────────────────

class RecordReportIn(BaseModel):
    session_id:    Optional[int] = None
    subject_name:  str = ""
    subject_email: str = ""
    report_type:   str = "life_script"   # life_script / child / parent_child / marital
    variant:       str = "full"           # trial / full / vip
    pdf_url:       str                    # GCS 或 Blob 公開連結
    source:        str = ""               # 哪個外部系統回報的
    # 1 = 由 admin 後台手動觸發寄信（先入 pending）
    # 0 = 外部系統已自行寄信（傳統行為，預設）
    pending_send:  int = 0


class ReportOut(BaseModel):
    report_id:    int
    session_id:   Optional[int]
    subject_name: str
    subject_email: Optional[str]
    pdf_url:      Optional[str]
    status:       str
    talent_report_kind: Optional[str]
    email_sent:   int
    created_at:   Optional[str]
    completed_at: Optional[str]


# ─── 驗 shared secret ───────────────────────────────────────────────────────

def _verify_ingest_secret(authorization: Optional[str], explicit_secret: Optional[str]):
    expected = (os.getenv("REPORTS_INGEST_SECRET") or "").strip()
    if not expected:
        return  # 未設定 → 開發模式，放行
    sent = ""
    if authorization and authorization.lower().startswith("bearer "):
        sent = authorization[7:].strip()
    elif explicit_secret:
        sent = explicit_secret.strip()
    if sent != expected:
        raise HTTPException(status_code=401, detail="REPORTS_INGEST_SECRET 不正確")


# ─── 端點 ────────────────────────────────────────────────────────────────────

@router.post("/record")
def record_report(
    payload: RecordReportIn,
    authorization: Optional[str] = Header(None),
    x_ingest_secret: Optional[str] = Header(None, alias="X-Ingest-Secret"),
    db: Session = Depends(get_db),
):
    """
    外部 React App（成人/兒童）在自動模式完成生成後 callback。
    流程：
      1. 若有 session_id，更新該 Report
      2. 否則建立一筆「孤兒」Report（session_id=NULL），給管理員後台稽核用
    """
    _verify_ingest_secret(authorization, x_ingest_secret)

    if not payload.pdf_url:
        raise HTTPException(status_code=400, detail="缺少 pdf_url")

    now_ts = int(time.time())

    rep = None
    if payload.session_id:
        rep = db.query(M.Report).filter(M.Report.session_id == payload.session_id).first()

    # pending_send=1 表示外部系統尚未寄信，留給後台手動觸發
    email_sent_value = 0 if payload.pending_send else 1

    if rep is None:
        rep = M.Report(
            session_id     = payload.session_id,
            status         = "completed",
            pdf_url        = payload.pdf_url,
            notify_email   = payload.subject_email or None,
            email_sent     = email_sent_value,
            talent_report_kind = f"{payload.report_type}_{payload.variant}",
            client_summary = f'{{"subject_name":"{payload.subject_name}","source":"{payload.source}"}}',
            completed_at   = func.now(),
        )
        db.add(rep)
    else:
        rep.pdf_url = payload.pdf_url
        rep.status = "completed"
        rep.notify_email = payload.subject_email or rep.notify_email
        # 只有當外部系統已寄信時才覆寫 email_sent；pending_send 不要清掉既有狀態
        if not payload.pending_send:
            rep.email_sent = 1
        rep.talent_report_kind = f"{payload.report_type}_{payload.variant}"
        rep.completed_at = func.now()

    db.commit()
    db.refresh(rep)

    return {
        "ok": True,
        "report_id": rep.report_id,
        "session_id": rep.session_id,
        "pdf_url": rep.pdf_url,
    }


@router.get("/list")
def list_reports(
    limit: int = Query(100, le=500),
    only_mine: bool = Query(False, description="True = 只看自己受測者的；False (admin) = 全部"),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """列出已生成的報告 + GCS URL（管理員後台用）"""
    user = require_user(authorization, db)

    q = db.query(M.Report, M.Session).outerjoin(
        M.Session, M.Report.session_id == M.Session.session_id
    ).filter(M.Report.pdf_url.isnot(None))

    # 一般顧問只能看自己的；admin 看全部
    if user.role != "admin" or only_mine:
        q = q.filter(M.Session.consultant_name == user.name)

    rows = q.order_by(M.Report.report_id.desc()).limit(limit).all()
    out = []
    for rep, sess in rows:
        out.append({
            "report_id":    rep.report_id,
            "session_id":   rep.session_id,
            "subject_name": (sess.subject_name if sess else "(無 session)"),
            "subject_email": rep.notify_email,
            "report_kind":  rep.talent_report_kind,
            "pdf_url":      rep.pdf_url,
            "status":       rep.status,
            "email_sent":   rep.email_sent,
            "completed_at": rep.completed_at.isoformat() if rep.completed_at else None,
            "consultant":   (sess.consultant_name if sess else None),
        })
    return {"ok": True, "count": len(out), "reports": out}


@router.get("/by-subject")
def by_subject(
    email: str = Query(..., description="受測者 email"),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """依受測者 email 查報告（受測者自己看用）"""
    require_user(authorization, db)
    rows = db.query(M.Report).filter(
        M.Report.notify_email == email,
        M.Report.pdf_url.isnot(None),
    ).order_by(M.Report.report_id.desc()).limit(20).all()
    return {
        "ok": True,
        "count": len(rows),
        "reports": [
            {
                "report_id": r.report_id,
                "report_kind": r.talent_report_kind,
                "pdf_url": r.pdf_url,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in rows
        ],
    }


@router.get("/diag")
def diag() -> dict:
    """設定診斷"""
    secret = (os.getenv("REPORTS_INGEST_SECRET") or "").strip()
    return {
        "ingest_secret_set": bool(secret),
        "ingest_secret_len": len(secret),
        "note": "未設定時 /record 端點開放任何來源 POST（僅開發用）；正式環境請設定。",
    }


# ─── 報告生成事件監看 ────────────────────────────────────────────────────────
#
# 設計：外部 React App（成人 / 兒童）每跑完一個章節或關鍵步驟，就 POST 一筆事件
# 過來，後台分頁讀取後可即時看到「現在生成到第 5 章」「上傳 GCS 中」「失敗在第 7 章」
# 等狀態，並提供完整的錯誤訊息與耗時。
#
# 事件 phase：
#   started        ── 按下「生成」當下
#   chapter_start  ── 第 N 章 / 子章節開始呼叫 Gemini
#   chapter_done   ── 該章節結束
#   chapter_failed ── 該章節呼叫失敗
#   chapter_retry  ── 該章節重試
#   pdf_render     ── 開始渲染 PDF
#   gcs_upload     ── 上傳 GCS
#   email_sent     ── 自動寄信成功
#   queue          ── 進入待審核佇列（B 流程）
#   done           ── 全部完成
#   failed         ── 整筆失敗
# ────────────────────────────────────────────────────────────────────────────

class ReportEventIn(BaseModel):
    correlation_id: str
    session_id:    Optional[int] = None
    report_type:   str = "life_script"
    variant:       str = "full"
    subject_name:  Optional[str] = None
    subject_email: Optional[str] = None
    source:        Optional[str] = None
    phase:         str
    chapter_num:   Optional[int] = None
    section_id:    Optional[str] = None
    duration_ms:   Optional[int] = None
    error_message: Optional[str] = None
    payload:       Optional[dict] = None


@router.post("/events")
def post_report_event(
    payload: ReportEventIn,
    authorization: Optional[str] = Header(None),
    x_ingest_secret: Optional[str] = Header(None, alias="X-Ingest-Secret"),
    db: Session = Depends(get_db),
):
    """外部 React App callback：寫入單一生成事件
    可被頻繁呼叫（每章節 1-2 筆），所以盡量輕量。
    """
    _verify_ingest_secret(authorization, x_ingest_secret)

    import json as _json
    payload_json = _json.dumps(payload.payload, ensure_ascii=False) if payload.payload else None

    ev = M.ReportGenerationEvent(
        correlation_id  = payload.correlation_id[:64],
        session_id      = payload.session_id,
        report_type     = payload.report_type[:20] if payload.report_type else "life_script",
        variant         = payload.variant[:20] if payload.variant else "full",
        subject_name    = payload.subject_name,
        subject_email   = payload.subject_email,
        source          = payload.source,
        phase           = payload.phase[:30],
        chapter_num     = payload.chapter_num,
        section_id      = payload.section_id[:10] if payload.section_id else None,
        duration_ms     = payload.duration_ms,
        error_message   = payload.error_message,
        payload_json    = payload_json,
    )
    db.add(ev)
    db.commit()
    return {"ok": True, "id": ev.id}


@router.get("/events/sessions")
def list_event_sessions(
    limit: int = Query(50, le=200),
    report_type: Optional[str] = Query(None, description="life_script/child/parent_child/marital"),
    only_failed: bool = Query(False),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """列出最近 N 個生成「會話」（依 correlation_id 分組）
    每組顯示最新狀態：first_phase 時間 / last_phase / 是否完成 / 是否失敗 / 章節進度
    """
    require_user(authorization, db)

    # 找出最近的 correlation_id（依最新事件時間排序）
    sub = (
        db.query(
            M.ReportGenerationEvent.correlation_id.label("cid"),
            func.max(M.ReportGenerationEvent.created_at).label("last_at"),
            func.min(M.ReportGenerationEvent.created_at).label("first_at"),
            func.max(M.ReportGenerationEvent.id).label("max_id"),
            func.count(M.ReportGenerationEvent.id).label("event_count"),
        )
        .group_by(M.ReportGenerationEvent.correlation_id)
    )
    if report_type:
        sub = sub.filter(M.ReportGenerationEvent.report_type == report_type)

    rows = sub.order_by(func.max(M.ReportGenerationEvent.id).desc()).limit(limit).all()

    out: list[dict] = []
    for r in rows:
        cid = r.cid
        # 拿這個 cid 的所有事件，找首事件 + 末事件 + 是否失敗 + 章節數
        evs = (
            db.query(M.ReportGenerationEvent)
            .filter(M.ReportGenerationEvent.correlation_id == cid)
            .order_by(M.ReportGenerationEvent.id.asc())
            .all()
        )
        if not evs:
            continue
        first_ev = evs[0]
        last_ev  = evs[-1]
        failed_evs = [e for e in evs if e.phase in ("failed", "chapter_failed")]
        chapter_done = max((e.chapter_num or 0) for e in evs if e.phase == "chapter_done") if any(e.phase == "chapter_done" for e in evs) else 0
        chapter_total = max((e.chapter_num or 0) for e in evs) if evs else 0

        # 已完成的判定
        is_done   = any(e.phase == "done" for e in evs)
        is_failed = any(e.phase == "failed" for e in evs)
        is_emailed = any(e.phase == "email_sent" for e in evs)
        is_queued  = any(e.phase == "queue" for e in evs)

        item = {
            "correlation_id":  cid,
            "report_type":     first_ev.report_type,
            "variant":         first_ev.variant,
            "subject_name":    first_ev.subject_name,
            "subject_email":   first_ev.subject_email,
            "source":          first_ev.source,
            "session_id":      first_ev.session_id,
            "first_at":        first_ev.created_at.isoformat() if first_ev.created_at else None,
            "last_at":         last_ev.created_at.isoformat()  if last_ev.created_at  else None,
            "last_phase":      last_ev.phase,
            "event_count":     len(evs),
            "chapter_done":    chapter_done,
            "chapter_max":     chapter_total,
            "is_done":         is_done,
            "is_failed":       is_failed,
            "is_emailed":      is_emailed,
            "is_queued":       is_queued,
            "failed_count":    len(failed_evs),
            "last_error":      (failed_evs[-1].error_message if failed_evs else None),
        }
        if not only_failed or (is_failed or failed_evs):
            out.append(item)

    return {"ok": True, "count": len(out), "sessions": out}


@router.get("/events/{correlation_id}")
def get_report_event_timeline(
    correlation_id: str,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """單一 correlation_id 的完整事件時間線（後台「展開」用）"""
    require_user(authorization, db)

    rows = (
        db.query(M.ReportGenerationEvent)
        .filter(M.ReportGenerationEvent.correlation_id == correlation_id)
        .order_by(M.ReportGenerationEvent.id.asc())
        .all()
    )
    if not rows:
        raise HTTPException(404, f"找不到 correlation_id={correlation_id}")

    import json as _json
    return {
        "ok": True,
        "correlation_id": correlation_id,
        "events": [
            {
                "id":            r.id,
                "phase":         r.phase,
                "chapter_num":   r.chapter_num,
                "section_id":    r.section_id,
                "duration_ms":   r.duration_ms,
                "error_message": r.error_message,
                "payload":       (_json.loads(r.payload_json) if r.payload_json else None),
                "created_at":    r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


class SendEmailIn(BaseModel):
    notify_email: Optional[str] = None  # 若不傳，用 Report.notify_email
    custom_message: Optional[str] = None  # 預留：自訂訊息


@router.post("/{report_id}/send-email")
def admin_send_report_email(
    report_id: int,
    body: SendEmailIn,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """管理員後台「預覽 + 寄信」按鈕觸發。
    把 GCS 報告連結寄到 notify_email，並標記 email_sent=1。
    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "需 admin 權限")

    rep = db.query(M.Report).filter(M.Report.report_id == report_id).first()
    if not rep:
        raise HTTPException(404, f"找不到報告 #{report_id}")
    if not rep.pdf_url:
        raise HTTPException(400, "此報告尚未上傳 GCS（pdf_url 為空），無法寄信")

    to = (body.notify_email or rep.notify_email or "").strip()
    if not to or "@" not in to:
        raise HTTPException(400, "收件 email 不存在或格式錯誤，請在報告管理頁先補上 email")

    # 從 talent_report_kind 推斷報告類型
    kind = (rep.talent_report_kind or "life_script_full")
    type_label_map = {
        "life_script":  "成人腦波分析報告",
        "child":        "兒童腦波分析報告",
        "parent_child": "親子腦波報告",
        "marital":      "夫妻腦波報告",
    }
    base = kind.split("_")[0] if "_" in kind else "life_script"
    title = type_label_map.get(kind.split("_")[0] if "_" in kind else "life_script", "腦波分析報告")
    # 嘗試從 client_summary 取受測者姓名
    subject_name = ""
    try:
        import json as _json
        if rep.client_summary:
            cs = _json.loads(rep.client_summary)
            subject_name = cs.get("subject_name", "")
    except Exception:
        pass
    if not subject_name and rep.session_id:
        sess = db.query(M.Session).filter(M.Session.session_id == rep.session_id).first()
        if sess:
            subject_name = sess.subject_name or ""

    from app.services import email_sender
    result = email_sender.send_report_link_email(
        to            = to,
        subject_name  = subject_name or "您",
        report_title  = title,
        pdf_url       = rep.pdf_url,
    )

    if result.get("ok"):
        rep.email_sent = 1
        rep.notify_email = to
        db.commit()
        return {"ok": True, "report_id": report_id, "sent_to": to, "method": result.get("method", "")}
    else:
        raise HTTPException(502, f"寄信失敗：{result.get('error') or result}")


@router.delete("/events/{correlation_id}")
def delete_report_event(
    correlation_id: str,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """刪除一筆 correlation_id 的所有事件（管理員清理用）"""
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "需 admin 權限")
    n = (
        db.query(M.ReportGenerationEvent)
        .filter(M.ReportGenerationEvent.correlation_id == correlation_id)
        .delete()
    )
    db.commit()
    return {"ok": True, "deleted": n}
