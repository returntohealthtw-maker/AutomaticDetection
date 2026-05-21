"""
報告 PDF 渲染器（reportlab，純伺服器端）

從 ai_report 的 results dict 渲染成 A4 PDF：
- 頁首：受測者姓名、報告標題、生成時間
- 章節：標題 + 各節文字
- 頁尾：頁碼

使用：
  from app.services.pdf_builder import render_report_pdf
  pdf_path = render_report_pdf(
      out_path="reports/abc.pdf",
      subject_name="陳小明",
      report_type="life_script",
      variant="trial",
      chapters_list=[{num,title,icon},...],
      results={"1_1": {chapter_num,section_num,section_title,text}, ...},
      brainwave_data={...},
  )
"""
from __future__ import annotations
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 報告類型 → 中文標題
REPORT_TITLES = {
    "life_script":  "腦波分析人生劇本",
    "child":        "兒童腦波天賦解碼",
    "parent_child": "親子腦波共振關係報告",
    "marital":      "夫妻腦波共振關係報告",
}

VARIANT_LABELS = {
    "trial": "體驗版",
    "full":  "完整版",
    "vip":   "VIP 版",
}


def _find_cjk_font() -> Optional[str]:
    """嘗試找一個可用的 CJK 字型路徑。
    Railway 容器內：/usr/share/fonts 等位置。
    Windows 本地：C:\\Windows\\Fonts。
    若都找不到，回 None（reportlab 會用 Helvetica，中文會顯示為方塊）。
    """
    candidates = [
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # 至少不會出錯（無中文）
        "C:\\Windows\\Fonts\\msjh.ttc",   # 微軟正黑體
        "C:\\Windows\\Fonts\\mingliu.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


_CJK_FONT_NAME = "ReportCJK"
_FONT_REGISTERED = False


def _ensure_font_registered():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        path = _find_cjk_font()
        if path:
            pdfmetrics.registerFont(TTFont(_CJK_FONT_NAME, path))
            logger.info("PDF 字型已註冊：%s", path)
        else:
            logger.warning("找不到 CJK 字型，中文可能顯示為方塊")
        _FONT_REGISTERED = True
    except Exception as e:
        logger.exception("註冊字型失敗：%s", e)


def render_report_pdf(
    out_path:       str,
    subject_name:   str,
    report_type:    str,
    variant:        str,
    chapters_list:  List[Dict],
    results:        Dict[str, Dict],
    brainwave_data: Optional[Dict] = None,
    subject_age:    Optional[int]  = None,
    subject_gender: Optional[str]  = None,
) -> str:
    """渲染並寫入 PDF，回傳 out_path"""
    _ensure_font_registered()

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    font_name = _CJK_FONT_NAME if _find_cjk_font() else "Helvetica"

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontName=font_name, fontSize=26, leading=32, alignment=TA_CENTER,
        textColor=colors.HexColor("#2D3561"),
        spaceAfter=8,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontName=font_name, fontSize=13, leading=18, alignment=TA_CENTER,
        textColor=colors.HexColor("#6b7a99"),
        spaceAfter=20,
    )
    meta_style = ParagraphStyle(
        "Meta", parent=styles["Normal"],
        fontName=font_name, fontSize=10.5, leading=15, alignment=TA_CENTER,
        textColor=colors.HexColor("#8a93a8"),
        spaceAfter=24,
    )
    chapter_title_style = ParagraphStyle(
        "ChapterTitle", parent=styles["Heading1"],
        fontName=font_name, fontSize=20, leading=26,
        textColor=colors.HexColor("#1a2540"),
        spaceBefore=24, spaceAfter=12,
    )
    section_title_style = ParagraphStyle(
        "SectionTitle", parent=styles["Heading2"],
        fontName=font_name, fontSize=14, leading=20,
        textColor=colors.HexColor("#3b4a6b"),
        spaceBefore=14, spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["BodyText"],
        fontName=font_name, fontSize=11, leading=18,
        textColor=colors.HexColor("#222"), alignment=TA_LEFT,
        spaceAfter=10,
    )

    story = []

    report_title = REPORTS_LABEL(report_type, variant)
    story.append(Paragraph(report_title, title_style))
    story.append(Paragraph(f"{subject_name} 的個人化腦波分析", subtitle_style))

    meta_bits = []
    if subject_age is not None:
        meta_bits.append(f"{subject_age} 歲")
    if subject_gender:
        meta_bits.append(subject_gender)
    meta_bits.append(datetime.now().strftime("%Y/%m/%d %H:%M"))
    story.append(Paragraph(" · ".join(meta_bits), meta_style))

    # 腦波摘要表
    bw = brainwave_data or {}
    ba = bw.get("bands_avg") or {}
    rows = [
        ["指標", "數值"],
        ["注意力 (Attention)",   f"{bw.get('attention_percentage', '--')}"],
        ["放鬆度 (Meditation)",  f"{bw.get('meditation_percentage', '--')}"],
    ]
    for k, label in (("delta","Delta"),("theta","Theta"),("alpha","Alpha"),("beta","Beta"),("gamma","Gamma")):
        if k in ba:
            try:
                rows.append([label, f"{float(ba[k]):.1f}"])
            except Exception:
                rows.append([label, str(ba[k])])
    if len(rows) > 1:
        t = Table(rows, colWidths=[80*mm, 60*mm])
        t.setStyle(TableStyle([
            ("FONT",       (0,0), (-1,-1), font_name, 10),
            ("BACKGROUND", (0,0), (-1,0),  colors.HexColor("#2D3561")),
            ("TEXTCOLOR",  (0,0), (-1,0),  colors.white),
            ("ALIGN",      (0,0), (-1,-1), "LEFT"),
            ("GRID",       (0,0), (-1,-1), 0.4, colors.HexColor("#dde3f0")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f5f7fa")]),
            ("LEFTPADDING",  (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING",   (0,0), (-1,-1), 6),
            ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 18))

    story.append(PageBreak())

    # 章節
    for chapter in chapters_list:
        ch_num   = chapter.get("num")
        ch_title = chapter.get("title", "")
        ch_icon  = chapter.get("icon", "")
        story.append(Paragraph(f"第 {ch_num} 章　{ch_icon} {_esc(ch_title)}", chapter_title_style))

        section_keys = [k for k in results.keys() if results[k].get("chapter_num") == ch_num]
        section_keys.sort(key=lambda k: results[k].get("section_num", 0))
        for key in section_keys:
            sec = results[key]
            sec_num   = sec.get("section_num", "")
            sec_title = sec.get("section_title", "")
            text      = sec.get("text", "")
            story.append(Paragraph(f"第 {sec_num} 節　{_esc(sec_title)}", section_title_style))
            for para in (text or "").split("\n\n"):
                p = _esc(para.replace("\n", "<br/>"))
                if p.strip():
                    story.append(Paragraph(p, body_style))
        story.append(PageBreak())

    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm,
        title=report_title, author="onlineReport",
    )

    def _on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont(font_name, 8)
        canvas.setFillColor(colors.HexColor("#8a93a8"))
        canvas.drawCentredString(A4[0]/2, 10*mm, f"onlineReport · {subject_name}　第 {doc.page} 頁")
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return out_path


def REPORTS_LABEL(report_type: str, variant: str) -> str:
    base = REPORT_TITLES.get(report_type, "腦波分析報告")
    v    = VARIANT_LABELS.get(variant, "")
    return f"{base}（{v}）" if v else base


def _esc(s: str) -> str:
    """reportlab Paragraph 用 HTML-like 標籤，需 escape & < >；換行 <br/> 保留。"""
    if s is None:
        return ""
    s = str(s)
    return (
        s.replace("&", "&amp;")
         .replace("<br/>", "\u0001BR\u0001")  # 暫存
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace("\u0001BR\u0001", "<br/>")
    )
