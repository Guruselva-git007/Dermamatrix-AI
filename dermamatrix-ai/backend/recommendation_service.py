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
    {"id": "barrier-moisturiser", "name": "Fragrance-free barrier moisturiser", "domain": "Skin", "category": "Skin care", "key_property": "Fragrance-conscious emollient", "purpose": "Supportive moisturising care for a gentle skin routine.", "precautions": "Check allergies and stop if irritation occurs.", "search_terms": "fragrance free barrier moisturiser", "tags": ["dry skin", "irritation", "barrier", "eczema"], "affiliate_env": "AFFILIATE_MOISTURISER_URL", "product_url_env": "PRODUCT_MOISTURISER_URL"},
    {"id": "sun-protection", "name": "Broad-spectrum sun protection", "domain": "Skin", "category": "Skin care", "key_property": "Broad-spectrum labelled protection", "purpose": "Everyday sun-protection product discovery for a routine discussion.", "precautions": "Not a treatment; choose a labelled product from a licensed seller.", "search_terms": "broad spectrum sunscreen", "tags": ["sun protection", "pigmentation", "hyperpigmentation", "melasma", "acne"], "affiliate_env": "AFFILIATE_SUNSCREEN_URL", "product_url_env": "PRODUCT_SUNSCREEN_URL"},
    {"id": "scalp-cleanser", "name": "Gentle scalp cleanser", "domain": "Hair", "category": "Hair care", "key_property": "Low-irritation cleansing category", "purpose": "Supportive product discovery for routine scalp cleansing.", "precautions": "Avoid using on broken or painful skin without professional advice.", "search_terms": "gentle fragrance free scalp cleanser", "tags": ["hair", "scalp", "dandruff", "flakes"], "affiliate_env": "AFFILIATE_SCALP_CLEANSER_URL", "product_url_env": "PRODUCT_SCALP_CLEANSER_URL"},
    {"id": "nail-emollient", "name": "Protective nail-care emollient", "domain": "Nails", "category": "Nail care", "key_property": "Cuticle and surrounding-skin comfort", "purpose": "Supportive care for dry cuticles and nail surroundings.", "precautions": "Not for self-treating painful, lifting, or discoloured nails.", "search_terms": "protective cuticle and nail care emollient", "tags": ["nail care", "cuticle", "dry nails"], "affiliate_env": "AFFILIATE_NAIL_CARE_URL", "product_url_env": "PRODUCT_NAIL_CARE_URL"},
]


