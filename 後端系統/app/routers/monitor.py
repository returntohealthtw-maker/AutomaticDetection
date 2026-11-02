"""
即時監控模組
- WebSocket：儀表板頁面訂閱，有新資料時推送
- broadcast()：供其他 router 在收到資料時呼叫
- POST /api/admin/recompute-braindna：批次重算所有舊 Session 的 BrainDNA 值
"""
import json
import time
import statistics
from typing import List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Header, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core import models as M
from app.routers.auth import require_admin

router = APIRouter(tags=["監控"])

# 連線中的 WebSocket 客戶端
_clients: List[WebSocket] = []


async def broadcast(event: str, data: dict):
    """向所有儀表板客戶端廣播事件"""
    msg = json.dumps({"event": event, "data": data, "ts": int(time.time() * 1000)},
                     ensure_ascii=False)
    dead = []
    for ws in _clients:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.remove(ws)


@router.websocket("/ws/monitor")
async def websocket_monitor(ws: WebSocket):
    await ws.accept()
    _clients.append(ws)
    try:
        while True:
            await ws.receive_text()   # 保持連線（心跳）
    except WebSocketDisconnect:
        _clients.remove(ws)


# ─── 管理員端點：用八卦 MBTI（唯一權威）重算 DB / Firebase 的 mbti、bagua ───────────

@router.post("/api/admin/resync-mbti", tags=["管理員"])
def resync_mbti(
    dry_run: bool = True,
    firebase: bool = False,
    session_ids: Optional[str] = None,
    sources: str = "raw_arrays",
    min_rows: int = 30,
    authorization: Optional[str] = Header(None),
    db: DBSession = Depends(get_db),
):
    """
    只重算並更新 sessions.mbti / sessions.bagua（不動腦波資料、不生成報告）。

    - dry_run=true（預設）：只回傳 before/after，不寫入
    - firebase=true：同時 PATCH Firebase sessions/{firebase_session_id} 的 mbti、bagua
    - session_ids：以逗號分隔，只處理指定 session；不給則處理全部有腦波資料的 session
    來源與報告 / 上傳流程相同：compute_bagua_mbti(raw_arrays_json → captures → 平均)
    - sources：只接受哪些輸入來源（預設只收 raw_arrays；"avg" 是 0-100 單點平均，
      曾造成大量 INTP/ESTP 擠壓，不應拿來覆蓋 DB）。可用逗號指定 raw_arrays,captures
    - min_rows：來源為 captures 時，至少要有幾筆逐秒資料才接受
    """
    require_admin(authorization, db)
    from app.services.algorithms import compute_averages, compute_bagua_mbti

    wanted = None
    if session_ids:
        wanted = {int(x) for x in session_ids.split(",") if x.strip().isdigit()}

    q = db.query(M.Session).order_by(M.Session.session_id)
    if wanted:
        q = q.filter(M.Session.session_id.in_(wanted))
    sessions = q.all()

    allowed_sources = {x.strip() for x in sources.split(",") if x.strip()}
    changed, same, skipped = [], 0, []
    fb_ok, fb_fail = 0, 0
    fb_client = None
    fb_headers = {}
    if firebase and not dry_run:
        import httpx as _httpx
        from app.services import firebase_sync as _fbs
        fb_headers = _fbs._get_auth_headers()
        fb_client = _httpx.Client(timeout=20.0)

    for sess in sessions:
        sid = sess.session_id
        try:
            caps = db.query(M.EegCapture).filter(M.EegCapture.session_id == sid)\
                     .order_by(M.EegCapture.seq_num).all()
            if not caps:
                skipped.append({"session_id": sid, "reason": "no captures"})
                continue
            fields = ["good_signal", "attention", "meditation", "delta", "theta", "low_alpha",
                      "high_alpha", "low_beta", "high_beta", "low_gamma", "high_gamma"]
            det = [{k: getattr(c, k) for k in fields} for c in caps if c.is_baseline == 0] or \
                  [{k: getattr(c, k) for k in fields} for c in caps]
            avg = compute_averages(det)
            raw = json.loads(sess.raw_arrays_json) if sess.raw_arrays_json else None
            is_child = (sess.report_type or "").lower().startswith("child")
            bm = compute_bagua_mbti(avg, det, raw, is_child)
            if not bm or not bm.get("mbti_type"):
                skipped.append({"session_id": sid, "reason": "no mbti result"})
                continue
            new_m, new_b = bm.get("mbti_type"), bm.get("bagua")
            _src = bm.get("source")
            _n_rows = len([c for c in caps if c.is_baseline == 0])
            if _src not in allowed_sources or (_src == "captures" and _n_rows < min_rows):
                skipped.append({"session_id": sid, "reason": f"source={_src} rows={_n_rows} not accepted"})
                continue
            if sess.mbti == new_m and sess.bagua == new_b:
                same += 1
                continue
            changed.append({"session_id": sid, "subject": sess.subject_name,
                            "old_mbti": sess.mbti, "new_mbti": new_m,
                            "old_bagua": sess.bagua, "new_bagua": new_b,
                            "source": bm.get("source")})
            if not dry_run:
                sess.mbti, sess.bagua = new_m, new_b
                if fb_client is not None and sess.firebase_session_id and fb_headers:
                    try:
                        from app.services import firebase_sync as _fbs
                        r = fb_client.patch(f"{_fbs.FIREBASE_API_BASE}/sessions/{sess.firebase_session_id}",
                                            headers=fb_headers, json={"mbti": new_m, "bagua": new_b})
                        if r.status_code in (200, 204):
                            fb_ok += 1
                        else:
                            fb_fail += 1
                            changed[-1]["firebase_error"] = f"{r.status_code} {r.text[:80]}"
                    except Exception as _fe:
                        fb_fail += 1
                        changed[-1]["firebase_error"] = str(_fe)[:80]
        except Exception as e:
            skipped.append({"session_id": sid, "reason": f"error: {str(e)[:120]}"})

    if not dry_run:
        db.commit()
    if fb_client is not None:
        fb_client.close()
    return {"ok": True, "dry_run": dry_run, "total": len(sessions), "unchanged": same,
            "changed": len(changed), "skipped": len(skipped),
            "firebase_ok": fb_ok, "firebase_fail": fb_fail,
            "changes": changed, "skipped_detail": skipped}


