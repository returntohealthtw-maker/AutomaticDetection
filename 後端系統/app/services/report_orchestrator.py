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
DEFAULT_URLS = {
    "life_script":  "https://brianave-report-image.vercel.app",
    "child":        "https://brianwave-child.vercel.app",
    "parent_child": "https://web-production-f1aec.up.railway.app",
    "marital":      "https://web-production-2c7d43.up.railway.app",
}

# 每家系統的 API 模式
SYSTEM_MODES = {
    "life_script":  "redirect",   # 沒 REST API；開連結讓使用者在外部 UI 操作
    "child":        "redirect",
    "parent_child": "redirect",
    "marital":      "marital_rest",  # 真實 REST API
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


def is_external_available(report_type: str) -> bool:
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
    把採集到的 5-band 平均 (delta/theta/alpha/beta/gamma 0-100)
    + attention/meditation 轉成「七大腦波指標」(0-100)：
       high_alpha, low_alpha, theta, high_beta, low_beta, high_gamma, low_gamma

    因為單通道 EEG 沒分 low/high alpha-beta-gamma，這邊用簡單映射：
      high_alpha ≈ alpha 平均 * 1.1（上限 100）
      low_alpha  ≈ alpha 平均 * 0.9
      ... 類似
    """
    def cap(v): return max(0, min(100, int(v)))
    ba = (bw or {}).get("bands_avg") or {}
    alpha  = ba.get("alpha", 50)
    theta  = ba.get("theta", 50)
    beta   = ba.get("beta",  50)
    gamma  = ba.get("gamma", 50)
    return {
        "high_alpha": cap(alpha * 1.1),
        "low_alpha":  cap(alpha * 0.9),
        "theta":      cap(theta),
        "high_beta":  cap(beta * 1.1),
        "low_beta":   cap(beta * 0.9),
        "high_gamma": cap(gamma * 1.1),
        "low_gamma":  cap(gamma * 0.9),
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
            "mbti":      husband.get("mbti", "----"),
            "brainwave": husband.get("brainwave") or _bw_to_seven_indices(husband.get("bw", {})),
        },
        "wife": {
            "name":      wife.get("name", "太太"),
            "age":       int(wife.get("age", 0) or 0),
            "mbti":      wife.get("mbti", "----"),
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
# 模式 2：redirect（沒 REST，回網址讓前端開新分頁）
# ──────────────────────────────────────────────────────────────────────
def _call_redirect(base: str, subject_name: str, brainwave_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    回傳 redirect_url 給前端，前端開新分頁讓使用者在外部 UI 完成
    （未來在那 3 個系統加 deep-link 支援，可在這邊把 brainwave_data 編入 query string）
    """
    return {
        "ok":           True,
        "mode":         "redirect",
        "external_url": base,
        "redirect_url": base + "/",
        "note":         "此報告類型外部系統尚無 REST API，已開連結讓您在該系統內完成生成",
        "subject_name": subject_name,
        "has_data":     bool(brainwave_data),
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

    mode = SYSTEM_MODES.get(report_type, "redirect")

    # marital 需要兩個人，從 extra 拿 husband/wife
    if mode == "marital_rest":
        e = extra or {}
        husband = e.get("husband") or {
            "name": e.get("husband_name") or subject_name,
            "age":  subject_age or 0,
            "mbti": e.get("husband_mbti") or "----",
            "bw":   brainwave_data or {},
        }
        wife = e.get("wife") or {
            "name": e.get("wife_name") or "太太",
            "age":  e.get("wife_age") or 0,
            "mbti": e.get("wife_mbti") or "----",
            "bw":   e.get("wife_brainwave_data") or brainwave_data or {},
        }
        return _call_marital(base, husband, wife, meta=e)

    # 其他 3 個都走 redirect
    return _call_redirect(base, subject_name, brainwave_data)


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
        extra={"wife": {"name":"林雅婷","age":34,"mbti":"ENFP",
                        "bw":{"bands_avg":{"alpha":55,"theta":76,"beta":58,"gamma":52}}}}
    )
    print(json.dumps(r, ensure_ascii=False, indent=2)[:400])
