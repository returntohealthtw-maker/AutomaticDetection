"""
報告生成引擎
流程：讀取腦波數據 → 計算演算法 → 儲存結果 → 生成 PDF → 傳送 LINE／Email
"""
import os
import json
import time
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from sqlalchemy.orm import Session as DbSession
from app.core.database import SessionLocal
from app.core import models
from app.core.config import settings
from app.services.algorithms import compute_averages, compute_all_indices, compute_mbti


def _clip_zh(text: str, max_len: int = 100) -> str:
    t = (text or "").replace("\n", "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _pct(indices: dict, key: str, default: float = 50.0) -> float:
    if key not in indices:
        return default
    try:
        return float(indices[key].get("pct", default))
    except (TypeError, ValueError):
        return default


def _resolve_talent_kind(session) -> str:
    """對應「報告範本」四種：child_teacher / child_student / teen_teacher / teen_student"""
    age = int(session.subject_age or 0)
    aud = (getattr(session, "report_audience", None) or "student").lower()
    is_teacher = aud == "teacher"
    if age <= 12:
        return "child_teacher" if is_teacher else "child_student"
    return "teen_teacher" if is_teacher else "teen_student"


def _talent_pdf_title(session) -> str:
    k = _resolve_talent_kind(session)
    titles = {
        "child_teacher":  "兒童天賦報告教師版",
        "child_student":  "兒童天賦報告學生版（3～12歲）",
        "teen_teacher":   "青少年天賦報告教師版",
        "teen_student":   "青少年天賦報告學生版（13～18歲）",
    }
    return titles.get(k, "腦波天賦分析報告")


def _build_client_summaries(session, indices: dict, mbti: dict, avg) -> dict:
    """
    客戶掃描 QR 後顯示的五段文字（各約 100 字）。
    內容由指標與 MBTI 自動生成，可再串接語言模型或人工校稿流程。
    """
    name = session.subject_name or "受測者"
    age = int(session.subject_age or 0)
    mbti_type = mbti.get("mbti_type", "—")
    conf = int(mbti.get("confidence", 0) or 0)
    srr = _pct(indices, "SRR")
    emo = _pct(indices, "EMO")
    foc = _pct(indices, "FOC")
    cre = _pct(indices, "CRE")
    soc = _pct(indices, "SOC")
    res = _pct(indices, "RES")
    ei = _pct(indices, "EI")

    family = (
        f"「{name}」目前{age}歲，從腦波情緒整合度（EMO {emo:.0f}%）與恢復指數（SRR {srr:.0f}%）觀察，"
        f"家庭互動模式可能偏向「{'高敏感需求' if emo > 55 else '穩定支持'}」。"
        f"建議照顧者以一致、可預測的作息與清楚的情感回應，降低不確定感；"
        f"若 MBTI 推估為 {mbti_type}（信心 {conf}%），可搭配其偏好溝通節奏，避免過度催促造成防衛。"
    )

    personality = (
        f"在性格張力上，外向／內向傾向指標（EI {ei:.0f}%）與社交指標（SOC {soc:.0f}%）顯示"
        f"「{'外顯行動與人際期待' if ei > 52 else '內在評估與獨處需求'}」可能形成落差。"
        f"地雷情境常出現在{'被否定感受' if emo > 58 else '被過度干預'}時；"
        f"可練習先同理再引導，並給予可選擇的步驟，降低對立。"
    )

    stress = (
        f"現階段壓力反應可從恢復指數（SRR {srr:.0f}%）與專注穩定（FOC {foc:.0f}%）綜合判讀："
        f"{'生理與心理恢復節奏偏緊繃，需預留緩衝時間' if srr < 48 else '整體尚可，但需留意突發負荷'}。"
        f"建議以規律睡眠、短暫離題活動與呼吸練習調節；課業或同儕壓力宜分段處理，避免長時間高警覺狀態。"
    )

    talent = (
        f"天賦主軸可參考創造與覺察指標（CRE {cre:.0f}%）與情緒整合（EMO {emo:.0f}%）："
        f"學習上適合「{'探索式、專題式' if cre > 52 else '結構化、步驟清楚'}」的任務設計。"
        f"腦波整體顯示 {mbti_type} 類型在{'概念連結' if cre > 50 else '執行與回饋'}面向具優勢，可朝能發揮自主性的領域配置資源。"
    )

    career = (
        f"就學科與未來職涯路徑，建議優先強化「{'人文社會與創意' if cre > 54 else '邏輯與操作'}」與「{'團隊協作' if soc > 52 else '獨立完成'}」的平衡。"
        f"可選擇能累積小勝利的專案制學習；工作上適合{'顧問、教學、企劃' if soc > 55 else '分析、技術、研發'}等角色，並定期檢視壓力恢復（RES {res:.0f}%）以維持長期投入。"
    )

    return {
        "family":       _clip_zh(family),
        "personality":  _clip_zh(personality),
        "stress":       _clip_zh(stress),
        "talent":       _clip_zh(talent),
        "career":       _clip_zh(career),
    }


async def generate_report_async(report_id: int, session_id: int):
    """
    背景報告生成主流程（由 FastAPI BackgroundTasks 呼叫）
    """
    db = SessionLocal()
    try:
        # 更新狀態為處理中
        report = db.query(models.Report).filter(
            models.Report.report_id == report_id
        ).first()
        if not report:
            return
        report.status = "processing"
        db.commit()

        # 1. 讀取腦波數據
        captures = db.query(models.EegCapture).filter(
            models.EegCapture.session_id == session_id
        ).order_by(models.EegCapture.seq_num).all()

        detection_captures = [
            {
                "good_signal": c.good_signal,
                "attention":   c.attention,
                "meditation":  c.meditation,
                "delta":       c.delta,
                "theta":       c.theta,
                "low_alpha":   c.low_alpha,
                "high_alpha":  c.high_alpha,
                "low_beta":    c.low_beta,
                "high_beta":   c.high_beta,
                "low_gamma":   c.low_gamma,
                "high_gamma":  c.high_gamma,
            }
            for c in captures if c.is_baseline == 0
        ]

        if not detection_captures:
            detection_captures = [
                {k: getattr(c, k) for k in [
                    "good_signal","attention","meditation","delta","theta",
                    "low_alpha","high_alpha","low_beta","high_beta","low_gamma","high_gamma"
                ]} for c in captures
            ]

        # 2. 計算頻帶平均值
        avg = compute_averages(detection_captures)

        # 3. 計算 30 個指標
        indices = compute_all_indices(avg)

        # 4. 計算 MBTI
        mbti = compute_mbti(avg)

        # 5. 儲存計算結果到資料庫
        index_objects = [
            models.ReportIndex(
                report_id   = report_id,
                index_name  = name,
                index_value = round(data["value"], 4),
                index_pct   = data["pct"],
                category    = data["category"]
            )
            for name, data in indices.items()
        ]
        db.bulk_save_objects(index_objects)
        db.commit()

        session_obj = db.query(models.Session).filter(
            models.Session.session_id == session_id
        ).first()

        summaries = _build_client_summaries(session_obj, indices, mbti, avg)
        report.client_summary = json.dumps(summaries, ensure_ascii=False)
        report.talent_report_kind = _resolve_talent_kind(session_obj)
        db.commit()

        # 6. 生成 PDF
        pdf_path = await _generate_pdf(
            session  = session_obj,
            indices  = indices,
            mbti     = mbti,
            avg      = avg
        )

        # 7. 上傳到 GCS（或本地）
        pdf_url = await _upload_pdf(pdf_path, report_id)

        # 8. 更新報告狀態
        report.status       = "completed"
        report.pdf_url      = pdf_url
        report.completed_at = None  # SQLAlchemy 會用 server default
        db.commit()

        # 9. 傳送 LINE 通知
        if report.line_user_id:
            base = (settings.PUBLIC_APP_BASE_URL or "").rstrip("/")
            client_link = (
                f"{base}/api/v1/public/client/{report.qr_token}"
                if base and report.qr_token
                else ""
            )
            await _send_line_message(
                user_id  = report.line_user_id,
                name     = session_obj.subject_name,
                pdf_url  = pdf_url,
                mbti     = mbti["mbti_type"],
                client_url = client_link,
            )
            report.line_sent = 1
            db.commit()

        # 10. Email 傳送報告連結（若設定 SMTP）
        if report.notify_email:
            base = (settings.PUBLIC_APP_BASE_URL or "").rstrip("/")
            client_link = (
                f"{base}/api/v1/public/client/{report.qr_token}"
                if base and report.qr_token
                else ""
            )
            ok = await _send_report_email(
                to_addr   = report.notify_email,
                subject   = f"【天賦檢測】{session_obj.subject_name or ''} 報告已產生",
                pdf_url   = pdf_url,
                extra_link = client_link,
            )
            if ok:
                report.email_sent = 1
                db.commit()

        print(f"[OK] Report {report_id} done: {pdf_url}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] Report {report_id} failed: {e}")
        rep = db.query(models.Report).filter(models.Report.report_id == report_id).first()
        if rep:
            rep.status = "failed"
            db.commit()
    finally:
        db.close()


async def _generate_pdf(session, indices: dict, mbti: dict, avg) -> str:
    """生成 PDF 報告（使用 ReportLab）"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os

    os.makedirs("reports", exist_ok=True)
    pdf_path = f"reports/report_{session.session_id}_{int(time.time())}.pdf"

    doc  = SimpleDocTemplate(pdf_path, pagesize=A4,
                              leftMargin=2*cm, rightMargin=2*cm,
                              topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=18, spaceAfter=12)
    h2_style    = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, spaceAfter=6)
    body_style  = styles["Normal"]

    # 標題（18 歲以下：教育機構天賦報告四版型；其餘沿用原成人／兒童命名）
    if (session.subject_age or 0) <= 18:
        report_title = _talent_pdf_title(session)
    else:
        report_title = "成人腦波深度報告" if session.report_type == "adult" else "兒童腦波分析報告"
    story.append(Paragraph(report_title, title_style))
    story.append(Spacer(1, 0.3*cm))

    # 受測者資訊
    story.append(Paragraph("受測者資訊", h2_style))
    info_data = [
        ["姓名", session.subject_name or "—",
         "性別", "男" if session.subject_gender == "M" else "女"],
        ["生日", session.subject_birthday or "—",
         "報告類型", report_title],
        ["MBTI 類型", mbti["mbti_type"],
         "信心指數", f"{mbti['confidence']}%"],
    ]
    info_table = Table(info_data, colWidths=[3*cm, 5*cm, 3*cm, 5*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F5F5F5")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("PADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    # 頻帶基本數值
    story.append(Paragraph("腦波頻帶分析", h2_style))
    band_data = [
        ["頻帶", "平均功率", "說明"],
        ["θ Theta（直覺）", f"{avg.theta:.0f}", "直覺力、潛意識連結"],
        ["α↑ High Alpha（氣血）", f"{avg.high_alpha:.0f}", "生命活力、氣血能量"],
        ["α↓ Low Alpha（安定）", f"{avg.low_alpha:.0f}", "內在安定感、靜心"],
        ["β↓ Low Beta（邏輯）", f"{avg.low_beta:.0f}", "邏輯分析、理性思考"],
        ["β↑ High Beta（執行）", f"{avg.high_beta:.0f}", "執行力、專注警覺"],
        ["γ↓ Low Gamma（慈悲）", f"{avg.low_gamma:.0f}", "慈悲心、情感連結"],
        ["γ↑ High Gamma（觀察）", f"{avg.high_gamma:.0f}", "環境觀察力、感知細節"],
    ]
    band_table = Table(band_data, colWidths=[5*cm, 3*cm, 8*cm])
    band_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2E86AB")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("PADDING", (0,0), (-1,-1), 5),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F0F8FF")]),
    ]))
    story.append(band_table)
    story.append(Spacer(1, 0.5*cm))

    # 30 個指標按類別分組
    categories = {
        "cognitive":   "認知能力",
        "stress":      "壓力與放鬆",
        "emotional":   "情緒與性格",
        "social":      "人際互動",
        "leadership":  "領導力",
    }
    for cat_key, cat_label in categories.items():
        cat_indices = {k: v for k, v in indices.items() if v["category"] == cat_key}
        if not cat_indices:
            continue

        story.append(Paragraph(cat_label, h2_style))
        rows = [["指標", "名稱", "數值", "百分比"]]
        for name, data in cat_indices.items():
            rows.append([name, data["label"],
                         f"{data['value']:.3f}", f"{data['pct']}%"])

        table = Table(rows, colWidths=[2.5*cm, 6*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#4CAF50")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("PADDING", (0,0), (-1,-1), 5),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FBF9")]),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3*cm))

    doc.build(story)
    return pdf_path


async def _upload_pdf(pdf_path: str, report_id: int) -> str:
    """
    上傳 PDF 到 GCS（若未設定 GCS，使用本地路徑）
    """
    if not settings.GCS_BUCKET_NAME:
        # 本地開發模式：直接回傳本地路徑
        base_url = settings.REPORT_BASE_URL
        filename = os.path.basename(pdf_path)
        return f"{base_url}/{filename}"

    try:
        from google.cloud import storage
        client  = storage.Client(project=settings.GCS_PROJECT_ID)
        bucket  = client.bucket(settings.GCS_BUCKET_NAME)
        blob    = bucket.blob(f"reports/{os.path.basename(pdf_path)}")
        blob.upload_from_filename(pdf_path)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"[WARN] GCS upload failed, using local: {e}")
        return f"{settings.REPORT_BASE_URL}/{os.path.basename(pdf_path)}"


async def _send_line_message(
    user_id: str, name: str, pdf_url: str, mbti: str, client_url: str = ""
):
    """透過 LINE Messaging API 傳送報告連結"""
    if not settings.LINE_CHANNEL_ACCESS_TOKEN:
        print(f"LINE Token 未設定，跳過傳送（{user_id}）")
        return

    message = {
        "to": user_id,
        "messages": [{
            "type": "flex",
            "altText": f"【腦波報告完成】{name} 的報告已產生",
            "contents": {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [{
                        "type": "text",
                        "text": "🧠 腦波報告完成",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#ffffff"
                    }],
                    "backgroundColor": "#2E86AB"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": f"受測者：{name}", "size": "md"},
                        {"type": "text", "text": f"MBTI 類型：{mbti}", "size": "md", "color": "#2E86AB", "weight": "bold"},
                        {"type": "text", "text": "您的腦波分析報告已產生，點下方按鈕查看", "size": "sm", "color": "#888888", "wrap": True}
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                        "type": "button",
                        "style": "primary",
                        "color": "#2E86AB",
                        "action": {"type": "uri", "label": "查看報告 PDF", "uri": pdf_url}
                        },
                    ] + ([{
                        "type": "button",
                        "style": "secondary",
                        "color": "#00BCD4",
                        "action": {"type": "uri", "label": "客戶五段摘要", "uri": client_url}
                    }] if client_url else [])
                }
            }
        }]
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.line.me/v2/bot/message/push",
            json=message,
            headers={
                "Authorization": f"Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        if resp.status_code == 200:
            print(f"[OK] LINE sent to {user_id}")
        else:
            print(f"[ERROR] LINE failed: {resp.text}")


async def _send_report_email(
    to_addr: str, subject: str, pdf_url: str, extra_link: str = ""
) -> bool:
    """SMTP 寄送報告 PDF 連結，並可附客戶摘要頁連結。"""
    if not settings.SMTP_HOST or not settings.SMTP_FROM:
        print("[Email] SMTP 未設定，略過寄信")
        return False
    body = f"""您好，

您的天賦檢測報告已產生。

📄 PDF 報告：{pdf_url}
"""
    if extra_link:
        body += f"\n📱 客戶摘要頁（五段重點）：{extra_link}\n"
    body += "\n此信為系統自動發送，請勿直接回覆。\n"

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_addr
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        ctx = ssl.create_default_context()
        port = int(settings.SMTP_PORT or 587)
        if port == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, port, context=ctx, timeout=20) as server:
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, [to_addr], msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, port, timeout=20) as server:
                server.ehlo()
                server.starttls(context=ctx)
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, [to_addr], msg.as_string())
        print(f"[OK] Email sent to {to_addr}")
        return True
    except Exception as e:
        print(f"[ERROR] Email failed: {e}")
        return False
