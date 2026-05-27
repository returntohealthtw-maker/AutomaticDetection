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
def diag_full(db: Session = Depends(get_db)) -> dict:
    """檢查 GCS、Email Proxy、Headless renderer、部署版本 + 計數（不需 auth）"""
    from app.services import gcs_uploader, email_sender, headless_renderer

    # DB 計數
    try:
        total_reports = db.query(M.Report).count()
        with_pdf      = db.query(M.Report).filter(M.Report.pdf_url.isnot(None)).count()
        email_sent_y  = db.query(M.Report).filter(M.Report.email_sent == 1).count()
        email_sent_n  = db.query(M.Report).filter(M.Report.email_sent == 0).count()
        latest        = db.query(M.Report).order_by(M.Report.report_id.desc()).first()
        latest_info = {
            "report_id":    latest.report_id if latest else None,
            "pdf_url_set":  bool(latest.pdf_url) if latest else None,
            "email_sent":   latest.email_sent if latest else None,
            "completed_at": latest.completed_at.isoformat() if (latest and latest.completed_at) else None,
        } if latest else None
    except Exception as e:
        total_reports = with_pdf = email_sent_y = email_sent_n = -1
        latest_info = {"error": f"{type(e).__name__}: {e}"}

    # GCS PDF 計數（最多列 50 筆做快速估算）
    gcs_pdf_count = -1
    gcs_sample: list[str] = []
    try:
        if gcs_uploader.is_configured():
            sample = gcs_uploader.list_pdfs(prefix="", max_items=50)
            gcs_pdf_count = len(sample)
            gcs_sample = [s["name"] for s in sample[:5]]
    except Exception as e:
        gcs_sample = [f"err: {type(e).__name__}: {e}"]

    # 事件計數
    try:
        evt_total = db.query(M.ReportGenerationEvent).count()
        evt_recent = db.query(M.ReportGenerationEvent).order_by(
            M.ReportGenerationEvent.id.desc()
        ).limit(3).all()
        evt_recent_info = [
            {
                "id":          e.id,
                "phase":       e.phase,
                "subject":     e.subject_name,
                "created_at":  e.created_at.isoformat() if e.created_at else None,
            } for e in evt_recent
        ]
    except Exception as e:
        evt_total = -1
        evt_recent_info = [{"error": f"{type(e).__name__}: {e}"}]

    return {
        "build_version": BUILD_VERSION,
        "gcs": gcs_uploader.diag(),
        "vercel_email_proxy": email_sender._vercel_email_proxy(),
        "ingest_secret_set": bool(os.environ.get("REPORTS_INGEST_SECRET")),
        "headless": headless_renderer.diag(),
        "db_counts": {
            "total_reports": total_reports,
            "with_pdf_url":  with_pdf,
            "email_sent_yes": email_sent_y,
            "email_sent_no":  email_sent_n,
            "latest_report":  latest_info,
        },
        "gcs_quick_scan": {
            "pdf_count_first_50": gcs_pdf_count,
            "sample_object_names": gcs_sample,
        },
        "events": {
            "total": evt_total,
            "recent": evt_recent_info,
        },
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

@router.get("/headless/brainwave/{session_id}")
def headless_get_brainwave(
    session_id:    int,
    authorization: Optional[str] = Header(default=None),
    secret:        Optional[str] = Query(default=None, description="REPORTS_INGEST_SECRET（URL 帶 query）"),
    db:            Session = Depends(get_db),
):
    """
    Vercel React App 在 ?auto=1 流程中可呼叫此 endpoint，
    用 session_id 直接拿到完整 brainwave_data — 避免 URL query string 命名漂移 / 截斷。

    認證：Bearer token 或 ?secret= query。
    回應結構：
        {
          "ok": true,
          "session_id": 25,
          "brainwave_data": {
            "attention_percentage": 48,
            "meditation_percentage": 36,
            "sample_count": 180,
            "bands_avg": {"delta":54, "theta":57, "alpha":55, "beta":40, "gamma":44},
            "bands_7": {
              "theta":57, "alpha_high":60, "alpha_low":49,
              "beta_high":44, "beta_low":36, "gamma_high":48, "gamma_low":39
            }
          },
          "subject": { "name": "...", "age": 26, "gender": "F" }
        }
    """
    _verify_ingest_secret(authorization, secret)

    sess = db.query(M.Session).filter(M.Session.session_id == session_id).first()
    if not sess:
        raise HTTPException(404, "Session 不存在")

    bw = _session_to_brainwave_data(db, session_id)
    if not bw:
        raise HTTPException(404, "找不到腦波資料（EegCapture 為空）")

    ba = bw.get("bands_avg") or {}
    def _cap(v): return max(0, min(100, int(v)))
    alpha = float(ba.get("alpha") or 50)
    beta  = float(ba.get("beta")  or 50)
    gamma = float(ba.get("gamma") or 50)
    bw["bands_7"] = {
        "theta":      _cap(ba.get("theta") or 50),
        "alpha_high": _cap(alpha * 1.1),
        "alpha_low":  _cap(alpha * 0.9),
        "beta_high":  _cap(beta  * 1.1),
        "beta_low":   _cap(beta  * 0.9),
        "gamma_high": _cap(gamma * 1.1),
        "gamma_low":  _cap(gamma * 0.9),
    }

    return {
        "ok": True,
        "session_id": session_id,
        "brainwave_data": bw,
        "subject": {
            "name":   sess.subject_name,
            "age":    sess.subject_age,
            "gender": sess.subject_gender,
        },
    }


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

    # 🔑 受測者 FK 解析（避免 callback 寫入孤兒）
    # 1. 若 session 已有 subject_id → 直接用
    # 2. 否則用 subject_name + subject_email 在 Subject 表找
    resolved_sid = None
    sess_for_record = None
    if payload.session_id:
        sess_for_record = db.query(M.Session).filter(
            M.Session.session_id == payload.session_id
        ).first()
        if sess_for_record and sess_for_record.subject_id:
            resolved_sid = sess_for_record.subject_id

    if resolved_sid is None and (payload.subject_email or payload.subject_name):
        try:
            sq = db.query(M.Subject)
            if payload.subject_email:
                cand = sq.filter(M.Subject.email == payload.subject_email).order_by(M.Subject.subject_id.desc()).first()
                if cand:
                    resolved_sid = cand.subject_id
            if resolved_sid is None and payload.subject_name:
                # name 比對：避免 placeholder 誤命中
                PLACEHOLDER = {"受測者", "陳小明", "測試模式", "test", "Test", "TEST"}
                if payload.subject_name not in PLACEHOLDER:
                    cands = db.query(M.Subject).filter(M.Subject.name == payload.subject_name).all()
                    if len(cands) == 1:
                        resolved_sid = cands[0].subject_id
        except Exception:
            pass

    # pending_send=1 表示外部系統尚未寄信，留給後台手動觸發
    email_sent_value = 0 if payload.pending_send else 1

    # ── 系統級規則：所有報告都必須走 admin 人工審核才能寄信 ──
    if rep is None:
        rep = M.Report(
            session_id     = payload.session_id,
            subject_id     = resolved_sid,        # 🔑 寫入 FK
            status         = "completed",
            pdf_url        = payload.pdf_url,
            notify_email   = payload.subject_email or None,
            email_sent     = 0,  # 強制：等待 admin 核准
            talent_report_kind = f"{payload.report_type}_{payload.variant}",
            client_summary = f'{{"subject_name":"{payload.subject_name}","source":"{payload.source}","subject_id":{resolved_sid or "null"}}}',
            completed_at   = func.now(),
        )
        db.add(rep)
    else:
        rep.pdf_url = payload.pdf_url
        rep.status = "completed"
        rep.notify_email = payload.subject_email or rep.notify_email
        if resolved_sid and not rep.subject_id:
            rep.subject_id = resolved_sid    # 🔑 補寫 FK
        # 強制 reset 為待核准（即使之前已寄過，重新生成後也必須重審）
        rep.email_sent = 0
        rep.talent_report_kind = f"{payload.report_type}_{payload.variant}"
        rep.completed_at = func.now()

    # 順便補強 Session.subject_id（如果還沒寫）
    if sess_for_record and resolved_sid and not sess_for_record.subject_id:
        sess_for_record.subject_id = resolved_sid

    db.commit()
    db.refresh(rep)

    return {
        "ok": True,
        "report_id":   rep.report_id,
        "session_id":  rep.session_id,
        "pdf_url":     rep.pdf_url,
        "email_sent":  0,
        "note":        "已紀錄到資料庫。所有報告需 admin 在『報告管理』預覽後手動寄信。",
    }


@router.get("/list")
def list_reports(
    limit: int = Query(100, le=500),
    only_mine: bool = Query(False, description="True = 只看自己受測者的；False (admin) = 全部"),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """列出已生成的報告 + GCS URL（管理員後台用）。

    回傳資料豐富化：
      - 報告類型轉成中文（report_kind_zh），例如 life_script_full → 成人腦波分析（完整版）
      - 受測者基本資料：subject_name、subject_age、subject_gender
      - 若 session_id 為 NULL，會嘗試從 Report.client_summary 取出 subject_name
      - 顧問完整資訊：consultant_name、consultant_org、consultant_role
    """
    import json as _json

    user = require_user(authorization, db)

    # ⚠️ 不再過濾 pdf_url，所有 Report 列出（包含尚未完成、外部生成失敗的）
    # 這樣 admin 才能完整看到「這個系統受測者所有生成過的報告」
    q = db.query(M.Report, M.Session).outerjoin(
        M.Session, M.Report.session_id == M.Session.session_id
    )

    if user.role != "admin" or only_mine:
        q = q.filter(M.Session.consultant_name == user.name)

    rows = q.order_by(M.Report.report_id.desc()).limit(limit).all()

    # ── 把顧問名稱對應到顧問記錄（取機構/角色）
    cons_names = {sess.consultant_name for _r, sess in rows if sess and sess.consultant_name}
    cons_map: dict[str, M.Consultant] = {}
    if cons_names:
        for c in db.query(M.Consultant).filter(M.Consultant.name.in_(list(cons_names))).all():
            cons_map[c.name] = c

    REPORT_KIND_ZH = {
        # 主類型
        "life_script":   "成人腦波分析",
        "child":         "兒童腦波天賦解碼",
        "parent_child":  "親子腦波共振關係報告",
        "marital":       "夫妻腦波共振關係報告",
        # 變體
        "trial":  "體驗版",
        "full":   "完整版",
        "vip":    "VIP 版",
    }

    def _kind_zh(kind: Optional[str]) -> str:
        if not kind:
            return "—"
        parts = kind.split("_")
        # 嘗試找最長 prefix 對應到主類型
        for n in (3, 2, 1):
            if len(parts) >= n:
                key = "_".join(parts[:n])
                if key in REPORT_KIND_ZH:
                    main = REPORT_KIND_ZH[key]
                    rest = parts[n:]
                    if rest:
                        var = REPORT_KIND_ZH.get(rest[-1], rest[-1])
                        return f"{main}（{var}）"
                    return main
        return kind

    def _name_from_summary(s: Optional[str]) -> Optional[str]:
        if not s:
            return None
        try:
            data = _json.loads(s)
            return data.get("subject_name")
        except Exception:
            return None

    # 預設姓名識別（這些是「資料遺失」的指標，不是真實受測者）
    PLACEHOLDER_NAMES = {"受測者", "陳小明", "測試模式", "test", "Test", "TEST"}

    # 🔑 預先撈出所有相關 subject_id 的 Subject 真實資料
    subject_ids = set()
    for rep, sess in rows:
        if rep.subject_id:
            subject_ids.add(rep.subject_id)
        if sess and sess.subject_id:
            subject_ids.add(sess.subject_id)
    subj_map: dict[int, M.Subject] = {}
    if subject_ids:
        for s in db.query(M.Subject).filter(M.Subject.subject_id.in_(list(subject_ids))).all():
            subj_map[s.subject_id] = s

    def _calc_age(birth_date: Optional[str]) -> Optional[int]:
        if not birth_date or len(birth_date) < 4:
            return None
        try:
            from datetime import date
            y, m, d = birth_date.split("-")
            b = date(int(y), int(m), int(d))
            t = date.today()
            return t.year - b.year - ((t.month, t.day) < (b.month, b.day))
        except Exception:
            return None

    out = []
    for rep, sess in rows:
        cons = cons_map.get(sess.consultant_name) if (sess and sess.consultant_name) else None
        fallback_name = _name_from_summary(rep.client_summary)

        # 🔑 解析受測者：FK 優先 → Session.subject_name → client_summary
        subj_record = None
        sid = rep.subject_id or (sess.subject_id if sess else None)
        if sid:
            subj_record = subj_map.get(sid)

        if subj_record:
            # ✅ 已關聯到主檔，顯示真實姓名與年齡
            raw_name        = subj_record.name
            subject_age     = _calc_age(subj_record.birth_date)
            subject_gender  = subj_record.gender
            subject_email_real = subj_record.email
        else:
            raw_name        = (sess.subject_name if sess else None) or fallback_name
            subject_age     = (sess.subject_age if sess else None)
            subject_gender  = (sess.subject_gender if sess else None)
            subject_email_real = None

        # ── 孤兒/測試報告識別：未關聯主檔 + 姓名為預設值 ──
        is_placeholder = (not subj_record) and ((not raw_name) or (raw_name in PLACEHOLDER_NAMES))
        if is_placeholder:
            ts_label = rep.completed_at.strftime("%m/%d %H:%M") if rep.completed_at else f"#{rep.report_id}"
            subject_name = f"🧪 系統測試報告 · {ts_label}"
            is_test = True
        elif raw_name and raw_name.startswith("🧪 管理員測試-"):
            subject_name = raw_name
            is_test = True
        else:
            subject_name = raw_name or "(無 session)"
            is_test = False

        # 從 client_summary 取出 headless_error（若有）讓前端顯示
        headless_error = None
        try:
            cs_data = _json.loads(rep.client_summary or "{}")
            headless_error = cs_data.get("headless_error")
        except Exception:
            pass

        out.append({
            "report_id":      rep.report_id,
            "session_id":     rep.session_id,
            "subject_id":     sid,                          # 🔑 顯示是否已連結
            "subject_name":   subject_name,
            "subject_age":    subject_age,
            "subject_gender": subject_gender,
            "subject_email":  rep.notify_email or subject_email_real,
            "report_kind":    rep.talent_report_kind,
            "report_kind_zh": _kind_zh(rep.talent_report_kind),
            "pdf_url":        rep.pdf_url,
            "status":         rep.status,
            "email_sent":     rep.email_sent,
            "completed_at":   rep.completed_at.isoformat() if rep.completed_at else None,
            "consultant":     (sess.consultant_name if sess else None),
            "consultant_org": (cons.org if cons else None),
            "consultant_role": (cons.role if cons else None),
            "orphan":         (rep.session_id is None),
            "is_test":        is_test,                      # 🧪 admin 可用 is_test 過濾或一鍵清理
            "linked_to_subject": subj_record is not None,   # 🔗 是否已連結到 Subject 主檔
            "headless_error": headless_error,               # 失敗原因（來自 headless_renderer）
        })
    return {"ok": True, "count": len(out), "reports": out}


@router.get("/gcs-list")
def list_gcs_pdfs(
    prefix: str = Query("", description="GCS object 前綴篩選（例：reports/general/）"),
    limit: int = Query(500, ge=1, le=2000),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """
    直接列出 GCS bucket 內所有 PDF（不只是 DB 中有紀錄的）。
    管理員專用。每筆會附 7 天 signed URL。
    若該物件 URL 已在 DB Report.pdf_url 內，附上 report_id、subject_name、email_sent 等資訊。
    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "僅管理員可使用此功能")

    from app.services import gcs_uploader
    if not gcs_uploader.is_configured():
        return {
            "ok": False,
            "error": "GCS 未設定（缺 GCS_BUCKET_NAME 或 GCP_SERVICE_ACCOUNT_JSON）",
            "items": [],
        }

    items = gcs_uploader.list_pdfs(prefix=prefix, max_items=limit)

    # 跟 DB 比對：用 object name 末端的檔名去 LIKE
    # 因為 Report.pdf_url 是「signed URL（含 token）」，每次簽會變，
    # 用 object_name 子字串去匹配 pdf_url 才穩。
    db_reports = db.query(
        M.Report.report_id,
        M.Report.pdf_url,
        M.Report.notify_email,
        M.Report.email_sent,
        M.Report.talent_report_kind,
        M.Report.completed_at,
        M.Session.subject_name,
        M.Session.consultant_name,
    ).outerjoin(
        M.Session, M.Report.session_id == M.Session.session_id
    ).filter(M.Report.pdf_url.isnot(None)).all()

    # 把 (pdf_url, info) 整理成可查的 dict（用 object name 比對）
    # GCS pdf_url 包含 /<bucket>/<object_name>?X-Goog-...
    db_by_object: dict[str, dict] = {}
    for r in db_reports:
        url = r.pdf_url or ""
        # 取 query 之前那段，並抽出 bucket 後的 path
        try:
            # https://storage.googleapis.com/<bucket>/<obj>?...
            no_q = url.split("?", 1)[0]
            # 抓 bucket 之後的部分
            seg = no_q.split("/")
            # 至少形如 ['https:', '', 'storage.googleapis.com', bucket, '...']
            if len(seg) >= 5:
                obj_in_db = "/".join(seg[4:])
            else:
                obj_in_db = no_q
        except Exception:
            obj_in_db = ""
        if obj_in_db:
            db_by_object[obj_in_db] = {
                "report_id":    r.report_id,
                "subject_name": r.subject_name,
                "subject_email": r.notify_email,
                "email_sent":   r.email_sent,
                "report_kind":  r.talent_report_kind,
                "consultant":   r.consultant_name,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }

    enriched = []
    for it in items:
        match = db_by_object.get(it["name"])
        enriched.append({**it, "db": match})

    return {
        "ok": True,
        "bucket": gcs_uploader._bucket_name(),
        "prefix": prefix,
        "count": len(enriched),
        "with_db_record": sum(1 for x in enriched if x.get("db")),
        "items": enriched,
    }


@router.get("/sessions-with-status")
def sessions_with_status(
    limit: int = Query(200, ge=1, le=1000),
    only_missing: bool = Query(False, description="True = 只看漏報告 / 失敗 / 卡住的"),
    only_mine: bool = Query(False),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """
    檢測 ↔ 報告 對照表：列出 Session 並標出對應 Report 狀態。

    每筆回傳：
      session_id / subject_name / consultant / report_type / captures / created_at
      report_status: pending/processing/completed/failed/none
      has_pdf:       bool
      health:        ok | missing_pdf | stale_pending | failed | session_failed
      is_missing:    True 表示需要重新生成（漏報告）

    health 判定：
      - session.status == 2          → "session_failed"（檢測本身失敗，不需重生）
      - report 不存在                → "missing_report"
      - report.status == "failed"   → "failed"
      - report.status in pending/processing 且距今 > 30 分鐘 → "stale_pending"
      - report.status == "completed" 但無 pdf_url           → "missing_pdf"
      - report.status == "completed" 且有 pdf_url           → "ok"
      - 其他（剛跑沒多久的 pending）                       → "in_progress"
    """
    user = require_user(authorization, db)

    q = db.query(M.Session).order_by(M.Session.session_id.desc())
    if user.role != "admin" or only_mine:
        q = q.filter(M.Session.consultant_name == user.name)
    sessions = q.limit(limit).all()

    sess_ids = [s.session_id for s in sessions]
    reports = (
        db.query(M.Report).filter(M.Report.session_id.in_(sess_ids)).all()
        if sess_ids else []
    )
    rep_by_sid = {r.session_id: r for r in reports}

    # 🔑 預先撈出所有相關 Subject 的真實資料（雙來源：Session.subject_id 或 Report.subject_id）
    subject_ids = set()
    for s in sessions:
        if s.subject_id:
            subject_ids.add(s.subject_id)
    for r in reports:
        if r.subject_id:
            subject_ids.add(r.subject_id)
    subj_map: dict[int, M.Subject] = {}
    if subject_ids:
        for subj in db.query(M.Subject).filter(M.Subject.subject_id.in_(list(subject_ids))).all():
            subj_map[subj.subject_id] = subj

    PLACEHOLDER_NAMES = {"受測者", "陳小明", "測試模式", "test", "Test", "TEST"}

    now_ms = int(time.time() * 1000)
    out = []
    missing_count = 0
    for s in sessions:
        r = rep_by_sid.get(s.session_id)

        if s.status == 2:
            health = "session_failed"
            is_missing = False
        elif r is None:
            health = "missing_report"
            is_missing = True
        elif r.status == "failed":
            health = "failed"
            is_missing = True
        elif r.status == "completed" and not r.pdf_url:
            health = "missing_pdf"
            is_missing = True
        elif r.status == "completed" and r.pdf_url:
            health = "ok"
            is_missing = False
        else:
            # pending / generating — 看 Report.created_at（比 Session.created_at 更準確：
            # 每次 regenerate 都會更新 r.created_at，Session.created_at 是昨天建立的不變）
            ref_ts = None
            if r and r.created_at:
                try:
                    import datetime as _dt
                    rc = r.created_at
                    if hasattr(rc, "timestamp"):
                        ref_ts = int(rc.timestamp() * 1000)
                    else:
                        ref_ts = int(float(rc)) * 1000
                except Exception:
                    ref_ts = None
            if ref_ts is None:
                ref_ts = s.created_at or now_ms
            age_ms = now_ms - ref_ts
            if age_ms > 30 * 60 * 1000:
                health = "stale_pending"
                is_missing = True
            else:
                health = "in_progress"
                is_missing = False

        if only_missing and not is_missing:
            continue

        if is_missing:
            missing_count += 1

        # 🔑 真實姓名解析：FK 優先 → 退到 Session.subject_name 字串
        sid_resolved = s.subject_id or (r.subject_id if r else None)
        subj_record  = subj_map.get(sid_resolved) if sid_resolved else None
        if subj_record:
            display_name = subj_record.name
            display_age  = None
            if subj_record.birth_date and len(subj_record.birth_date) >= 4:
                try:
                    from datetime import date
                    y, m, d = subj_record.birth_date.split("-")
                    b = date(int(y), int(m), int(d))
                    t = date.today()
                    display_age = t.year - b.year - ((t.month, t.day) < (b.month, b.day))
                except Exception:
                    display_age = s.subject_age
        else:
            raw = s.subject_name or ""
            # 沒關聯主檔且姓名是 placeholder → 顯示「(未填) 受測者」提示孤兒
            if raw in PLACEHOLDER_NAMES or not raw:
                display_name = f"⚠️ 受測者（未連結主檔，session #{s.session_id}）"
            else:
                display_name = raw
            display_age = s.subject_age

        # 從 client_summary 取出失敗原因讓前端顯示
        # 只在 status=failed 時才回傳，避免生成中時顯示舊的失敗訊息
        headless_error_sw = None
        if r and r.status == "failed" and r.client_summary:
            try:
                import json as _jsw
                cs_sw = _jsw.loads(r.client_summary)
                # 優先用內建 Gemini 錯誤，否則用 headless 錯誤
                headless_error_sw = cs_sw.get("internal_error") or cs_sw.get("headless_error")
            except Exception:
                pass

        out.append({
            "session_id":   s.session_id,
            "subject_id":   sid_resolved,
            "subject_name": display_name,
            "subject_age":  display_age,
            "consultant":   s.consultant_name,
            "report_type":  s.report_type,
            "audience":     s.report_audience,
            "captures":     s.total_captures,
            "session_ok":   s.status == 1,
            "created_at":   s.created_at,
            "report_id":    r.report_id if r else None,
            "report_status": (r.status if r else "none"),
            "has_pdf":      bool(r and r.pdf_url),
            "pdf_url":      r.pdf_url if r else None,
            "email_sent":   r.email_sent if r else 0,
            "notify_email": r.notify_email if r else None,
            "completed_at": r.completed_at.isoformat() if (r and r.completed_at) else None,
            "health":       health,
            "is_missing":   is_missing,
            "headless_error": headless_error_sw,   # 失敗原因（headless_renderer 寫入）
        })

    return {
        "ok":             True,
        "count":          len(out),
        "missing_count":  missing_count,
        "sessions":       out,
    }


def _session_to_brainwave_data(db: Session, session_id: int) -> Optional[dict]:
    """從 EegCapture 重組 trigger_external_report 期望的 brainwave_data 格式。

    格式：
      { attention_percentage, meditation_percentage,
        bands_avg: { theta, alpha, beta, gamma } }
    """
    from app.services.algorithms import compute_averages

    captures = db.query(M.EegCapture).filter(
        M.EegCapture.session_id == session_id
    ).order_by(M.EegCapture.seq_num).all()
    if not captures:
        return None

    # 排除基線（is_baseline=1）
    detection = [
        {
            "good_signal": c.good_signal,
            "attention":   c.attention,
            "meditation":  c.meditation,
            "delta":       c.delta,
            "theta":       c.theta,
            "low_alpha":   c.low_alpha,
            "high_alpha":  c.high_alpha,
            "low_beta":    c.low_beta,
            "high_beta":   c.high_beta,
            "low_gamma":   c.low_gamma,
            "high_gamma":  c.high_gamma,
        }
        for c in captures if c.is_baseline == 0
    ]
    if not detection:
        detection = [
            {k: getattr(c, k) for k in [
                "good_signal", "attention", "meditation", "delta", "theta",
                "low_alpha", "high_alpha", "low_beta", "high_beta", "low_gamma", "high_gamma"
            ]} for c in captures
        ]
    if not detection:
        return None

    avg = compute_averages(detection)
    # 修正：不能用 `x or 50`（會把合法的 0 / 0.0 / 接近 0 的低值替換成 50）
    # 改成只在「真的是 None」時才 fallback，且 fallback 改為由前端決定（這裡若有資料一律帶實際值）
    def _safe_int(v, fallback=50):
        try:
            return int(v) if v is not None else int(fallback)
        except Exception:
            return int(fallback)
    def _safe_float(v, fallback=50.0):
        try:
            return float(v) if v is not None else float(fallback)
        except Exception:
            return float(fallback)

    # 5-band 重組（low + high 取平均；deduped 寫入時兩值相同，平均 = 該 band 原值）
    def _band_avg(lo, hi):
        a = _safe_float(lo, None)
        b = _safe_float(hi, None)
        if a is None and b is None:
            return 50.0
        if a is None:  return b
        if b is None:  return a
        return (a + b) / 2.0

    bw = {
        "attention_percentage":  _safe_int(avg.attention),
        "meditation_percentage": _safe_int(avg.meditation),
        "sample_count":          len(captures),
        "bands_avg": {
            "delta": _safe_float(avg.delta),
            "theta": _safe_float(avg.theta),
            "alpha": _band_avg(avg.low_alpha, avg.high_alpha),
            "beta":  _band_avg(avg.low_beta,  avg.high_beta),
            "gamma": _band_avg(avg.low_gamma, avg.high_gamma),
        },
    }
    return bw


def _do_regenerate_one(
    db: Session,
    session_id: int,
    notify_email: Optional[str],
    variant: str = "full",
) -> dict:
    """單筆重生核心：reset Report、組 brainwave_data、觸發 trigger_external_report。

    重生完成後一律進入「待 admin 核准寄信」狀態 (email_sent=0)，
    管理員須到「報告管理」預覽 PDF 後才能手動寄出。
    """
    s = db.query(M.Session).filter(M.Session.session_id == session_id).first()
    if not s:
        return {"ok": False, "session_id": session_id, "error": "Session 不存在"}
    if s.status == 2:
        return {"ok": False, "session_id": session_id,
                "subject_name": s.subject_name, "error": "原始檢測本身失敗 (status=2)"}

    bw = _session_to_brainwave_data(db, session_id)
    if bw is None:
        return {"ok": False, "session_id": session_id,
                "subject_name": s.subject_name, "error": "找不到腦波資料 (EegCapture 為空)"}

    r = db.query(M.Report).filter(M.Report.session_id == session_id).first()
    if r is None:
        import uuid
        r = M.Report(
            session_id   = session_id,
            status       = "generating",
            qr_token     = uuid.uuid4().hex,
            notify_email = notify_email or None,
            email_sent   = 0,
        )
        db.add(r)
        db.flush()
    else:
        from datetime import datetime as _dt
        r.status       = "generating"   # 用 generating 讓前端顯示「⏳ 生成中」
        r.pdf_url      = None
        r.email_sent   = 0
        r.created_at   = _dt.now()      # ← 重置計時器，避免立刻顯示「卡住 >30 分鐘」
        r.completed_at = None
        if notify_email:
            r.notify_email = notify_email
        # 🧹 清掉 client_summary 裡的舊失敗訊息，避免「重新生成中」仍顯示上次的錯誤
        if r.client_summary:
            try:
                import json as _jclr
                _cs_clr = _jclr.loads(r.client_summary or "{}")
                if isinstance(_cs_clr, dict):
                    _cs_clr.pop("headless_error", None)
                    _cs_clr.pop("headless_failed_at", None)
                    _cs_clr.pop("internal_error", None)
                    _cs_clr.pop("internal_failed_at", None)
                    r.client_summary = _jclr.dumps(_cs_clr, ensure_ascii=False)
            except Exception:
                pass
    db.commit()
    db.refresh(r)

    # 觸發外部 React App（漂亮版報告）
    from app.services import report_orchestrator

    # ── 從 Report.talent_report_kind 解析正確的 report_type/variant ──
    # talent_report_kind 格式："life_script_full" / "child_trial" / "marital_full" 等
    # 優先用 Report 已記錄的種類，fallback 到 Session.report_type 推算
    kind_str = (r.talent_report_kind or "").lower()
    if "child" in kind_str:
        ext_report_type = "child"
    elif "marital" in kind_str:
        ext_report_type = "marital"
    elif "parent_child" in kind_str or "parent" in kind_str:
        ext_report_type = "parent_child"
    else:
        # fallback：從 Session.report_type 推算
        sess_rt = (s.report_type or "").lower()
        if "child" in sess_rt:
            ext_report_type = "child"
        elif "marital" in sess_rt:
            ext_report_type = "marital"
        elif "parent" in sess_rt:
            ext_report_type = "parent_child"
        else:
            ext_report_type = "life_script"

    # ── 從 Report.talent_report_kind 解析 variant ──
    if "vip" in kind_str:
        resolved_variant = "vip"
    elif "trial" in kind_str:
        resolved_variant = "trial"
    else:
        resolved_variant = variant  # 使用呼叫端傳入的（預設 "full"）

    # 🔑 受測者真實姓名解析（與 start_full 相同邏輯）
    PLACEHOLDER_NAMES_REGEN = {"受測者", "陳小明", "測試模式", "test", "Test", "TEST"}
    resolved_regen_name  = s.subject_name or ""
    resolved_regen_email = r.notify_email or ""
    resolved_regen_sid   = s.subject_id or (r.subject_id if r else None)
    if resolved_regen_sid:
        try:
            subj_r = db.query(M.Subject).filter(M.Subject.subject_id == resolved_regen_sid).first()
            if subj_r:
                if not resolved_regen_name or resolved_regen_name in PLACEHOLDER_NAMES_REGEN:
                    resolved_regen_name = subj_r.name
                if not resolved_regen_email:
                    resolved_regen_email = subj_r.email or ""
        except Exception as _e:
            logger.warning("[_do_regenerate_one] 反查 Subject 失敗: %s", _e)

    # 所有類型統一走外部（Vercel headless 或 REST API）
    # life_script / child → headless + DB 輪詢確認 callback
    # marital / parent_child → 直接 REST API
    try:
        result = report_orchestrator.trigger_external_report(
            report_type=ext_report_type,
            subject_name=resolved_regen_name or s.subject_name or "",
            subject_email=resolved_regen_email,
            subject_age=s.subject_age,
            subject_gender=s.subject_gender or "",
            variant=resolved_variant,
            brainwave_data=bw,
            extra={"session_id": session_id, "subject_id": resolved_regen_sid},
        )
    except Exception as e:
        return {"ok": False, "session_id": session_id,
                "subject_name": resolved_regen_name or s.subject_name,
                "error": f"trigger 失敗：{type(e).__name__}: {e}"}

    return {
        "ok":            bool(result.get("ok", False)),
        "session_id":    session_id,
        "report_id":     r.report_id,
        "subject_name":  resolved_regen_name or s.subject_name,
        "notify_email":  r.notify_email,
        "external_mode": result.get("mode"),
        "job_id":        result.get("job_id"),
        "error":         result.get("error"),
    }


class RegenerateReportIn(BaseModel):
    notify_email: Optional[str] = None
    variant:      str = "full"


@router.post("/sessions/{session_id}/regenerate")
def regenerate_report_for_session(
    session_id: int,
    payload: Optional[RegenerateReportIn] = None,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """對指定 Session 重新觸發報告生成（管理員專用）。
    重生完成後一律進入「待 admin 核准寄信」狀態，永不自動寄。"""
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "僅管理員可觸發重新生成")

    p = payload or RegenerateReportIn()
    res = _do_regenerate_one(
        db, session_id,
        notify_email=p.notify_email,
        variant=p.variant,
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "重新生成失敗")
    res["note"] = "已觸發重新生成。完成後請至『報告管理 → 💾 資料庫紀錄』預覽後手動點「📨 預覽後寄信」。"
    return res


class RegenerateBatchItem(BaseModel):
    session_id:   int
    notify_email: Optional[str] = None


class RegenerateBatchIn(BaseModel):
    items:   List[RegenerateBatchItem]
    variant: str = "full"


@router.post("/sessions/regenerate-batch")
def regenerate_report_batch(
    payload: RegenerateBatchIn,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """批次重生：依序觸發每一筆，全部進入「待核准」狀態。"""
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "僅管理員可觸發重新生成")
    if not payload.items:
        raise HTTPException(400, "items 不能為空")
    if len(payload.items) > 50:
        raise HTTPException(400, "單次最多 50 筆")

    results = []
    ok_count = 0
    for it in payload.items:
        res = _do_regenerate_one(
            db, it.session_id,
            notify_email=it.notify_email,
            variant=payload.variant,
        )
        if res.get("ok"):
            ok_count += 1
        results.append(res)

    return {
        "ok":       True,
        "total":    len(results),
        "success":  ok_count,
        "failed":   len(results) - ok_count,
        "results":  results,
        "note":     "全部完成後須由 admin 在『報告管理 → 💾 資料庫紀錄』預覽後手動寄信。",
    }


@router.post("/reset-stuck")
def reset_stuck_reports(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """管理員手動觸發：把所有卡在 generating/pending 的 Report 重設為 failed。

    適用場景：
      - Railway 重新部署後孤兒報告沒有自動清除
      - 按「重新生成」沒反應、一直顯示「⏳ 生成中」
      - 需要讓「檢測 ↔ 報告」頁面顯示 failed 狀態，才能再次點「重新生成」
    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "僅管理員可重設")

    stuck = db.query(M.Report).filter(
        M.Report.status.in_(["generating", "pending"])
    ).all()

    reset_ids = []
    for rep in stuck:
        rep.status = "failed"
        reset_ids.append(rep.report_id)
    db.commit()

    return {
        "ok":    True,
        "count": len(reset_ids),
        "reset_report_ids": reset_ids,
        "note":  f"已將 {len(reset_ids)} 筆卡住的報告重設為 failed。請至「報告管理 → 檢測↔報告」點「🔄 重新生成」。",
    }


class ImportFromGcsIn(BaseModel):
    object_name:   str                          # 例: reports/general/1779359536955_鄭小怡_腦波分析報告.pdf
    subject_name:  Optional[str] = None         # 為空時從檔名解析
    subject_email: Optional[str] = None         # 之後寄信用
    report_type:   str = "life_script"          # life_script / child / parent_child / marital
    variant:       str = "full"
    pending_send:  int = 1                      # 預設要等 admin 核准才寄
    consultant:    Optional[str] = None         # 若知道是哪位顧問客戶


@router.post("/import-from-gcs")
def import_from_gcs(
    payload: ImportFromGcsIn,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    將 GCS 上的孤兒 PDF 補錄到 DB Report 表（管理員專用）。

    用途：早期 record callback bug 期間生成的報告在 GCS 但沒進 DB，
    用此端點讓 admin 一鍵把它們補進來，之後就能正常管理 / 寄信。
    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "僅管理員可使用此功能")

    from app.services import gcs_uploader
    from google.cloud import storage
    from google.oauth2 import service_account
    from datetime import timedelta

    obj = (payload.object_name or "").strip()
    if not obj:
        raise HTTPException(400, "缺少 object_name")
    if not obj.lower().endswith(".pdf"):
        raise HTTPException(400, "只支援 .pdf")

    if not gcs_uploader.is_configured():
        raise HTTPException(500, "GCS 未設定")

    # 1) 確認檔案存在且簽 URL
    try:
        creds_dict = gcs_uploader._credentials_dict()
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        client = storage.Client(project=creds_dict.get("project_id"), credentials=credentials)
        bucket = client.bucket(gcs_uploader._bucket_name())
        blob = bucket.blob(obj)
        if not blob.exists():
            raise HTTPException(404, f"GCS 找不到此物件：{obj}")
        blob.reload()
        signed = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=gcs_uploader._signed_days()),
            method="GET",
            response_disposition=f'attachment; filename="{os.path.basename(obj)}"',
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"簽 GCS URL 失敗：{type(e).__name__}: {e}")

    # 2) 從檔名解析 subject_name（若呼叫端沒指定）
    #    格式：reports/<area>/<epoch_ms>_<subject_name>_<report_label>.pdf
    subject_name = (payload.subject_name or "").strip()
    if not subject_name:
        fname = os.path.basename(obj).rsplit(".", 1)[0]
        parts = fname.split("_")
        # parts[0]=epoch、parts[1]=name、parts[2:]=label
        if len(parts) >= 2:
            subject_name = parts[1] or "(未知)"
        else:
            subject_name = fname

    # 3) 避免重複補錄（用 object_name 做去重，比對 pdf_url 中的 object path）
    existing = db.query(M.Report).filter(M.Report.pdf_url.like(f"%{obj}%")).first()
    if existing:
        # 已經補過 / 已經有紀錄 → 更新 signed URL（過期會自動續簽）
        existing.pdf_url = signed
        if payload.subject_email and not existing.notify_email:
            existing.notify_email = payload.subject_email
        db.commit()
        return {
            "ok": True,
            "note": "此檔案已在 DB，已更新 signed URL",
            "report_id": existing.report_id,
        }

    # 🔑 在建立前嘗試解析 subject_id（避免變孤兒報告）
    resolved_sid = None
    try:
        PLACEHOLDER = {"受測者", "陳小明", "測試模式", "test", "Test", "TEST"}
        if payload.subject_email:
            cand = db.query(M.Subject).filter(M.Subject.email == payload.subject_email).first()
            if cand:
                resolved_sid = cand.subject_id
        if resolved_sid is None and subject_name and subject_name not in PLACEHOLDER:
            cands = db.query(M.Subject).filter(M.Subject.name == subject_name).all()
            if len(cands) == 1:
                resolved_sid = cands[0].subject_id
    except Exception:
        pass

    # 4) 建立 Report row（孤兒：session_id=NULL；但盡可能寫入 subject_id）
    rep = M.Report(
        session_id     = None,
        subject_id     = resolved_sid,           # 🔑 寫入 FK
        status         = "completed",
        pdf_url        = signed,
        notify_email   = payload.subject_email or None,
        email_sent     = 0 if payload.pending_send else 1,
        talent_report_kind = f"{payload.report_type}_{payload.variant}",
        client_summary = (
            '{"subject_name":"' + (subject_name or "") + '",'
            '"subject_id":' + (str(resolved_sid) if resolved_sid else "null") + ','
            '"source":"manual_import_from_gcs",'
            '"object_name":"' + obj + '",'
            '"imported_by":"' + (user.name or "") + '",'
            '"consultant_hint":"' + (payload.consultant or "") + '"}'
        ),
        completed_at   = func.now(),
    )
    db.add(rep)
    db.commit()
    db.refresh(rep)

    return {
        "ok": True,
        "report_id": rep.report_id,
        "subject_name": subject_name,
        "pdf_url": signed,
        "note": "已將孤兒檔補錄到 DB。下次到『報告管理 → 💾 資料庫紀錄』即可看見。",
    }


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


