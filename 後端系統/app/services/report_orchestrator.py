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
    ba = (bw or {}).get("bands_avg") or {}
    return {
        "Delta":  cap(ba.get("delta", 50)),
        "Theta":  cap(ba.get("theta", 50)),
        "High α": cap(ba.get("alpha", 50) * 1.1),
        "Low α":  cap(ba.get("alpha", 50) * 0.9),
        "High β": cap(ba.get("beta",  50) * 1.1),
        "Low β":  cap(ba.get("beta",  50) * 0.9),
        "High γ": cap(ba.get("gamma", 50) * 1.1),
        "Low γ":  cap(ba.get("gamma", 50) * 0.9),
    }


# ──────────────────────────────────────────────────────────────────────
# 模式 3：vite_prefill（成人/兒童 — 帶 query string 讓 React 自動執行）
# ──────────────────────────────────────────────────────────────────────
def _call_vite_prefill(
    base:           str,
    subject_name:   str,
    subject_email:  str,
    brainwave_data: Optional[Dict[str, Any]],
    variant:        str = "full",
    session_id:     Optional[int] = None,
    api_base:       str = "",
) -> Dict[str, Any]:
    """
    回傳一個帶 query string 的 URL，前端打開後 React 會：
      1. 從 query 解出資料，自動填入表單  
      2. 自動 click 「單筆生成」→ 進入工作站
      3. 自動逐節生成（48 sub-sections）
      4. 生成完自動寄信到 ?email=...
      5. 結束後顯示「✅ 已寄送」
    需在成人/兒童 repo 的 App.tsx 內加 auto-run 支援
    """
    from urllib.parse import urlencode
    ba = (brainwave_data or {}).get("bands_avg") or {}
    # 7 大指標 (0-100) — React 端 BrainwaveData 結構
    # api_base + session_id 讓 React 在完成後可以 callback 主後端的 /reports/record
    params = {
        "auto":       "1",
        "name":       subject_name or "",
        "email":      subject_email or "",
        "variant":    variant,
        "api_base":   api_base or "",
        "session_id": str(session_id or ""),
        # 腦波 7 大指標：模擬從單通道 alpha/beta/gamma 推 high/low
        "focus":      int((brainwave_data or {}).get("attention_percentage", 50)),
        "relaxation": int((brainwave_data or {}).get("meditation_percentage", 50)),
        "theta":      int(ba.get("theta", 50)),
        "highAlpha":  int(min(100, ba.get("alpha", 50) * 1.1)),
        "lowAlpha":   int(max(0,   ba.get("alpha", 50) * 0.9)),
        "highBeta":   int(min(100, ba.get("beta",  50) * 1.1)),
        "lowBeta":    int(max(0,   ba.get("beta",  50) * 0.9)),
        "highGamma":  int(min(100, ba.get("gamma", 50) * 1.1)),
        "lowGamma":   int(max(0,   ba.get("gamma", 50) * 0.9)),
    }
    qs = urlencode(params)
    redirect_url = f"{base}/?{qs}"
    return {
        "ok":           True,
        "mode":         "vite_prefill",
        "external_url": base,
        "redirect_url": redirect_url,
        "note":         "已開啟自動模式，React 前端會自動填表並生成（瀏覽器需保持開啟）",
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
        return _call_parent_child(
            base=base,
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
    return _call_vite_prefill(
        base=base,
        subject_name=subject_name,
        subject_email=subject_email,
        brainwave_data=brainwave_data,
        variant=variant,
        session_id=(extra or {}).get("session_id"),
        api_base=api_base,
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
        extra={"wife": {"name":"林雅婷","age":34,"mbti":"ENFP",
                        "bw":{"bands_avg":{"alpha":55,"theta":76,"beta":58,"gamma":52}}}}
    )
    print(json.dumps(r, ensure_ascii=False, indent=2)[:400])
