"""
Gmail SMTP 寄信

設定：
  GMAIL_USER         = your.account@gmail.com         （你的 Gmail 帳號）
  GMAIL_APP_PASSWORD = 16 字元 App Password           （非 Gmail 密碼）
  GMAIL_FROM_NAME    = onlineReport 線上腦波分析系統   （顯示寄件人；可選）

App Password 取得：
  https://myaccount.google.com/apppasswords
  （需先在 https://myaccount.google.com/security 開啟「兩步驟驗證」）

使用：
  from app.services.email_sender import send_report_email
  result = send_report_email(
      to="user@example.com",
      subject_name="陳小明",
      chapter_title="你的腦波 DNA",
      chapter_text="...",
  )
"""
from __future__ import annotations
import os
import re
import ssl
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587   # TLS


def _env(name: str, fallback: str = "") -> str:
    return (os.environ.get(name) or getattr(settings, name, "") or fallback).strip()


def _user() -> str:
    return _env("GMAIL_USER")


def _app_password() -> str:
    """16-char App Password；Gmail 帳號密碼不行"""
    raw = _env("GMAIL_APP_PASSWORD")
    # 去掉空白（很多人會貼成 "abcd efgh ijkl mnop"）
    return raw.replace(" ", "")


def _from_name() -> str:
    return _env("GMAIL_FROM_NAME", "onlineReport 線上腦波分析系統")


def is_configured() -> bool:
    return bool(_user()) and bool(_app_password())


def _valid_email(addr: str) -> bool:
    if not addr or not isinstance(addr, str):
        return False
    return bool(re.match(r"^[\w\.\-\+]+@[\w\-]+\.[\w\-\.]+$", addr.strip()))


# ─────────────────────────────────────────────────────────────────────
# 底層 SMTP 寄信
# ─────────────────────────────────────────────────────────────────────
def send_email(
    to: str,
    subject: str,
    html: str,
    plain_text: Optional[str] = None,
) -> dict:
    """
    寄一封 HTML email。回傳:
      {"ok": True,  "from": "...", "to": "..."}
      {"ok": False, "error": "...", "from": "...", "to": "..."}
    """
    if not _valid_email(to):
        return {"ok": False, "error": f"無效的收件地址: {to!r}"}

    user = _user()
    pwd  = _app_password()
    if not user or not pwd:
        return {"ok": False, "error": "GMAIL_USER 或 GMAIL_APP_PASSWORD 尚未設定（請至 Railway Variables）"}

    sender_addr = formataddr((str(Header(_from_name(), "utf-8")), user))

    # multipart/alternative 同時帶 plain + html
    msg = MIMEMultipart("alternative")
    msg["Subject"] = str(Header(subject, "utf-8"))
    msg["From"]    = sender_addr
    msg["To"]      = to.strip()

    if plain_text:
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=25) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(user, pwd)
            smtp.send_message(msg)
        return {"ok": True, "from": user, "to": to}
    except smtplib.SMTPAuthenticationError as e:
        return {"ok": False, "error": f"Gmail 認證失敗（請確認用 App Password，不是 Gmail 密碼）: {e}", "from": user, "to": to}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "from": user, "to": to}


# ─────────────────────────────────────────────────────────────────────
# 高階：寄報告 email
# ─────────────────────────────────────────────────────────────────────
def _text_to_html_paragraphs(text: str) -> str:
    """純文字 → <p> 段落（空行斷段，單行換 <br>）"""
    if not text:
        return ""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paras)


def send_report_email(
    to: str,
    subject_name: str,
    chapter_title: str,
    chapter_text: str,
    chapter_icon: str = "📄",
    report_url: Optional[str] = None,
    section_title: Optional[str] = None,
) -> dict:
    """寄送一章/一節 AI 報告到受測者 Email"""
    subject_line = f"📄 您的腦波分析報告：{chapter_title} - onlineReport"

    section_html = (
        f'<div style="font-size:13px;color:#7d8aa8;margin-top:6px;">{section_title}</div>'
        if section_title else ""
    )

    body_html_inner = _text_to_html_paragraphs(chapter_text)

    cta_html = (
        f'<div style="text-align:center;margin-top:32px;">'
        f'<a href="{report_url}" style="display:inline-block;padding:14px 32px;'
        f'background:#4a90e2;color:white;text-decoration:none;'
        f'border-radius:10px;font-weight:600;font-size:15px;">查看完整線上報告 →</a>'
        f'</div>'
        if report_url else ""
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{subject_line}</title>
</head>
<body style="margin:0;padding:0;background:#f5f7fa;font-family:'PingFang TC','Microsoft JhengHei','Helvetica Neue',sans-serif;color:#333;">
  <div style="max-width:680px;margin:0 auto;background:white;">
    <div style="background:linear-gradient(135deg,#2D3561,#4a90e2);padding:36px 32px;color:white;">
      <div style="font-size:13px;opacity:0.85;letter-spacing:2px;">onlineReport · 線上腦波分析系統</div>
      <div style="font-size:24px;font-weight:700;margin-top:12px;line-height:1.4;">{subject_name} 的腦波分析報告</div>
      <div style="font-size:15px;opacity:0.95;margin-top:10px;">{chapter_icon} {chapter_title}</div>
      {section_html}
    </div>
    <div style="padding:36px 32px;font-size:15px;line-height:1.95;color:#222;">
      {body_html_inner}
      {cta_html}
    </div>
    <div style="background:#f5f7fa;padding:24px 32px;text-align:center;color:#888;font-size:12px;line-height:1.6;border-top:1px solid #eee;">
      此 Email 由 onlineReport 線上腦波分析系統自動寄發<br>
      若您並未進行腦波檢測，請忽略此封信件
    </div>
  </div>
</body>
</html>"""

    result = send_email(
        to=to,
        subject=subject_line,
        html=html,
        plain_text=f"{subject_name} 的腦波分析報告\n\n{chapter_icon} {chapter_title}\n\n{chapter_text}",
    )
    if result.get("ok"):
        logger.info("✅ Gmail 寄發成功: to=%s, from=%s", to, result.get("from"))
    else:
        logger.error("❌ Gmail 寄發失敗: %s", result.get("error"))
    return result
