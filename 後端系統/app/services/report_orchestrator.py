"""
報告 orchestrator：呼叫外部 4 個已部署的報告生成系統

每家 API 介接策略不同：
  marital      ✅ 完整 REST：POST /api/generate { husband, wife } → 回 PDF binary
  life_script  ⚠️ 沒 REST API（純 UI），改回傳 deep-link 給前端開新視窗
  child        ⚠️ 同上（Next.js UI；目前只有 /api/diagnose）
  parent_child ⚠️ image upload UI；不能直接 POST 數值

對於沒 REST 的，回傳：
  { ok: True, mode: "redirect", redirect_url: "https://...", note: "需在外部 UI 完成操作" }

對於 marital，會立即拿到 PDF bytes → 我們存到 reports/{id}.pdf 後回 result_url
"""
from __future__ import annotations
import os
import time
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# 報告 PDF 存放位置
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 各家公開預設網址（環境變數沒設時的 fallback）
# life_script：現在改用本機 Railway 內建 /report-app/（不再依賴 Vercel）
# 若環境變數 REPORT_URL_LIFE_SCRIPT 有設定則以環境變數為準（可保留 Vercel 作備援）
DEFAULT_URLS = {
    "life_script":  "__local__",   # 代表使用本機 /report-app/
    "child":        "__local__",   # 代表使用本機 /child-report-app/（已移植，不再走 Vercel）
    "parent_child": "__local__",   # 代表使用本機 /parent-child/（已移植，不再走 Railway）
    "marital":      "https://web-production-2c7d43.up.railway.app",
}

# Railway fallback URLs（若環境變數強制外部時使用）
FALLBACK_URLS = {
    "parent_child": "https://web-production-f1aec.up.railway.app",
}

# 本機 report-app 的路徑前綴（headless 開瀏覽器時改用 localhost）
LOCAL_REPORT_APP_PATH       = "/report-app/"
LOCAL_CHILD_REPORT_APP_PATH = "/child-report-app/"

# 每家系統的 API 模式
SYSTEM_MODES = {
    "life_script":  "vite_prefill",      # 開連結 + URL 帶 query string 讓 React 自動填表執行
    "child":        "vite_prefill",
    "parent_child": "parent_child_rest", # HomeAnalysisReport 自帶 /generate
    "marital":      "marital_rest",      # 真實 REST API
}


def _url_for(report_type: str) -> Optional[str]:
    mp = {
        "life_script":   settings.REPORT_URL_LIFE_SCRIPT,
        "child":         settings.REPORT_URL_CHILD,
        "parent_child":  settings.REPORT_URL_PARENT_CHILD,
        "marital":       settings.REPORT_URL_MARITAL,
    }
    u = (mp.get(report_type) or "").strip().rstrip("/")
    if u:
        return u
    return DEFAULT_URLS.get(report_type)


def _local_base_url() -> str:
    """本機 Railway 的根 URL（headless browser 用）"""
    port = int(os.environ.get("PORT", 8000))
    return f"http://127.0.0.1:{port}"


def _is_local(report_type: str) -> bool:
    """是否走本機內建服務（優先用本機，穩定且不依賴外部 Vercel / Railway）

    支援 life_script（/report-app/）、child（/child-report-app/）、
    parent_child（/parent-child/）。

    判斷順序：
    1. 環境變數 USE_EXTERNAL_LIFE_SCRIPT=1   → life_script 強制走外部
    2. 環境變數 USE_EXTERNAL_CHILD=1         → child 強制走外部
    3. 環境變數 USE_EXTERNAL_PARENT_CHILD=1  → parent_child 強制走外部
    4. 本機對應目錄 / 路由存在 → 走本機
    5. 否則走外部
    """
    if report_type not in ("life_script", "child", "parent_child"):
        return False

    # 強制外部 flag
    if report_type == "life_script" and os.environ.get("USE_EXTERNAL_LIFE_SCRIPT", "").strip() == "1":
        return False
    if report_type == "child" and os.environ.get("USE_EXTERNAL_CHILD", "").strip() == "1":
        return False
    if report_type == "parent_child" and os.environ.get("USE_EXTERNAL_PARENT_CHILD", "").strip() == "1":
        return False

    if report_type == "parent_child":
        # 親子報告已內建於主程式，只要 parent_child_data 目錄存在即視為本機可用
        pc_candidates = [
            "/app/parent_child_data",            # Docker / Railway
            "parent_child_data",                 # 本地開發（CWD = 後端系統/）
        ]
        for c in pc_candidates:
            if os.path.isdir(c):
                return True
        return True  # router 已 include，預設走本機

    # 對應靜態目錄名稱（life_script / child）
    dir_name = "report-app" if report_type == "life_script" else "child-report-app"
    local_index_candidates = [
        f"/app/static-app/{dir_name}/index.html",   # Docker / Railway
        f"static-app/{dir_name}/index.html",          # 本地開發
    ]
    for c in local_index_candidates:
        if os.path.isfile(c):
            return True
    return False


