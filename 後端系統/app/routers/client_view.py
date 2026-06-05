"""
客戶掃描 QR 後開啟的公開頁（不需登入）。
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session as DbSession

from app.core.database import get_db
from app.core import models

router = APIRouter(prefix="/api/v1/public", tags=["客戶公開頁"])


def _summary_html(data: dict) -> str:
    sections = [
        ("原生家庭狀況", data.get("family", "")),
        ("性格矛盾與地雷", data.get("personality", "")),
        ("現階段面臨的壓力", data.get("stress", "")),
        ("人生天賦設計", data.get("talent", "")),
        ("最佳學科＆事業＆工作", data.get("career", "")),
    ]
    blocks = ""
    for title, text in sections:
        blocks += f"""
        <section class="sec">
          <h2>{title}</h2>
          <p>{text or "（尚無摘要）"}</p>
        </section>"""
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>天賦檢測摘要</title>
  <style>
    body {{ margin:0; font-family:'Microsoft JhengHei',sans-serif; background:#f0f4f8; color:#1a1a2e; }}
    .wrap {{ max-width:520px; margin:0 auto; padding:20px 16px 40px; }}
    h1 {{ font-size:20px; margin:8px 0 20px; text-align:center; }}
    .sec {{ background:white; border-radius:14px; padding:16px 18px; margin-bottom:14px;
            box-shadow:0 2px 10px rgba(0,0,0,0.06); }}
    .sec h2 {{ font-size:15px; color:#2D3561; margin:0 0 10px; border-left:4px solid #00BCD4; padding-left:10px; }}
    .sec p {{ font-size:14px; line-height:1.75; margin:0; white-space:pre-wrap; color:#444; }}
    .foot {{ text-align:center; font-size:11px; color:#aaa; margin-top:24px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>🧠 教育機構學生天賦檢測</h1>
    {blocks}
    <div class="foot">本頁為檢測後摘要，完整報告請由顧問提供或 Email／LINE 連結。</div>
  </div>
</body>
</html>"""


@router.get("/client/{token}", response_class=HTMLResponse)
def client_summary_page(token: str, db: DbSession = Depends(get_db)):
    r = db.query(models.Report).filter(models.Report.qr_token == token).first()
    if not r:
        raise HTTPException(status_code=404, detail="找不到連結")
    if not r.client_summary:
        html = """<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>處理中</title></head>
<body style="font-family:sans-serif;text-align:center;padding:40px 20px;color:#555;">
<h2>報告產生中</h2><p>請稍後再掃描同一 QR Code，或稍候由顧問提供連結。</p>
</body></html>"""
        return HTMLResponse(html)
    try:
        data = json.loads(r.client_summary)
    except json.JSONDecodeError:
        data = {}
    return HTMLResponse(_summary_html(data))


@router.get("/client/{token}/json")
def client_summary_json(token: str, db: DbSession = Depends(get_db)):
    r = db.query(models.Report).filter(models.Report.qr_token == token).first()
    if not r:
        raise HTTPException(status_code=404, detail="找不到報告")
    try:
        return json.loads(r.client_summary or "{}")
    except json.JSONDecodeError:
        return {}


@router.get("/client/{token}/pdf")
def client_download_pdf(token: str, db: DbSession = Depends(get_db)):
    """
    永久報告下載端點（Email 連結使用此 URL）。
    每次點擊時動態重新產生 GCS Signed URL（7 天有效），
    避免 Email 連結因 GCS token 過期而失效。
    """
    r = db.query(models.Report).filter(models.Report.qr_token == token).first()
    if not r:
        raise HTTPException(status_code=404, detail="找不到報告")

    if not r.pdf_url:
        html = """<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>報告未就緒</title></head>
<body style="font-family:sans-serif;text-align:center;padding:40px 20px;color:#555;">
<h2>報告尚未產生</h2><p>PDF 尚未完成，請聯絡顧問確認狀態。</p>
</body></html>"""
        return HTMLResponse(html, status_code=200)

    # 動態重新簽署，確保連結永遠有效
    from app.services import gcs_uploader
    fresh_url = None
    try:
        fresh_url = gcs_uploader.generate_fresh_signed_url(r.pdf_url)
        if fresh_url:
            # 同步更新 DB，延長快取有效期
            r.pdf_url = fresh_url
            db.commit()
    except Exception:
        pass

    redirect_url = fresh_url or r.pdf_url
    return RedirectResponse(url=redirect_url, status_code=302)