# ─── 管理員端點：批次重算舊 Session 的 BrainDNA 值 ────────────────────────────

@router.post("/api/admin/recompute-braindna", tags=["管理員"])
def recompute_braindna(
    force: bool = False,
    authorization: Optional[str] = Header(None),
    db: DBSession = Depends(get_db),
):
    """
    批次重算所有舊 Session 的 BrainDNA 計算結果。

    - 只處理有 raw_arrays_json 且 r_lalpha 筆數 >= 10 的 Session
    - force=false（預設）：跳過已有 mind_stress 的 Session
    - force=true：強制重算所有有效 Session（更新已有的值）

    回傳：{ total, updated, skipped_no_data, skipped_already_done, failed }
    """
    require_admin(authorization, db)

    from app.services.braindna_algorithms import compute_all as _compute_all
    from app.services.braindna_algorithms import _select_best_window, MIN_DELTA_QUALITY as _MDQ
    from app.algorithms.report import generate_quick_mbti

    # 查所有有 raw_arrays_json 或 firebase_session_id 的 Session
    query = db.query(M.Session).filter(
        (M.Session.raw_arrays_json.isnot(None)) |
        (M.Session.firebase_session_id.isnot(None))
    )
    sessions = query.order_by(M.Session.session_id).all()

    stats = {
        "total": len(sessions),
        "updated": 0,
        "skipped_no_data": 0,     # raw_arrays 有值但 r_lalpha 資料不足
        "skipped_already_done": 0, # 已有 mind_stress 且 force=False
        "failed": 0,
        "details": [],
    }

    for sess in sessions:
        sid = sess.session_id
        try:
            # 跳過已算過的（除非 force）
            if not force and sess.mind_stress is not None:
                stats["skipped_already_done"] += 1
                continue

            _is_child = (getattr(sess, "report_type", None) or "").lower() in ("child", "child_report")
            raw = None
            _raw_source = "none"

            # 來源 1：Firebase 180 筆特徵（最高優先）
            if sess.firebase_session_id:
                try:
                    import asyncio as _aio
                    from app.services.firebase_sync import fetch_eeg_features, firebase_features_to_raw_arrays
                    _fb_features = _aio.run(fetch_eeg_features(sess.firebase_session_id))
                    if _fb_features and len(_fb_features) >= 10:
                        raw = firebase_features_to_raw_arrays(_fb_features)
                        _raw_source = "firebase"
                except Exception:
                    pass  # Firebase 失敗則繼續 fallback

            # 來源 2：PostgreSQL raw_arrays_json
            if raw is None and sess.raw_arrays_json:
                raw = json.loads(sess.raw_arrays_json)
                _raw_source = "pg_raw"

            if raw is None:
                stats["skipped_no_data"] += 1
                stats["details"].append({"session_id": sid, "status": "skip", "reason": "no raw data (no firebase_session_id and no raw_arrays_json)"})
                continue

            n_la = len(raw.get("r_lalpha") or [])

            # 需要至少 10 筆 r_lalpha 才能用 BrainDNA 算法
            if n_la < 10:
                stats["skipped_no_data"] += 1
                stats["details"].append({"session_id": sid, "status": "skip", "reason": f"r_lalpha only {n_la} samples (source={_raw_source})"})
                continue

            # 重算 BrainDNA 核心指標（兒童報告使用兒童閾值）
            result = _compute_all(raw, is_child=_is_child)
            if not result.get("valid"):
                stats["failed"] += 1
                stats["details"].append({"session_id": sid, "status": "failed", "reason": "compute_all returned invalid"})
                continue

            sess.mind_stress   = result.get("stress")
            sess.mind_balance  = result.get("balance")
            sess.mind_energy   = result.get("energy")
            sess.mind_color    = result.get("color")
            sess.overall_score = result.get("overall_score")
            sess.bdna_mode     = f"bdna_{result.get('input_scale', 'unknown')}"

            # 同步更新 EegCapture(seq_num=0) 的頻段值（帶入修正後的 BrainDNA 算法結果）
            cap = db.query(M.EegCapture).filter(
                M.EegCapture.session_id == sid,
                M.EegCapture.seq_num == 0,
            ).first()
            if cap and result.get("bands"):
                b = result["bands"]
                cap.delta      = b.get("delta",      cap.delta)
                cap.theta      = b.get("theta",      cap.theta)
                cap.low_alpha  = b.get("low_alpha",  cap.low_alpha)
                cap.high_alpha = b.get("high_alpha", cap.high_alpha)
                cap.low_beta   = b.get("low_beta",   cap.low_beta)
                cap.high_beta  = b.get("high_beta",  cap.high_beta)
                cap.low_gamma  = b.get("low_gamma",  cap.low_gamma)
                cap.high_gamma = b.get("high_gamma", cap.high_gamma)

            # 重算 MBTI / 八卦：唯一權威 = compute_bagua_mbti（與上傳 / 報告 / Firebase 同源）。
            # 舊版這裡用 generate_quick_mbti（另一套算法），force=true 會把 DB 的 mbti 蓋回舊算法。
            try:
                from app.services.algorithms import compute_bagua_mbti as _bagua_mbti
                _bm = _bagua_mbti(raw_arrays=raw, is_child=_is_child)
                if not _bm:
                    raise ValueError("bagua mbti empty")
                sess.mbti  = _bm.get("mbti_type")
                sess.bagua = _bm.get("bagua")
            except Exception:
                pass  # MBTI 失敗不影響主要指標（不回退舊算法，避免把 DB 蓋回另一套 MBTI）

            stats["updated"] += 1
            stats["details"].append({
                "session_id": sid,
                "status": "ok",
                "samples": n_la,
                "stress": sess.mind_stress,
                "balance": sess.mind_balance,
                "energy": sess.mind_energy,
                "color": sess.mind_color,
                "mbti": sess.mbti,
                "bands": result.get("bands"),
            })

        except Exception as e:
            stats["failed"] += 1
            stats["details"].append({"session_id": sid, "status": "error", "reason": str(e)})

    db.commit()

    # 摘要（不含 details 保持回應簡潔）
    return {
        "ok": True,
        "summary": {
            "total_sessions_with_raw_data": stats["total"],
            "updated": stats["updated"],
            "skipped_no_data": stats["skipped_no_data"],
            "skipped_already_done": stats["skipped_already_done"],
            "failed": stats["failed"],
        },
        "details": stats["details"],
    }


