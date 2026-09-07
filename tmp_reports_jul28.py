"""
?勗?瑼?蝞∠?嚗?  POST /api/v1/reports/record   憭 React App 摰?敺?callback嚗? GCS URL 撖怠 DB
  GET  /api/v1/reports/list     蝞∠??∪??啁嚗??箸????+ 銝????
  GET  /api/v1/reports/by-subject/{email}   靘?email ?亙銝?葫???勗?蝝??
瘜冽?嚗?record ?勗???Vercel ???澆嚗蝙??shared secret 隤?
      嚗EPORTS_INGEST_SECRET env var嚗瘝身??閮曹遙雿?皞????潛嚗?"""
from typing import Any, Optional, List
import time
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core import models as M
from app.core.database import get_db
from app.routers.auth import require_user, require_admin

router = APIRouter(prefix="/api/v1/reports", tags=["?勗?蝞∠?"])

# ?函蔡?璅?嚗?甈?commit ?嫣?甈∪?舐Ⅱ隤??啁?撘?蝺?
BUILD_VERSION = "planc-v15-timeout-45min"


@router.get("/session/{session_id}/signed-url")
def get_report_signed_url(
    session_id: int,
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """
    ?箸?摰?session ????啁???? GCS Signed URL??
    靘隞?APP ???勗? PDF ???雿輻嚗?甈∟?瘙??Ｙ??啁??????嚗?    - days: ??憭拇嚗?閮?7 憭抬????30 憭?    """
    rep = db.query(M.Report).filter(M.Report.session_id == session_id).first()
    if not rep:
        raise HTTPException(status_code=404, detail="甇?session 撠?勗?")
    if rep.status != "completed":
        raise HTTPException(status_code=409, detail=f"?勗?撠摰?嚗???{rep.status}嚗?)
    if not rep.pdf_url:
        raise HTTPException(status_code=404, detail="?勗???PDF ???")

    from app.services import gcs_uploader
    from urllib.parse import urlparse, unquote

    # ?? GCS object name嚗?斤偷???賂?
    parsed = urlparse(rep.pdf_url)
    raw_path = unquote(parsed.path)
    bucket = gcs_uploader._bucket_name() if gcs_uploader.is_configured() else "brainwave-child-reports"
    prefix = f"/{bucket}/"
    gcs_path = raw_path[len(prefix):] if raw_path.startswith(prefix) else raw_path.lstrip("/")

    signed_url = gcs_uploader.generate_fresh_signed_url(rep.pdf_url, days=days)
    if not signed_url:
        # GCS ?芾身摰?憭望?嚗?亙??單??URL嚗?賢歇??嚗?        signed_url = rep.pdf_url

    return {
        "session_id":  session_id,
        "report_id":   rep.report_id,
        "gcs_path":    gcs_path,
        "signed_url":  signed_url,
        "expires_days": days,
        "status":      rep.status,
    }


@router.get("/diag/full")
def diag_full(db: Session = Depends(get_db)) -> dict:
    """瑼Ｘ GCS?mail Proxy?eadless renderer?蝵脩???+ 閮嚗?? auth嚗?""
    from app.services import gcs_uploader, email_sender, headless_renderer

    # DB 閮
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

    # GCS PDF 閮嚗?憭? 50 蝑?敹恍摯蝞?
    gcs_pdf_count = -1
    gcs_sample: list[str] = []
    try:
        if gcs_uploader.is_configured():
            sample = gcs_uploader.list_pdfs(prefix="", max_items=50)
            gcs_pdf_count = len(sample)
            gcs_sample = [s["name"] for s in sample[:5]]
    except Exception as e:
        gcs_sample = [f"err: {type(e).__name__}: {e}"]

    # 鈭辣閮
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
    """????headless 隞餃?嚗恣?閫撖嚗?""
    from app.services import headless_renderer
    return {
        "jobs": headless_renderer.list_jobs(),
        "active_count": sum(1 for j in headless_renderer.list_jobs() if j.get("status") == "running"),
    }


@router.get("/headless/job/{job_id}")
def get_headless_job(job_id: str) -> dict:
    """?桐? headless 隞餃????""
    from app.services import headless_renderer
    j = headless_renderer.get_job(job_id)
    if not j:
        raise HTTPException(404, "?曆???headless job")
    return j


@router.get("/diag/fontmap")
def diag_fontmap() -> dict:
    """?湔??reportlab ?折??_ps2tt_map ?臭??舀? reportcjk嚗?    銝血?閰行??酉?誑???祕靘???""
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

    # ?岫??閮餃??????    candidates = []
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
    """?湔?澆 render_report_pdf 頝??扔撠?sample嚗??喳???traceback??""
    import traceback, tempfile
    from app.services import pdf_builder
    out_path = os.path.join(tempfile.gettempdir(), "_diag_test.pdf")
    try:
        sample = {
            "1_1": {
                "chapter_num": 1, "section_num": 1,
                "section_title": "皜祈岫蝭", "text": "?皜祈岫?ello world.",
            }
        }
        chapters = [{"num": 1, "title": "皜祈岫蝡?, "icon": "??"}]
        result = pdf_builder.render_report_pdf(
            out_path=out_path,
            subject_name="皜祈岫??,
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


# ??? Schemas ?????????????????????????????????????????????????????????????????

class RecordReportIn(BaseModel):
    session_id:    Optional[Any] = None   # ?亙? int ??string嚗RL params ?喃??摮葡嚗?    subject_name:  str = ""
    subject_email: str = ""
    report_type:   str = "life_script"   # life_script / child / parent_child / marital
    variant:       str = "full"           # trial / full / vip
    pdf_url:       str                    # GCS ??Blob ?祇????
    source:        str = ""               # ?芸??函頂蝯勗??梁?
    # 1 = ??admin 敺??閫貊撖縑嚗???pending嚗?    # 0 = 憭蝟餌絞撌脰銵?靽∴??喟絞銵嚗?閮哨?
    pending_send:  int = 0

    @validator('session_id', pre=True, always=True)
    def coerce_session_id(cls, v):
        """摰寡迂摮葡 '31'???31?one?征摮葡嚗絞銝頧 int ??None"""
        if v is None or v == '' or v == 'null':
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None


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


# ??? 撽?shared secret ???????????????????????????????????????????????????????

def _verify_ingest_secret(authorization: Optional[str], explicit_secret: Optional[str]):
    expected = (os.getenv("REPORTS_INGEST_SECRET") or "").strip()
    if not expected:
        return  # ?芾身摰????璅∪?嚗銵?    sent = ""
    if authorization and authorization.lower().startswith("bearer "):
        sent = authorization[7:].strip()
    elif explicit_secret:
        sent = explicit_secret.strip()
    if sent != expected:
        raise HTTPException(status_code=401, detail="REPORTS_INGEST_SECRET 銝迤蝣?)


# ??? 蝡舫? ????????????????????????????????????????????????????????????????????

@router.get("/headless/brainwave/{session_id}")
def headless_get_brainwave(
    session_id:    int,
    authorization: Optional[str] = Header(default=None),
    secret:        Optional[str] = Query(default=None, description="REPORTS_INGEST_SECRET嚗RL 撣?query嚗?),
    db:            Session = Depends(get_db),
):
    """
    Vercel React App ???auto=1 瘚?銝剖?澆甇?endpoint嚗?    ??session_id ?湔?踹摰 brainwave_data ???踹? URL query string ?賢?瞍宏 / ?芣??
    隤?嚗earer token ???secret= query??    ??蝯?嚗?        {
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
        raise HTTPException(404, "Session 銝???)

    bw = _session_to_brainwave_data(db, session_id)
    if not bw:
        raise HTTPException(404, "?曆??啗瘜Ｚ???EegCapture ?箇征嚗?)

    # bands_7 撌脩 _session_to_brainwave_data 隞亦?撖?low/high 摮?澆‵?伐?
    # 銝???alpha?0.9/?1.1 隡啁?閬???
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
    憭 React App嚗?鈭??咱嚗?芸?璅∪?摰???敺?callback??    瘚?嚗?      1. ?交? session_id嚗?啗府 Report
      2. ?血?撱箇?銝蝑迨?eport嚗ession_id=NULL嚗?蝯衣恣?敺蝔賣??    """
    _verify_ingest_secret(authorization, x_ingest_secret)

    if not payload.pdf_url:
        raise HTTPException(status_code=400, detail="蝻箏? pdf_url")

    now_ts = int(time.time())

    rep = None
    if payload.session_id:
        # ??session_id + ??report 蝔桅?????蝑??踹?銝?憿??勗?鈭閬?
        _kind = f"{payload.report_type}_{payload.variant}" if payload.report_type and payload.variant else None
        if _kind:
            rep = db.query(M.Report).filter(
                M.Report.session_id == payload.session_id,
                M.Report.talent_report_kind == _kind,
            ).first()
            # ?交銝?車憿??勗?嚗停?啣?銝蝑?銝??隞車憿?
        else:
            # 瘝? kind 鞈?嚗??澆?嚗??芣??session 銝洵銝蝑 kind 閮?
            rep = db.query(M.Report).filter(
                M.Report.session_id == payload.session_id,
                M.Report.talent_report_kind == None,  # noqa: E711
            ).first()

    # ?? ?葫??FK 閫??嚗??callback 撖怠摮文?嚗?    # 1. ??session 撌脫? subject_id ???湔??    # 2. ?血???subject_name + subject_email ??Subject 銵冽
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
                # name 瘥?嚗??placeholder 隤文銝?                PLACEHOLDER = {"?葫??, "?喳???, "皜祈岫璅∪?", "test", "Test", "TEST"}
                if payload.subject_name not in PLACEHOLDER:
                    cands = db.query(M.Subject).filter(M.Subject.name == payload.subject_name).all()
                    if len(cands) == 1:
                        resolved_sid = cands[0].subject_id
        except Exception:
            pass

    # pending_send=1 銵函內憭蝟餌絞撠撖縑嚗?蝯血??唳??孛??    email_sent_value = 0 if payload.pending_send else 1

    # ?? ??session_id ?箇征嚗?閰行?餈? generating/pending 摮文??勗?嚗ession_id=NULL嚗???? ??
    # 撣貉??湔嚗?蝡?session_id 蝡嗆???誑 null 撱箇?嚗eact App 摰?敺?callback 雿葆銝 session_id
    if rep is None and not payload.session_id and resolved_sid:
        try:
            orphan_candidate = (
                db.query(M.Report)
                .filter(
                    M.Report.subject_id  == resolved_sid,
                    M.Report.session_id  == None,          # noqa: E711
                    M.Report.status.in_(["generating", "pending", "failed"]),
                )
                .order_by(M.Report.report_id.desc())
                .first()
            )
            if orphan_candidate:
                rep = orphan_candidate
                logger.info(
                    "[/record] session_id 蝻箏仃嚗歇?曉摮文??勗? report_id=%s (subject_id=%s) 鋆??",
                    rep.report_id, resolved_sid,
                )
        except Exception as _oe:
            logger.warning("[/record] 摮文??勗?鋆??憭望?: %s", _oe)

    # ?? 蝟餌絞蝝??????敹?韏?admin 鈭箏極撖拇?撖縑 ??
    if rep is None:
        rep = M.Report(
            session_id     = payload.session_id,
            subject_id     = resolved_sid,        # ?? 撖怠 FK
            status         = "completed",
            pdf_url        = payload.pdf_url,
            notify_email   = payload.subject_email or None,
            email_sent     = 0,  # 撘瑕嚗?敺?admin ?詨?
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
            rep.subject_id = resolved_sid    # ?? 鋆神 FK
        # 撘瑕 reset ?箏??詨?嚗雿蹂??歇撖?嚗??啁???銋???撖抬?
        rep.email_sent = 0
        rep.talent_report_kind = f"{payload.report_type}_{payload.variant}"
        rep.completed_at = func.now()

    # ?噶鋆撥 Session.subject_id嚗???瘝神嚗?    if sess_for_record and resolved_sid and not sess_for_record.subject_id:
        sess_for_record.subject_id = resolved_sid

    db.commit()
    db.refresh(rep)

    return {
        "ok": True,
        "report_id":   rep.report_id,
        "session_id":  rep.session_id,
        "pdf_url":     rep.pdf_url,
        "email_sent":  0,
        "note":        "撌脩??鞈?摨怒???? admin ?具?恣??閬賢???撖縑??,
    }


@router.get("/list")
def list_reports(
    limit: int = Query(100, le=500),
    only_mine: bool = Query(False, description="True = ?芰??芸楛?葫??嚗alse (admin) = ?券"),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """?撌脩????勗? + GCS URL嚗恣?敺?剁???
    ?鞈?鞊???
      - ?勗?憿?頧?銝剜?嚗eport_kind_zh嚗?靘? life_script_full ???犖?行郭??嚗??渡?嚗?      - ?葫??祈???subject_name?ubject_age?ubject_gender
      - ??session_id ??NULL嚗??岫敺?Report.client_summary ? subject_name
      - 憿批?摰鞈?嚗onsultant_name?onsultant_org?onsultant_role
    """
    import json as _json

    user = require_user(authorization, db)

    # ?? 銝??蕪 pdf_url嚗???Report ?嚗??怠??芸????函??仃??嚗?    # ?見 admin ?摰??頂蝯勗?皜祈????????    q = db.query(M.Report, M.Session).outerjoin(
        M.Session, M.Report.session_id == M.Session.session_id
    )

    if user.role != "admin" or only_mine:
        q = q.filter(M.Session.consultant_name == user.name)

    rows = q.order_by(M.Report.report_id.desc()).limit(limit).all()

    # ?? ?“??蝔勗??憿批?閮?嚗?璈?/閫嚗?    cons_names = {sess.consultant_name for _r, sess in rows if sess and sess.consultant_name}
    cons_map: dict[str, M.Consultant] = {}
    if cons_names:
        for c in db.query(M.Consultant).filter(M.Consultant.name.in_(list(cons_names))).all():
            cons_map[c.name] = c

    REPORT_KIND_ZH = {
        # 銝駁???        "life_script":   "?犖?行郭??",
        "child":         "?咱?行郭憭抵釵閫?Ⅳ",
        "parent_child":  "閬芸??行郭?望???勗?",
        "marital":       "憭怠氖?行郭?望???勗?",
        # 霈?
        "trial":  "擃???,
        "full":   "摰??,
        "vip":    "VIP ??,
    }

    def _kind_zh(kind: Optional[str]) -> str:
        if not kind:
            return "??
        parts = kind.split("_")
        # ?岫?暹???prefix 撠??唬蜓憿?
        for n in (3, 2, 1):
            if len(parts) >= n:
                key = "_".join(parts[:n])
                if key in REPORT_KIND_ZH:
                    main = REPORT_KIND_ZH[key]
                    rest = parts[n:]
                    if rest:
                        var = REPORT_KIND_ZH.get(rest[-1], rest[-1])
                        return f"{main}嚗var}嚗?
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

    # ?身憪?霅嚗??胯??憭晞???嚗??舐?撖血?皜祈?
    PLACEHOLDER_NAMES = {"?葫??, "?喳???, "皜祈岫璅∪?", "test", "Test", "TEST"}

    # ?? ???????subject_id ??Subject ?祕鞈?
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

    # ?? ???釭嚗? chapter_done 鈭辣??payload imagen_used ?斗 ?????????
    # 'ok'      = ???蝭?賜 Imagen ??
    # 'fallback' = ?喳?銝蝡 Canvas 2D ??SVG ??嚗???
    # None       = ?∩?隞嗉???????芾???
    session_ids_for_img = [rep.session_id for rep, _ in rows if rep.session_id is not None]
    img_quality_by_sid: dict[int, str] = {}
    if session_ids_for_img:
        try:
            evts = db.query(M.ReportGenerationEvent).filter(
                M.ReportGenerationEvent.session_id.in_(session_ids_for_img),
                M.ReportGenerationEvent.phase == "chapter_done",
            ).all()
        except Exception:
            evts = []
        for evt in evts:
            sid_evt = evt.session_id
            if sid_evt is None:
                continue
            try:
                payload = _json.loads(evt.payload_json or "{}")
                imagen_used = payload.get("imagen_used")
            except Exception:
                imagen_used = None

            if imagen_used is False:
                # ?喳?銝蝡???? ??蝣箏?瞍?嚗?????                img_quality_by_sid[sid_evt] = "fallback"
            elif imagen_used is True and img_quality_by_sid.get(sid_evt) != "fallback":
                # ?桀????Ⅱ摰??????急???ok
                img_quality_by_sid[sid_evt] = "ok"

    out = []
    for rep, sess in rows:
        cons = cons_map.get(sess.consultant_name) if (sess and sess.consultant_name) else None
        fallback_name = _name_from_summary(rep.client_summary)

        # ?? 閫???葫??FK ?芸? ??Session.subject_name ??client_summary
        subj_record = None
        sid = rep.subject_id or (sess.subject_id if sess else None)
        if sid:
            subj_record = subj_map.get(sid)

        if subj_record:
            # ??撌脤??臬銝餅?嚗＊蝷箇?撖血???撟湧翩
            raw_name        = subj_record.name
            subject_age     = _calc_age(subj_record.birth_date)
            subject_gender  = subj_record.gender
            subject_email_real = subj_record.email
        else:
            raw_name        = (sess.subject_name if sess else None) or fallback_name
            subject_age     = (sess.subject_age if sess else None)
            subject_gender  = (sess.subject_gender if sess else None)
            subject_email_real = None

        # ?? 摮文?/皜祈岫?勗?霅嚗?銝餅? + 憪??粹?閮剖???
        is_placeholder = (not subj_record) and ((not raw_name) or (raw_name in PLACEHOLDER_NAMES))
        if is_placeholder:
            ts_label = rep.completed_at.strftime("%m/%d %H:%M") if rep.completed_at else f"#{rep.report_id}"
            subject_name = f"?妒 蝟餌絞皜祈岫?勗? 繚 {ts_label}"
            is_test = True
        elif raw_name and raw_name.startswith("?妒 蝞∠??⊥葫閰?"):
            subject_name = raw_name
            is_test = True
        else:
            subject_name = raw_name or "(??session)"
            is_test = False

        # 敺?client_summary ? headless_error ??靽???∟?閮?        headless_error = None
        relation_members: list = []
        try:
            cs_data = _json.loads(rep.client_summary or "{}")
            headless_error = cs_data.get("headless_error")
            kind_lower = (rep.talent_report_kind or "").lower()
            if "marital" in kind_lower:
                # 憭怠氖?勗?嚗? client_summary ??拐犖憪???session_id
                husband_name = cs_data.get("husband_name") or cs_data.get("subject_name") or ""
                wife_name    = cs_data.get("wife_name") or ""
                relation_members = [
                    {"name": husband_name, "session_id": cs_data.get("husband_session_id") or rep.session_id, "role": "husband"},
                    {"name": wife_name,    "session_id": cs_data.get("wife_session_id"),                       "role": "wife"},
                ]
            elif "parent_child" in kind_lower or "parent" in kind_lower:
                # 閬芸??勗?嚗? client_summary ??????                relation_members = cs_data.get("members") or []
        except Exception:
            pass

        out.append({
            "report_id":        rep.report_id,
            "session_id":       rep.session_id,
            "subject_id":       sid,
            "subject_name":     subject_name,
            "subject_age":      subject_age,
            "subject_gender":   subject_gender,
            "subject_email":    rep.notify_email or subject_email_real,
            "report_kind":      rep.talent_report_kind,
            "report_kind_zh":   _kind_zh(rep.talent_report_kind),
            "pdf_url":          rep.pdf_url,
            "status":           rep.status,
            "email_sent":       rep.email_sent,
            "completed_at":     rep.completed_at.isoformat() if rep.completed_at else None,
            "consultant":       (sess.consultant_name if sess else None),
            "consultant_org":   (cons.org if cons else None),
            "consultant_role":  (cons.role if cons else None),
            "orphan":           (rep.session_id is None),
            "is_test":          is_test,
            "linked_to_subject": subj_record is not None,
            "headless_error":   headless_error,
            "error_message":    rep.error_message or headless_error,  # ?芸???error_message 甈?嚗allback ??client_summary
            "image_quality":    img_quality_by_sid.get(rep.session_id) if rep.session_id else None,
            # ???勗?撠惇嚗????∪???+ session_id嚗dmin 敺憿舐內???啁??嚗?            "relation_members": relation_members,
        })
    return {"ok": True, "count": len(out), "reports": out}


@router.get("/gcs-list")
def list_gcs_pdfs(
    prefix: str = Query("", description="GCS object ?韌蝭拚嚗?嚗eports/general/嚗?),
    limit: int = Query(500, ge=1, le=2000),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """
    ?湔? GCS bucket ?扳???PDF嚗??芣 DB 銝剜?蝝??嚗?    蝞∠??∪??具?蝑???7 憭?signed URL??    ?亥府?拐辣 URL 撌脣 DB Report.pdf_url ?改??? report_id?ubject_name?mail_sent 蝑?閮?    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "?恣??臭蝙?冽迨?")

    from app.services import gcs_uploader
    if not gcs_uploader.is_configured():
        return {
            "ok": False,
            "error": "GCS ?芾身摰?蝻?GCS_BUCKET_NAME ??GCP_SERVICE_ACCOUNT_JSON嚗?,
            "items": [],
        }

    items = gcs_uploader.list_pdfs(prefix=prefix, max_items=limit)

    # 頝?DB 瘥?嚗 object name ?怎垢??? LIKE
    # ? Report.pdf_url ?胯igned URL嚗 token嚗?瘥活蝪賣?霈?
    # ??object_name 摮?銝脣?寥? pdf_url ?帘??    db_reports = db.query(
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

    # ??(pdf_url, info) ?渡???亦? dict嚗 object name 瘥?嚗?    # GCS pdf_url ? /<bucket>/<object_name>?X-Goog-...
    # signed URL ?急? URL 蝺函Ⅳ?葉??? unquote 敺??質? GCS list ??憪楝敺?撠?    import urllib.parse as _urlparse
    db_by_object: dict[str, dict] = {}
    for r in db_reports:
        url = r.pdf_url or ""
        # ??query 銋???挾嚗蒂?賢 bucket 敺? path
        try:
            # https://storage.googleapis.com/<bucket>/<obj>?...
            no_q = url.split("?", 1)[0]
            # ??bucket 銋????            seg = no_q.split("/")
            # ?喳?敶Ｗ? ['https:', '', 'storage.googleapis.com', bucket, '...']
            if len(seg) >= 5:
                obj_in_db = "/".join(seg[4:])
            else:
                obj_in_db = no_q
            # signed URL ?葉??鋡?URL 蝺函Ⅳ嚗?E8%98%87...嚗??閫?Ⅳ???GCS 頝臬?瘥?
            obj_in_db = _urlparse.unquote(obj_in_db)
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
    only_missing: bool = Query(False, description="True = ?芰?瞍??/ 憭望? / ?∩???),
    only_mine: bool = Query(False),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """
    瑼Ｘ葫 ???勗? 撠銵剁?? Session 銝行??箏???Report ???
    瘥??嚗?      session_id / subject_name / consultant / report_type / captures / created_at
      report_status: pending/processing/completed/failed/none
      has_pdf:       bool
      health:        ok | missing_pdf | stale_pending | failed | session_failed
      is_missing:    True 銵函內?閬??啁???瞍??

    health ?文?嚗?      - session.status == 2          ??"session_failed"嚗炎皜祆頨怠仃??銝???嚗?      - report 銝???               ??"missing_report"
      - report.status == "failed"   ??"failed"
      - report.status in pending/processing 銝?隞?> 30 ?? ??"stale_pending"
      - report.status == "completed" 雿 pdf_url           ??"missing_pdf"
      - report.status == "completed" 銝? pdf_url           ??"ok"
      - ?嗡?嚗?頝?憭???pending嚗?                      ??"in_progress"
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

    # ?? ???????Subject ??撖西?????皞?Session.subject_id ??Report.subject_id嚗?    subject_ids = set()
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

    PLACEHOLDER_NAMES = {"?葫??, "?喳???, "皜祈岫璅∪?", "test", "Test", "TEST"}

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
            # pending / generating ????Report.created_at嚗? Session.created_at ?湔?蝣綽?
            # 瘥活 regenerate ?賣??湔 r.created_at嚗ession.created_at ?舀憭拙遣蝡?銝?嚗?            ref_ts = None
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

        # ?? ?祕憪?閫??嚗K ?芸? ?????Session.subject_name 摮葡
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
            # 瘝??臭蜓瑼?憪???placeholder ??憿舐內???芸‵) ?葫??蝷箏迨??            if raw in PLACEHOLDER_NAMES or not raw:
                display_name = f"?? ?葫???芷??銝餅?嚗ession #{s.session_id}嚗?
            else:
                display_name = raw
            display_age = s.subject_age

        # 敺?client_summary ?憭望???霈?蝡舫＊蝷?        # ?芸 status=failed ???嚗???葉?＊蝷箄??仃????        headless_error_sw = None
        if r and r.status == "failed" and r.client_summary:
            try:
                import json as _jsw
                cs_sw = _jsw.loads(r.client_summary)
                # ?芸??典撱?Gemini ?航炊嚗? headless ?航炊
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
            "health":        health,
            "is_missing":    is_missing,
            "headless_error": headless_error_sw,   # 憭望???嚗eadless_renderer 撖怠嚗?            "needs_retest":  bool(s.needs_retest),  # 蝞∠??⊥?閮??葫
            "retest_reason": s.retest_reason or "",
        })

    return {
        "ok":             True,
        "count":          len(out),
        "missing_count":  missing_count,
        "sessions":       out,
    }


def _session_to_brainwave_data(db: Session, session_id: int) -> Optional[dict]:
    """敺?EegCapture ?? trigger_external_report ????brainwave_data ?澆???
    ?澆?嚗?      { attention_percentage, meditation_percentage,
        bands_avg: { theta, alpha, beta, gamma } }
    """
    from app.services.algorithms import compute_averages

    captures = db.query(M.EegCapture).filter(
        M.EegCapture.session_id == session_id
    ).order_by(M.EegCapture.seq_num).all()
    if not captures:
        return None

    # ??箇?嚗s_baseline=1嚗?    detection = [
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

    # ?迤????賂?session.total_captures嚗? len(captures) ?湔?蝣綽?
    # ?啁? save-stats 瘚??芸神 1 蝑?EegCapture嚗像??閬?seq_num=0嚗?
    # 雿?total_captures 閮?? _summarizeEegAccum ??甇?敞蝛?璅??賂?蝘嚗?    sess_for_sc = db.query(M.Session).filter(M.Session.session_id == session_id).first()
    real_sample_count = (
        (sess_for_sc.total_captures if sess_for_sc and sess_for_sc.total_captures else 0)
        or len(captures)
    )

    avg = compute_averages(detection)
    # 靽格迤嚗??賜 `x or 50`嚗???瘜? 0 / 0.0 / ?亥? 0 ???潭?? 50嚗?    # ?寞??芸??? None????fallback嚗? fallback ?寧?勗?蝡舀捱摰??ㄐ?交?鞈?銝敺葆撖阡??潘?
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

    # 5-band ??嚗ow + high ?像??deduped 撖怠??潛??撟喳? = 閰?band ?潘?
    def _band_avg(lo, hi):
        a = _safe_float(lo, None)
        b = _safe_float(hi, None)
        if a is None and b is None:
            return 50.0
        if a is None:  return b
        if b is None:  return a
        return (a + b) / 2.0

    lo_alpha = _safe_float(avg.low_alpha)
    hi_alpha = _safe_float(avg.high_alpha)
    lo_beta  = _safe_float(avg.low_beta)
    hi_beta  = _safe_float(avg.high_beta)
    lo_gamma = _safe_float(avg.low_gamma)
    hi_gamma = _safe_float(avg.high_gamma)

    # ?? BrainDNA 蝞?嚗??皞?摨?Firebase ??raw_arrays_json ??DB 撟喳?????
    # 鞈?靘??芸???隤芣?嚗?    #   1. Firebase嚗etch 180 蝑敺???firebase_features_to_raw_arrays ??BrainDNA
    #   2. PostgreSQL raw_arrays_json嚗ession 靽???180 蝘????BrainDNA
    #   3. DB 撟喳??潘?EegCapture ?桃?撟喳?嚗??敺?fallback
    _bdna_bands = None
    _bdna_source = "db_avg"
    try:
        import json as _json
        from app.services.braindna_algorithms import compute_all as _bdna_compute
        _sess_obj = db.query(M.Session).filter(M.Session.session_id == session_id).first()
        _is_child = (getattr(_sess_obj, "report_type", None) or "").lower() in ("child", "child_report")
        _child_age = getattr(_sess_obj, "subject_age", None) if _is_child else None

        # 靘? 1嚗irebase 180 蝑敺蛛??甈?嚗?        if _sess_obj and _sess_obj.firebase_session_id:
            try:
                import asyncio as _aio
                from app.services.firebase_sync import fetch_eeg_features, firebase_features_to_raw_arrays
                _fb_features = _aio.run(fetch_eeg_features(_sess_obj.firebase_session_id))
                if _fb_features and len(_fb_features) >= 10:
                    _fb_raw = firebase_features_to_raw_arrays(_fb_features)
                    _result = _bdna_compute(_fb_raw, is_child=_is_child, child_age=_child_age)
                    if _result.get("valid") and _result.get("bands"):
                        _bdna_bands = _result["bands"]
                        _bdna_source = "firebase_180"
            except Exception as _fe:
                pass  # Firebase 憭望??匱蝥?銝?fallback

        # 靘? 2嚗ostgreSQL raw_arrays_json
        if _bdna_bands is None and _sess_obj and _sess_obj.raw_arrays_json:
            _raw = _json.loads(_sess_obj.raw_arrays_json)
            _result = _bdna_compute(_raw, is_child=_is_child, child_age=_child_age)
            if _result.get("valid") and _result.get("bands"):
                _bdna_bands = _result["bands"]
                _bdna_source = "pg_raw_arrays"
    except Exception:
        pass  # ???DB 撟喳???
    # BrainDNA ??蝯?閬神?券 8 ?餅挾嚗 delta/theta嚗?    _bdna_delta = _safe_float(avg.delta)
    _bdna_theta = _safe_float(avg.theta)
    if _bdna_bands:
        lo_alpha    = float(_bdna_bands.get("low_alpha",  lo_alpha))
        hi_alpha    = float(_bdna_bands.get("high_alpha", hi_alpha))
        lo_beta     = float(_bdna_bands.get("low_beta",   lo_beta))
        hi_beta     = float(_bdna_bands.get("high_beta",  hi_beta))
        lo_gamma    = float(_bdna_bands.get("low_gamma",  lo_gamma))
        hi_gamma    = float(_bdna_bands.get("high_gamma", hi_gamma))
        _bdna_delta = float(_bdna_bands.get("delta", _bdna_delta))
        _bdna_theta = float(_bdna_bands.get("theta", _bdna_theta))
    # ?????????????????????????????????????????????????????????????????????????

    # ?? 霈??qEEG 銝之?賢??嚗???Session.qeeg_scores_json嚗??????????????
    _qeeg_abilities = None
    try:
        import json as _qjson
        _sess_qeeg = db.query(M.Session).filter(M.Session.session_id == session_id).first()
        _qraw = getattr(_sess_qeeg, "qeeg_scores_json", None)
        if _qraw:
            _qdata = _qjson.loads(_qraw) if isinstance(_qraw, str) else _qraw
            _ab = _qdata.get("ability_scores") or {}
            if _ab:
                _qeeg_abilities = {
                    k: round(_ab[k]["score"])
                    for k in _ab if isinstance(_ab.get(k), dict)
                }
    except Exception:
        pass

    bw = {
        "attention_percentage":  _safe_int(avg.attention),
        "meditation_percentage": _safe_int(avg.meditation),
        "sample_count":          real_sample_count,
        "bands_avg": {
            "delta": _bdna_delta,
            "theta": _bdna_theta,
            "alpha": _band_avg(lo_alpha, hi_alpha),
            "beta":  _band_avg(lo_beta,  hi_beta),
            "gamma": _band_avg(lo_gamma, hi_gamma),
            "low_alpha":  lo_alpha, "high_alpha": hi_alpha,
            "low_beta":   lo_beta,  "high_beta":  hi_beta,
            "low_gamma":  lo_gamma, "high_gamma": hi_gamma,
        },
        "bands_7": {
            "theta":      _bdna_theta,
            "alpha_high": hi_alpha,
            "alpha_low":  lo_alpha,
            "beta_high":  hi_beta,
            "beta_low":   lo_beta,
            "gamma_high": hi_gamma,
            "gamma_low":  lo_gamma,
        },
        "_source": _bdna_source,  # ?菟?剁?firebase_180 / pg_raw_arrays / db_avg
    }
    # ?芸??qEEG ?????嚗??null 瘙?嚗?    if _qeeg_abilities:
        bw["qeeg_abilities"] = _qeeg_abilities
    return bw


def _do_regenerate_one(
    db: Session,
    session_id: int,
    notify_email: Optional[str],
    variant: str = "full",
) -> dict:
    """?桃????詨?嚗eset Report?? brainwave_data?孛??trigger_external_report??
    ??摰?敺?敺脣?? admin ?詨?撖縑????(email_sent=0)嚗?    蝞∠??⊿??啜?恣??閬?PDF 敺??賣????箝?    """
    s = db.query(M.Session).filter(M.Session.session_id == session_id).first()
    if not s:
        return {"ok": False, "session_id": session_id, "error": "Session 銝???}
    if s.status == 2:
        return {"ok": False, "session_id": session_id,
                "subject_name": s.subject_name, "error": "??瑼Ｘ葫?祈澈憭望? (status=2)"}

    bw = _session_to_brainwave_data(db, session_id)
    if bw is None:
        return {"ok": False, "session_id": session_id,
                "subject_name": s.subject_name, "error": "?曆??啗瘜Ｚ???(EegCapture ?箇征)"}

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
        r.status       = "generating"   # ??generating 霈?蝡舫＊蝷箝 ??銝准?        r.pdf_url      = None
        r.email_sent   = 0
        r.created_at   = _dt.now()      # ???蔭閮??剁??踹?蝡憿舐內?雿?>30 ????        r.completed_at = None
        if notify_email:
            r.notify_email = notify_email
        # ?完 皜? client_summary 鋆∠??仃???荔??踹????啁??葉??憿舐內銝活?隤?        if r.client_summary:
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

    # 閫貊憭 React App嚗?鈭桃??勗?嚗?    from app.services import report_orchestrator

    # ?? 敺?Report.talent_report_kind 閫??甇?Ⅱ??report_type/variant ??
    # talent_report_kind ?澆?嚗?life_script_full" / "child_trial" / "marital_full" 蝑?    # ?芸???Report 撌脰???蝔桅?嚗allback ??Session.report_type ?函?
    kind_str = (r.talent_report_kind or "").lower()
    if "child" in kind_str:
        ext_report_type = "child"
    elif "marital" in kind_str:
        ext_report_type = "marital"
    elif "parent_child" in kind_str or "parent" in kind_str:
        ext_report_type = "parent_child"
    else:
        # fallback嚗? Session.report_type ?函?
        sess_rt = (s.report_type or "").lower()
        if "child" in sess_rt:
            ext_report_type = "child"
        elif "marital" in sess_rt:
            ext_report_type = "marital"
        elif "parent" in sess_rt:
            ext_report_type = "parent_child"
        else:
            ext_report_type = "life_script"

    # ?? 敺?Report.talent_report_kind 閫?? variant ??
    if "vip" in kind_str:
        resolved_variant = "vip"
    elif "trial" in kind_str:
        resolved_variant = "trial"
    else:
        resolved_variant = variant  # 雿輻?澆蝡臬?亦?嚗?閮?"full"嚗?
    # ?? ?葫??撖血??圾????start_full ?詨??摩嚗?    PLACEHOLDER_NAMES_REGEN = {"?葫??, "?喳???, "皜祈岫璅∪?", "test", "Test", "TEST"}
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
            logger.warning("[_do_regenerate_one] ? Subject 憭望?: %s", _e)

    # ????絞銝韏啣??剁?Vercel headless ??REST API嚗?    # life_script / child ??headless + DB 頛芾岷蝣箄? callback
    # marital / parent_child ???湔 REST API
    regen_extra: dict = {"session_id": session_id, "subject_id": resolved_regen_sid}

    # ???勗????嚗? client_summary ???/?鞈?
    if ext_report_type in ("marital", "parent_child"):
        try:
            import json as _rjson
            cs_regen = _rjson.loads(r.client_summary or "{}")
            if ext_report_type == "marital":
                if cs_regen.get("wife_session_id"):
                    regen_extra["wife_session_id"] = cs_regen["wife_session_id"]
                if cs_regen.get("wife_name"):
                    regen_extra["wife_name"] = cs_regen["wife_name"]
                if cs_regen.get("husband_name"):
                    regen_extra["husband_name"] = cs_regen["husband_name"]
            elif ext_report_type == "parent_child" and cs_regen.get("members"):
                regen_extra["members"] = cs_regen["members"]
        except Exception as _re:
            logger.warning("[_do_regenerate_one] 霈??client_summary ???憭望?: %s", _re)

    try:
        result = report_orchestrator.trigger_external_report(
            report_type=ext_report_type,
            subject_name=resolved_regen_name or s.subject_name or "",
            subject_email=resolved_regen_email,
            subject_age=s.subject_age,
            subject_gender=s.subject_gender or "",
            subject_birthday=s.subject_birthday or "",
            variant=resolved_variant,
            brainwave_data=bw,
            extra=regen_extra,
        )
    except Exception as e:
        return {"ok": False, "session_id": session_id,
                "subject_name": resolved_regen_name or s.subject_name,
                "error": f"trigger 憭望?嚗type(e).__name__}: {e}"}

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
    """撠?摰?Session ?閫貊?勗???嚗恣?撠嚗?    ??摰?敺?敺脣?? admin ?詨?撖縑????瘞訾??芸?撖?""
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "?恣??航孛?潮??啁???)

    p = payload or RegenerateReportIn()
    res = _do_regenerate_one(
        db, session_id,
        notify_email=p.notify_email,
        variant=p.variant,
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("error") or "???憭望?")
    res["note"] = "撌脰孛?潮??啁?????隢??恣????? 鞈?摨怎???閬賢???暺???汗敺?靽～?
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
    """?寞活??嚗?摨孛?潭?銝蝑??券?脣???詨?????""
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "?恣??航孛?潮??啁???)
    if not payload.items:
        raise HTTPException(400, "items 銝?箇征")
    if len(payload.items) > 50:
        raise HTTPException(400, "?格活?憭?50 蝑?)

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
        "note":     "?券摰?敺???admin ?具?恣????? 鞈?摨怎???閬賢???撖縑??,
    }


@router.post("/reset-stuck")
def reset_stuck_reports(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """蝞∠??⊥??孛?潘??????generating/pending ??Report ?身??failed??
    ?拍?湔嚗?      - Railway ??函蔡敺迨????????      - ???啁????????湧＊蝷箝 ??銝准?      - ?閬??炎皜????勗????ａ＊蝷?failed ?????活暺??啁???    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "?恣??舫?閮?)

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
        "note":  f"撌脣? {len(reset_ids)} 蝑雿??勗??身??failed???喋?恣????瑼Ｘ葫???????????,
    }


class ImportFromGcsIn(BaseModel):
    object_name:   str                          # 靘? reports/general/1779359536955_?剖??︵?行郭???勗?.pdf
    subject_name:  Optional[str] = None         # ?箇征??瑼?閫??
    subject_email: Optional[str] = None         # 銋?撖縑??    report_type:   str = "life_script"          # life_script / child / parent_child / marital
    variant:       str = "full"
    pending_send:  int = 1                      # ?身閬? admin ?詨???
    consultant:    Optional[str] = None         # ?亦??芯?憿批?摰Ｘ


@router.post("/import-from-gcs")
def import_from_gcs(
    payload: ImportFromGcsIn,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    撠?GCS 銝?摮文? PDF 鋆???DB Report 銵剁?蝞∠??∪??剁???
    ?券??拇? record callback bug ?????? GCS 雿???DB嚗?    ?冽迨蝡舫?霈?admin 銝?菜?摰??脖?嚗?敺停?賣迤撣貊恣??/ 撖縑??    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "?恣??臭蝙?冽迨?")

    from app.services import gcs_uploader
    from google.cloud import storage
    from google.oauth2 import service_account
    from datetime import timedelta

    obj = (payload.object_name or "").strip()
    if not obj:
        raise HTTPException(400, "蝻箏? object_name")
    if not obj.lower().endswith(".pdf"):
        raise HTTPException(400, "?芣??.pdf")

    if not gcs_uploader.is_configured():
        raise HTTPException(500, "GCS ?芾身摰?)

    # 1) 蝣箄?瑼?摮銝偷 URL
    try:
        creds_dict = gcs_uploader._credentials_dict()
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        client = storage.Client(project=creds_dict.get("project_id"), credentials=credentials)
        bucket = client.bucket(gcs_uploader._bucket_name())
        blob = bucket.blob(obj)
        if not blob.exists():
            raise HTTPException(404, f"GCS ?曆??唳迨?拐辣嚗obj}")
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
        raise HTTPException(500, f"蝪?GCS URL 憭望?嚗type(e).__name__}: {e}")

    # 2) 敺??圾??subject_name嚗?澆蝡舀???嚗?    #    ?澆?嚗eports/<area>/<epoch_ms>_<subject_name>_<report_label>.pdf
    subject_name = (payload.subject_name or "").strip()
    if not subject_name:
        fname = os.path.basename(obj).rsplit(".", 1)[0]
        parts = fname.split("_")
        # parts[0]=epoch?arts[1]=name?arts[2:]=label
        if len(parts) >= 2:
            subject_name = parts[1] or "(?芰)"
        else:
            subject_name = fname

    # 3) ?踹???鋆?嚗 object_name ???瘥? pdf_url 銝剔? object path嚗?    # signed URL ??URL 蝺函Ⅳ嚗???瘥???頝臬??楊蝣澆?頝臬?
    import urllib.parse as _urlparse
    obj_encoded = _urlparse.quote(obj, safe="/")
    existing = (
        db.query(M.Report)
        .filter(
            M.Report.pdf_url.like(f"%{obj}%") |
            M.Report.pdf_url.like(f"%{obj_encoded}%")
        )
        .first()
    )
    if existing:
        # 撌脩?鋆? / 撌脩????????湔 signed URL嚗????芸?蝥偷嚗?        existing.pdf_url = signed
        if payload.subject_email and not existing.notify_email:
            existing.notify_email = payload.subject_email
        db.commit()
        return {
            "ok": True,
            "note": "甇斗?獢歇??DB嚗歇?湔 signed URL",
            "report_id": existing.report_id,
        }

    # ?? ?典遣蝡??岫閫?? subject_id嚗??摮文??勗?嚗?    resolved_sid = None
    try:
        PLACEHOLDER = {"?葫??, "?喳???, "皜祈岫璅∪?", "test", "Test", "TEST"}
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

    # 4) 撱箇? Report row嚗迨??session_id=NULL嚗??∪?賢神??subject_id嚗?    rep = M.Report(
        session_id     = None,
        subject_id     = resolved_sid,           # ?? 撖怠 FK
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
        "note": "撌脣?摮文?瑼?? DB??甈∪??恣????? 鞈?摨怎???舐?閬?,
    }


@router.delete("/gcs-file")
def delete_gcs_file(
    object_name: str = Query(..., description="GCS object name嚗?憒?reports/general/xxx.pdf"),
    also_db: bool = Query(True, description="True = ???芷 DB 銝剖??? Report 閮?嚗eport_id ?芣?靘???LIKE 瘥?嚗?),
    report_id: Optional[int] = Query(None, description="蝎曄Ⅱ?芷?? report_id嚗? also_db+LIKE嚗?),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """蝞∠??∪??剁?敺?GCS ?芷?? PDF 瑼?嚗蒂?舫?????DB 蝝??
    撱箄降?喳 report_id嚗移蝣箏?歹?銝?銝剜? URL 蝺函Ⅳ撟脫嚗?    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "?恣??臬??GCS 瑼?")

    obj = (object_name or "").strip()
    if not obj:
        raise HTTPException(400, "object_name 銝?箇征")

    from app.services import gcs_uploader

    # 1) ?芷 GCS ?拐辣
    gcs_result = gcs_uploader.delete_pdf_object(obj)

    # 2) ?芷 DB Report 閮?
    db_deleted = []
    if report_id:
        # ?芸?嚗 report_id 蝎曄Ⅱ?芷嚗?葉?? URL 蝺函Ⅳ撠 LIKE 銝??
        rep = db.query(M.Report).filter(M.Report.report_id == report_id).first()
        if rep:
            db_deleted.append({"report_id": rep.report_id, "session_id": rep.session_id})
            db.delete(rep)
            db.commit()
    elif also_db:
        # ?嚗 LIKE 瘥?嚗?冽 ASCII-only ??object_name嚗?        from urllib.parse import quote
        # ?岫??? + URL 蝺函Ⅳ?
        patterns = [f"%{obj}%"]
        try:
            encoded_obj = quote(obj, safe="/")
            if encoded_obj != obj:
                patterns.append(f"%{encoded_obj}%")
        except Exception:
            pass
        matched_ids = set()
        for pat in patterns:
            for rep in db.query(M.Report).filter(M.Report.pdf_url.like(pat)).all():
                if rep.report_id not in matched_ids:
                    matched_ids.add(rep.report_id)
                    db_deleted.append({"report_id": rep.report_id, "session_id": rep.session_id})
                    db.delete(rep)
        if db_deleted:
            db.commit()

    return {
        "ok": gcs_result.get("ok", False),
        "object_name": obj,
        "gcs": gcs_result,
        "db_deleted": db_deleted,
        "note": f"GCS {'?芷??' if gcs_result.get('ok') else '?芷憭望?嚗? + str(gcs_result.get('error', ''))}"
               + (f"嚗B 撌脣??{len(db_deleted)} 蝑???? if db_deleted else "嚗B ?∪?????),
    }


@router.get("/by-subject")
def by_subject(
    email: str = Query(..., description="?葫??email"),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """靘?皜祈?email ?亙???葫?撌梁??剁?"""
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
    """閮剖?閮箸"""
    secret = (os.getenv("REPORTS_INGEST_SECRET") or "").strip()
    return {
        "ingest_secret_set": bool(secret),
        "ingest_secret_len": len(secret),
        "note": "?芾身摰? /record 蝡舫??隞颱?靘? POST嚗???剁?嚗迤撘憓?閮剖???,
    }


@router.get("/diag/mbti/{session_id}")
def diag_mbti(
    session_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """MBTI 閮箸嚗＊蝷?session ??lo_alpha/theta ?詨潦?西?蝞?蝔BTI 蝯???    ?冽??BTI 瘞賊? ISTP??憿?""
    import math
    from scipy.stats import norm as _norm
    from app.services.algorithms import _to_raw, BandAverages, compute_mbti, compute_mbti_layers_from_captures, aggregate_mbti_profiles
    from app.algorithms.bagua import Bagua
    from app.algorithms.data_stats import DATA_STATS

    require_user(authorization, db)

    # ??session
    sess = db.query(M.Session).filter(M.Session.session_id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session {session_id} 銝???)

    # ?瘜Ｘ??    caps = db.query(M.EegCapture).filter(M.EegCapture.session_id == session_id).all()
    if not caps:
        return {"session_id": session_id, "error": "甇?session ?∟瘜Ｚ???}

    det = [c for c in caps if c.is_baseline == 0] or list(caps)
    n = len(det)
    def avg_attr(attr): return sum(getattr(c, attr, 0) or 0 for c in det) / n

    lo_alpha_avg = avg_attr("low_alpha")
    hi_alpha_avg = avg_attr("high_alpha")
    theta_avg    = avg_attr("theta")

    # 閮? MBTI
    avg_obj = BandAverages(
        delta=avg_attr("delta"), theta=theta_avg,
        low_alpha=lo_alpha_avg, high_alpha=hi_alpha_avg,
        low_beta=avg_attr("low_beta"), high_beta=avg_attr("high_beta"),
        low_gamma=avg_attr("low_gamma"), high_gamma=avg_attr("high_gamma"),
        attention=avg_attr("attention"), meditation=avg_attr("meditation"),
        sample_count=n,
    )
    result = compute_mbti(avg_obj)

    # 閮???嚗to_raw ?芸?霅 raw ThinkGear ??vs 0-100 ?嚗?    raw_la = _to_raw(lo_alpha_avg)
    raw_th = _to_raw(theta_avg)
    la_mean = DATA_STATS["lowAlpha"]["mean"]
    la_std  = DATA_STATS["lowAlpha"]["std"]
    p_la = float(_norm.cdf(math.log10(max(raw_la, 0.1)), la_mean, la_std))
    p_th = float(_norm.cdf(math.log10(max(raw_th, 0.1)), la_mean, la_std))
    bagua     = Bagua.calcBagua(None, raw_la)
    bagua_li  = Bagua.calcBaguaWithLi(raw_la, raw_th)

    # 4 撅斗??? MBTI + 憭扳?? (雿輻??啁黎蝯???蝞?)
    det_dicts = [
        {"low_alpha": getattr(c,"low_alpha",0), "theta": getattr(c,"theta",0),
         "attention": getattr(c,"attention",0), "meditation": getattr(c,"meditation",0),
         "delta": getattr(c,"delta",0), "high_alpha": getattr(c,"high_alpha",0),
         "low_beta": getattr(c,"low_beta",0), "high_beta": getattr(c,"high_beta",0),
         "low_gamma": getattr(c,"low_gamma",0), "high_gamma": getattr(c,"high_gamma",0)}
        for c in det
    ]

    # 雿輻?啁? build_mbti_payload嚗???MindColor + 蝢斤?閰?嚗?    from app.services.algorithms import build_mbti_payload
    mbti_payload = build_mbti_payload(avg_obj, det_dicts)
    layers       = mbti_payload.get("mbti_layers") or {}
    profiles     = mbti_payload.get("mbti_profiles") or []

    bagua_zones = [
        {"name": "qian", "range_norm": [0, 59.7], "pct": [0, 0.125], "mbti": ["INTJ","INTP"]},
        {"name": "dui",  "range_norm": [59.7, 63.1], "pct": [0.125, 0.25], "mbti": ["ENTJ","ENTP"]},
        {"name": "zhen", "range_norm": [63.1, 65.6], "pct": [0.25, 0.375], "mbti": ["ENFJ","ENFP"]},
        {"name": "xun",  "range_norm": [65.6, 67.9], "pct": [0.375, 0.5], "mbti": ["ISTJ","ISFJ"]},
        {"name": "kan",  "range_norm": [67.9, 70.1], "pct": [0.5, 0.625], "mbti": ["ESTJ","ESFJ"]},
        {"name": "gen",  "range_norm": [70.1, 72.6], "pct": [0.625, 0.75], "mbti": ["ISTP","ISFP"]},
        {"name": "kun",  "range_norm": [72.6, 100],  "pct": [0.75, 1.0],  "mbti": ["ESTP","ESFP"]},
    ]

    return {
        "session_id":    session_id,
        "subject_name":  sess.subject_name,
        "db_values": {
            "lo_alpha_avg_from_db": round(lo_alpha_avg, 2),
            "hi_alpha_avg_from_db": round(hi_alpha_avg, 2),
            "theta_avg_from_db":    round(theta_avg, 2),
            "note": "DB ?脣???? ThinkGear ?潘??啁?嚗?擃潘?>1000嚗誨銵典?憪撘?
        },
        "calculation": {
            "lo_alpha_normalized": round(lo_alpha_avg, 2),
            "lo_alpha_raw_inverted": round(raw_la, 0),
            "lo_alpha_log10":       round(math.log10(max(raw_la, 0.1)), 4),
            "lo_alpha_percentile":  round(p_la, 4),
            "theta_normalized":     round(theta_avg, 2),
            "theta_raw_inverted":   round(raw_th, 0),
            "theta_percentile":     round(p_th, 4),
            "theta_is_high":        p_th > 0.5,
        },
        "bagua_result": {
            "bagua_7gua":      bagua.id,
            "bagua_8gua_li":   bagua_li.id,
            "bagua_name":      bagua_li.name,
            "note":            "8 ?佗??恍?佗???蝡?_etBaguaMBTI(useLi=true) 銝?湛??箏?蝙?函??蝯?,
            "gen_zone_range": "normalized lo_alpha in [70.1, 72.6] ??ISTP/ISFP",
            "current_zone": next((z for z in bagua_zones if z["name"] == bagua_li.id), None),
        },
        "mbti_result":   result,
        "mbti":          mbti_payload,          # ?啁?摰 payload嚗蝢斤?閰?嚗?        "mbti_layers":   {k: {"type": v.get("type") or v.get("mbti_type"), "confidence": v.get("confidence")} for k, v in (layers or {}).items()},
        "mbti_profiles": profiles,
        "all_bagua_zones": bagua_zones,
        "diagnosis": (
            "?? lo_alpha ?賢??gen)?血???[70.1-72.6]嚗??迨蝭??蝙?刻????ISTP/ISFP??
            "?亙?鈭箇蜇?臬???ISTP嚗”蝷箏?皜祈? lo_alpha ?餅挾?潛隡潘?撅祆?蝞?甇?虜銵??
            if bagua_li.id == "gen" else
            f"lo_alpha={lo_alpha_avg:.1f} ??{bagua_li.id}({bagua_li.name})??8?? ??{result['mbti_type']}"
        ),
    }


# ????????????????????????????????????????????????????????????????????????????
# 蝞∠??∴?頝典董??皜祈閬?# ????????????????????????????????????????????????????????????????????????????
@router.get("/all-subjects-overview")
def all_subjects_overview(
    q: Optional[str] = Query(None, description="?摮?憪? / Email / ?? / 憿批?嚗?),
    limit: int = Query(500, ge=1, le=2000),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """蝞∠??∪??剁?????董?????葫??閮?
    瘥??嚗?      - ?箸鞈?嚗ubject_id / name / birth_date / gender / age / email / phone /
                  occupation / medical_history / medications / consultant_id /
                  consultant_name / consultant_org / created_at
      - 瑼Ｘ葫?湔活敶蜇嚗essions_count?atest_session_id?atest_session_at??                      latest_report_type
      - 閰脣?皜祈??????憭?20 蝑???pdf_url?tatus?mail_sent??        report_kind?ompleted_at?ession_id嚗?      - 閰脣?皜祈??唬?甈⊥炎皜祉??行郭撟喳?嚗ttention / meditation /
        bands_avg: theta/alpha/beta/gamma嚗?
    瘥?蝑嚗?頠?嚗?      A. 銝餉?嚗 Subject.subject_id ? Session.subject_id ??Report.subject_id
      B. ?航?嚗?銝摰對?嚗??潮?瘝?憛?subject_id ?? Session/Report嚗?         ???subject_name 摮葡瘥???    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="?恣??舀?楊撣唾??葫??閮?)

    # 1) ????Subjects嚗dmin ?舐??券嚗?    subj_q = db.query(M.Subject)
    if q:
        kw = f"%{q.strip()}%"
        from sqlalchemy import or_ as _or
        subj_q = subj_q.filter(_or(
            M.Subject.name.like(kw),
            M.Subject.email.like(kw),
            M.Subject.phone.like(kw),
        ))
    subjects = subj_q.order_by(M.Subject.subject_id.desc()).limit(limit).all()

    # 2) 憿批?皜
    cons_ids = {s.consultant_id for s in subjects if s.consultant_id}
    cons_map: dict[int, M.Consultant] = {}
    if cons_ids:
        for c in db.query(M.Consultant).filter(M.Consultant.consultant_id.in_(cons_ids)).all():
            cons_map[c.consultant_id] = c

    subject_id_set = {s.subject_id for s in subjects}
    name_set  = {s.name for s in subjects if s.name}

    # 3A) 銝餉?嚗ubject_id ?湔?賭葉嚗 NULL ?蕪嚗?    sess_by_subj: dict[int, list[M.Session]] = {}
    if subject_id_set:
        sess_rows_fk = db.query(M.Session).filter(
            M.Session.subject_id.in_(list(subject_id_set))
        ).order_by(M.Session.session_id.desc()).all()
        for s in sess_rows_fk:
            sess_by_subj.setdefault(s.subject_id, []).append(s)

    # 3B) ?航?嚗???subject_id IS NULL ?? Session嚗 name 瘥?鋆?
    sess_by_name_legacy: dict[str, list[M.Session]] = {}
    if name_set:
        legacy_sessions = db.query(M.Session).filter(
            M.Session.subject_id.is_(None),
            M.Session.subject_name.in_(list(name_set)),
        ).order_by(M.Session.session_id.desc()).limit(5000).all()
        for s in legacy_sessions:
            sess_by_name_legacy.setdefault(s.subject_name, []).append(s)

    # 4) ???? session 撠???Report
    all_sess_ids = []
    for arr in sess_by_subj.values():
        all_sess_ids.extend([x.session_id for x in arr])
    for arr in sess_by_name_legacy.values():
        all_sess_ids.extend([x.session_id for x in arr])
    rep_map: dict[int, M.Report] = {}
    if all_sess_ids:
        for r in db.query(M.Report).filter(M.Report.session_id.in_(all_sess_ids)).all():
            rep_map[r.session_id] = r

    # 4B) ???eport.subject_id ?湔????orphan reports??瘝? session_id嚗??脖?
    orphan_reps_by_sid: dict[int, list[M.Report]] = {}
    if subject_id_set:
        for r in db.query(M.Report).filter(
            M.Report.subject_id.in_(list(subject_id_set)),
            M.Report.session_id.is_(None),
        ).order_by(M.Report.report_id.desc()).all():
            orphan_reps_by_sid.setdefault(r.subject_id, []).append(r)

    # 5) helper嚗僑朣∟?蝞?    def _age_from_birth(birth: str) -> Optional[int]:
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
        # ?? ???蔥嚗K ?賭葉??+ ????name ?賭葉??        sess_list_fk     = sess_by_subj.get(s.subject_id, [])
        sess_list_legacy = sess_by_name_legacy.get(s.name, [])
        # ??session_id ?駁?
        seen_sids = set()
        sess_list: list = []
        for ss in (sess_list_fk + sess_list_legacy):
            if ss.session_id in seen_sids:
                continue
            seen_sids.add(ss.session_id)
            sess_list.append(ss)
        sess_list.sort(key=lambda x: x.session_id, reverse=True)
        latest = sess_list[0] if sess_list else None

        # 閰脣?皜祈??????orphan reports嚗?憭?20 蝑?
        rep_list = []
        seen_rids = set()
        # ?? session ?????        for ss in sess_list[:20]:
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
        # Report.subject_id ?湔???? session_id IS NULL ?迨???        for r in orphan_reps_by_sid.get(s.subject_id, [])[:20]:
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

        # ??唬?甈⊥炎皜祉??行郭撟喳?
        bw = None
        if latest:
            try:
                bw = _session_to_brainwave_data(db, latest.session_id)
            except Exception:
                bw = None

        out.append({
            # ?箸鞈?
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
            # 憿批?鞈?嚗?董?遣瑼?
            "consultant_id":       s.consultant_id,
            "consultant_name":     (cons.name if cons else None),
            "consultant_org":      (cons.org  if cons else None),
            "consultant_role":     (cons.role if cons else None),
            "consultant_org_type": (cons.org_type if cons else None),
            "consultant_phone":    (cons.phone if cons else None),
            # 瑼Ｘ葫?湔活敶蜇
            "sessions_count":         len(sess_list),
            "latest_session_id":      (latest.session_id if latest else None),
            "latest_report_type":     (latest.report_type if latest else None),
            "latest_consultant_name": (latest.consultant_name if latest else None),
            "latest_session_at":      (latest.created_at * 1000 if latest and latest.created_at else None),  # 蝘?瘥怎?
            "latest_needs_retest":    bool(latest.needs_retest) if latest else False,
            # ?勗? + ?行郭
            "reports":           rep_list,
            "latest_brainwave":  bw,
        })

    return {
        "ok":    True,
        "count": len(out),
        "subjects": out,
    }


# ??? ?勗???鈭辣??? ????????????????????????????????????????????????????????
#
# 閮剛?嚗???React App嚗?鈭?/ ?咱嚗?頝?銝??蝭???菜郊撽?撠?POST 銝蝑?隞?# ??嚗??啣??????臬???啜?函??蝚?5 蝡???GCS 銝准仃?蝚?7 蝡?# 蝑???銝行?靘??渡??航炊閮????#
# 鈭辣 phase嚗?#   started        ?? ?????銝?#   chapter_start  ?? 蝚?N 蝡?/ 摮?蝭???澆 Gemini
#   chapter_done   ?? 閰脩?蝭蝯?
#   chapter_failed ?? 閰脩?蝭?澆憭望?
#   chapter_retry  ?? 閰脩?蝭?岫
#   pdf_render     ?? ??皜脫? PDF
#   gcs_upload     ?? 銝 GCS
#   email_sent     ?? ?芸?撖縑??
#   queue          ?? ?脣敺祟?訾???B 瘚?嚗?#   done           ?? ?券摰?
#   failed         ?? ?渡?憭望?
# ????????????????????????????????????????????????????????????????????????????

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
    """憭 React App callback嚗神?亙銝??鈭辣
    ?航◤?餌??澆嚗?蝡? 1-2 蝑?嚗?隞亦????    """
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
    """??餈?N ????閰晞?靘?correlation_id ??嚗?    瘥?憿舐內??啁???first_phase ?? / last_phase / ?臬摰? / ?臬憭望? / 蝡??脣漲
    """
    require_user(authorization, db)

    # ?曉?餈? correlation_id嚗???唬?隞嗆???摨?
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
        # ?輸?cid ????隞塚??暸?鈭辣 + ?思?隞?+ ?臬憭望? + 蝡???        evs = (
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

        # 撌脣????文?
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
    """?桐? correlation_id ???港?隞嗆???嚗??啜??嚗?""
    require_user(authorization, db)

    rows = (
        db.query(M.ReportGenerationEvent)
        .filter(M.ReportGenerationEvent.correlation_id == correlation_id)
        .order_by(M.ReportGenerationEvent.id.asc())
        .all()
    )
    if not rows:
        raise HTTPException(404, f"?曆???correlation_id={correlation_id}")

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
    notify_email: Optional[str] = None  # ?乩??喉???Report.notify_email
    custom_message: Optional[str] = None  # ??嚗閮???

@router.post("/{report_id}/send-email")
def admin_send_report_email(
    report_id: int,
    body: SendEmailIn,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """蝞∠??∪??啜?閬?+ 撖縑???孛?潦?    ??GCS ?勗????撖 notify_email嚗蒂璅? email_sent=1??    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "? admin 甈?")

    rep = db.query(M.Report).filter(M.Report.report_id == report_id).first()
    if not rep:
        raise HTTPException(404, f"?曆??啣??#{report_id}")
    if not rep.pdf_url:
        raise HTTPException(400, "甇文???芯???GCS嚗df_url ?箇征嚗??⊥?撖縑")

    to = (body.notify_email or rep.notify_email or "").strip()
    if not to or "@" not in to:
        raise HTTPException(400, "?嗡辣 email 銝??冽??澆??航炊嚗??典?恣????銝?email")

    # 敺?talent_report_kind ?冽?勗?憿?
    kind = (rep.talent_report_kind or "life_script_full")
    type_label_map = {
        "life_script":  "?犖?行郭???勗?",
        "child":        "?咱?行郭???勗?",
        "parent_child": "閬芸??行郭?勗?",
        "marital":      "憭怠氖?行郭?勗?",
    }
    base = kind.split("_")[0] if "_" in kind else "life_script"
    title = type_label_map.get(kind.split("_")[0] if "_" in kind else "life_script", "?行郭???勗?")
    # ?岫敺?client_summary ??皜祈???    subject_name = ""
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

    # 雿輻瘞訾?銝????嚗?api/v1/public/client/{token}/pdf嚗?
    # 暺??????啁偷蝵莎??踹? GCS token ??????    # ??qr_token 銝??剁?????嚗? fallback ?蝪賜蔡銝甈∪??曉 Email??    from app.core.config import settings
    base = (settings.PUBLIC_BASE_URL or "").rstrip("/")

    if rep.qr_token and base:
        # 瘞訾????嚗???GCS token嚗偶????        email_pdf_url = f"{base}/api/v1/public/client/{rep.qr_token}/pdf"
    else:
        # fallback嚗??啁偷蝵?signed URL嚗? 憭拙??嚗?        from app.services import gcs_uploader
        email_pdf_url = rep.pdf_url
        try:
            fresh = gcs_uploader.generate_fresh_signed_url(rep.pdf_url)
            if fresh:
                email_pdf_url = fresh
                rep.pdf_url = fresh
                db.commit()
        except Exception:
            pass

    from app.services import email_sender
    result = email_sender.send_report_link_email(
        to            = to,
        subject_name  = subject_name or "??,
        report_title  = title,
        pdf_url       = email_pdf_url,
        expires_days  = 0,  # 瘞訾????嚗?憿舐內?? 憭拇???蝷?    )

    if result.get("ok"):
        rep.email_sent = 1
        rep.notify_email = to
        db.commit()
        return {"ok": True, "report_id": report_id, "sent_to": to, "method": result.get("method", "")}
    else:
        raise HTTPException(502, f"撖縑憭望?嚗result.get('error') or result}")


@router.post("/admin/relink-orphan-reports")
def admin_relink_orphan_reports(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """?? 銝?萄?閰行?摮文??勗?嚗ubject_id IS NULL嚗??臬? Subject 銝餅???
    ?撘?撠??伐?靘??嚗?
      1. Report.session_id ??Session.subject_id嚗 Session 撌脤??荔?
      2. Report.session_id ??Session.consultant_name + subject_name ??Subject by name + consultant
      3. 潃?Session.subject_name ??placeholder嚗??葫??蝑????曇府 consultant ??         Session 撱箸??? 簣 7 憭拙???銝?ubject嚗憭??仿?嚗?????
      4. Report.completed_at 簣 24h嚗?撠府?挾??consultant 撱箇??銝 Subject

    摰嚗 UPDATE 銝?歹??曆??啁??勗?蝬剜? subject_id=NULL嚗dmin 隞??????    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "??admin ?臬銵?)

    # 1) ????subject_id=NULL ??Report
    orphans = db.query(M.Report).filter(M.Report.subject_id.is_(None)).all()
    if not orphans:
        return {"ok": True, "scanned": 0, "linked": 0, "still_orphan": 0, "details": []}

    # ??皞? lookup table
    sess_map: dict[int, M.Session] = {}
    sess_ids = {r.session_id for r in orphans if r.session_id}
    if sess_ids:
        for s in db.query(M.Session).filter(M.Session.session_id.in_(list(sess_ids))).all():
            sess_map[s.session_id] = s

    # 憿批? name ??consultant_id
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

        # 蝑 1嚗ession ?芸楛??subject_id
        if sess and sess.subject_id:
            chosen_sid = sess.subject_id
            method = "session.subject_id"

        PLACEHOLDER_NAMES = {"?葫??, "?喳???, "皜祈岫璅∪?", "test", "Test", "TEST", "", None}

        # 蝑 2嚗ession.consultant + Session.subject_name ??Subject嚗??????撠?
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

        # 蝑 3 潃?placeholder 憪? ???具府憿批????銝 Subject???        # ?拍??嚗dmin ?具T$1 皜祈岫???駁??葫?停???雿“??        # 嚗????脣捆?????嗅祕?芣?銝雿?皜祈?憒?敹???嚗?刻??箏?銝鈭箝?        if (chosen_sid is None and sess and sess.consultant_name
                and (not sess.subject_name or sess.subject_name in PLACEHOLDER_NAMES)):
            cons_id = cons_name_to_id.get(sess.consultant_name)
            if cons_id:
                cands = db.query(M.Subject).filter(
                    M.Subject.consultant_id == cons_id
                ).all()
                if len(cands) == 1:
                    chosen_sid = cands[0].subject_id
                    method = "consultant has only 1 subject (placeholder)"

        # 蝑 4嚗ompleted_at 簣 24h ??consultant 撱箇??銝 Subject嚗?敺?畾蛛?雓寞?嚗?        # 嚗??session_id is null + ??completed_at ???岫嚗?????
        if (chosen_sid is None and rep.session_id is None and rep.completed_at and sess is None
                and rep.client_summary):
            try:
                import json as _json
                cs = _json.loads(rep.client_summary)
                guess_name = cs.get("subject_name", "")
                # 銝 PLACEHOLDER ??閰佗?PLACEHOLDER ?湔閬摮文?皜祈岫?勗?嚗??嚗?                PLACEHOLDER_NAMES = {"?葫??, "?喳???, "皜祈岫璅∪?", "test", "Test", "TEST"}
                if guess_name and guess_name not in PLACEHOLDER_NAMES and not guess_name.startswith("?妒 "):
                    cands = db.query(M.Subject).filter(M.Subject.name == guess_name).all()
                    if len(cands) == 1:
                        chosen_sid = cands[0].subject_id
                        method = "client_summary.name (unique)"
            except Exception:
                pass

        if chosen_sid:
            rep.subject_id = chosen_sid
            # ???湔 Session.subject_id 鋆撥???
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


@router.post("/{report_id}/link-session")
def admin_link_session(
    report_id: int,
    body: dict,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """admin ???迨??Report ????唳?摰?Session嚗身摰?session_id嚗?    ??撠?Report.subject_id / subject_name 撠?閰?Session ??皜祈???    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "??admin ?臬銵?)

    rep = db.query(M.Report).filter(M.Report.report_id == report_id).first()
    if not rep:
        raise HTTPException(404, f"?曆??啣??#{report_id}")

    sess_id = body.get("session_id")
    if not isinstance(sess_id, int) or sess_id <= 0:
        raise HTTPException(400, "session_id 敹??舀迤?湔")

    sess = db.query(M.Session).filter(M.Session.session_id == sess_id).first()
    if not sess:
        raise HTTPException(404, f"?曆???Session #{sess_id}")

    # 蝣箄? session 撠?隞?report
    existing = db.query(M.Report).filter(
        M.Report.session_id == sess_id,
        M.Report.report_id != report_id,
    ).first()
    if existing:
        raise HTTPException(
            400,
            f"Session #{sess_id} 撌脫??勗? #{existing.report_id}嚗existing.talent_report_kind}嚗?"
            "隢??芷????????,
        )

    rep.session_id = sess_id
    if sess.subject_id:
        rep.subject_id = sess.subject_id
    db.commit()
    db.refresh(rep)
    return {
        "ok": True,
        "report_id":   report_id,
        "session_id":  sess_id,
        "subject_name": sess.subject_name,
        "subject_id":   sess.subject_id,
    }


@router.post("/{report_id}/manual-link-subject")
def admin_manual_link_subject(
    report_id: int,
    body: dict,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> dict:
    """admin ???蝑?Report ???? subject_id嚗?????嚗?""
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "??admin ?臬銵?)

    rep = db.query(M.Report).filter(M.Report.report_id == report_id).first()
    if not rep:
        raise HTTPException(404, f"?曆??啣??#{report_id}")

    sid = body.get("subject_id")
    if not isinstance(sid, int) or sid <= 0:
        raise HTTPException(400, "subject_id 敹??舀迤?湔")

    subj = db.query(M.Subject).filter(M.Subject.subject_id == sid).first()
    if not subj:
        raise HTTPException(404, f"?曆???Subject #{sid}")

    rep.subject_id = sid
    if rep.session_id:
        sess = db.query(M.Session).filter(M.Session.session_id == rep.session_id).first()
        if sess:
            sess.subject_id = sid
    db.commit()
    return {"ok": True, "report_id": report_id, "linked_to": sid, "subject_name": subj.name}


@router.delete("/sessions/{session_id}/delete-report")
def delete_session_report(
    session_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """蝞∠??∪??剁??芷?? Session ?????GCS PDF嚗?霈?舫??啁???
    - ?芷 Report DB 閮?嚗 pdf_url?tatus 蝑?
    - ?岫?芷 GCS 銝? PDF嚗 GCS ?芾身摰??拐辣銝??剁?銝蔣??DB ?芷嚗?    - 靽? Session ??EegCapture嚗瘜Ｗ?憪????嚗誑靘輸??啁???    """
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "?恣??臬?文??)

    s = db.query(M.Session).filter(M.Session.session_id == session_id).first()
    if not s:
        raise HTTPException(404, f"?曆???Session #{session_id}")

    r = db.query(M.Report).filter(M.Report.session_id == session_id).first()
    if not r:
        raise HTTPException(404, f"Session #{session_id} 瘝?撠????)

    from app.services import gcs_uploader
    gcs_result = {"ok": True, "note": "??pdf_url嚗歲??GCS ?芷"}
    if r.pdf_url:
        gcs_result = gcs_uploader.delete_pdf_object(r.pdf_url)

    deleted_info = {
        "report_id":   r.report_id,
        "session_id":  session_id,
        "subject_name": s.subject_name,
        "pdf_url":     r.pdf_url,
        "gcs":         gcs_result,
    }
    db.delete(r)
    db.commit()

    return {
        "ok": True,
        "deleted": deleted_info,
        "note": "?勗?撌脣?歹?Session 靽???閫貊????,
    }


@router.delete("/{report_id}/delete-test")
def delete_test_report(
    report_id: int,
    force_unpaid: bool = Query(False, description="True = ?喃蝙?瘜Ｚ????芷嚗??閰?session 瘝?撌脖?甈曄???),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """蝞∠??∪??剁??芷?葫閰血??subject_name ?粹?閮剖潛?摮文??勗?嚗?
    摰瑼Ｘ嚗?      - 敹???admin
      - ?身嚗?? subject_name 敹??舫?閮剖潔?銝嚗?皜祈?/ ?喳???/ 皜祈岫璅∪? / ?妒 蝞∠??⊥葫閰?* / 蝛綽?
      - force_unpaid=true嚗雿?subject_name ?箇?撖血????芾? session 瘝?撌脖?甈橘?status='paid'嚗???
        銋?閮勗?扎?潭????行郭鞈?雿隞狡??皜祈岫 session??
    ??API 銝??餃 GCS 銝? PDF嚗?蔣?踹隞??荔?嚗??DB row??    """
    import json as _json

    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "?恣??臬?斗葫閰血??)

    rep = db.query(M.Report).filter(M.Report.report_id == report_id).first()
    if not rep:
        raise HTTPException(404, f"?曆??啣??#{report_id}")

    PLACEHOLDER_NAMES = {"?葫??, "?喳???, "皜祈岫璅∪?", "test", "Test", "TEST"}

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
        or raw_name.startswith("?妒 蝞∠??⊥葫閰?")
    )

    if not is_placeholder:
        if not force_unpaid:
            raise HTTPException(
                400,
                f"?勗? #{report_id} ??皜祈?raw_name}??銝皜祈岫?勗?嚗?甇ａ?甇?API ?芷??
                "?亦Ⅱ撖西??芷嚗?蝣箄??芯?甈橘?嚗??? ?force_unpaid=true ???,
            )
        # force_unpaid=True嚗?澆??冽炎??        # 1. ?亦 session_id嚗迨???嚗??祕憪?撠望?蝯?        if not rep.session_id:
            raise HTTPException(
                400,
                f"?勗? #{report_id}嚗?皜祈?{raw_name}嚗摮文??勗?嚗 session嚗?"
                "?⊥?蝣箄?隞狡???蝳迫?芸??芷????蝣箄?敺????,
            )
        # 2. ??session_id嚗閬府 session ?遙雿?Payment 閮?嚗???status嚗?銝敺???        any_payment = (
            db.query(M.Payment)
            .filter(M.Payment.session_id == rep.session_id)
            .first()
        )
        if any_payment:
            raise HTTPException(
                400,
                f"?勗? #{report_id}嚗?皜祈?{raw_name}嚗? Session #{rep.session_id} "
                f"撌脫?隞狡蝝??Payment #{any_payment.payment_id}嚗tatus={any_payment.status}嚗?蝳迫?芷??,
            )

    # ?芷????    deleted_info = {
        "report_id":     rep.report_id,
        "session_id":    rep.session_id,
        "raw_name":      raw_name,
        "report_kind":   rep.talent_report_kind,
        "completed_at":  rep.completed_at.isoformat() if rep.completed_at else None,
        "force_unpaid":  force_unpaid,
    }
    db.delete(rep)
    db.commit()
    return {"ok": True, "deleted": deleted_info}


@router.delete("/{report_id}")
def admin_delete_report(
    report_id: int,
    confirm: int = Query(0, description="敹?撣??confirm=1 ?????),
    delete_gcs: int = Query(0, description="1=???芷 GCS 銝? PDF 瑼?"),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """蝞∠??∪??剁??芷隞餅??勗???DB 蝝??
    - 敹?撣??confirm=1
    - delete_gcs=1 ?????GCS 銝? PDF嚗?閮剖??DB嚗?    - 銝?憪??賢??桅??塚?隞颱??勗???迎?蝞∠??∟銵?鞎穿?
    """
    from app.services import gcs_uploader as _gcs
    require_admin(authorization, db)
    if confirm != 1:
        raise HTTPException(400, "隢?銝??confirm=1 蝣箄??芷")

    rep = db.query(M.Report).filter(M.Report.report_id == report_id).first()
    if not rep:
        raise HTTPException(404, f"?曆??啣??#{report_id}")

    gcs_result = None
    if delete_gcs and rep.pdf_url:
        try:
            gcs_result = _gcs.delete_pdf_object(rep.pdf_url)
        except Exception as e:
            gcs_result = f"GCS ?芷憭望?嚗e}"

    deleted_info = {
        "report_id":   rep.report_id,
        "session_id":  rep.session_id,
        "pdf_url":     rep.pdf_url,
        "gcs_deleted": gcs_result,
    }
    db.delete(rep)
    db.commit()
    return {"ok": True, "deleted": deleted_info}


@router.post("/restore-from-gcs")
def restore_report_from_gcs(
    body: dict,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """蝞∠??∪??剁?敺?GCS PDF URL ?遣 Report DB 蝝???冽隤文??嚗?
    body 甈?嚗?      - pdf_url        (str, required)  GCS public URL
      - subject_name   (str, optional)  ?葫????      - notify_email   (str, optional)  ? Email
      - report_kind    (str, optional)  ?勗?憿? (life_script / child / ...)
      - completed_at   (str, optional)  ISO ??摮葡嚗?瑼???GCS metadata ?冽葫嚗?    """
    import datetime as _dt

    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "?恣??舫????)

    pdf_url = (body.get("pdf_url") or "").strip()
    if not pdf_url:
        raise HTTPException(400, "pdf_url 銝?箇征")
    if not pdf_url.startswith("https://storage.googleapis.com/"):
        raise HTTPException(400, "pdf_url 敹???GCS public URL")

    # ?脫迫????????URL
    existing = db.query(M.Report).filter(M.Report.pdf_url == pdf_url).first()
    if existing:
        raise HTTPException(
            409,
            f"甇?GCS URL 撌脣????#{existing.report_id}嚗existing.status}嚗?銝?????,
        )

    subject_name = (body.get("subject_name") or "").strip() or None
    notify_email = (body.get("notify_email") or "").strip() or None
    report_kind  = (body.get("report_kind") or "").strip() or None
    completed_at_str = (body.get("completed_at") or "").strip()

    completed_at = None
    if completed_at_str:
        try:
            completed_at = _dt.datetime.fromisoformat(completed_at_str.replace("Z", "+00:00"))
        except Exception:
            pass
    if completed_at is None:
        completed_at = _dt.datetime.utcnow()

    # 撠?subject_name 摮 client_summary 隞乩噶 list API 憿舐內
    import json as _json
    summary_obj: dict = {}
    if subject_name:
        summary_obj["subject_name"] = subject_name
    summary_obj["restored_from_gcs"] = True

    new_rep = M.Report(
        session_id          = None,
        subject_id          = None,
        status              = "completed",
        pdf_url             = pdf_url,
        notify_email        = notify_email,
        email_sent          = 0,
        talent_report_kind  = report_kind,
        client_summary      = _json.dumps(summary_obj, ensure_ascii=False),
        completed_at        = completed_at,
    )
    db.add(new_rep)
    db.commit()
    db.refresh(new_rep)

    return {
        "ok": True,
        "report_id": new_rep.report_id,
        "pdf_url":   pdf_url,
        "subject_name": subject_name,
    }


@router.delete("/events/{correlation_id}")
def delete_report_event(
    correlation_id: str,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """?芷銝蝑?correlation_id ????隞塚?蝞∠??⊥??嚗?""
    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "? admin 甈?")
    n = (
        db.query(M.ReportGenerationEvent)
        .filter(M.ReportGenerationEvent.correlation_id == correlation_id)
        .delete()
    )
    db.commit()
    return {"ok": True, "deleted": n}


# ?? ??銝?誨 PDF ????????????????????????????????????????????????????????????

@router.post("/{report_id}/upload-pdf")
async def upload_replacement_pdf(
    report_id: int,
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """蝞∠??∪??剁?銝 PDF 瑼??誨?勗???GCS ?嚗蒂?湔 DB ??pdf_url??
    ?券???靽桀儔?勗???嚗?蝻箏???撠?嚗?銝? ???砍蝺刻摩 ????甇?API ?銝??
    銵嚗?      - ? PDF 銝??GCS  reports/manual/{report_id}_{timestamp}_{??瑼?}
      - ?湔 Report.pdf_url ?箸 GCS public URL
      - ?湔 Report.status = 'completed'?eport.completed_at = now()
      - ???pdf_url
    """
    import json as _json
    import datetime

    user = require_user(authorization, db)
    if user.role != "admin":
        raise HTTPException(403, "?恣??臭??喳?隞???)

    rep = db.query(M.Report).filter(M.Report.report_id == report_id).first()
    if not rep:
        raise HTTPException(404, f"?曆??啣??#{report_id}")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(400, "銝??獢蝛箇?")
    if len(pdf_bytes) < 1024:
        raise HTTPException(400, "瑼?憭芸?嚗?賭??舀???PDF")

    # ?? 銝??GCS ?????????????????????????????????????????????????????????????
    bucket_name = os.environ.get("GCS_BUCKET_NAME", "").strip()
    sa_json_str = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "").strip()
    if not bucket_name or not sa_json_str:
        missing = "GCS_BUCKET_NAME" if not bucket_name else "GCP_SERVICE_ACCOUNT_JSON"
        raise HTTPException(503, f"GCS 撠閮剖?嚗撩撠?{missing}嚗?)

    try:
        from google.cloud import storage as gcs_lib
        from google.oauth2 import service_account as sa_mod

        creds_info = _json.loads(sa_json_str)
        creds = sa_mod.Credentials.from_service_account_info(creds_info)
        client = gcs_lib.Client(credentials=creds, project=creds_info.get("project_id"))
        bucket = client.bucket(bucket_name)

        # 靽???瑼?雿?銝?report_id ???嚗??蝒?        ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        safe_name = (file.filename or "report.pdf").replace("/", "_")
        pathname = f"reports/manual/{report_id}_{ts}_{safe_name}"

        blob = bucket.blob(pathname)
        blob.upload_from_string(pdf_bytes, content_type="application/pdf")

        # 雿輻 Signed URL嚗? 憭拇???嚗????bucket ???URL ?⊥?摮???
        from datetime import timedelta
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=7),
            method="GET",
            response_disposition=f'attachment; filename="{safe_name}"',
        )
        size_kb = len(pdf_bytes) // 1024

    except Exception as exc:
        raise HTTPException(500, f"GCS 銝憭望?嚗exc}") from exc

    # ?? ?湔 DB ????????????????????????????????????????????????????????????????
    old_url = rep.pdf_url
    rep.pdf_url = signed_url
    rep.status = "completed"
    rep.completed_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(rep)

    return {
        "ok": True,
        "report_id": report_id,
        "pdf_url": signed_url,
        "old_pdf_url": old_url,
        "gcs_pathname": pathname,
        "size_kb": size_kb,
    }
