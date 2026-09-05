"""Server-side assessment discussion-PDF generation.

Reports deliberately include only stored metadata. Uploaded source images and
visual overlays are not retained by DermaMatrix and are never reconstructed.
"""

from __future__ import annotations

import io
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _text(value: object, fallback: str = "Not available") -> str:
    value = str(value).strip() if value is not None else ""
    return escape(value or fallback)


def _bullets(values: list[object] | None) -> str:
    safe_values = [_text(value) for value in values or [] if str(value).strip()]
    return "<br/>".join(f"• {value}" for value in safe_values) or "Not available"


def build_assessment_report_pdf(*, account: dict, assessment: dict) -> bytes:
    """Create a concise, printable discussion brief from one stored assessment."""
    summary = assessment.get("summary") or {}
    screening = summary.get("screening") or {}
    risk = summary.get("risk") or {}
    pirs = summary.get("pirs") or {}
    quality = summary.get("quality") or {}
    classification = summary.get("classification") or {}
    segmentation = summary.get("segmentation") or {}
    recommendations = summary.get("recommendations") or {}
    care_plan = summary.get("care_plan") or {}

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="DermaMatrix AI screening discussion brief",
        author="DermaMatrix AI",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("DermaTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=colors.HexColor("#123A68"), alignment=TA_LEFT, spaceAfter=3 * mm)
    eyebrow = ParagraphStyle("DermaEyebrow", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=colors.HexColor("#3178C6"), spaceAfter=3 * mm)
    heading = ParagraphStyle("DermaHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#173B63"), spaceBefore=5 * mm, spaceAfter=2.4 * mm)
    body = ParagraphStyle("DermaBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=13, textColor=colors.HexColor("#34495E"))
    note = ParagraphStyle("DermaNote", parent=body, fontSize=8, leading=11, textColor=colors.HexColor("#5C6E80"))

    created_at = str(assessment.get("created_at", ""))[:19].replace("T", " ")
    risk_value = f"{_text(risk.get('score'), '—')}/100 · {_text(risk.get('level'), 'UNCERTAIN')}"
    pirs_value = f"{_text(pirs.get('score'), '—')}/100 · {_text(pirs.get('band'), 'UNCERTAIN')}"
    prediction = classification.get("top_prediction") or {}
    classification_value = _text(prediction.get("condition"), "No scoped disease classification was run") if classification.get("available") else "No scoped disease classification was run"
    confidence = prediction.get("confidence") or classification.get("model_confidence")
    if confidence is not None and classification.get("available"):
        classification_value += f"<br/><font color='#5C6E80'>Research-model output confidence: {_text(round(float(confidence) * 100))}% (not medical certainty)</font>"

    rows = [
        [Paragraph("Assessment ID", eyebrow), Paragraph(_text(assessment.get("assessment_id")), body)],
        [Paragraph("Assessment date", eyebrow), Paragraph(_text(created_at), body)],
        [Paragraph("Area and input", eyebrow), Paragraph(f"{_text(assessment.get('area'))} · {_text(summary.get('input_type'))}", body)],
        [Paragraph("Reported-concern priority", eyebrow), Paragraph(risk_value, body)],
        [Paragraph("PIRS record", eyebrow), Paragraph(pirs_value, body)],
        [Paragraph("Image / input readiness", eyebrow), Paragraph(_text(quality.get("label")), body)],
        [Paragraph("Account", eyebrow), Paragraph(_text(account.get("full_name")), body)],
    ]
    table = Table(rows, colWidths=[50 * mm, 120 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF6FF")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E6F4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story = [
        Paragraph("DERMAMATRIX AI", eyebrow),
        Paragraph("Screening discussion brief", title),
        Paragraph("Generated from locally stored assessment metadata. Uploaded images and visual overlays are not retained in this prototype.", note),
        Spacer(1, 4 * mm),
        table,
        Paragraph("Screening summary", heading),
        Paragraph(_text(screening.get("title")), body),
        Spacer(1, 1.5 * mm),
        Paragraph(_text(screening.get("summary")), body),
        Paragraph("Model and explanation scope", heading),
        Paragraph(f"<b>Classification:</b> {classification_value}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Segmentation:</b> {_text(segmentation.get('status'), 'Not run')}. {_text(segmentation.get('notice'), '')}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(_text((summary.get("explainability") or {}).get("notice"), "No additional explainability artifact was retained."), note),
        Paragraph("General guidance for discussion", heading),
        Paragraph(f"<b>Next step:</b> {_text(care_plan.get('next_step'))}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Routine:</b><br/>{_bullets((recommendations.get('routine') or {}).get('morning'))}<br/>{_bullets((recommendations.get('routine') or {}).get('evening'))}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Wellbeing:</b><br/>{_bullets(recommendations.get('diet'))}", body),
        Paragraph("Important safety notice", heading),
        Paragraph("This educational college-project prototype is not a medical device. It does not diagnose disease, prescribe medicine, or replace a registered medical practitioner. Discuss new routines, products, supplements, symptoms, and treatment decisions with a qualified clinician or pharmacist.", body),
    ]
    document.build(story)
    return buffer.getvalue()
