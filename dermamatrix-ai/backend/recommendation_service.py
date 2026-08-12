"""Structured, non-prescription care content for the education prototype.

Content is grouped here instead of being generated from a model prediction or
hard-coded in the browser. It must not be used as a disease treatment plan.
"""

from __future__ import annotations


GENERAL_WELLBEING = {
    "routine": {
        "morning": ["Use a gentle, non-irritating cleansing step if it suits your skin or scalp.", "Avoid picking, harsh scrubbing, or adding several new products at once."],
        "evening": ["Keep the routine simple and stop any product that burns, stings, or worsens irritation.", "Record changes in the progress page rather than judging change from one photo."],
    },
    "diet": ["Aim for regular meals that include protein and a variety of fruits or vegetables.", "Stay hydrated according to your usual health needs.", "Use laboratory testing and professional advice before taking supplements for a suspected deficiency."],
    "supplements": ["Food sources come first. Vitamin D, B12, iron, folate, and biotin should only be discussed with a clinician or pharmacist when relevant to your history or tests."],
    "precautions": ["These are general wellbeing suggestions, not treatment for a detected disease.", "Seek professional care promptly for severe pain, rapid change, broken skin, fever, or if you feel unwell."],
}

PRODUCT_CATALOG = [
    {"id": "barrier-moisturiser", "name": "Fragrance-free barrier moisturiser", "category": "Skin care", "key_property": "Fragrance-conscious emollient", "purpose": "General dry-feeling skin comfort", "precautions": "Check allergies and stop if irritation occurs.", "url": ""},
    {"id": "sun-protection", "name": "Broad-spectrum sun protection", "category": "Skin care", "key_property": "Broad-spectrum labelled protection", "purpose": "Everyday sun-protection product discovery", "precautions": "Not a treatment; choose from a licensed seller.", "url": ""},
    {"id": "scalp-cleanser", "name": "Gentle scalp cleanser", "category": "Hair care", "key_property": "Low-irritation cleansing category", "purpose": "Routine scalp cleansing", "precautions": "Avoid using on broken or painful skin without professional advice.", "url": ""},
    {"id": "nail-emollient", "name": "Protective nail-care emollient", "category": "Nail care", "key_property": "Cuticle and surrounding-skin comfort", "purpose": "General dry cuticle support", "precautions": "Not for self-treating painful, lifting, or discoloured nails.", "url": ""},
]


def build_recommendations(area: str, research_classifier: dict | None) -> dict:
    """Return data-backed general care; never infer treatment from a research label."""
    items = PRODUCT_CATALOG[:2]
    if area == "Hair":
        items = [PRODUCT_CATALOG[2]]
    elif area == "Nails":
        items = [PRODUCT_CATALOG[3]]
    research_note = "No condition classification was run for this image type."
    if research_classifier and research_classifier.get("available"):
        research_note = "The research classifier output is shown for clinician discussion only; products and routine are not selected from its label."
    return {"scope": "General wellbeing and personal-care education", "research_note": research_note, **GENERAL_WELLBEING, "products": items}