@router.get("/api/admin/raw-debug/{session_id}", tags=["管理員"])
def raw_debug(
    session_id: int,
    authorization: Optional[str] = Header(None),
    db: DBSession = Depends(get_db),
):
    """診斷特定 session 的 raw_arrays 原始值範圍，用於確認 ThinkGear 資料尺度"""
    require_admin(authorization, db)
    sess = db.query(M.Session).filter(M.Session.session_id == session_id).first()
    if not sess or not sess.raw_arrays_json:
        return {"error": "no raw data"}
    raw = json.loads(sess.raw_arrays_json)

    from app.services.braindna_algorithms import _select_best_window, RAW_KEYS, CAP
    stats_all = {}
    for k in RAW_KEYS:
        arr = [v for v in (raw.get(k) or []) if v and v > 0]
        if arr:
            stats_all[k] = {
                "n": len(arr),
                "min": round(min(arr)),
                "max": round(max(arr)),
                "mean": round(sum(arr)/len(arr)),
                "cap": CAP[k],
                "pct_at_cap": round(sum(1 for v in arr if v >= CAP[k]) / len(arr) * 100, 1),
            }

    # best window 統計
    best = _select_best_window(raw)
    best_stats = {}
    for k in RAW_KEYS:
        arr = [v for v in (best.get(k) or []) if v and v > 0]
        if arr:
            uncapped_totals = []
            for i in range(len((best.get(RAW_KEYS[0]) or []))):
                t = sum((best.get(kk) or [0]*100)[i] for kk in RAW_KEYS if i < len(best.get(kk) or []))
                if t > 0:
                    uncapped_totals.append(t)
            avg_total = round(sum(uncapped_totals)/len(uncapped_totals)) if uncapped_totals else 0
            best_stats[k] = {
                "mean": round(sum(arr)/len(arr)),
                "max": round(max(arr)),
                "cap": CAP[k],
                "avg_uncapped_total": avg_total,
                "avg_proportion_pct": round(min(sum(arr)/len(arr), CAP[k]) / avg_total * 100, 2) if avg_total > 0 else 0,
            }

    return {
        "session_id": session_id,
        "all_180s_raw_stats": stats_all,
        "best_30s_window_stats": best_stats,
    }


