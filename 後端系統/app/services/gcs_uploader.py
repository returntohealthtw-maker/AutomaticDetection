"""
Google Cloud Storage 上傳器

設定（Railway Variables）：
  GCS_BUCKET_NAME         = brainwave-child-reports（或你的 bucket）
  GCP_SERVICE_ACCOUNT_JSON = {"type":"service_account",...}（整段 JSON）
  GCS_SIGNED_URL_DAYS     = 7（簽名 URL 有效天數，預設 7）

使用：
  from app.services import gcs_uploader
  url = gcs_uploader.upload_pdf("reports/x.pdf", "life_script_2026_abc.pdf")
"""
from __future__ import annotations
import os
import json
import logging
from datetime import timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def _env(name: str, fallback: str = "") -> str:
    return (os.environ.get(name) or fallback).strip()


def _bucket_name() -> str:
    return _env("GCS_BUCKET_NAME")


def _credentials_dict() -> Optional[dict]:
    raw = _env("GCP_SERVICE_ACCOUNT_JSON")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception as e:
        logger.error("GCP_SERVICE_ACCOUNT_JSON 不是合法 JSON：%s", e)
        return None


def is_configured() -> bool:
    return bool(_bucket_name()) and bool(_credentials_dict())


def _signed_days() -> int:
    try:
        return int(_env("GCS_SIGNED_URL_DAYS", "7"))
    except ValueError:
        return 7


def upload_pdf(local_path: str, object_name: str) -> Optional[str]:
    """
    上傳 PDF 到 GCS，回傳一個 7 天有效的 signed URL（用於 email 連結）。

    失敗回 None；呼叫端可決定是否 fallback。
    """
    if not is_configured():
        logger.warning("GCS 未設定（缺 GCS_BUCKET_NAME 或 GCP_SERVICE_ACCOUNT_JSON）")
        return None

    if not os.path.isfile(local_path):
        logger.error("GCS 上傳失敗：本地檔案不存在 %s", local_path)
        return None

    try:
        from google.cloud import storage
        from google.oauth2 import service_account

        creds_dict = _credentials_dict()
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        client = storage.Client(project=creds_dict.get("project_id"), credentials=credentials)
        bucket = client.bucket(_bucket_name())
        blob = bucket.blob(object_name)
        blob.upload_from_filename(local_path, content_type="application/pdf")
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=_signed_days()),
            method="GET",
            response_disposition=f'attachment; filename="{os.path.basename(object_name)}"',
        )
        logger.info("✅ GCS 上傳成功 gs://%s/%s", _bucket_name(), object_name)
        return url
    except Exception as e:
        logger.exception("GCS 上傳失敗：%s", e)
        return None


def delete_pdf_object(pdf_url: str) -> dict:
    """從 GCS 刪除一個 PDF 檔案。

    pdf_url 可以是：
      - GCS signed URL: https://storage.googleapis.com/BUCKET/reports/xxx.pdf?X-Goog-...
      - GCS public URL: https://storage.googleapis.com/BUCKET/reports/xxx.pdf
      - 直接的 object name: reports/general/xxx.pdf

    回傳 {"ok": True, "object_name": "..."} 或 {"ok": False, "error": "..."}
    """
    if not pdf_url:
        return {"ok": False, "error": "pdf_url 為空"}
    if not is_configured():
        return {"ok": False, "error": "GCS 未設定"}

    # 從 URL 萃取 object name
    try:
        from urllib.parse import urlparse, unquote
        parsed = urlparse(pdf_url)
        if parsed.scheme in ("http", "https") and "storage.googleapis.com" in parsed.netloc:
            # https://storage.googleapis.com/BUCKET/object/path?...
            path = unquote(parsed.path)  # e.g. /my-bucket/reports/general/xxx.pdf
            bucket = _bucket_name()
            prefix = f"/{bucket}/"
            if path.startswith(prefix):
                object_name = path[len(prefix):]
            else:
                # bucket 在 hostname 裡（CNAME 模式），整個 path 就是 object name
                object_name = path.lstrip("/")
        else:
            # 直接傳入 object name（無 scheme）
            object_name = pdf_url.lstrip("/")
    except Exception as e:
        return {"ok": False, "error": f"URL 解析失敗：{e}"}

    if not object_name:
        return {"ok": False, "error": "無法從 URL 解析 object name"}

    try:
        creds_dict = _credentials_dict()
        from google.cloud import storage
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        client = storage.Client(project=creds_dict.get("project_id"), credentials=credentials)
        bucket = client.bucket(_bucket_name())
        blob = bucket.blob(object_name)
        if blob.exists():
            blob.delete()
            logger.info("✅ GCS 刪除成功 gs://%s/%s", _bucket_name(), object_name)
            return {"ok": True, "object_name": object_name, "existed": True}
        else:
            logger.warning("GCS 物件不存在（跳過刪除）: %s", object_name)
            return {"ok": True, "object_name": object_name, "existed": False,
                    "note": "GCS 上無此物件（可能已被刪除或 URL 已過期）"}
    except Exception as e:
        logger.exception("GCS 刪除失敗：%s", e)
        return {"ok": False, "error": str(e)}