def is_external_available(report_type: str) -> bool:
    """是否走外部 Vercel 系統生成報告。

    全部走外部 — Vercel React App 已內建 ?auto=1 完整自動模式。
    headless Chromium 在主後端背景執行，使用 DB 輪詢取代頁面文字偵測，
    確保 /reports/record callback 到達即視為完成（不再靠 done_keywords）。
    """
    return _url_for(report_type) is not None


def _save_pdf(pdf_bytes: bytes, prefix: str = "marital") -> tuple[str, str]:
    """存 PDF 到本地 reports/ 並回 (job_id, file_path)"""
    job_id = f"{prefix}-{uuid.uuid4().hex[:12]}"
    path = REPORTS_DIR / f"{job_id}.pdf"
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return job_id, str(path)


def _public_pdf_url(job_id: str) -> str:
    base = settings.PUBLIC_BASE_URL or os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    if base and not base.startswith("http"):
        base = f"https://{base}"
    base = base.rstrip("/")
    return f"{base}/api/v1/report-gen/pdf/{job_id}" if base else f"/api/v1/report-gen/pdf/{job_id}"


# ──────────────────────────────────────────────────────────────────────
# 各家轉換器：把 AutomaticDetection 的腦波 stats 轉成該系統需要的格式
# ──────────────────────────────────────────────────────────────────────
def _bw_to_seven_indices(bw: Dict[str, Any]) -> Dict[str, float]:
    """
    把採集到的腦波資料轉成「七大腦波指標」(0-100)：
       high_alpha, low_alpha, theta, high_beta, low_beta, high_gamma, low_gamma

    只使用真實量測值：優先讀 bands_7，其次讀 bands_avg 的個別子頻帶欄位。
    若找不到實際子頻帶值，一律使用合併帶數值（不乘以估算係數）。
    絕不使用 ×0.9/×1.1 等估算公式，以確保數值與管理後台一致。
    """
    def cap(v): return max(0, min(100, int(v)))
    def _g(d, k, fallback=None):
        v = d.get(k)
        return fallback if v is None else v
    b7 = (bw or {}).get("bands_7") or {}
    ba = (bw or {}).get("bands_avg") or {}
    alpha  = _g(ba, "alpha",  50)
    theta  = _g(ba, "theta",  50)
    beta   = _g(ba, "beta",   50)
    gamma  = _g(ba, "gamma",  50)

    # 讀取實際子頻帶：bands_7 優先，再查 bands_avg 兩種命名，找不到就用合併帶原值（不估算）
    def _sub(key_b7, key1, key2, base):
        v = (_g(b7, key_b7)
             or (_g(ba, key1) if _g(ba, key1) is not None else _g(ba, key2)))
        return cap(v) if v is not None else cap(base)

    return {
        "high_alpha": _sub("alpha_high", "high_alpha", "alpha_high", alpha),
        "low_alpha":  _sub("alpha_low",  "low_alpha",  "alpha_low",  alpha),
        "theta":      cap(theta),
        "high_beta":  _sub("beta_high",  "high_beta",  "beta_high",  beta),
        "low_beta":   _sub("beta_low",   "low_beta",   "beta_low",   beta),
        "high_gamma": _sub("gamma_high", "high_gamma", "gamma_high", gamma),
        "low_gamma":  _sub("gamma_low",  "low_gamma",  "gamma_low",  gamma),
    }


