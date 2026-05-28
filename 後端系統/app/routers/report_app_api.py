"""
本機版報告 App API — 對應 Vercel 上的 api/ serverless functions
讓 static-app/report-app/（本機 React build）能呼叫這些端點，
完全不再依賴 Vercel。

端點：
  POST /api/gemini          — Gemini 文字 / SVG / 圖像生成（同 api/gemini.ts）
  POST /api/gcsSignedUrl    — GCS signed URL（同 api/gcsSignedUrl.ts）
  POST /api/uploadPdfProxy  — 伺服器端 GCS 上傳代理（繞過瀏覽器 CORS）
  POST /api/sendEmail       — 寄信（同 api/sendEmail.ts）
"""
from __future__ import annotations
import os
import logging
from typing import Optional, Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _gemini_key() -> str:
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        raise ValueError("GEMINI_API_KEY 未設定")
    return key


def _cors_headers() -> dict:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


# ── /api/gemini ───────────────────────────────────────────────────────────────

@router.options("/api/gemini")
async def gemini_options():
    return JSONResponse({}, headers=_cors_headers())


@router.post("/api/gemini")
async def gemini_proxy(request: Request):
    """代理 Gemini API — 對應 Vercel api/gemini.ts"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "無效 JSON"}, status_code=400, headers=_cors_headers())

    req_type = body.get("type")
    if not req_type:
        return JSONResponse({"error": "缺少 type 欄位"}, status_code=400, headers=_cors_headers())

    try:
        key = _gemini_key()
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=503, headers=_cors_headers())

    headers = {"Content-Type": "application/json"}

    async def _call(model: str, verb: str, payload: dict) -> dict:
        url = f"{GEMINI_API_BASE}/models/{model}:{verb}?key={key}"
        async with httpx.AsyncClient(timeout=120) as cli:
            r = await cli.post(url, json=payload, headers=headers)
        return r.status_code, r.json()

    try:
        # ── text / svg ────────────────────────────────────────────────────────
        if req_type in ("text", "svg"):
            prompt = body.get("prompt")
            if not prompt:
                return JSONResponse({"error": "缺少 prompt"}, status_code=400, headers=_cors_headers())
            status, d = await _call(
                "gemini-2.5-flash", "generateContent",
                {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.75 if req_type == "text" else 0.3, "maxOutputTokens": 8192},
                }
            )
            if status >= 400:
                logger.error("[report_app_api/gemini/%s] %s %s", req_type, status, str(d)[:200])
                return JSONResponse({"error": d.get("error", {}).get("message", "Gemini 錯誤")},
                                    status_code=status, headers=_cors_headers())
            text = d.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            key_name = "text" if req_type == "text" else "svg"
            return JSONResponse({key_name: text}, headers=_cors_headers())

        # ── image ─────────────────────────────────────────────────────────────
        if req_type == "image":
            prompt = body.get("prompt")
            if not prompt:
                return JSONResponse({"error": "缺少 prompt"}, status_code=400, headers=_cors_headers())
            imagen_model = os.environ.get("IMAGEN_MODEL", "imagen-4.0-generate-001")
            status, d = await _call(
                imagen_model, "predict",
                {"instances": [{"prompt": prompt}],
                 "parameters": {"sampleCount": 1, "aspectRatio": "16:9", "personGeneration": "dont_allow"}}
            )
            if status >= 400:
                return JSONResponse({"error": d.get("error", {}).get("message", "Imagen 錯誤")},
                                    status_code=status, headers=_cors_headers())
            pred0 = (d.get("predictions") or [{}])[0]
            image_bytes = pred0.get("bytesBase64Encoded")
            return JSONResponse({"imageBytes": image_bytes, "model": imagen_model}, headers=_cors_headers())

        # ── extract ───────────────────────────────────────────────────────────
        if req_type == "extract":
            image_b64 = body.get("imageBase64")
            if not image_b64:
                return JSONResponse({"error": "缺少 imageBase64"}, status_code=400, headers=_cors_headers())
            extract_prompt = body.get("prompt", "請解析腦波數值並輸出 JSON")
            image_mime = "image/jpeg" if image_b64.startswith("/9j/") else "image/png"
            status, d = await _call(
                "gemini-2.5-flash", "generateContent",
                {"contents": [{"role": "user", "parts": [
                    {"inlineData": {"mimeType": image_mime, "data": image_b64}},
                    {"text": extract_prompt},
                ]}],
                 "generationConfig": {"temperature": 0, "maxOutputTokens": 800}}
            )
            if status >= 400:
                return JSONResponse({"error": d.get("error", {}).get("message", "解析錯誤")},
                                    status_code=status, headers=_cors_headers())
            text = (d.get("candidates") or [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            import json as _json
            import re
            m = re.search(r'\{[^{}]*"theta"[^{}]*\}', text)
            raw = m.group(0) if m else text.strip().lstrip("```json").rstrip("```").strip()
            try:
                parsed = _json.loads(raw)
                validated = {}
                for k in ["theta","highAlpha","lowAlpha","highBeta","lowBeta","highGamma","lowGamma","focus","relaxation"]:
                    v = parsed.get(k)
                    if v is not None:
                        try:
                            vv = int(round(float(v)))
                            if 1 <= vv <= 99:
                                validated[k] = vv
                        except Exception:
                            pass
                return JSONResponse({"data": validated, "rawResponse": text[:200]}, headers=_cors_headers())
            except Exception as e:
                return JSONResponse({"data": {}, "rawResponse": text[:200], "parseError": str(e)},
                                    headers=_cors_headers())

        return JSONResponse({"error": f"未知 type: {req_type}"}, status_code=400, headers=_cors_headers())

    except Exception as e:
        logger.exception("[report_app_api/gemini] 例外")
        return JSONResponse({"error": str(e)}, status_code=500, headers=_cors_headers())


# ── /api/gcsSignedUrl ─────────────────────────────────────────────────────────

@router.options("/api/gcsSignedUrl")
async def gcs_options():
    return JSONResponse({}, headers=_cors_headers())


@router.post("/api/gcsSignedUrl")
async def gcs_signed_url(request: Request):
    """產生 GCS signed PUT URL — 對應 Vercel api/gcsSignedUrl.ts"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "無效 JSON"}, status_code=400, headers=_cors_headers())

    pathname    = body.get("pathname", "")
    content_type = body.get("contentType", "application/pdf")

    if not pathname or not pathname.startswith("reports/"):
        return JSONResponse({"error": "pathname 必須以 reports/ 開頭"}, status_code=400, headers=_cors_headers())

    bucket_name = os.environ.get("GCS_BUCKET_NAME", "").strip()
    sa_json     = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "").strip()

    if not bucket_name or not sa_json:
        missing = "GCS_BUCKET_NAME" if not bucket_name else "GCP_SERVICE_ACCOUNT_JSON"
        return JSONResponse({"error": f"GCS 尚未設定（缺少 {missing}）"}, status_code=503, headers=_cors_headers())

    try:
        import json as _json
        import datetime
        from google.cloud import storage as gcs
        from google.oauth2 import service_account

        credentials_info = _json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        client  = gcs.Client(credentials=creds)
        bucket  = client.bucket(bucket_name)
        blob    = bucket.blob(pathname)

        upload_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=15),
            method="PUT",
            content_type=content_type,
        )
        download_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(days=7),
            method="GET",
        )
        public_url = f"https://storage.googleapis.com/{bucket_name}/{pathname.lstrip('/')}"

        return JSONResponse({
            "uploadUrl":   upload_url,
            "downloadUrl": download_url,
            "publicUrl":   public_url,
            "pathname":    pathname,
        }, headers=_cors_headers())

    except Exception as e:
        logger.exception("[report_app_api/gcsSignedUrl]")
        return JSONResponse({"error": str(e)}, status_code=500, headers=_cors_headers())


