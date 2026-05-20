"""
報告 orchestrator：呼叫外部 4 個已部署的報告生成系統

報告類型 → URL 對照（env vars）：
  life_script   → REPORT_URL_LIFE_SCRIPT     (成人 / 腦波分析人生劇本)
  child         → REPORT_URL_CHILD           (兒童腦波天賦解碼)
  parent_child  → REPORT_URL_PARENT_CHILD    (親子腦波共振關係報告)
  marital       → REPORT_URL_MARITAL         (夫妻腦波共振關係報告)

呼叫流程 (HTTP)：
  POST {base}/api/generate
    {
      "subject_name": "...",
      "subject_email": "...",
      "subject_age": 35,
      "subject_gender": "男",
      "variant": "trial" | "full" | "vip",
      "chapters_to_generate": [1, 3, 8, 12] | null,
      "brainwave_data": { ... 採集統計值 ... },
      "callback_url": "https://我們/api/v1/report-gen/external-callback"
    }
  → 預期回 { ok: true, job_id: "xxx", status_url: "...", result_url: "..." }

  之後我們可以輪詢 status_url 或等 callback。

若 URL 未設定 → 回 None，呼叫端可以 fallback 到內建 Gemini 生成
"""
from __future__ import annotations
import time
import logging
from typing import Optional, Dict, Any, List

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _url_for(report_type: str) -> Optional[str]:
    mp = {
        "life_script":   settings.REPORT_URL_LIFE_SCRIPT,
        "child":         settings.REPORT_URL_CHILD,
        "parent_child":  settings.REPORT_URL_PARENT_CHILD,
        "marital":       settings.REPORT_URL_MARITAL,
    }
    u = (mp.get(report_type) or "").strip().rstrip("/")
    return u or None


def is_external_available(report_type: str) -> bool:
    return _url_for(report_type) is not None


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
    """
    同步發起一個外部報告生成
    回傳格式（dict）：
      { ok: True,  external_job_id: "...", status_url: "...", result_url: "...", message: "..." }
      { ok: False, error: "..." }
    """
    base = _url_for(report_type)
    if not base:
        return {"ok": False, "error": f"未設定 {report_type} 的 REPORT_URL"}

    body = {
        "subject_name":         subject_name,
        "subject_email":        subject_email,
        "subject_age":          subject_age,
        "subject_gender":       subject_gender,
        "variant":              variant,
        "chapters_to_generate": chapters_to_generate,
        "brainwave_data":       brainwave_data or {},
        "callback_url":         callback_url,
        "source":               "AutomaticDetection",
        "requested_at":         int(time.time()),
    }
    if extra:
        body.update(extra)

    url = f"{base}/api/generate"
    try:
        with httpx.Client(timeout=30.0) as cli:
            r = cli.post(url, json=body)
        if r.status_code >= 400:
            return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text[:500]}
        return {
            "ok":              True,
            "external_url":    base,
            "external_job_id": data.get("job_id"),
            "status_url":      data.get("status_url"),
            "result_url":      data.get("result_url"),
            "raw":             data,
        }
    except httpx.TimeoutException:
        return {"ok": False, "error": "外部系統逾時"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def poll_external_status(status_url: str) -> Dict[str, Any]:
    """
    主動輪詢外部系統的狀態
    回傳：
      { ok: True, status: "running"/"completed"/"error", progress: 0-100, result_url?: "..." }
      { ok: False, error: "..." }
    """
    if not status_url:
        return {"ok": False, "error": "status_url 為空"}
    try:
        with httpx.Client(timeout=15.0) as cli:
            r = cli.get(status_url)
        if r.status_code >= 400:
            return {"ok": False, "error": f"HTTP {r.status_code}"}
        return {"ok": True, **(r.json() if r.headers.get("content-type","").startswith("application/json") else {"raw": r.text})}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def diag() -> Dict[str, Any]:
    """商業上線前驗 4 個 URL 是否設好"""
    return {
        "life_script":  bool(settings.REPORT_URL_LIFE_SCRIPT),
        "child":        bool(settings.REPORT_URL_CHILD),
        "parent_child": bool(settings.REPORT_URL_PARENT_CHILD),
        "marital":      bool(settings.REPORT_URL_MARITAL),
        "timeout_sec":  settings.REPORT_REQUEST_TIMEOUT_SEC,
    }