# Product discovery is separate from an assessment recommendation.  These are
# user-initiated search categories based on the source-linked knowledge layer;
# they are never selected from a photo, model label, risk score, or diagnosis.
PRODUCT_DISCOVERY_CATALOG = [
    *PRODUCT_CATALOG,
    {"id": "gentle-cleanser", "name": "Gentle facial cleanser", "domain": "Skin", "category": "Skin care", "key_property": "Low-irritation cleansing category", "purpose": "Browse cleanser options as part of a simple routine discussion.", "precautions": "Stop if it burns or worsens irritation; this is not a treatment recommendation.", "search_terms": "gentle facial cleanser", "tags": ["acne", "blackheads", "sensitive skin", "cleanser"]},
    {"id": "salicylic-acid", "name": "Salicylic acid product category", "domain": "Skin", "category": "Ingredient discovery", "key_property": "Over-the-counter active-ingredient category", "purpose": "User-led search for salicylic-acid product options to discuss with a clinician or pharmacist.", "precautions": "Not selected from a photo. Confirm suitability and avoid combining actives without professional advice.", "search_terms": "salicylic acid skin care product", "tags": ["acne", "blackheads", "open comedones", "oil"]},
    {"id": "benzoyl-peroxide", "name": "Benzoyl peroxide product category", "domain": "Skin", "category": "Ingredient discovery", "key_property": "Over-the-counter active-ingredient category", "purpose": "User-led search for benzoyl-peroxide product options to discuss with a clinician or pharmacist.", "precautions": "Not selected from a photo. Check labels and seek professional advice before use, especially for persistent or inflamed concerns.", "search_terms": "benzoyl peroxide skin care product", "tags": ["acne", "pimples", "breakouts"]},
    {"id": "ketoconazole-shampoo", "name": "Ketoconazole shampoo", "domain": "Hair", "category": "Scalp care", "key_property": "Medicated-shampoo category", "purpose": "User-led product discovery for a ketoconazole shampoo category.", "precautions": "Scalp flaking has multiple causes. Confirm the cause and suitability with a clinician or pharmacist before use.", "search_terms": "ketoconazole shampoo", "tags": ["dandruff", "seborrheic dermatitis", "scalp flakes"]},
    {"id": "selenium-sulfide-shampoo", "name": "Selenium sulfide shampoo", "domain": "Hair", "category": "Scalp care", "key_property": "Medicated-shampoo category", "purpose": "User-led product discovery for a selenium-sulfide shampoo category.", "precautions": "Scalp flaking has multiple causes. Confirm the cause and suitability with a clinician or pharmacist before use.", "search_terms": "selenium sulfide shampoo", "tags": ["dandruff", "seborrheic dermatitis", "scalp flakes"]},
    {"id": "zinc-pyrithione-shampoo", "name": "Zinc pyrithione shampoo", "domain": "Hair", "category": "Scalp care", "key_property": "Medicated-shampoo category", "purpose": "User-led product discovery for a zinc-pyrithione shampoo category.", "precautions": "Scalp flaking has multiple causes. Confirm the cause and suitability with a clinician or pharmacist before use.", "search_terms": "zinc pyrithione shampoo", "tags": ["dandruff", "seborrheic dermatitis", "scalp flakes"]},
    {"id": "minoxidil-category", "name": "Minoxidil product category", "domain": "Hair", "category": "Hair-loss discussion", "key_property": "Hair-loss product category", "purpose": "User-led search for a minoxidil product category to discuss with a qualified clinician or pharmacist.", "precautions": "Hair loss has many causes. Do not use this page to self-diagnose; check suitability and interactions first.", "search_terms": "minoxidil hair loss product", "tags": ["hair loss", "thinning", "pattern hair loss", "alopecia"]},
    {"id": "topical-antifungal", "name": "Topical antifungal product category", "domain": "Skin", "category": "Pharmacy discussion", "key_property": "Non-prescription antifungal category", "purpose": "User-led discovery of topical antifungal product categories to discuss after a professional confirms the cause.", "precautions": "Do not self-treat an uncertain rash or start oral medication based on an image or this search page.", "search_terms": "topical antifungal skin product", "tags": ["tinea", "ringworm", "fungal infection"]},
    {"id": "nail-antifungal", "name": "Nail antifungal product category", "domain": "Nails", "category": "Pharmacy discussion", "key_property": "Nail-treatment category", "purpose": "User-led discovery of nail antifungal product categories to discuss after professional assessment.", "precautions": "Nail discoloration and thickening can have several causes. Confirm the cause before choosing a product.", "search_terms": "nail antifungal product", "tags": ["nail fungus", "onychomycosis", "thick nail"]},
    {"id": "vitamin-d-information", "name": "Vitamin D supplement information", "domain": "Wellness", "category": "Supplement information", "key_property": "Testing-first wellbeing discussion", "purpose": "Explore external vitamin D information or products only after discussing relevance with a clinician or pharmacist.", "precautions": "Do not self-dose for a presumed deficiency; images cannot diagnose a vitamin deficiency.", "search_terms": "vitamin D supplement", "tags": ["vitamin d", "supplement", "wellness"]},
    {"id": "iron-information", "name": "Iron supplement information", "domain": "Wellness", "category": "Supplement information", "key_property": "Testing-first wellbeing discussion", "purpose": "Explore external iron information or products only after professional review of symptoms and tests.", "precautions": "Do not start iron for hair, nail, or skin changes without appropriate testing and clinical advice.", "search_terms": "iron supplement", "tags": ["iron", "folate", "supplement", "wellness"]},
]


def catalog_for_area(area: str, *, risk_score: int = 0) -> list[dict]:
    """Return domain-relevant non-medicinal products after a priority gate."""
    if risk_score >= 40:
        return []
    selected = PRODUCT_CATALOG if area == "All" else [item for item in PRODUCT_CATALOG if item["domain"] == area]
    return [materialize_product(item) for item in selected]


def product_discovery_catalog(area: str = "All") -> list[dict]:
    """Return user-led product categories; never use an assessment output."""
    selected = PRODUCT_DISCOVERY_CATALOG if area == "All" else [item for item in PRODUCT_DISCOVERY_CATALOG if item["domain"] == area]
    return [materialize_product(item) for item in selected]


def search_product_discovery(query: str) -> list[dict]:
    """Resolve topic/category matches or a neutral exact marketplace search."""
    normalized = " ".join(str(query or "").split())
    query_lower = normalized.casefold()
    if not query_lower:
        return product_discovery_catalog()
    query_tokens = [
        token for token in query_lower.replace("-", " ").split()
        if len(token) > 2 and token not in {"care", "product", "products", "for", "and", "with", "the"}
    ]
    matches = []
    for item in PRODUCT_DISCOVERY_CATALOG:
        searchable = " ".join([
            item.get("name", ""), item.get("purpose", ""), item.get("search_terms", ""),
            " ".join(item.get("tags", [])),
        ]).casefold()
        if query_lower in searchable or (query_tokens and all(token in searchable for token in query_tokens)):
            matches.append(materialize_product(item))
    if matches:
        return matches
    return [materialize_product({
        "id": "exact-user-search",
        "name": normalized,
        "domain": "Search",
        "category": "Exact product search",
        "key_property": "Search term entered by you",
        "purpose": "Open independent shopping results for the exact product or ingredient you entered.",
        "precautions": "A marketplace result is not a recommendation, proof of suitability, or a substitute for clinician or pharmacist advice.",
        "search_terms": normalized,
        "tags": [normalized],
    })]


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