# ── /api/uploadPdfProxy ───────────────────────────────────────────────────────
# 從瀏覽器接收 PDF binary，在 Railway server 端上傳到 GCS，
# 完全繞過 signed URL direct PUT 的 CORS 問題。

@router.options("/api/uploadPdfProxy")
async def upload_pdf_proxy_options():
    return JSONResponse({}, headers=_cors_headers())


@router.post("/api/uploadPdfProxy")
async def upload_pdf_proxy(request: Request):
    """接收 PDF binary 並在伺服器端上傳至 GCS（繞過瀏覽器 CORS 限制）"""
    from urllib.parse import unquote
    pathname_raw = request.headers.get("X-Pathname", "").strip()
    # Header 值可能是 URL-encoded（瀏覽器 fetch 不允許非 ASCII header）
    pathname = unquote(pathname_raw)
    if not pathname or not pathname.startswith("reports/"):
        return JSONResponse(
            {"error": "Header X-Pathname 必須以 reports/ 開頭"},
            status_code=400,
            headers=_cors_headers(),
        )

    pdf_bytes = await request.body()
    if not pdf_bytes:
        return JSONResponse({"error": "空 body"}, status_code=400, headers=_cors_headers())

    bucket_name = os.environ.get("GCS_BUCKET_NAME", "").strip()
    sa_json_str = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "").strip()
    if not bucket_name or not sa_json_str:
        missing = "GCS_BUCKET_NAME" if not bucket_name else "GCP_SERVICE_ACCOUNT_JSON"
        return JSONResponse(
            {"error": f"GCS 尚未設定（缺少 {missing}）"},
            status_code=503,
            headers=_cors_headers(),
        )

    try:
        import json as _json
        import datetime
        from google.cloud import storage as gcs_lib
        from google.oauth2 import service_account as sa_mod

        creds_info = _json.loads(sa_json_str)
        creds = sa_mod.Credentials.from_service_account_info(creds_info)
        client = gcs_lib.Client(credentials=creds, project=creds_info.get("project_id"))
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(pathname)
        blob.upload_from_string(pdf_bytes, content_type="application/pdf")

        dl_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(days=7),
            method="GET",
        )
        pub_url = f"https://storage.googleapis.com/{bucket_name}/{pathname}"

        size_kb = len(pdf_bytes) // 1024
        logger.info("[uploadPdfProxy] 上傳成功: %s (%dKB)", pathname, size_kb)
        return JSONResponse(
            {"downloadUrl": dl_url, "publicUrl": pub_url, "pathname": pathname, "sizeKB": size_kb},
            headers=_cors_headers(),
        )
    except Exception as e:
        logger.exception("[uploadPdfProxy]")
        return JSONResponse({"error": str(e)}, status_code=500, headers=_cors_headers())