@router.get("/api/admin/raw-export/{session_id}", tags=["管理員"])
def raw_export(
    session_id: int,
    authorization: Optional[str] = Header(None),
    db: DBSession = Depends(get_db),
):
    """回傳 raw_arrays_json 原始內容，供本地深度分析用"""
    require_admin(authorization, db)
    sess = db.query(M.Session).filter(M.Session.session_id == session_id).first()
    if not sess or not sess.raw_arrays_json:
        return {"error": "no raw data"}
    raw = json.loads(sess.raw_arrays_json)
    return {"session_id": session_id, "raw_arrays": raw}


@router.get("/api/admin/compare-windows/{session_id}", tags=["管理員"])
def compare_windows(
    session_id: int,
    authorization: Optional[str] = Header(None),
    db: DBSession = Depends(get_db),
):
    """
    比較同一 Session 在不同視窗長度下的 BrainDNA 計算結果。
    回傳：
      window_30s  — 目前方式（選最佳 30 秒視窗）
      window_full — 使用全部資料（不做視窗選取，170-180 秒全算）
    """
    require_admin(authorization, db)
    sess = db.query(M.Session).filter(M.Session.session_id == session_id).first()
    if not sess or not sess.raw_arrays_json:
        return {"error": "no raw data"}

    raw = json.loads(sess.raw_arrays_json)
    n_samples = len(raw.get("r_lalpha") or [])

    from app.services.braindna_algorithms import (
        calc_band_proportions, _select_best_window, WINDOW_SIZE
    )

    # ── 模式 A：目前方式（選最佳 30 秒視窗）─────────────────────────────────
    best_win = _select_best_window(raw)
    best_win_start_sec = None
    # 找出 best window 對應的起始秒數
    la_full = raw.get("r_lalpha") or []
    la_best = best_win.get("r_lalpha") or []
    if la_full and la_best:
        for i in range(len(la_full)):
            if la_full[i:i+len(la_best)] == la_best:
                best_win_start_sec = i
                break

    result_30s = calc_band_proportions(best_win)

    # ── 模式 B：全部資料（不做視窗選取）────────────────────────────────────
    # 直接對完整 raw_arrays 計算（略過視窗選取步驟）
    import math as _math
    from app.services.braindna_algorithms import (
        RAW_KEYS, CAP, _clamp, _proportion_range, _PROP_RANGE
    )

    prop_sum = {k: 0.0 for k in RAW_KEYS}
    valid = 0
    for i in range(n_samples):
        raw_row = {
            k: float((raw.get(k) or [0])[i] if i < len(raw.get(k) or []) else 0)
            for k in RAW_KEYS
        }
        uncapped_total = sum(raw_row.values())
        if uncapped_total <= 0:
            continue
        for k in RAW_KEYS:
            prop_sum[k] += _clamp(raw_row[k], CAP[k]) / uncapped_total
        valid += 1

    result_full = None
    if valid > 0:
        result_full = {}
        name_map = {
            "r_delta":  "delta",      "r_theta":   "theta",
            "r_lalpha": "low_alpha",  "r_halpha":  "high_alpha",
            "r_lbeta":  "low_beta",   "r_hbeta":   "high_beta",
            "r_lgamma": "low_gamma",  "r_hgamma":  "high_gamma",
        }
        for k, name in name_map.items():
            raw_prop = prop_sum[k] / valid
            l1, l2 = _PROP_RANGE[k]
            result_full[name] = round(_proportion_range(raw_prop, l1, l2) * 100)

    return {
        "session_id":         session_id,
        "total_samples":      n_samples,
        "best_window_start":  best_win_start_sec,
        "best_window_length": len(la_best),
        "window_30s":         result_30s,
        "window_full":        result_full,
        "diff": {
            k: (result_full.get(k, 0) - result_30s.get(k, 0))
            for k in (result_30s or {})
        } if result_30s and result_full else None,
    }