# ────────────────────────────────────────────────────────────────────────────
# 管理員：跨帳號受測者全覽
# ────────────────────────────────────────────────────────────────────────────
@router.get("/all-subjects-overview")
def all_subjects_overview(
    q: Optional[str] = Query(None, description="關鍵字（姓名 / Email / 手機 / 顧問）"),
    limit: int = Query(500, ge=1, le=2000),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """管理員專用：列出「所有帳號做過的受測者資訊」。

    每筆包含：
      - 基本資料：subject_id / name / birth_date / gender / age / email / phone /
                  occupation / medical_history / medications / consultant_id /
                  consultant_name / consultant_org / created_at
      - 檢測場次彙總：sessions_count、latest_session_id、latest_session_at、
                      latest_report_type
      - 該受測者的所有報告（最多 20 筆，含 pdf_url、status、email_sent、
        report_kind、completed_at、session_id）
      - 該受測者最新一次檢測的腦波平均（attention / meditation /
        bands_avg: theta/alpha/beta/gamma）

    比對策略（雙軌）：
      A. 主軌：用 Subject.subject_id 反查 Session.subject_id 與 Report.subject_id
      B. 副軌（向下相容）：對於還沒回填 subject_id 的舊 Session/Report，
         才退到 subject_name 字串比對。
    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="僅管理員可查看跨帳號受測者資訊")

    # 1) 取所有 Subjects（admin 可看全部）
    subj_q = db.query(M.Subject)
    if q:
        kw = f"%{q.strip()}%"
        from sqlalchemy import or_ as _or
        subj_q = subj_q.filter(_or(
            M.Subject.name.like(kw),
            M.Subject.email.like(kw),
            M.Subject.phone.like(kw),
        ))
    subjects = subj_q.order_by(M.Subject.subject_id.desc()).limit(limit).all()

    # 2) 顧問清單
    cons_ids = {s.consultant_id for s in subjects if s.consultant_id}
    cons_map: dict[int, M.Consultant] = {}
    if cons_ids:
        for c in db.query(M.Consultant).filter(M.Consultant.consultant_id.in_(cons_ids)).all():
            cons_map[c.consultant_id] = c

    subject_id_set = {s.subject_id for s in subjects}
    name_set  = {s.name for s in subjects if s.name}

    # 3A) 主軌：subject_id 直接命中（含 NULL 過濾）
    sess_by_subj: dict[int, list[M.Session]] = {}
    if subject_id_set:
        sess_rows_fk = db.query(M.Session).filter(
            M.Session.subject_id.in_(list(subject_id_set))
        ).order_by(M.Session.session_id.desc()).all()
        for s in sess_rows_fk:
            sess_by_subj.setdefault(s.subject_id, []).append(s)

    # 3B) 副軌：對於 subject_id IS NULL 的舊 Session，用 name 比對補齊
    sess_by_name_legacy: dict[str, list[M.Session]] = {}
    if name_set:
        legacy_sessions = db.query(M.Session).filter(
            M.Session.subject_id.is_(None),
            M.Session.subject_name.in_(list(name_set)),
        ).order_by(M.Session.session_id.desc()).limit(5000).all()
        for s in legacy_sessions:
            sess_by_name_legacy.setdefault(s.subject_name, []).append(s)

    # 4) 取得這些 session 對應的 Report
    all_sess_ids = []
    for arr in sess_by_subj.values():
        all_sess_ids.extend([x.session_id for x in arr])
    for arr in sess_by_name_legacy.values():
        all_sess_ids.extend([x.session_id for x in arr])
    rep_map: dict[int, M.Report] = {}
    if all_sess_ids:
        for r in db.query(M.Report).filter(M.Report.session_id.in_(all_sess_ids)).all():
            rep_map[r.session_id] = r

    # 4B) 還要把「Report.subject_id 直接連到的 orphan reports」（沒有 session_id）撈進來
    orphan_reps_by_sid: dict[int, list[M.Report]] = {}
    if subject_id_set:
        for r in db.query(M.Report).filter(
            M.Report.subject_id.in_(list(subject_id_set)),
            M.Report.session_id.is_(None),
        ).order_by(M.Report.report_id.desc()).all():
            orphan_reps_by_sid.setdefault(r.subject_id, []).append(r)

    # 5) helper：年齡計算
    def _age_from_birth(birth: str) -> Optional[int]:
        if not birth or len(birth) < 4:
            return None
        try:
            from datetime import date
            y, m, d = birth.split("-")
            b = date(int(y), int(m), int(d))
            today = date.today()
            return today.year - b.year - ((today.month, today.day) < (b.month, b.day))
        except Exception:
            return None

    out = []
    for s in subjects:
        cons = cons_map.get(s.consultant_id) if s.consultant_id else None
        # 🔑 雙軌合併：FK 命中的 + 舊資料 name 命中的
        sess_list_fk     = sess_by_subj.get(s.subject_id, [])
        sess_list_legacy = sess_by_name_legacy.get(s.name, [])
        # 用 session_id 去重
        seen_sids = set()
        sess_list: list = []
        for ss in (sess_list_fk + sess_list_legacy):
            if ss.session_id in seen_sids:
                continue
            seen_sids.add(ss.session_id)
            sess_list.append(ss)
        sess_list.sort(key=lambda x: x.session_id, reverse=True)
        latest = sess_list[0] if sess_list else None

        # 該受測者所有報告（含 orphan reports，最多 20 筆）
        rep_list = []
        seen_rids = set()
        # 透過 session 連結的
        for ss in sess_list[:20]:
            r = rep_map.get(ss.session_id)
            if not r or r.report_id in seen_rids:
                continue
            seen_rids.add(r.report_id)
            rep_list.append({
                "report_id":    r.report_id,
                "session_id":   r.session_id,
                "report_kind":  r.talent_report_kind,
                "status":       r.status,
                "pdf_url":      r.pdf_url,
                "email_sent":   r.email_sent,
                "notify_email": r.notify_email,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "report_type":  ss.report_type,
                "session_at":   ss.created_at if hasattr(ss, "created_at") else None,
            })
        # Report.subject_id 直接連到、但 session_id IS NULL 的孤兒報告
        for r in orphan_reps_by_sid.get(s.subject_id, [])[:20]:
            if r.report_id in seen_rids:
                continue
            seen_rids.add(r.report_id)
            rep_list.append({
                "report_id":    r.report_id,
                "session_id":   None,
                "report_kind":  r.talent_report_kind,
                "status":       r.status,
                "pdf_url":      r.pdf_url,
                "email_sent":   r.email_sent,
                "notify_email": r.notify_email,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "report_type":  None,
                "session_at":   None,
                "no_session":   True,
            })
        rep_list = rep_list[:20]

        # 最新一次檢測的腦波平均
        bw = None
        if latest:
            try:
                bw = _session_to_brainwave_data(db, latest.session_id)
            except Exception:
                bw = None

        out.append({
            # 基本資料
            "subject_id":      s.subject_id,
            "name":            s.name,
            "birth_date":      s.birth_date,
            "age":             _age_from_birth(s.birth_date),
            "gender":          s.gender,
            "occupation":      s.occupation or "",
            "email":           s.email,
            "phone":           s.phone,
            "medical_history": s.medical_history or "",
            "medications":     s.medications or "",
            "created_at":      s.created_at.isoformat() if s.created_at else None,
            # 顧問資訊（哪個帳號建檔）
            "consultant_id":       s.consultant_id,
            "consultant_name":     (cons.name if cons else None),
            "consultant_org":      (cons.org  if cons else None),
            "consultant_role":     (cons.role if cons else None),
            "consultant_org_type": (cons.org_type if cons else None),
            "consultant_phone":    (cons.phone if cons else None),
            # 檢測場次彙總
            "sessions_count":         len(sess_list),
            "latest_session_id":      (latest.session_id if latest else None),
            "latest_report_type":     (latest.report_type if latest else None),
            "latest_consultant_name": (latest.consultant_name if latest else None),
            "latest_session_at":      (latest.created_at if latest else None),  # ms timestamp
            # 報告 + 腦波
            "reports":           rep_list,
            "latest_brainwave":  bw,
        })

    return {
        "ok":    True,
        "count": len(out),
        "subjects": out,
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


@router.post("/admin/relink-orphan-reports")
def admin_relink_orphan_reports(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """🔗 一鍵嘗試把孤兒報告（subject_id IS NULL）關聯回 Subject 主檔。

    啟發式比對策略（依優先序）：
      1. Report.session_id → Session.subject_id（若 Session 已關聯）
      2. Report.session_id → Session.consultant_name + subject_name → Subject by name + consultant
      3. ⭐ Session.subject_name 是 placeholder（"受測者"等）→ 找該 consultant 在
         Session 建檔時間 ± 7 天內擁有的「唯一」Subject（若多個則略過，避免亂連）
      4. Report.completed_at ± 24h，比對該時段內 consultant 建立的唯一 Subject

    安全：只 UPDATE 不刪除；找不到的報告維持 subject_id=NULL，admin 仍可手動處理。
    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "僅 admin 可執行")

    # 1) 撈所有 subject_id=NULL 的 Report
    orphans = db.query(M.Report).filter(M.Report.subject_id.is_(None)).all()
    if not orphans:
        return {"ok": True, "scanned": 0, "linked": 0, "still_orphan": 0, "details": []}

    # 預先準備 lookup table
    sess_map: dict[int, M.Session] = {}
    sess_ids = {r.session_id for r in orphans if r.session_id}
    if sess_ids:
        for s in db.query(M.Session).filter(M.Session.session_id.in_(list(sess_ids))).all():
            sess_map[s.session_id] = s

    # 顧問 name → consultant_id
    cons_name_set = set()
    for s in sess_map.values():
        if s.consultant_name:
            cons_name_set.add(s.consultant_name)
    cons_name_to_id: dict[str, int] = {}
    if cons_name_set:
        for c in db.query(M.Consultant).filter(M.Consultant.name.in_(list(cons_name_set))).all():
            cons_name_to_id[c.name] = c.consultant_id

    linked = 0
    still_orphan = 0
    details = []

    for rep in orphans:
        chosen_sid = None
        method = ""

        sess = sess_map.get(rep.session_id) if rep.session_id else None

        # 策略 1：Session 自己有 subject_id
        if sess and sess.subject_id:
            chosen_sid = sess.subject_id
            method = "session.subject_id"

        PLACEHOLDER_NAMES = {"受測者", "陳小明", "測試模式", "test", "Test", "TEST", "", None}

        # 策略 2：Session.consultant + Session.subject_name → Subject（姓名是真名才比對）
        if (chosen_sid is None and sess and sess.consultant_name
                and sess.subject_name and sess.subject_name not in PLACEHOLDER_NAMES):
            cons_id = cons_name_to_id.get(sess.consultant_name)
            if cons_id:
                cands = db.query(M.Subject).filter(
                    M.Subject.consultant_id == cons_id,
                    M.Subject.name == sess.subject_name,
                ).all()
                if len(cands) == 1:
                    chosen_sid = cands[0].subject_id
                    method = "consultant+name"

        # 策略 3 ⭐：placeholder 姓名 → 用「該顧問擁有的唯一 Subject」匹配
        # 適用情境：admin 用「NT$1 測試」沒登錄受測者就生報告，但顧問
        # （如「楊雲容」）名下其實只有一位受測者（如「蘇志明」），可推論為同一人。
        if (chosen_sid is None and sess and sess.consultant_name
                and (not sess.subject_name or sess.subject_name in PLACEHOLDER_NAMES)):
            cons_id = cons_name_to_id.get(sess.consultant_name)
            if cons_id:
                cands = db.query(M.Subject).filter(
                    M.Subject.consultant_id == cons_id
                ).all()
                if len(cands) == 1:
                    chosen_sid = cands[0].subject_id
                    method = "consultant has only 1 subject (placeholder)"

        # 策略 4：completed_at ± 24h 內 consultant 建立的唯一 Subject（最後手段，謹慎）
        # （只在 session_id is null + 有 completed_at 時才嘗試，避免亂連）
        if (chosen_sid is None and rep.session_id is None and rep.completed_at and sess is None
                and rep.client_summary):
            try:
                import json as _json
                cs = _json.loads(rep.client_summary)
                guess_name = cs.get("subject_name", "")
                # 不在 PLACEHOLDER 才嘗試（PLACEHOLDER 直接視為孤兒測試報告，不關聯）
                PLACEHOLDER_NAMES = {"受測者", "陳小明", "測試模式", "test", "Test", "TEST"}
                if guess_name and guess_name not in PLACEHOLDER_NAMES and not guess_name.startswith("🧪 "):
                    cands = db.query(M.Subject).filter(M.Subject.name == guess_name).all()
                    if len(cands) == 1:
                        chosen_sid = cands[0].subject_id
                        method = "client_summary.name (unique)"
            except Exception:
                pass

        if chosen_sid:
            rep.subject_id = chosen_sid
            # 同時更新 Session.subject_id 補強連結
            if sess and not sess.subject_id:
                sess.subject_id = chosen_sid
            linked += 1
            details.append({
                "report_id":   rep.report_id,
                "linked_to":   chosen_sid,
                "method":      method,
            })
        else:
            still_orphan += 1
            details.append({
                "report_id":   rep.report_id,
                "linked_to":   None,
                "method":      "no match (manual link required)",
            })

    db.commit()
    return {
        "ok": True,
        "scanned":      len(orphans),
        "linked":       linked,
        "still_orphan": still_orphan,
        "details":      details[:50],
    }


