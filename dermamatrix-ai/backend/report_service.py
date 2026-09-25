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
    result = summary.get("assessment_result") or {}
    canonical = result.get("canonical_evidence") or summary.get("canonical_evidence") or {}
    screening = summary.get("screening") or {}
    risk = summary.get("risk") or {}
    pirs = canonical.get("pirs") if canonical else summary.get("pirs") or {}
    quality = canonical.get("image_quality") if canonical else summary.get("quality") or {}
    classification = summary.get("classification") or {}
    segmentation = summary.get("segmentation") or {}
    recommendations = summary.get("recommendations") or {}
    medication_information = summary.get("medication_information") or recommendations.get("medication_information") or {}
    care_plan = summary.get("care_plan") or {}
    severity = canonical.get("severity") if canonical else summary.get("severity") or {}
    cdss = summary.get("clinical_decision_support") or {}
    journey = summary.get("journey") or {}
    intelligence = summary.get("condition_intelligence") or {}
    finding = intelligence.get("finding") or {}
    care_pathway = intelligence.get("care_pathway") or {}
    follow_up = intelligence.get("follow_up") or {}
    doctor = intelligence.get("doctor") or {}

    result_condition = result.get("condition") or {}
    consumer = result.get("consumer") or {}
    consumer_primary = consumer.get("primary_result") or {}
    consumer_topic = consumer.get("condition_information") or {}
    result_status = result.get("status") or {}
    result_severity = result.get("severity") or {}
    result_risk = canonical.get("assessment_risk") or result.get("assessment_risk") or summary.get("assessment_risk") or {}
    result_priority = result.get("care_priority") or {}
    result_urgency = result.get("urgency") or {}
    result_input = result.get("input") or {}
    result_visual_evidence = result.get("visual_evidence") or summary.get("visual_evidence") or {}
    image_findings = canonical.get("image_findings") or result.get("image_findings") or summary.get("image_findings") or {}
    presentation_case = result.get("presentation") or summary.get("presentation_case") or {}

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
    heading = ParagraphStyle("DermaHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11.2, leading=13.5, textColor=colors.HexColor("#173B63"), spaceBefore=4 * mm, spaceAfter=2 * mm)
    body = ParagraphStyle("DermaBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=colors.HexColor("#34495E"))
    note = ParagraphStyle("DermaNote", parent=body, fontSize=7.8, leading=10.5, textColor=colors.HexColor("#5C6E80"))

    created_at = str(assessment.get("created_at", ""))[:19].replace("T", " ")
    priority_value = f"{_text(result_priority.get('score', risk.get('score')), '—')}/100 · {_text(result_priority.get('level', risk.get('level')), 'NOT ASSESSED')}"
    assessment_risk_value = (
        f"{_text(result_risk.get('score'))}/100 · {_text(result_risk.get('level'))}"
        if result_risk.get("available") and result_risk.get("score") is not None
        else _text(result_risk.get("notice"), "Not assessed")
    )
    prediction = classification.get("top_prediction") or {}
    classification_value = _text(prediction.get("condition"), "No scoped disease classification was run") if classification.get("available") else "No scoped disease classification was run"
    likelihood = prediction.get("calibrated_probability")
    calibration = classification.get("calibration") or {}
    uncertainty = classification.get("uncertainty") or {}
    if likelihood is not None and classification.get("available"):
        classification_value += f"<br/><font color='#5C6E80'>Estimated likelihood: {_text(round(float(likelihood) * 100))}% · calibration: {_text(calibration.get('calibration_version'))} · certainty: {_text(uncertainty.get('certainty'))}</font>"
    elif classification.get("available"):
        raw_score = prediction.get("relative_score")
        classification_value += f"<br/><font color='#5C6E80'>Raw model score: {_text(round(float(raw_score) * 100)) if isinstance(raw_score, (int, float)) else 'not available'}%. This is a relative research ranking, not a calibrated likelihood or diagnosis.</font>"
    assessment_state = str(result_status.get("state") or "").upper()
    outcome_label = {
        "HEALTHY": "No apparent concerns identified in the submitted image",
        "CONDITION": "Possible model-supported condition",
        "UNCERTAIN": "Image-findings assessment" if image_findings.get("available") else "Could not assess confidently",
    }.get(assessment_state, "Assessment state unavailable in this saved record")
    validated_condition_name = result_condition.get("name") if result_condition.get("available") else None
    knowledge_finding = _text(
        consumer_primary.get("title") or validated_condition_name or ("Image findings" if image_findings.get("available") else None),
        "No condition label established; image findings are listed below.",
    )
    knowledge_finding_note = _text(
        consumer_primary.get("summary") or result_condition.get("notice") or finding.get("label"),
        "The condition-knowledge layer did not add a diagnosis.",
    )
    result_likelihood = result_condition.get("estimated_likelihood")
    likelihood_value = (
        f"{round(float(result_likelihood) * 100)}% calibrated research-model likelihood" if result_likelihood is not None
        else f"{consumer_primary.get('confidence')}% raw model score (uncalibrated)" if consumer_primary.get("confidence") is not None and consumer_primary.get("confidence_kind") == "raw_softmax"
        else "Not available"
    )
    severity_value = result_severity.get("level") or severity.get("level") or "Not assessed"
    severity_note = result_severity.get("notice") or severity.get("label") or "No symptom severity was assessed."
    pirs_value = f"{pirs['score']}/100 · {_text(pirs.get('band'))}" if pirs.get("score") is not None else "Not assessed"
    input_quality = (result_input.get("quality") or {}).get("label") or quality.get("label")
    visual_evidence_value = (
        f"{round(float(result_visual_evidence['affected_area_percent']))}% of frame · {_text(result_visual_evidence.get('source'))}"
        if result_visual_evidence.get("available") and result_visual_evidence.get("affected_area_percent") is not None
        else _text(result_visual_evidence.get("notice"), "No reliable visual candidate-region evidence was used.")
    )
    urgency_value = result_urgency.get("level") or "ROUTINE MONITORING"
    reported_factors = [
        f"{factor.get('label', 'Reported context')}: {factor.get('interpretation', '')}"
        for factor in intelligence.get("reported_context_factors") or []
    ]
    references = [reference.get("title", "Source") for reference in (intelligence.get("knowledge") or {}).get("references") or []]
    product_discovery = [
        f"{product.get('name', 'Care category')}: {product.get('purpose', 'General personal-care discovery.')}"
        for product in (recommendations.get("products") or recommendations.get("general_care_categories") or [])
    ]
    product_scope = recommendations.get("product_notice") if recommendations.get("products") else recommendations.get("general_care_notice")

    rows = [
        [Paragraph("Assessment ID", eyebrow), Paragraph(_text(assessment.get("assessment_id")), body)],
        [Paragraph("Assessment date", eyebrow), Paragraph(_text(created_at), body)],
        [Paragraph("Area and input", eyebrow), Paragraph(f"{_text(assessment.get('area'))} · {_text(summary.get('input_type'))}", body)],
        [Paragraph("Assessment outcome", eyebrow), Paragraph(_text(outcome_label), body)],
        [Paragraph("Result label", eyebrow), Paragraph(knowledge_finding, body)],
        [Paragraph("Model score", eyebrow), Paragraph(_text(likelihood_value), body)],
        [Paragraph("Visual evidence", eyebrow), Paragraph(_text(visual_evidence_value), body)],
        [Paragraph("Assessment concern score", eyebrow), Paragraph(_text(assessment_risk_value), body)],
        [Paragraph("Reported symptom severity", eyebrow), Paragraph(f"{_text(severity_value)} · {_text(severity_note)}", body)],
        [Paragraph("PIRS (reported-concern tracking)", eyebrow), Paragraph(_text(pirs_value), body)],
        [Paragraph("Care priority", eyebrow), Paragraph(f"{priority_value}<br/><font color='#5C6E80'>Reported concern priority, not disease risk.</font>", body)],
        [Paragraph("Urgency and next step", eyebrow), Paragraph(f"{_text(result_risk.get('urgency_label') or urgency_value)} · {_text(result_urgency.get('notice') or cdss.get('next_step'))}", body)],
        [Paragraph("Image / input readiness", eyebrow), Paragraph(_text(input_quality), body)],
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
        Paragraph("Assessment summary", heading),
        Paragraph(_text(screening.get("title")), body),
        Spacer(1, 1.5 * mm),
        Paragraph(_text(screening.get("summary")), body),
        Paragraph("Assessment score explanation", heading),
        Paragraph(_text(result_risk.get("explanation") or result_risk.get("notice")), body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Contributing factors:</b><br/>{_bullets(result_risk.get('factor_labels') or [factor.get('label') for factor in result_risk.get('factors') or []])}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Method:</b> {_text(result_risk.get('methodology'))} · version {_text(result_risk.get('methodology_version'))}. {_text(result_risk.get('notice'), 'This score is not a disease probability or diagnosis.')}", note),
        Paragraph("Model and explanation scope", heading),
        Paragraph(f"<b>Classification:</b> {classification_value}", body),
        *([Paragraph(f"<b>Reference-file provenance:</b> {_text(presentation_case.get('notice'))}", note)] if presentation_case.get("is_reference_case") or presentation_case.get("matched") else []),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Segmentation:</b> {_text(segmentation.get('status'), 'Not run')}. {_text(segmentation.get('notice'), '')}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(_text((summary.get("explainability") or {}).get("notice") or (classification.get("explainability") or {}).get("explanation_text"), "No additional explainability artifact was retained."), note),
        Paragraph("Evidence and context", heading),
        Paragraph("Local image findings", heading),
        Paragraph(_text(image_findings.get("summary"), "No local image findings were retained for this record."), body),
        Spacer(1, 1.5 * mm),
        Paragraph(_bullets([f"{item.get('finding', 'Finding')}: {item.get('visible_evidence', '')}" for item in image_findings.get("observations") or []]), body),
        Spacer(1, 1.5 * mm),
        Paragraph(_bullets(image_findings.get("not_assessable")), note),
        Paragraph(f"<b>Result label:</b> {knowledge_finding}<br/>{knowledge_finding_note}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Reported context factors:</b><br/>{_bullets(reported_factors)}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Care pathway:</b> {_text(care_pathway.get('category'))}. {_text(care_pathway.get('next_step'))}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Follow-up:</b> {_text(follow_up.get('guidance'))} {_text(follow_up.get('timeline'))}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Professional support:</b> {_text(doctor.get('specialty'))}. {_text(doctor.get('appointment'))}", body),
        Paragraph(f"<b>Knowledge references:</b> {_bullets(references)}", note),
        Paragraph("General guidance for discussion", heading),
        Paragraph("Possible conditions and associated symptoms", heading),
        Paragraph(_text(consumer.get("differential_status")), note),
        Paragraph(_bullets([item.get("name") for item in consumer.get("possible_conditions") or []]), body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Common associated symptoms:</b><br/>{_bullets(consumer.get('common_symptoms'))}", body),
        Paragraph("Causes, triggers and care", heading),
        Paragraph(f"<b>Possible contributors:</b><br/>{_bullets(consumer.get('possible_causes'))}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Care steps:</b><br/>{_bullets(consumer.get('care_steps'))}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Treatment paths:</b><br/>{_bullets([item for section in consumer.get('treatment_sections') or [] for item in section.get('items') or []])}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Pattern context:</b> {_text(consumer_topic.get('description'), 'A specific condition could not be established from the available evidence.')}", note),
        Paragraph(f"<b>CDSS status:</b> {_text(cdss.get('status'))}. {_text(cdss.get('next_step') or cdss.get('notice'))}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Next step:</b> {_text(care_plan.get('next_step'))}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Routine:</b><br/>{_bullets((recommendations.get('routine') or {}).get('morning'))}<br/>{_bullets((recommendations.get('routine') or {}).get('evening'))}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Wellbeing:</b><br/>{_bullets(recommendations.get('diet'))}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Lifestyle:</b><br/>{_bullets(recommendations.get('lifestyle'))}", body),
        Paragraph(f"<b>Monitoring:</b><br/>{_bullets((consumer.get('monitoring') or {}).get('what_to_track'))}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Medication information:</b> {_text(medication_information.get('notice'), 'No medication recommendation is generated from this assessment.')} {_text(medication_information.get('consultation_notice'), 'Discuss medication decisions with a qualified doctor or pharmacist.')}", body),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>General product discovery:</b><br/>{_bullets(product_discovery)}<br/>{_text(product_scope, 'No product need was established from this assessment.')}", body),
        Paragraph(f"<b>Ongoing query:</b> {_text(journey.get('journey_id'), 'Not saved as an ongoing query')} · baseline {_text(journey.get('baseline_date'))}", note),
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
        result = summary.get("assessment_result") or {}
        canonical = result.get("canonical_evidence") or summary.get("canonical_evidence") or {}
        risk = canonical.get("assessment_risk") or result.get("assessment_risk") or summary.get("assessment_risk") or summary.get("risk") or {}
        pirs = canonical.get("pirs") or summary.get("pirs") or {}
        severity = canonical.get("severity") or summary.get("severity") or {}
        condition = result.get("condition") or {}
        consumer_title = ((result.get("consumer") or {}).get("primary_result") or {}).get("title")
        scope = consumer_title or (condition.get("name") if condition.get("available") else "Image findings" if (canonical.get("image_findings") or result.get("image_findings") or {}).get("available") else "Screening summary")
        analysis_rows.append([
            str(analysis.get("created_at", ""))[:10],
            str(analysis.get("area", "")),
            str(scope),
            f"{risk['score']}/100" if risk.get("score") is not None else "Not assessed",
            f"{pirs['score']}/100 · {severity.get('level', 'Not assessed')}" if pirs.get("score") is not None else f"Not assessed · {severity.get('level', 'Not assessed')}",
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
        Paragraph("Assessment concern indicators are transparent project-defined estimates, not disease probabilities, diagnoses, or clinically validated medical-risk scores. A screening summary is not a confirmed diagnosis.", note),
        Spacer(1, 1.5 * mm),
        compact_table(["Date", "Area", "Result scope", "Concern", "PIRS / severity"], analysis_rows, [24 * mm, 18 * mm, 54 * mm, 28 * mm, 46 * mm]),
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