# ──────────────────────────────────────────────────────────────────────
# 模式 1：marital_rest（真實 REST，回 PDF）
# ──────────────────────────────────────────────────────────────────────
def _call_marital(
    base: str,
    husband: Dict[str, Any],
    wife:    Dict[str, Any],
    meta:    Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """夫妻 API：POST /api/generate → PDF binary"""
    body = {
        "report_id":       (meta or {}).get("report_id",  f"AD-{int(time.time())}"),
        "test_date":       (meta or {}).get("test_date",  time.strftime("%Y-%m-%d")),
        "marriage_years":  int((meta or {}).get("marriage_years", 0)),
        "has_children":    bool((meta or {}).get("has_children", False)),
        "children_info":   (meta or {}).get("children_info", ""),
        "notes":           (meta or {}).get("notes", ""),
        "husband": {
            "name":      husband.get("name", "先生"),
            "age":       int(husband.get("age", 0) or 0),
            "brainwave": husband.get("brainwave") or _bw_to_seven_indices(husband.get("bw", {})),
        },
        "wife": {
            "name":      wife.get("name", "太太"),
            "age":       int(wife.get("age", 0) or 0),
            "brainwave": wife.get("brainwave") or _bw_to_seven_indices(wife.get("bw", {})),
        },
    }
    url = f"{base}/api/generate"
    try:
        with httpx.Client(timeout=settings.REPORT_REQUEST_TIMEOUT_SEC) as cli:
            r = cli.post(url, json=body)
        if r.status_code >= 400:
            return {"ok": False, "mode": "marital_rest", "error": f"HTTP {r.status_code}: {r.text[:200]}"}
        # 預期 200 + content-type: application/pdf
        ctype = r.headers.get("content-type", "")
        if "pdf" in ctype.lower() or r.content[:4] == b"%PDF":
            job_id, path = _save_pdf(r.content, prefix="marital")
            return {
                "ok":         True,
                "mode":       "marital_rest",
                "external_url": base,
                "result_url": _public_pdf_url(job_id),
                "job_id":     job_id,
                "file_size":  len(r.content),
                "file_path":  path,
            }
        # 萬一回 JSON
        try:
            data = r.json()
            return {"ok": True, "mode": "marital_rest", "external_url": base, "raw": data,
                    "result_url": data.get("result_url"), "job_id": data.get("job_id")}
        except Exception:
            return {"ok": False, "mode": "marital_rest",
                    "error": f"非預期回應 content-type={ctype}, head={r.content[:60]!r}"}
    except httpx.TimeoutException:
        return {"ok": False, "mode": "marital_rest", "error": "外部 marital 系統逾時"}
    except Exception as e:
        return {"ok": False, "mode": "marital_rest", "error": f"{type(e).__name__}: {e}"}


# ──────────────────────────────────────────────────────────────────────
# 模式 2：parent_child_rest（HomeAnalysisReport — 自帶 /generate）
# ──────────────────────────────────────────────────────────────────────
def _call_parent_child(
    base:            str,
    family_name:     str,
    members:         List[Dict[str, Any]],
    image_mode:      str = "none",   # none / illustrated
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    members format (HomeAnalysisReport schema):
      [{ "role": "dad"|"mom"|"child1"|"child2",
         "role_zh": "爸爸"|"媽媽"|"孩子1"|"孩子2",
         "name": "王俊宏",
         "present": True,
         "data": {
            "concentration_pct": 87,
            "relaxation_pct":    60,
            "metrics": { "Delta": 28, "Theta": 66, "High α": 56, "Low α": 49,
                         "High β": 95, "Low β":100, "High γ": 50, "Low γ": 50 }
         }}, ...]
    """
    body = {
        "family_name":       family_name,
        "members":           members,
        "image_mode":        image_mode,
        "selected_sections": selected_sections,
    }
    try:
        with httpx.Client(timeout=60.0) as cli:
            r = cli.post(f"{base}/generate", json=body)
        if r.status_code >= 400:
            return {"ok": False, "mode": "parent_child_rest",
                    "error": f"HTTP {r.status_code}: {r.text[:200]}"}
        data = r.json()
        job_id = data.get("job_id")
        if not job_id:
            return {"ok": False, "mode": "parent_child_rest", "error": f"無 job_id: {data}"}
        return {
            "ok":          True,
            "mode":        "parent_child_rest",
            "external_url": base,
            "job_id":      job_id,
            "status_url":  f"{base}/status/{job_id}",
            "stream_url":  f"{base}/stream/{job_id}",
            "result_url":  f"{base}/report/{job_id}",
        }
    except httpx.TimeoutException:
        return {"ok": False, "mode": "parent_child_rest", "error": "親子系統逾時"}
    except Exception as e:
        return {"ok": False, "mode": "parent_child_rest", "error": f"{type(e).__name__}: {e}"}


def _bw_to_metrics(bw: Dict[str, Any]) -> Dict[str, int]:
    """把 AutomaticDetection 的 bands_avg 轉成 HomeAnalysisReport metrics 結構"""
    def cap(v): return max(0, min(100, int(v)))
    def _g(d, k, fallback=50):
        v = d.get(k)
        return fallback if v is None else v
    def _sub(key1, key2, base):
        """優先讀真實 sub-band；找不到就用合併帶原值，絕不估算"""
        v = ba.get(key1) if ba.get(key1) is not None else ba.get(key2)
        return float(v) if v is not None else float(base)
    ba = (bw or {}).get("bands_avg") or {}
    delta = _g(ba, "delta")
    theta = _g(ba, "theta")
    alpha = _g(ba, "alpha")
    beta  = _g(ba, "beta")
    gamma = _g(ba, "gamma")
    return {
        "Delta":  cap(delta),
        "Theta":  cap(theta),
        "High α": cap(_sub("high_alpha", "alpha_high", alpha)),
        "Low α":  cap(_sub("low_alpha",  "alpha_low",  alpha)),
        "High β": cap(_sub("high_beta",  "beta_high",  beta)),
        "Low β":  cap(_sub("low_beta",   "beta_low",   beta)),
        "High γ": cap(_sub("high_gamma", "gamma_high", gamma)),
        "Low γ":  cap(_sub("low_gamma",  "gamma_low",  gamma)),
    }


# ──────────────────────────────────────────────────────────────────────
# 模式 3：vite_prefill（成人/兒童 — 帶 query string 讓 React 自動執行）
# ──────────────────────────────────────────────────────────────────────
def _call_vite_prefill(
    base:                 str,
    subject_name:         str,
    subject_email:        str,
    brainwave_data:       Optional[Dict[str, Any]],
    variant:              str = "full",
    session_id:           Optional[int] = None,
    api_base:             str = "",
    report_type:          str = "life_script",
    chapters_to_generate: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    在主後端用 Playwright Chromium 在背景打開 Vercel React App，
    讓 Vercel App 內建的 ?auto=1 流程跑完：
      1. URL 自動填表
      2. Gemini 生成全部章節
      3. jsPDF 渲染（保留你的原設計）
      4. 上傳 GCS
      5. /api/sendEmail 寄信
      6. POST /api/v1/reports/record 回呼主後端
    使用者完全看不到 Vercel UI，也可隨時關閉 APP。

    Fallback：若 Playwright 不可用（例如 Dockerfile 還沒加 Chromium），
    退回原本的 redirect 模式（前端開新分頁）。
    """
    from . import headless_renderer

    # 如果 brainwave_data 還沒帶 mbti_primary，嘗試即時計算補入
    if brainwave_data and not brainwave_data.get("mbti_primary"):
        try:
            from app.services.algorithms import BandAverages, build_mbti_payload
            ba_inner = (brainwave_data.get("bands_avg") or {})
            _avg = BandAverages(
                attention  = brainwave_data.get("attention_percentage", 50),
                meditation = brainwave_data.get("meditation_percentage", 50),
                delta      = ba_inner.get("delta", 50),
                theta      = ba_inner.get("theta", 50),
                low_alpha  = ba_inner.get("low_alpha", ba_inner.get("alpha", 50)),
                high_alpha = ba_inner.get("high_alpha", ba_inner.get("alpha", 50)),
                low_beta   = ba_inner.get("low_beta", ba_inner.get("beta", 50)),
                high_beta  = ba_inner.get("high_beta", ba_inner.get("beta", 50)),
                low_gamma  = ba_inner.get("low_gamma", ba_inner.get("gamma", 50)),
                high_gamma = ba_inner.get("high_gamma", ba_inner.get("gamma", 50)),
            )
            brainwave_data = {**brainwave_data, **build_mbti_payload(_avg)}
        except Exception as _me:
            logger.warning("orchestrator: MBTI payload build failed: %s", _me)

    if headless_renderer.is_available():
        result = headless_renderer.start_headless_job(
            report_type=report_type,
            vercel_base=base,
            subject_name=subject_name,
            subject_email=subject_email,
            brainwave_data=brainwave_data,
            variant=variant,
            session_id=session_id,
            api_base=api_base,
            chapters_to_generate=chapters_to_generate,
        )
        if result.get("ok"):
            return {
                "ok":            True,
                "mode":          "headless",           # 給前端判斷用
                "external_url":  base,
                "job_id":        result["job_id"],
                "vercel_url":    result["vercel_url"],  # debug 用
                "note":          "報告正在主後端背景生成，使用者可關閉 APP",
                "subject_name":  subject_name,
            }
        # is_available=True 但啟動失敗 → 也 fallback
        logger.warning("headless 啟動失敗（會 fallback redirect）：%s", result.get("error"))

    # Fallback：原本的 vite_prefill（讓使用者瀏覽器自己跑）
    from urllib.parse import urlencode
    def _g(d, k, fallback=50):
        v = d.get(k)
        return fallback if v is None else v
    ba = (brainwave_data or {}).get("bands_avg") or {}
    b7 = (brainwave_data or {}).get("bands_7")   or {}  # 真實 High/Low 子頻帶
    attn  = _g(brainwave_data or {}, "attention_percentage")
    medi  = _g(brainwave_data or {}, "meditation_percentage")
    delta = _g(ba, "delta"); theta = _g(ba, "theta")
    alpha = _g(ba, "alpha"); beta  = _g(ba, "beta"); gamma = _g(ba, "gamma")

    # 優先讀 bands_7（真實量測），再讀 bands_avg 子鍵，找不到才用合併帶原值（不估算）
    def _sub_v(b7, ba, key_b7, key1, key2, base):
        for d, k in [(b7, key_b7), (ba, key1), (ba, key2)]:
            v = d.get(k)
            if v is not None:
                return int(max(0, min(100, v)))
        return int(max(0, min(100, base)))

    hi_alpha = _sub_v(b7, ba, "alpha_high", "high_alpha", "alpha_high", alpha)
    lo_alpha = _sub_v(b7, ba, "alpha_low",  "low_alpha",  "alpha_low",  alpha)
    hi_beta  = _sub_v(b7, ba, "beta_high",  "high_beta",  "beta_high",  beta)
    lo_beta  = _sub_v(b7, ba, "beta_low",   "low_beta",   "beta_low",   beta)
    hi_gamma = _sub_v(b7, ba, "gamma_high", "high_gamma", "gamma_high", gamma)
    lo_gamma = _sub_v(b7, ba, "gamma_low",  "low_gamma",  "gamma_low",  gamma)

    params = {
        "auto":       "1",
        "name":       subject_name or "",
        "email":      subject_email or "",
        "variant":    variant,
        "api_base":   api_base or "",
        "session_id": str(session_id or ""),
        # camelCase
        "focus":      int(attn),
        "relaxation": int(medi),
        "theta":      int(theta),
        "highAlpha":  hi_alpha,
        "lowAlpha":   lo_alpha,
        "highBeta":   hi_beta,
        "lowBeta":    lo_beta,
        "highGamma":  hi_gamma,
        "lowGamma":   lo_gamma,
        # snake_case 別名（符合設計文件）
        "alpha_high": hi_alpha,
        "alpha_low":  lo_alpha,
        "beta_high":  hi_beta,
        "beta_low":   lo_beta,
        "gamma_high": hi_gamma,
        "gamma_low":  lo_gamma,
        "attention":  int(attn), "meditation": int(medi),
        "delta": int(delta), "alpha": int(alpha), "beta": int(beta), "gamma": int(gamma),
    }
    if chapters_to_generate:
        params["chapters"] = ",".join(str(c) for c in chapters_to_generate)
    qs = urlencode(params)
    redirect_url = f"{base}/?{qs}"
    return {
        "ok":           True,
        "mode":         "vite_prefill",   # ⚠️ 前端需保持瀏覽器開啟（fallback 才會走到）
        "external_url": base,
        "redirect_url": redirect_url,
        "note":         "Playwright 未啟用，需在瀏覽器保持開啟 → 已 fallback 至 redirect 模式",
        "subject_name": subject_name,
    }


# ──────────────────────────────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────────────────────────────
def trigger_external_report(
    report_type:           str,
    subject_name:          str,
    subject_email:         str,
    subject_age:           Optional[int],
    subject_gender:        str,
    variant:               str = "full",
    chapters_to_generate:  Optional[List[int]] = None,
    brainwave_data:        Optional[Dict[str, Any]] = None,
    callback_url:          str = "",
    extra:                 Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    base = _url_for(report_type)
    if not base:
        return {"ok": False, "error": f"找不到 {report_type} 的對應 URL"}

    mode = SYSTEM_MODES.get(report_type, "vite_prefill")

    # 夫妻：需要兩個人，從 extra 拿 husband/wife
    if mode == "marital_rest":
        e = extra or {}
        wife_bw = e.get("wife_brainwave_data") or brainwave_data or {}
        husband = e.get("husband") or {
            "name": e.get("husband_name") or subject_name,
            "age":  subject_age or 0,
            "bw":   brainwave_data or {},
        }
        wife = e.get("wife") or {
            "name": e.get("wife_name") or "太太",
            "age":  e.get("wife_age") or 0,
            "bw":   wife_bw,
        }
        return _call_marital(base, husband, wife, meta=e)

    # 親子：需要 4 個家庭成員（dad, mom, child1, child2）
    if mode == "parent_child_rest":
        e = extra or {}
        family_name = e.get("family_name") or f"{subject_name}家"
        # 預設只有「孩子」一人，可由 extra 給完整 4 人
        members = e.get("members") or [
            {"role": "dad",    "role_zh": "爸爸", "name": e.get("dad_name", ""), "present": False, "data": None},
            {"role": "mom",    "role_zh": "媽媽", "name": e.get("mom_name", ""), "present": False, "data": None},
            {"role": "child1", "role_zh": "孩子1", "name": subject_name, "present": True,
             "data": {"concentration_pct": int((brainwave_data or {}).get("attention_percentage", 50)),
                      "relaxation_pct":    int((brainwave_data or {}).get("meditation_percentage", 50)),
                      "metrics":           _bw_to_metrics(brainwave_data or {})}},
            {"role": "child2", "role_zh": "孩子2", "name": e.get("child2_name", ""), "present": False, "data": None},
        ]
        # 使用本機內建親子報告（優先），或 fallback 到外部 Railway
        if _is_local("parent_child"):
            pc_base = _local_base_url() + "/parent-child"
        else:
            pc_base = FALLBACK_URLS.get("parent_child", base)
        return _call_parent_child(
            base=pc_base,
            family_name=family_name,
            members=members,
            image_mode=e.get("image_mode", "none"),
            selected_sections=e.get("selected_sections"),
        )

    # 成人/兒童：URL prefill 模式
    # api_base 三層 fallback：extra 指定 > settings.PUBLIC_BASE_URL > RAILWAY_PUBLIC_DOMAIN
    api_base = (extra or {}).get("api_base") or settings.PUBLIC_BASE_URL
    if not api_base:
        rd = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
        if rd:
            api_base = rd if rd.startswith("http") else f"https://{rd}"

    # life_script / child 走本機靜態 React App（不依賴外部 Vercel）
    if _is_local(report_type):
        local_base = _local_base_url()
        if report_type == "child":
            effective_base = local_base + LOCAL_CHILD_REPORT_APP_PATH.rstrip("/")
        else:
            effective_base = local_base + LOCAL_REPORT_APP_PATH.rstrip("/")
    else:
        effective_base = base

    return _call_vite_prefill(
        base=effective_base,
        subject_name=subject_name,
        subject_email=subject_email,
        brainwave_data=brainwave_data,
        variant=variant,
        session_id=(extra or {}).get("session_id"),
        api_base=api_base,
        report_type=report_type,
        chapters_to_generate=chapters_to_generate,
    )


def diag() -> Dict[str, Any]:
    """逐家列出狀態：URL、API 模式、是否能呼叫"""
    out = {}
    for rt in ("life_script", "child", "parent_child", "marital"):
        u = _url_for(rt)
        out[rt] = {
            "url":             u,
            "api_mode":        SYSTEM_MODES.get(rt),
            "configured":      bool(u),
            "supports_rest":   SYSTEM_MODES.get(rt) == "marital_rest",
            "from_env_or_default": "env" if (
                (rt == "life_script"  and settings.REPORT_URL_LIFE_SCRIPT)  or
                (rt == "child"        and settings.REPORT_URL_CHILD)        or
                (rt == "parent_child" and settings.REPORT_URL_PARENT_CHILD) or
                (rt == "marital"      and settings.REPORT_URL_MARITAL)
            ) else "default",
        }
    out["timeout_sec"] = settings.REPORT_REQUEST_TIMEOUT_SEC
    return out


# ──────────────────────────────────────────────────────────────────────
# 簡單測試（pytest 不要跑網路，所以保留為 manual）
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    print("=== diag ===")
    print(json.dumps(diag(), ensure_ascii=False, indent=2))
    print("\n=== 測試 marital ===")
    r = trigger_external_report(
        report_type="marital",
        subject_name="王俊宏", subject_email="", subject_age=36, subject_gender="男",
        brainwave_data={"bands_avg": {"alpha":60,"theta":45,"beta":78,"gamma":56}},
        extra={"wife": {"name":"林雅婷","age":34,
                        "bw":{"bands_avg":{"alpha":55,"theta":76,"beta":58,"gamma":52}}}}
    )
    print(json.dumps(r, ensure_ascii=False, indent=2)[:400])