def diag() -> dict:
    creds = _credentials_dict()
    return {
        "bucket_set":  bool(_bucket_name()),
        "bucket":      _bucket_name(),
        "creds_set":   bool(creds),
        "project_id":  (creds or {}).get("project_id", ""),
        "client_email": (creds or {}).get("client_email", ""),
        "signed_days": _signed_days(),
    }


def generate_fresh_signed_url(pdf_url: str, days: Optional[int] = None) -> Optional[str]:
    """
    從已儲存的 pdf_url（公開 URL 或舊 Signed URL）重新產生有效的 Signed URL。

    用於：
      - 管理員寄信前確保連結有效（舊 signed URL 可能已過期）
      - 公開 URL 在私有 bucket 無法存取，改為 Signed URL

    回傳新的 Signed URL，或 None（若 GCS 未設定或解析失敗）。
    """
    if not pdf_url or not is_configured():
        return None

    try:
        from urllib.parse import urlparse, unquote
        parsed = urlparse(pdf_url)
        path = unquote(parsed.path)

        if "storage.googleapis.com" not in parsed.netloc:
            logger.warning("generate_fresh_signed_url: 非 GCS URL，略過 %s", pdf_url[:80])
            return None

        bucket = _bucket_name()
        prefix = f"/{bucket}/"
        if path.startswith(prefix):
            object_name = path[len(prefix):]
        else:
            object_name = path.lstrip("/")

        if not object_name:
            return None

        from google.cloud import storage
        from google.oauth2 import service_account

        creds_dict = _credentials_dict()
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        client = storage.Client(project=creds_dict.get("project_id"), credentials=credentials)
        blob = client.bucket(bucket).blob(object_name)

        expiry_days = days if days is not None else _signed_days()
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=expiry_days),
            method="GET",
            response_disposition=f'attachment; filename="{os.path.basename(object_name)}"',
        )
        logger.info("✅ 重新簽署 URL 成功 gs://%s/%s（有效 %d 天）", bucket, object_name, expiry_days)
        return url
    except Exception as e:
        logger.exception("generate_fresh_signed_url 失敗：%s", e)
        return None


def list_pdfs(prefix: str = "", max_items: int = 500) -> list[dict]:
    """
    直接列出 GCS bucket 裡所有 PDF（後台『報告管理 → GCS 全部檔案』用）。

    每筆回傳：{
        "name":        object_name (e.g. reports/general/xxx.pdf)
        "size":        bytes
        "created":     ISO 字串
        "updated":     ISO 字串
        "content_type": "application/pdf"
        "signed_url":  7 天 signed URL（可直接點開或下載）
    }
    失敗或未設定時回傳 []。
    """
    if not is_configured():
        logger.warning("list_pdfs: GCS 未設定")
        return []

    try:
        from google.cloud import storage
        from google.oauth2 import service_account

        creds_dict = _credentials_dict()
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        client = storage.Client(project=creds_dict.get("project_id"), credentials=credentials)
        bucket = client.bucket(_bucket_name())

        out: list[dict] = []
        blobs = client.list_blobs(bucket, prefix=prefix or None, max_results=max_items)
        for b in blobs:
            # 只列 PDF
            name = b.name or ""
            if not name.lower().endswith(".pdf"):
                continue
            try:
                signed = b.generate_signed_url(
                    version="v4",
                    expiration=timedelta(days=_signed_days()),
                    method="GET",
                    response_disposition=f'attachment; filename="{os.path.basename(name)}"',
                )
            except Exception as e:
                logger.warning("簽 URL 失敗 (%s)：%s", name, e)
                signed = ""
            out.append({
                "name":         name,
                "size":         int(b.size or 0),
                "created":      b.time_created.isoformat() if b.time_created else "",
                "updated":      b.updated.isoformat() if b.updated else "",
                "content_type": b.content_type or "",
                "signed_url":   signed,
            })
        # 新到舊
        out.sort(key=lambda x: x.get("updated") or x.get("created") or "", reverse=True)
        return out
    except Exception as e:
        logger.exception("list_pdfs 失敗：%s", e)
        return []
