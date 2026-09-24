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

AREA_MORNING_CARE = {
    "Skin": "Cleanse gently if needed and use only products your skin tolerates.",
    "Hair": "Cleanse the hair and scalp gently when needed, using products you tolerate.",
    "Nails": "Keep nails and surrounding skin clean and dry; avoid harsh scrubbing.",
}

# Area-based education is shown for every image, including an unclear photo or
# a high-priority reported symptom. It describes common issues, never findings
# inferred from that particular image. Sources are public patient guidance.
AREA_CARE_GUIDANCE = {
    "Skin": {
        "common_symptoms": ["Dryness, tightness, flaking, or itching", "Redness, burning, or sensitivity", "Pimples, clogged pores, or excess oil", "Dark marks or changing color"],
        "possible_causes": ["Weather, frequent washing, or irritating skin products", "Acne and blocked pores", "Contact with a new product, fragrance, or other irritant", "Sun exposure or marks left after inflammation"],
        "care_steps": ["Wash gently with lukewarm water and a mild cleanser; avoid scrubbing or picking.", "Apply a fragrance-free moisturiser after washing, especially where skin feels dry.", "Protect exposed skin with shade or clothing and broad-spectrum SPF 30+ sunscreen.", "Introduce one new product at a time and stop one that causes persistent stinging or worsening irritation."],
        "routine": {
            "morning": ["Gently cleanse if needed; use a moisturiser suited to your skin.", "Apply broad-spectrum SPF 30+ sunscreen to exposed skin before going outdoors."],
            "evening": ["Wash away sunscreen, sweat, and makeup with a gentle cleanser.", "Moisturise while skin is slightly damp; leave irritated spots alone."],
            "follow_up": ["Note new products and whether dryness, itching, breakouts, or color changes improve or worsen.", "Seek an in-person review for a rapidly changing, painful, bleeding, or persistent area."],
        },
        "diet": ["Build regular meals around protein foods, vegetables or fruit, and whole grains.", "Drink enough fluids for your usual health needs; no single food reliably treats a skin condition.", "Avoid restrictive diets or supplements based on a photo; discuss suspected deficiencies with a clinician."],
        "lifestyle": ["Avoid harsh exfoliation and repeated picking, which can worsen irritation or marks.", "Keep sun protection consistent; reapply sunscreen as the label directs when outdoors.", "Track changes after a new cosmetic, detergent, or skin product to help spot possible irritants."],
        "medication_topics": [
            {"name": "Benzoyl peroxide", "used_for": "An over-the-counter option for mild acne-type pimples; it may dry or irritate skin."},
            {"name": "Salicylic acid", "used_for": "An over-the-counter option often used for blackheads and clogged pores."},
            {"name": "Azelaic acid", "used_for": "An acne-care ingredient that may also help marks after breakouts; availability varies by location."},
        ],
        "product_ids": ["gentle-cleanser", "barrier-moisturiser", "sun-protection"],
        "sources": [
            {"label": "AAD: simple skin care", "url": "https://www.aad.org/public/everyday-care/skin-care-basics/care/skin-care-budget"},
            {"label": "AAD: acne treatment ingredients", "url": "https://www.aad.org/public/diseases/acne/diy/adult-acne-treatment"},
        ],
    },
    "Hair": {
        "common_symptoms": ["Scalp itching or visible flakes", "Excess oil or scalp dryness", "Increased shedding or thinning", "Hair breakage or tender scalp"],
        "possible_causes": ["Dandruff, oily skin, or a dry or irritated scalp", "Heat, chemical processing, or tight hairstyles", "Stress, illness, hormonal changes, or inherited pattern loss", "Low protein or iron intake in some people"],
        "care_steps": ["Cleanse the scalp as often as your hair type and oiliness require; massage gently rather than scratching.", "Condition the hair lengths to reduce tangles and breakage.", "Limit tight styles, high heat, and rough brushing, especially if hair is fragile.", "If flaking is the main concern, a labelled dandruff shampoo may help; follow its instructions and stop if irritation occurs."],
        "routine": {
            "morning": ["Style hair with minimal pulling; use a wide-tooth comb or gentle brush where helpful.", "Protect exposed scalp from sun with a hat or suitable sun protection."],
            "evening": ["Wash the scalp when needed; apply shampoo to the scalp and conditioner mainly to hair lengths.", "Avoid sleeping with tight braids or styles that pull on the hairline."],
            "follow_up": ["Track shedding, new bald patches, persistent flakes, or scalp discomfort over several weeks.", "Arrange a review for sudden or patchy loss, pain, scarring, or persistent scalp symptoms."],
        },
        "diet": ["Include protein foods such as eggs, lentils, beans, fish, dairy, or other preferred sources regularly.", "Include iron-containing foods and a varied mix of vegetables, fruit, nuts, and seeds.", "Avoid crash diets; discuss tests before taking iron, biotin, or other hair supplements."],
        "lifestyle": ["Reduce tension from tight hairstyles and handle wet hair gently.", "Limit frequent heat styling or chemical treatments if strands are breaking.", "Record recent illness, stress, or medication changes to discuss if shedding persists."],
        "medication_topics": [
            {"name": "Dandruff shampoos", "used_for": "Ketoconazole or selenium sulfide shampoos are common options for persistent flakes; choose by label and pharmacist advice."},
            {"name": "Topical minoxidil", "used_for": "An option for some types of pattern hair loss, after the cause and suitability are reviewed."},
        ],
        "product_ids": ["scalp-cleanser", "gentle-conditioner", "ketoconazole-shampoo"],
        "sources": [
            {"label": "AAD: dandruff care", "url": "https://www.aad.org/public/everyday-care/hair-scalp-care/scalp/treat-dandruff"},
            {"label": "AAD: managing hair loss", "url": "https://www.aad.org/public/diseases/hair-loss/treatment/tips"},
            {"label": "AAD: pattern hair loss options", "url": "https://www.aad.org/public/diseases/hair-loss/treatment/male-pattern-hair-loss-treatment"},
        ],
    },
    "Nails": {
        "common_symptoms": ["Brittle, peeling, or splitting nails", "Thickening, discoloration, or lifting", "Soreness or swelling around a nail", "Ridges or a change in nail shape"],
        "possible_causes": ["Frequent water or detergent exposure and repeated manicures", "Minor injury, tight shoes, or nail biting", "Fungal infection in some thickened or discolored nails", "Skin conditions or other health factors that need examination"],
        "care_steps": ["Keep nails clean and dry; trim straight across and smooth snags with a file.", "Moisturise nails and surrounding skin after washing, especially if they split.", "Wear gloves for prolonged wet work or cleaning, and use shoes that do not press on toenails.", "Leave cuticles intact; avoid digging into sore nails or covering a changing nail with artificial nails."],
        "routine": {
            "morning": ["Dry hands and feet well, including around nails; apply a simple hand or nail moisturiser.", "Wear comfortable shoes and fresh socks if checking toenails."],
            "evening": ["Check for new pain, swelling, color change, or lifting when you trim or clean nails.", "Moisturise cuticles and surrounding skin; keep nails short enough to avoid snagging."],
            "follow_up": ["Compare a changing nail as it grows out; record pain, spreading discoloration, or swelling.", "Ask a clinician or pharmacist about a persistent thick or discolored nail before treating it as fungus."],
        },
        "diet": ["Eat regular, varied meals with protein foods, vegetables, fruit, and whole grains.", "Include iron and zinc food sources such as beans, lentils, meat, seafood, nuts, or seeds as suited to your diet.", "Skip high-dose biotin or iron for a nail change unless a clinician finds a reason; supplements are not a universal fix."],
        "lifestyle": ["Use gloves for cleaning and frequent wet work; dry hands well afterward.", "Avoid nail biting, cuticle cutting, and repeated harsh polish removal.", "Keep footwear breathable and avoid sharing nail clippers or towels."],
        "medication_topics": [
            {"name": "Antifungal nail lacquer", "used_for": "A pharmacist may suggest this when a fungal nail infection is likely; treatment can take months."},
            {"name": "Prescription antifungal tablets", "used_for": "A clinician may consider these after assessing or testing a persistent fungal nail; monitoring and interactions matter."},
        ],
        "product_ids": ["nail-emollient", "protective-gloves", "nail-antifungal"],
        "sources": [
            {"label": "AAD: healthy nail care", "url": "https://www.aad.org/public/everyday-care/nail-care-secrets/basics/healthy-nail-tips"},
            {"label": "NHS: fungal nail infection", "url": "https://www.nhs.uk/conditions/fungal-nail-infection/"},
            {"label": "NIH: biotin evidence", "url": "https://ods.od.nih.gov/factsheets/Biotin-Consumer/"},
        ],
    },
}