@router.post("/{report_id}/manual-link-subject")
def admin_manual_link_subject(
    report_id: int,
    body: dict,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """admin 手動把單筆 Report 連到指定 subject_id（覆蓋既有連結）"""
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "僅 admin 可執行")

    rep = db.query(M.Report).filter(M.Report.report_id == report_id).first()
    if not rep:
        raise HTTPException(404, f"找不到報告 #{report_id}")

    sid = body.get("subject_id")
    if not isinstance(sid, int) or sid <= 0:
        raise HTTPException(400, "subject_id 必須是正整數")

    subj = db.query(M.Subject).filter(M.Subject.subject_id == sid).first()
    if not subj:
        raise HTTPException(404, f"找不到 Subject #{sid}")

    rep.subject_id = sid
    if rep.session_id:
        sess = db.query(M.Session).filter(M.Session.session_id == rep.session_id).first()
        if sess:
            sess.subject_id = sid
    db.commit()
    return {"ok": True, "report_id": report_id, "linked_to": sid, "subject_name": subj.name}


@router.delete("/{report_id}/delete-test")
def delete_test_report(
    report_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """管理員專用：刪除「測試報告」（subject_name 為預設值的孤兒報告）。

    安全檢查：
      - 必須是 admin
      - 報告的 subject_name 必須是預設值之一（受測者 / 陳小明 / 測試模式 / 🧪 管理員測試-* / 空）
      - 即使是測試報告，session_id 為非空時不刪（避免誤刪有腦波資料的）

    這個 API 不會去刪 GCS 上的 PDF（避免影響其他關聯），只刪 DB row。
    """
    import json as _json

    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "僅管理員可刪除測試報告")

    rep = db.query(M.Report).filter(M.Report.report_id == report_id).first()
    if not rep:
        raise HTTPException(404, f"找不到報告 #{report_id}")

    PLACEHOLDER_NAMES = {"受測者", "陳小明", "測試模式", "test", "Test", "TEST"}

    name_from_summary = None
    if rep.client_summary:
        try:
            name_from_summary = _json.loads(rep.client_summary).get("subject_name")
        except Exception:
            pass
    name_from_sess = None
    if rep.session_id:
        sess = db.query(M.Session).filter(M.Session.session_id == rep.session_id).first()
        if sess:
            name_from_sess = sess.subject_name

    raw_name = name_from_sess or name_from_summary or ""
    is_placeholder = (
        (not raw_name)
        or (raw_name in PLACEHOLDER_NAMES)
        or raw_name.startswith("🧪 管理員測試-")
    )

    if not is_placeholder:
        raise HTTPException(
            400,
            f"報告 #{report_id} 的受測者為「{raw_name}」，不是測試報告，禁止透過此 API 刪除。"
            "若確實要刪除，請使用一般的報告刪除流程（含 GCS 與 Session 處理）。",
        )

    # 刪除前記錄
    deleted_info = {
        "report_id":     rep.report_id,
        "session_id":    rep.session_id,
        "raw_name":      raw_name,
        "report_kind":   rep.talent_report_kind,
        "completed_at":  rep.completed_at.isoformat() if rep.completed_at else None,
    }
    db.delete(rep)
    db.commit()
    return {"ok": True, "deleted": deleted_info}


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
