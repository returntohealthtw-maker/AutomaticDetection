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
SMTP_PORT_TLS = 587   # STARTTLS
SMTP_PORT_SSL = 465   # SSL (Railway 常擋 587，這個比較通)


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
    last_err = None

    # 先試 465 SSL（Railway/某些雲商擋 587）
    for attempt_label, attempt_fn in (
        ("465_ssl", lambda: _send_via_ssl(msg, user, pwd, context)),
        ("587_tls", lambda: _send_via_tls(msg, user, pwd, context)),
    ):
        try:
            attempt_fn()
            return {"ok": True, "from": user, "to": to, "via": attempt_label}
        except smtplib.SMTPAuthenticationError as e:
            return {"ok": False, "error": f"Gmail 認證失敗（請確認用 App Password，不是 Gmail 密碼）: {e}", "from": user, "to": to, "via": attempt_label}
        except Exception as e:
            last_err = (attempt_label, e)
            logger.warning("SMTP %s 失敗：%s（嘗試下一個 port）", attempt_label, e)

    via, e = last_err if last_err else ("none", Exception("沒有可用 SMTP port"))
    return {"ok": False, "error": f"{type(e).__name__}: {e}", "from": user, "to": to, "via": via}


def _send_via_ssl(msg, user, pwd, context):
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT_SSL, context=context, timeout=25) as smtp:
        smtp.ehlo()
        smtp.login(user, pwd)
        smtp.send_message(msg)


def _send_via_tls(msg, user, pwd, context):
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT_TLS, timeout=25) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(user, pwd)
        smtp.send_message(msg)


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


