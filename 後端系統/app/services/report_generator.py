"""
報告生成引擎
流程：讀取腦波數據 → 計算演算法 → 儲存結果 → 生成 PDF → 傳送 LINE
"""
import os
import time
import httpx
from sqlalchemy.orm import Session as DbSession
from app.core.database import SessionLocal
from app.core import models
from app.core.config import settings
from app.services.algorithms import compute_averages, compute_all_indices, compute_mbti


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

        # 6. 生成 PDF
        session_obj = db.query(models.Session).filter(
            models.Session.session_id == session_id
        ).first()

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
            await _send_line_message(
                user_id  = report.line_user_id,
                name     = session_obj.subject_name,
                pdf_url  = pdf_url,
                mbti     = mbti["mbti_type"]
            )
            report.line_sent = 1
            db.commit()

        print(f"[OK] Report {report_id} done: {pdf_url}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] Report {report_id} failed: {e}")
        if report:
            report.status = "failed"
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

    # 標題
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


async def _send_line_message(user_id: str, name: str, pdf_url: str, mbti: str):
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
                    "contents": [{
                        "type": "button",
                        "style": "primary",
                        "color": "#2E86AB",
                        "action": {"type": "uri", "label": "查看報告 PDF", "uri": pdf_url}
                    }]
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
