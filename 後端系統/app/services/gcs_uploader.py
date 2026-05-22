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