def send_consultant_welcome_email(
    to: str,
    name: str,
    phone: str,
    initial_password: str,
    org_type: str = "",
    org: str = "",
    login_url: Optional[str] = None,
) -> dict:
    """
    寄發「新顧問帳號開通」歡迎信。
    內容包含：登入手機（帳號）、初始密碼、登入連結、密碼修改提示。
    """
    subject_line = "🎉 您的 onlineReport 顧問帳號已開通 - 請查收登入資訊"

    if not login_url:
        base = (os.environ.get("PUBLIC_BASE_URL", "") or
                os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")).rstrip("/")
        if base and not base.startswith("http"):
            base = "https://" + base
        login_url = (base + "/app") if base else ""

    # 不提供網頁登入連結，避免顧問誤從瀏覽器登入
    # 請顧問安裝 APP 後輸入帳號密碼登入
    cta_html = (
        '<div style="margin:28px 0 8px;padding:16px 20px;background:#e8f5e9;'
        'border-left:4px solid #43a047;border-radius:6px;font-size:13px;line-height:1.7;color:#2e7d32;">'
        '<b>📱 如何登入？</b><br>'
        '請安裝「路加腦波檢測系統」APP，並使用上方帳號與初始密碼登入。<br>'
        '如尚未安裝，請向管理員索取 APK 安裝檔。'
        '</div>'
    )

    org_info_html = ""
    if org_type or org:
        org_info_html = (
            f'<tr><td style="padding:8px 14px;color:#666;width:80px;">身份</td>'
            f'<td style="padding:8px 14px;font-weight:600;">{org_type or "-"}</td></tr>'
            f'<tr><td style="padding:8px 14px;color:#666;">單位</td>'
            f'<td style="padding:8px 14px;font-weight:600;">{org or "-"}</td></tr>'
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
      <div style="font-size:24px;font-weight:700;margin-top:12px;line-height:1.4;">{name} 您好，您的顧問帳號已開通 🎉</div>
      <div style="font-size:14px;opacity:0.95;margin-top:10px;">管理員已核准您的申請，以下為登入資訊</div>
    </div>
    <div style="padding:36px 32px;font-size:15px;line-height:1.85;color:#222;">
      <p>請使用以下資訊登入 onlineReport 顧問端：</p>
      <table style="width:100%;border-collapse:collapse;margin-top:12px;background:#f8fafd;border-radius:10px;overflow:hidden;font-size:14px;">
        <tr><td style="padding:8px 14px;color:#666;width:80px;">姓名</td>
            <td style="padding:8px 14px;font-weight:600;">{name}</td></tr>
        <tr><td style="padding:8px 14px;color:#666;">登入帳號</td>
            <td style="padding:8px 14px;font-weight:600;font-family:monospace;">{phone}</td></tr>
        <tr><td style="padding:8px 14px;color:#666;">初始密碼</td>
            <td style="padding:8px 14px;font-weight:700;color:#c62828;font-family:monospace;font-size:16px;">{initial_password}</td></tr>
        {org_info_html}
      </table>

      {cta_html}

      <div style="margin-top:24px;padding:16px 20px;background:#fff8e1;border-left:4px solid #ffb300;border-radius:6px;font-size:13px;line-height:1.7;color:#5d4037;">
        <b>⚠️ 安全提醒</b><br>
        為保護您的帳號安全，請於首次登入後立即至「<b>帳號設定 → 修改密碼</b>」變更為您自己的密碼。<br>
        請勿將初始密碼透露給他人，本系統不會主動詢問您的密碼。
      </div>

      <div style="margin-top:20px;font-size:13px;color:#666;line-height:1.7;">
        如有任何問題，請與管理員聯繫。<br>
        歡迎加入 onlineReport，期待與您一起為客戶提供專業的腦波分析服務！
      </div>
    </div>
    <div style="background:#f5f7fa;padding:24px 32px;text-align:center;color:#888;font-size:12px;line-height:1.6;border-top:1px solid #eee;">
      此 Email 由 onlineReport 線上腦波分析系統自動寄發<br>
      若您並未申請顧問帳號，請忽略此封信件
    </div>
  </div>
</body>
</html>"""

    plain = (
        f"{name} 您好：\n\n"
        f"管理員已核准您的 onlineReport 顧問帳號申請，以下為登入資訊：\n\n"
        f"  登入帳號（手機）：{phone}\n"
        f"  初始密碼：{initial_password}\n"
    )
    if org_type or org:
        plain += f"  身份：{org_type or '-'}\n  單位：{org or '-'}\n"
    plain += (
        "\n📱 如何登入？\n"
        "請安裝「路加腦波檢測系統」APP，並使用上方帳號與初始密碼登入。\n"
        "如尚未安裝，請向管理員索取 APK 安裝檔。\n"
        "\n⚠️ 安全提醒：請於首次登入後立即修改密碼。\n"
        "如有任何問題，請與管理員聯繫。\n\n"
        "— onlineReport 線上腦波分析系統"
    )

    # 1) 先試 Railway 直連 Gmail SMTP
    result = send_email(to=to, subject=subject_line, html=html, plain_text=plain)
    if result.get("ok"):
        logger.info("✅ 顧問歡迎信寄送成功（SMTP）→ %s", to)
        return result

    # 2) Railway 偶爾擋 SMTP（"Network is unreachable" 等）→ 改打 Vercel proxy 繞道
    logger.warning("⚠ SMTP 失敗 (%s)，改走 Vercel proxy raw", result.get("error"))
    proxy_result = send_via_vercel_proxy_raw(to=to, subject=subject_line, html=html)
    if proxy_result.get("ok"):
        logger.info("✅ 顧問歡迎信寄送成功（Vercel proxy）→ %s", to)
        return proxy_result

    logger.error(
        "❌ 顧問歡迎信兩種方式都失敗: smtp=%s, proxy=%s",
        result.get("error"), proxy_result.get("error"),
    )
    return {
        "ok":    False,
        "error": f"smtp: {result.get('error')}; proxy: {proxy_result.get('error')}",
        "to":    to,
    }


def _vercel_email_proxy() -> str:
    """指向其中一個已部署的 Vercel app 的 /api/sendEmail。
    Railway 擋了 outbound SMTP 時用 Vercel 代寄，因為 Vercel 沒擋。
    """
    return (os.environ.get("VERCEL_EMAIL_PROXY", "") or
            "https://brianwave-child.vercel.app").rstrip("/")


def send_via_vercel_proxy(to: str, name: str, pdf_url: str) -> dict:
    """走 Vercel /api/sendEmail（避開 Railway SMTP 封鎖）。
    Vercel app 已驗證可寄信，這裡只是當 HTTP proxy 用。
    """
    import httpx
    url = f"{_vercel_email_proxy()}/api/sendEmail"
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(url, json={"to": to, "name": name, "pdfUrl": pdf_url})
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    logger.info("✅ Vercel email proxy 寄發成功: %s", to)
                    return {"ok": True, "from": "vercel_proxy", "to": to, "via": "vercel_proxy"}
                else:
                    return {"ok": False, "error": data.get("error", "vercel_proxy unknown"), "to": to, "via": "vercel_proxy"}
            return {"ok": False, "error": f"vercel_proxy HTTP {r.status_code}: {r.text[:200]}", "to": to, "via": "vercel_proxy"}
    except Exception as e:
        return {"ok": False, "error": f"vercel_proxy {type(e).__name__}: {e}", "to": to, "via": "vercel_proxy"}


def send_via_vercel_proxy_raw(to: str, subject: str, html: str) -> dict:
    """走 Vercel /api/sendEmail 的 raw 模式，寄任意 HTML email。
    Railway 直連 Gmail SMTP 被擋（Network is unreachable）時繞道用。
    Vercel app 還是用同一個 Gmail SMTP 設定寄出，差別只是經由 Vercel 出站。
    """
    import httpx
    url = f"{_vercel_email_proxy()}/api/sendEmail"
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(url, json={
                "mode":    "raw",
                "to":      to,
                "subject": subject,
                "html":    html,
            })
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    logger.info("✅ Vercel email proxy（raw）寄發成功: %s, method=%s", to, data.get("method"))
                    return {"ok": True, "from": "vercel_proxy_raw", "to": to, "via": f"vercel_proxy_raw[{data.get('method','?')}]"}
                else:
                    return {"ok": False, "error": data.get("error", "vercel_proxy unknown"), "to": to, "via": "vercel_proxy_raw"}
            # 試著解析 JSON 錯誤，否則回原文
            try:
                err = r.json().get("error") or r.json().get("detail") or r.text[:200]
            except Exception:
                err = r.text[:200]
            return {"ok": False, "error": f"vercel_proxy_raw HTTP {r.status_code}: {err}", "to": to, "via": "vercel_proxy_raw"}
    except Exception as e:
        return {"ok": False, "error": f"vercel_proxy_raw {type(e).__name__}: {e}", "to": to, "via": "vercel_proxy_raw"}


def send_report_link_email(
    to: str,
    subject_name: str,
    report_title: str,
    pdf_url: str,
    expires_days: int = 7,
) -> dict:
    """
    寄一封「報告生成完成 + 下載連結」的 Email（不含全文，PDF 在 GCS）。

    傳送策略：
    1. 先用本地 Gmail SMTP（465 SSL → 587 TLS）
    2. 失敗時 fallback 到 Vercel proxy（避開 Railway 雲商擋 SMTP 的問題）
    """
    subject_line = f"📄 您的腦波分析報告已產生：{report_title} - onlineReport"

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
      <div style="font-size:16px;opacity:0.95;margin-top:10px;">✅ {report_title} 已產生</div>
    </div>
    <div style="padding:40px 32px;font-size:15px;line-height:1.8;color:#222;">
      <p>您好 {subject_name}：</p>
      <p>您的個人化腦波分析報告已完成，請點擊下方按鈕下載 PDF：</p>

      <div style="text-align:center;margin:32px 0;">
        <a href="{pdf_url}" style="display:inline-block;padding:16px 40px;
           background:#4a90e2;color:white;text-decoration:none;
           border-radius:10px;font-weight:600;font-size:16px;
           box-shadow:0 4px 12px rgba(74,144,226,0.3);">📥 下載報告 PDF</a>
      </div>

      <p style="font-size:13px;color:#888;text-align:center;">
        ⏰ 下載連結將於 <b>{expires_days} 天後</b>失效，請儘早下載保存
      </p>

      <div style="margin-top:32px;padding:18px 22px;background:#f5f7fa;border-radius:10px;font-size:13px;line-height:1.7;color:#555;">
        <b>📌 報告使用建議</b><br>
        本報告依您的腦波數據與 AI 分析生成，建議搭配專業諮詢使用，<br>
        報告內容僅供個人化參考，不作為任何醫療診斷依據。
      </div>
    </div>
    <div style="background:#f5f7fa;padding:24px 32px;text-align:center;color:#888;font-size:12px;line-height:1.6;border-top:1px solid #eee;">
      此 Email 由 onlineReport 線上腦波分析系統自動寄發<br>
      若您並未進行腦波檢測，請忽略此封信件
    </div>
  </div>
</body>
</html>"""

    plain = (
        f"{subject_name} 您好：\n\n"
        f"您的腦波分析報告「{report_title}」已產生。\n\n"
        f"下載連結（{expires_days} 天內有效）：\n{pdf_url}\n\n"
        f"— onlineReport 線上腦波分析系統"
    )
    result = send_email(to=to, subject=subject_line, html=html, plain_text=plain)
    if result.get("ok"):
        logger.info("✅ 報告連結 email 寄發成功（SMTP）→ %s", to)
        return result

    # SMTP 失敗 → fallback Vercel proxy
    logger.warning("⚠ SMTP 失敗 (%s)，改走 Vercel proxy", result.get("error"))
    proxy_result = send_via_vercel_proxy(to=to, name=subject_name, pdf_url=pdf_url)
    if proxy_result.get("ok"):
        logger.info("✅ 報告連結 email 寄發成功（Vercel proxy）→ %s", to)
        return proxy_result

    logger.error("❌ Email 兩種方式都失敗: smtp=%s, proxy=%s",
                 result.get("error"), proxy_result.get("error"))
    return {"ok": False, "error": f"smtp: {result.get('error')}; proxy: {proxy_result.get('error')}", "to": to}