PRODUCT_CATALOG = [
    {"id": "barrier-moisturiser", "name": "Fragrance-free barrier moisturiser", "domain": "Skin", "category": "Skin care", "key_property": "Fragrance-conscious emollient", "purpose": "Supportive moisturising care for a gentle skin routine.", "precautions": "Check allergies and stop if irritation occurs.", "search_terms": "fragrance free barrier moisturiser", "tags": ["dry skin", "irritation", "barrier", "eczema"], "affiliate_env": "AFFILIATE_MOISTURISER_URL", "product_url_env": "PRODUCT_MOISTURISER_URL"},
    {"id": "sun-protection", "name": "Broad-spectrum sun protection", "domain": "Skin", "category": "Skin care", "key_property": "Broad-spectrum labelled protection", "purpose": "Everyday sun-protection product discovery for a routine discussion.", "precautions": "Not a treatment; choose a labelled product from a licensed seller.", "search_terms": "broad spectrum sunscreen", "tags": ["sun protection", "pigmentation", "hyperpigmentation", "melasma", "acne"], "affiliate_env": "AFFILIATE_SUNSCREEN_URL", "product_url_env": "PRODUCT_SUNSCREEN_URL"},
    {"id": "scalp-cleanser", "name": "Gentle scalp cleanser", "domain": "Hair", "category": "Hair care", "key_property": "Low-irritation cleansing category", "purpose": "Supportive product discovery for routine scalp cleansing.", "precautions": "Avoid using on broken or painful skin without professional advice.", "search_terms": "gentle fragrance free scalp cleanser", "tags": ["hair", "scalp", "dandruff", "flakes"], "affiliate_env": "AFFILIATE_SCALP_CLEANSER_URL", "product_url_env": "PRODUCT_SCALP_CLEANSER_URL"},
    {"id": "gentle-conditioner", "name": "Gentle hair conditioner", "domain": "Hair", "category": "Hair care", "key_property": "Conditioning for hair lengths", "purpose": "A basic conditioning option to reduce tangles and friction during combing.", "precautions": "Choose for your hair type and stop if it irritates your scalp.", "search_terms": "gentle hair conditioner", "tags": ["hair", "conditioner", "breakage"]},
    {"id": "nail-emollient", "name": "Protective nail-care emollient", "domain": "Nails", "category": "Nail care", "key_property": "Cuticle and surrounding-skin comfort", "purpose": "Supportive care for dry cuticles and nail surroundings.", "precautions": "Not for self-treating painful, lifting, or discoloured nails.", "search_terms": "protective cuticle and nail care emollient", "tags": ["nail care", "cuticle", "dry nails"], "affiliate_env": "AFFILIATE_NAIL_CARE_URL", "product_url_env": "PRODUCT_NAIL_CARE_URL"},
    {"id": "protective-gloves", "name": "Protective cleaning gloves", "domain": "Nails", "category": "Nail care", "key_property": "Water and detergent protection", "purpose": "Help limit prolonged wet work that can weaken nails and irritate surrounding skin.", "precautions": "Dry hands after use and check material sensitivity.", "search_terms": "reusable protective cleaning gloves", "tags": ["nails", "water", "gloves"]},
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
    # Keep discovery search forgiving without turning a care topic into a
    # diagnosis. These are spelling and everyday-language equivalents only.
    natural_terms = {
        "moisturizer": "moisturiser",
        "sunscreen": "sun protection",
        "sun screen": "sun protection",
        "fragrance free": "fragrance-free",
        "dry scalp": "scalp flakes",
        "pimples": "acne",
    }
    for spoken_term, catalogue_term in natural_terms.items():
        query_lower = query_lower.replace(spoken_term, catalogue_term)
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
        if query_lower in searchable or (query_tokens and any(token in searchable for token in query_tokens)):
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


def build_recommendations(area: str, research_classifier: dict | None, *, cdss: dict | None = None,
                          assessment_state: str | None = None, canonical_evidence: dict | None = None) -> dict:
    """Return state-aware education without turning an image into a prescription."""
    research_note = "No condition classification was run for this image type."
    if area == "Sweat":
        research_note = "Sweat guidance is based on questionnaire inputs only. A tabular ML model is not configured in this deployment."
    if research_classifier and research_classifier.get("available"):
        research_note = "The research classifier output is shown for clinician discussion only; products and routine are not selected from its label."
    products = []
    product_guidance = (cdss or {}).get("product_guidance", "GENERAL_SELF_CARE_ONLY")
    if assessment_state == "UNCERTAIN":
        product_guidance = "DEFER_PRODUCT_DECISIONS"
    elif assessment_state == "HEALTHY":
        product_guidance = "HEALTHY_MAINTENANCE_ONLY"
    if product_guidance in {"GENERAL_SELF_CARE_ONLY", "HEALTHY_MAINTENANCE_ONLY"}:
        products = catalog_for_area(area)
    guidance = AREA_CARE_GUIDANCE.get(area)
    # Educational categories are selected by the upload area alone. Urgent
    # symptoms still get an urgent alert; that does not erase basic care content.
    educational_products = [materialize_product(item) for item in PRODUCT_DISCOVERY_CATALOG
                            if guidance and item["id"] in guidance["product_ids"]]
    healthy = assessment_state == "HEALTHY"
    return {
        "scope": "Healthy-appearance maintenance education" if healthy else "General wellbeing and personal-care education",
        "research_note": research_note,
        "medicine_policy": "No treatment or medicine is needed based on this assessment. This does not replace care for symptoms, a changing concern, or a clinician recommendation." if healthy else "No medicine, prescription treatment, dose, or diagnosis-specific product is suggested from an uploaded image. A normal-looking or usable image is not interpreted as a treatment decision.",
        "product_guidance": product_guidance,
        "product_notice": "These are area-based care and product ideas. They are not selected from the photo or a diagnosis; check suitability before use.",
        "general_care_categories": educational_products,
        "general_care_notice": "These optional everyday-care categories match only the area you selected. The photo did not establish a condition or a product need; check suitability before use." if educational_products else "No area-based product categories are available.",
        "medication_information": {
            "available": False,
            "status": "NO_MEDICATION_RECOMMENDATION",
            "notice": "Common treatment options depend on the symptom and its cause. This image does not establish which, if any, is suitable for you.",
            "common_options": guidance["medication_topics"] if guidance else [],
            "consultation_notice": "Check suitability, interactions, and local availability with a qualified doctor or pharmacist; do not change a prescribed medicine based on this result.",
        },
        "affiliate_disclosure": "Affiliate disclosure appears only when an approved partner URL is configured. It never changes analysis, medical suitability, or product ordering.",
        **GENERAL_WELLBEING,
        "routine": guidance["routine"] if guidance else {
            **GENERAL_WELLBEING["routine"],
            "morning": [AREA_MORNING_CARE.get(area, GENERAL_WELLBEING["routine"]["morning"][0]), *GENERAL_WELLBEING["routine"]["morning"][1:]],
        },
        "common_symptoms": guidance["common_symptoms"] if guidance else [],
        "possible_causes": guidance["possible_causes"] if guidance else [],
        "care_steps": guidance["care_steps"] if guidance else [],
        "diet": guidance["diet"] if guidance else GENERAL_WELLBEING["diet"],
        "lifestyle": guidance["lifestyle"] if guidance else GENERAL_WELLBEING["lifestyle"],
        "sources": guidance["sources"] if guidance else [],
        "products": products,
    }