@router.get("/api/admin/raw-arrays-health", tags=["管理員"])
def raw_arrays_health(
    authorization: Optional[str] = Header(None),
    db: DBSession = Depends(get_db),
):
    """
    查詢所有 Session 的 raw_arrays 健康狀況：
    - no_raw:       沒有 raw_arrays_json（舊版本或檢測失敗）
    - too_short:    r_lalpha 筆數 < 10（無法使用 BrainDNA）
    - partial:      r_lalpha 筆數 10–89（< 90 秒資料）
    - full:         r_lalpha 筆數 >= 90（至少 1 個最佳窗口）
    - braindna_ok:  已有 mind_stress（已計算過 BrainDNA）
    """
    require_admin(authorization, db)

    all_sess = db.query(
        M.Session.session_id,
        M.Session.raw_arrays_json,
        M.Session.mind_stress,
    ).order_by(M.Session.session_id).all()

    result = {"no_raw": [], "too_short": [], "partial": [], "full": [], "braindna_ok": []}

    for sid, raw_json, mind_stress in all_sess:
        if not raw_json:
            result["no_raw"].append(sid)
            continue
        try:
            raw = json.loads(raw_json)
            n = len(raw.get("r_lalpha") or [])
        except Exception:
            result["no_raw"].append(sid)
            continue

        if n < 10:
            result["too_short"].append({"session_id": sid, "samples": n})
        elif n < 90:
            result["partial"].append({"session_id": sid, "samples": n})
        else:
            result["full"].append({"session_id": sid, "samples": n})

        if mind_stress is not None:
            result["braindna_ok"].append(sid)

    return {
        "counts": {k: len(v) for k, v in result.items()},
        "details": result,
    }


# ── 管理員標記 Session 需要重測 ──────────────────────────────────────────────
from pydantic import BaseModel as _PydBaseModel

class MarkRetestIn(_PydBaseModel):
    reason: str = ""

@router.post("/api/v1/monitor/sessions/{session_id}/mark-retest")
def mark_session_needs_retest(
    session_id: int,
    body: MarkRetestIn,
    authorization: Optional[str] = Header(None),
    db: DBSession = Depends(get_db),
):
    """管理員將某 session 標記為「需要重測」，使其出現在付款重測名單中。"""
    require_admin(authorization, db)
    sess = db.query(M.Session).filter(M.Session.session_id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session {session_id} 不存在")
    sess.needs_retest  = True
    sess.retest_reason = body.reason[:200] if body.reason else ""
    db.commit()
    return {"ok": True, "session_id": session_id, "message": "已標記需重測，將出現在付款重測名單"}


@router.delete("/api/v1/monitor/sessions/{session_id}/mark-retest")
def unmark_session_needs_retest(
    session_id: int,
    authorization: Optional[str] = Header(None),
    db: DBSession = Depends(get_db),
):
    """取消重測標記。"""
    require_admin(authorization, db)
    sess = db.query(M.Session).filter(M.Session.session_id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session {session_id} 不存在")
    sess.needs_retest  = False
    sess.retest_reason = None
    db.commit()
    return {"ok": True, "session_id": session_id, "message": "已取消重測標記"}


class RestorePdfIn(_PydBaseModel):
    pdf_url: str

@router.post("/api/v1/monitor/sessions/{session_id}/restore-pdf-url")
def restore_report_pdf_url(
    session_id: int,
    body: RestorePdfIn,
    authorization: Optional[str] = Header(None),
    db: DBSession = Depends(get_db),
):
    """[Admin] 將指定 session 的報告 pdf_url 還原（用於 headless job 中斷後從 GCS 找回舊 URL）"""
    require_admin(authorization, db)
    report = db.query(M.Report).filter(M.Report.session_id == session_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="找不到此 session 的報告記錄")
    report.pdf_url = body.pdf_url
    report.status  = "completed"
    db.commit()
    return {"ok": True, "session_id": session_id, "pdf_url": body.pdf_url}
