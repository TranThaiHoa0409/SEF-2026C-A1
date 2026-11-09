"""Tạo file PDF báo cáo bằng ReportLab."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Mô phỏng lỗi tạo PDF (Admin bật/tắt khi demo).
pdf_engine = {"failing": False}


class PdfError(Exception):
    pass


def build(path: Path, name: str, period_text: str, generated_at: str, owner: str, rows: list[tuple[str, str]]) -> None:
    """rows: (tên KPI, giá trị đã định dạng). Chỉ gồm KPI có dữ liệu."""
    if pdf_engine["failing"]:
        raise PdfError("The PDF engine is not responding (simulated).")
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4, title=name, author="BizBoard",
                            leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    table = Table([("KPI", "Value")] + rows, colWidths=[95 * mm, 60 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f6f4a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dde2de")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f7f5")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story = [
        Paragraph("BizBoard report", styles["Normal"]),
        Paragraph(name, styles["Title"]),
        Paragraph(f"<b>Period:</b> {period_text}", styles["Normal"]),
        Paragraph(f"<b>Generated:</b> {generated_at}", styles["Normal"]),
        Paragraph(f"<b>Created by:</b> {owner}", styles["Normal"]),
        Spacer(1, 8 * mm),
        table,
        Spacer(1, 8 * mm),
        Paragraph("Values are a snapshot at the time of generation and do not change when data refreshes. "
                  "Only completed orders are counted.", styles["Italic"]),
    ]
    doc.build(story)