# ── /api/sendEmail ────────────────────────────────────────────────────────────

@router.options("/api/sendEmail")
async def email_options():
    return JSONResponse({}, headers=_cors_headers())


@router.post("/api/sendEmail")
async def send_email_proxy(request: Request):
    """寄信 — 對應 Vercel api/sendEmail.ts，走 Resend"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "無效 JSON"}, status_code=400, headers=_cors_headers())

    to      = body.get("to", "")
    subject = body.get("subject", "您的腦波分析報告")
    pdf_url = body.get("pdfUrl") or body.get("pdf_url", "")

    if not to:
        return JSONResponse({"error": "缺少 to 欄位"}, status_code=400, headers=_cors_headers())

    gmail_user = os.environ.get("GMAIL_USER", "").strip()
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    from_name  = os.environ.get("GMAIL_FROM_NAME", "onlineReport 線上腦波分析系統")

    if not gmail_user or not gmail_pass:
        # 沒設定 Gmail 就靜默成功（後端 /reports/record callback 另外處理寄信）
        logger.warning("[report_app_api/sendEmail] GMAIL_USER/GMAIL_APP_PASSWORD 未設定，跳過寄信")
        return JSONResponse({"ok": True, "skipped": True, "reason": "email_not_configured"}, headers=_cors_headers())

    html = f"""<p>您好，</p>
<p>您的腦波分析報告已生成完成。</p>
<p><a href="{pdf_url}" style="background:#2D3561;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;">點此查看/下載報告</a></p>
<p>連結有效期限為 7 天。</p>
<p>— {from_name}</p>"""

    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{from_name} <{gmail_user}>"
        msg["To"]      = to
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(gmail_user, [to], msg.as_string())

        return JSONResponse({"ok": True}, headers=_cors_headers())
    except Exception as e:
        logger.exception("[report_app_api/sendEmail]")
        return JSONResponse({"error": str(e)}, status_code=500, headers=_cors_headers())
