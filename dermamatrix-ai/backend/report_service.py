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
    likelihood = prediction.get("calibrated_probability")
    calibration = classification.get("calibration") or {}
    uncertainty = classification.get("uncertainty") or {}
    if likelihood is not None and classification.get("available"):
        classification_value += f"<br/><font color='#5C6E80'>Estimated likelihood: {_text(round(float(likelihood) * 100))}% · calibration: {_text(calibration.get('calibration_version'))} · certainty: {_text(uncertainty.get('certainty'))}</font>"
    elif classification.get("available"):
        classification_value += "<br/><font color='#5C6E80'>Research ranking only. Calibration artifact unavailable, so no condition likelihood is shown.</font>"

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
        Paragraph(_text((summary.get("explainability") or {}).get("notice") or (classification.get("explainability") or {}).get("explanation_text"), "No additional explainability artifact was retained."), note),
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


def build_history_report_pdf(*, account: dict, analyses: list[dict], routines: list[dict], checkins: list[dict]) -> bytes:
    """Create one account-scoped, metadata-only history PDF.

    This is intentionally a history export, not a longitudinal diagnostic or
    healing report. It records what the person entered and what the prototype
    stored; it never claims to monitor someone between check-ins.
    """
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="DermaMatrix AI personal history export",
        author="DermaMatrix AI",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("HistoryTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=colors.HexColor("#123A68"), alignment=TA_LEFT, spaceAfter=3 * mm)
    eyebrow = ParagraphStyle("HistoryEyebrow", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=colors.HexColor("#3178C6"), spaceAfter=3 * mm)
    heading = ParagraphStyle("HistoryHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#173B63"), spaceBefore=5 * mm, spaceAfter=2.4 * mm)
    body = ParagraphStyle("HistoryBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.5, leading=12, textColor=colors.HexColor("#34495E"))
    note = ParagraphStyle("HistoryNote", parent=body, fontSize=7.8, leading=10.5, textColor=colors.HexColor("#5C6E80"))

    profile_rows = [
        [Paragraph("Account", eyebrow), Paragraph(_text(account.get("full_name")), body)],
        [Paragraph("Patient ID", eyebrow), Paragraph(_text(account.get("patient_id")), body)],
        [Paragraph("Email", eyebrow), Paragraph(_text(account.get("email_address")), body)],
        [Paragraph("Past history", eyebrow), Paragraph(_text(account.get("past_history")), body)],
        [Paragraph("Current history", eyebrow), Paragraph(_text(account.get("current_history")), body)],
    ]
    profile_table = Table(profile_rows, colWidths=[43 * mm, 127 * mm], hAlign="LEFT")
    profile_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF6FF")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E6F4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    def compact_table(headers: list[str], rows: list[list[str]], widths: list[float]) -> Table:
        cells = [[Paragraph(_text(header), eyebrow) for header in headers]]
        cells.extend([[Paragraph(_text(value), body) for value in row] for row in rows] or [[Paragraph("No saved records", body)] + [Paragraph("", body) for _ in headers[1:]]])
        table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF6FF")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E6F4")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return table

    analysis_rows = []
    for analysis in analyses[:50]:
        summary = analysis.get("summary") or {}
        risk = summary.get("risk") or {}
        classifier = summary.get("classification") or summary.get("research_classifier") or {}
        prediction = classifier.get("top_prediction") or {}
        scope = prediction.get("condition") if classifier.get("available") else "Screening summary only"
        analysis_rows.append([
            str(analysis.get("created_at", ""))[:10],
            str(analysis.get("area", "")),
            str(scope),
            f"{risk.get('score', '—')}/100 · {risk.get('level', 'UNCERTAIN')}",
        ])

    routine_rows = [[str(item.get("condition_label", "")), str(item.get("routine_name", "")), str(item.get("start_date", "")), f"{item.get('checkin_count', 0)} check-ins"] for item in routines[:50]]
    checkin_rows = [[str(item.get("checkin_date", "")), str(item.get("condition_label", "")), str(item.get("reported_trend", "")), f"{item.get('priority_score', '—')}/100"] for item in checkins[:100]]

    story = [
        Paragraph("DERMAMATRIX AI", eyebrow),
        Paragraph("Personal history export", title),
        Paragraph("This export contains account-scoped metadata. Uploaded photos, visual overlays, and any passive monitoring data are not retained by this prototype.", note),
        Spacer(1, 4 * mm),
        profile_table,
        Paragraph("Saved screening summaries", heading),
        Paragraph("Reported-concern priority is not disease risk. A screening summary is not a confirmed diagnosis.", note),
        Spacer(1, 1.5 * mm),
        compact_table(["Date", "Area", "Result scope", "Priority"], analysis_rows, [25 * mm, 24 * mm, 77 * mm, 44 * mm]),
        Paragraph("Routines", heading),
        compact_table(["Problem recorded", "Routine", "Started", "Tracking"], routine_rows, [47 * mm, 65 * mm, 28 * mm, 30 * mm]),
        Paragraph("Check-in timeline", heading),
        Paragraph("Check-ins are self-reported entries. They do not prove healing, treatment effectiveness, or absence of disease.", note),
        Spacer(1, 1.5 * mm),
        compact_table(["Date", "Routine", "Reported trend", "Priority"], checkin_rows, [28 * mm, 64 * mm, 43 * mm, 35 * mm]),
        Paragraph("Important safety notice", heading),
        Paragraph("This educational college-project prototype is not a medical device. It does not continuously observe a patient, diagnose disease, prescribe medicine, or replace a registered medical practitioner. Use this export to support a clinician conversation and seek timely care for severe, rapidly changing, or worrying symptoms.", body),
    ]
    document.build(story)
    return buffer.getvalue()
