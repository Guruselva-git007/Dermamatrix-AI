"""Structured, non-prescription care content for the education prototype.

Content is grouped here instead of being generated from a model prediction or
hard-coded in the browser. It must not be used as a disease treatment plan.
"""

from __future__ import annotations

from commerce_service import materialize_product


GENERAL_WELLBEING = {
    "routine": {
        "morning": ["Use a gentle, non-irritating cleansing step if it suits your skin or scalp.", "Avoid picking, harsh scrubbing, or adding several new products at once."],
        "evening": ["Keep the routine simple and stop any product that burns, stings, or worsens irritation.", "Record changes in the progress page rather than judging change from one photo."],
    },
    "diet": ["Aim for regular meals that include protein and a variety of fruits or vegetables.", "Stay hydrated according to your usual health needs.", "Use laboratory testing and professional advice before taking supplements for a suspected deficiency."],
    "lifestyle": ["Keep routines simple and avoid introducing several new products at once.", "Avoid known irritants and record meaningful changes for a clinician discussion."],
    "supplements": ["Food sources come first. Vitamin D, B12, iron, folate, and biotin should only be discussed with a clinician or pharmacist when relevant to your history or tests."],
    "precautions": ["These are general wellbeing suggestions, not treatment for a detected disease.", "Seek professional care promptly for severe pain, rapid change, broken skin, fever, or if you feel unwell."],
}

PRODUCT_CATALOG = [
    {"id": "barrier-moisturiser", "name": "Fragrance-free barrier moisturiser", "domain": "Skin", "category": "Skin care", "key_property": "Fragrance-conscious emollient", "purpose": "Supportive moisturising care for a gentle skin routine.", "precautions": "Check allergies and stop if irritation occurs.", "search_terms": "fragrance free barrier moisturiser", "affiliate_env": "AFFILIATE_MOISTURISER_URL", "product_url_env": "PRODUCT_MOISTURISER_URL"},
    {"id": "sun-protection", "name": "Broad-spectrum sun protection", "domain": "Skin", "category": "Skin care", "key_property": "Broad-spectrum labelled protection", "purpose": "Everyday sun-protection product discovery for a routine discussion.", "precautions": "Not a treatment; choose a labelled product from a licensed seller.", "search_terms": "broad spectrum sunscreen", "affiliate_env": "AFFILIATE_SUNSCREEN_URL", "product_url_env": "PRODUCT_SUNSCREEN_URL"},
    {"id": "scalp-cleanser", "name": "Gentle scalp cleanser", "domain": "Hair", "category": "Hair care", "key_property": "Low-irritation cleansing category", "purpose": "Supportive product discovery for routine scalp cleansing.", "precautions": "Avoid using on broken or painful skin without professional advice.", "search_terms": "gentle fragrance free scalp cleanser", "affiliate_env": "AFFILIATE_SCALP_CLEANSER_URL", "product_url_env": "PRODUCT_SCALP_CLEANSER_URL"},
    {"id": "nail-emollient", "name": "Protective nail-care emollient", "domain": "Nails", "category": "Nail care", "key_property": "Cuticle and surrounding-skin comfort", "purpose": "Supportive care for dry cuticles and nail surroundings.", "precautions": "Not for self-treating painful, lifting, or discoloured nails.", "search_terms": "protective cuticle and nail care emollient", "affiliate_env": "AFFILIATE_NAIL_CARE_URL", "product_url_env": "PRODUCT_NAIL_CARE_URL"},
]


def catalog_for_area(area: str, *, risk_score: int = 0) -> list[dict]:
    """Return domain-relevant non-medicinal products after a priority gate."""
    if risk_score >= 40:
        return []
    selected = PRODUCT_CATALOG if area == "All" else [item for item in PRODUCT_CATALOG if item["domain"] == area]
    return [materialize_product(item) for item in selected]


def build_recommendations(area: str, research_classifier: dict | None, *, cdss: dict | None = None) -> dict:
    """Return general care only when the CDSS has not deferred product decisions."""
    research_note = "No condition classification was run for this image type."
    if area == "Sweat":
        research_note = "Sweat guidance is based on questionnaire inputs only. A tabular ML model is not configured in this deployment."
    if research_classifier and research_classifier.get("available"):
        research_note = "The research classifier output is shown for clinician discussion only; products and routine are not selected from its label."
    products = []
    product_guidance = (cdss or {}).get("product_guidance", "GENERAL_SELF_CARE_ONLY")
    if product_guidance == "GENERAL_SELF_CARE_ONLY":
        products = catalog_for_area(area)
    return {
        "scope": "General wellbeing and personal-care education",
        "research_note": research_note,
        "medicine_policy": "No medicine, prescription treatment, dose, or diagnosis-specific product is suggested from an uploaded image. A normal-looking or usable image is not interpreted as a treatment decision.",
        "product_guidance": product_guidance,
        "product_notice": "Product choices are deferred until professional discussion because this assessment is uncertain or needs professional evaluation." if product_guidance != "GENERAL_SELF_CARE_ONLY" else "Only general personal-care categories are shown; they are not selected from a diagnosis or research label.",
        "medication_information": {
            "available": False,
            "status": "NO_MEDICATION_RECOMMENDATION",
            "notice": "No medication, dose, or diagnosis-specific treatment is generated from this assessment.",
            "consultation_notice": "Do not start, stop, or change medication without consulting a qualified doctor or pharmacist.",
        },
        "affiliate_disclosure": "Affiliate disclosure appears only when an approved partner URL is configured. It never changes analysis, medical suitability, or product ordering.",
        **GENERAL_WELLBEING,
        "products": products,
    }
