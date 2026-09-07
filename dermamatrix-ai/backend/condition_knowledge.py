"""Versioned condition-knowledge boundary for the assessment result.

This module is intentionally separate from image inference.  It maps only the
HAM10000 research labels that the local dermatoscopic adapter can emit.  It
does not turn a research ranking into a diagnosis, estimate a cause, prescribe
a treatment, or claim support for hair, nail, ordinary clinical-photo, or
sweat-gland conditions that do not have a configured validated model.
"""

from __future__ import annotations

from clinical_intelligence_service import AREA_SYMPTOMS


KNOWLEDGE_VERSION = "dermamatrix-condition-knowledge-v1.2"
LAST_REVIEWED = "2026-09-07"

SOURCE_CATALOG = {
    "ham10000": {
        "title": "HAM10000 dataset label taxonomy",
        "url": "https://doi.org/10.1038/sdata.2018.161",
        "evidence_type": "Research dataset / model-label provenance",
    },
    "actinic_keratosis": {
        "title": "MedlinePlus: Actinic keratosis",
        "url": "https://www.medlineplus.gov/ency/article/000827.htm",
        "evidence_type": "NIH patient education",
    },
    "skin_cancer": {
        "title": "NCI: Skin cancer treatment (PDQ®)",
        "url": "https://www.cancer.gov/types/skin/patient/skin-treatment-pdq",
        "evidence_type": "NCI patient information",
    },
    "melanoma": {
        "title": "NCI: Melanoma treatment (PDQ®)",
        "url": "https://www.cancer.gov/types/skin/patient/melanoma-treatment-pdq",
        "evidence_type": "NCI patient information",
    },
    "moles": {
        "title": "MedlinePlus: Moles (nevus)",
        "url": "https://medlineplus.gov/moles.html",
        "evidence_type": "NIH patient education",
    },
    "acne_guideline": {
        "title": "American Academy of Dermatology: Acne clinical guideline",
        "url": "https://www.aad.org/member/clinical-quality/guidelines/acne",
        "evidence_type": "AAD clinical guideline",
    },
    "psoriasis_guideline": {
        "title": "American Academy of Dermatology: Psoriasis clinical guideline",
        "url": "https://www.aad.org/member/clinical-quality/guidelines/psoriasis",
        "evidence_type": "AAD clinical guideline",
    },
    "seborrheic_keratosis": {
        "title": "American Academy of Dermatology: Seborrheic keratoses overview",
        "url": "https://www.aad.org/public/diseases/a-z/seborrheic-keratoses-overview",
        "evidence_type": "AAD patient education",
    },
    "eczema_guideline": {
        "title": "American Academy of Dermatology: Atopic dermatitis clinical guideline",
        "url": "https://www.aad.org/member/clinical-quality/guidelines/atopic-dermatitis",
        "evidence_type": "AAD clinical guideline",
    },
    "ringworm": {
        "title": "American Academy of Dermatology: Ringworm overview",
        "url": "https://www.aad.org/public/diseases/a-z/ringworm-overview",
        "evidence_type": "AAD patient education",
    },
    "hair_loss": {
        "title": "American Academy of Dermatology: Male pattern hair loss",
        "url": "https://www.aad.org/public/diseases/hair-loss/treatment/male-pattern-hair-loss-treatment",
        "evidence_type": "AAD patient education",
    },
    "alopecia_areata": {
        "title": "American Academy of Dermatology: Alopecia areata diagnosis and treatment",
        "url": "https://www.aad.org/public/diseases/hair-loss/types/alopecia/treatment",
        "evidence_type": "AAD patient education",
    },
    "nail_fungus": {
        "title": "American Academy of Dermatology: Nail fungus diagnosis and treatment",
        "url": "https://www.aad.org/public/diseases/a-z/nail-fungus-treatment",
        "evidence_type": "AAD patient education",
    },
    "nail_psoriasis": {
        "title": "American Academy of Dermatology: Nail psoriasis",
        "url": "https://www.aad.org/public/diseases/psoriasis/treatment/genitals/nails",
        "evidence_type": "AAD patient education",
    },
    "seborrheic_dermatitis": {
        "title": "American Academy of Dermatology: Seborrheic dermatitis diagnosis and treatment",
        "url": "https://www.aad.org/public/diseases/a-z/seborrheic-dermatitis-treatment",
        "evidence_type": "AAD patient education",
    },
    "nail_abnormalities": {
        "title": "MedlinePlus: Nail abnormalities",
        "url": "https://medlineplus.gov/ency/article/003247.htm",
        "evidence_type": "NIH patient education",
    },
    "cyanosis": {
        "title": "MedlinePlus: Blue discoloration of the skin (cyanosis)",
        "url": "https://medlineplus.gov/ency/article/003215.htm",
        "evidence_type": "NIH patient education",
    },
    "hyperhidrosis": {
        "title": "NHS: Excessive sweating (hyperhidrosis)",
        "url": "https://www.nhs.uk/conditions/excessive-sweating-hyperhidrosis/",
        "evidence_type": "NHS patient education",
    },
}


def _education_topic(
    *, topic_id: str, name: str, health_area: str, aliases: tuple[str, ...], description: str,
    visual_features: tuple[str, ...], symptoms: tuple[str, ...], contributors: tuple[str, ...],
    differentials: tuple[str, ...], care_options: tuple[str, ...], medication_topics: tuple[dict, ...],
    routine: tuple[str, ...], lifestyle: tuple[str, ...], red_flags: tuple[str, ...],
    specialty: str, source_keys: tuple[str, ...], timeline: str,
) -> dict:
    """Create an educational topic that is intentionally separate from a model class."""
    # A single item can be supplied as a readable string in the compact catalog
    # below.  Keep the public contract consistently list-shaped rather than
    # serialising that string one character at a time.
    def listify(value: tuple | str) -> list:
        return [value] if isinstance(value, str) else list(value)

    return {
        "id": topic_id,
        "name": name,
        "health_area": health_area,
        "aliases": list(aliases),
        "description": description,
        "visual_features": listify(visual_features),
        "common_symptoms": listify(symptoms),
        "common_contributors": listify(contributors),
        "differential_diagnoses": listify(differentials),
        "care_options": listify(care_options),
        "medication_topics": listify(medication_topics),
        "daily_routine": listify(routine),
        "diet_lifestyle": listify(lifestyle),
        "red_flags": listify(red_flags),
        "doctor_specialty": specialty,
        "follow_up_timeline": timeline,
        "evidence_references": [SOURCE_CATALOG[key] for key in source_keys],
        "status": "EDUCATION_ONLY_NOT_A_MODEL_CLASS",
        "medical_notice": "This condition guide is educational. It does not confirm a diagnosis, select a treatment, or replace an examination by a qualified clinician.",
        "medication_notice": "Medication topics are for a clinician or pharmacist discussion. Availability, suitability, contraindications, and use depend on the person and jurisdiction; no dosage is provided here.",
        "version": KNOWLEDGE_VERSION,
        "last_reviewed": LAST_REVIEWED,
    }


COMMON_CONDITION_KNOWLEDGE = {
    "acne": _education_topic(
        topic_id="acne", name="Acne", health_area="Skin", aliases=("acne vulgaris", "blackheads", "whiteheads", "comedones"),
        description="A common inflammatory condition of hair follicles and oil glands that can include blackheads, whiteheads, inflamed bumps, or deeper lesions.",
        visual_features=("Open or closed comedones", "Inflamed papules or pustules", "Dark marks or scarring after spots heal"),
        symptoms=("Tenderness", "Inflammation", "Oily appearance"),
        contributors=("Follicular plugging and oil production", "Inflammation", "Hormonal influences", "Occlusive cosmetics or friction in some people"),
        differentials=("Folliculitis", "Irritant/contact dermatitis", "Keratosis pilaris"),
        care_options=("Gentle cleansing and non-comedogenic moisturising", "Broad-spectrum sun protection", "Avoid picking or harsh scrubbing"),
        medication_topics=(
            {"name": "Benzoyl peroxide, topical retinoids, salicylic acid, or azelaic acid", "access": "OTC or prescription availability varies", "note": "Evidence-based topical options to discuss; select one approach with professional guidance if irritation, pregnancy, or other treatment considerations apply."},
            {"name": "Oral antibiotics, hormonal therapy, or isotretinoin", "access": "Prescription treatment", "note": "Discuss with a dermatologist when clinically appropriate; these are not automatic treatment choices."},
        ),
        routine=("Cleanse gently", "Use non-comedogenic moisturiser if needed", "Use sun protection", "Avoid squeezing lesions"),
        lifestyle=("A balanced diet is reasonable; no single food universally causes acne", "Keep product changes gradual so irritation can be recognised"),
        red_flags=("Painful deep nodules or cysts", "Scarring or rapid worsening", "Significant distress or lack of improvement with appropriate care"),
        specialty="Dermatologist", source_keys=("acne_guideline",), timeline="Response varies; discuss persistent, scarring, or severe concerns with a dermatologist.",
    ),
    "atopic-dermatitis": _education_topic(
        topic_id="atopic-dermatitis", name="Atopic dermatitis / eczema", health_area="Skin", aliases=("eczema", "dry itchy rash"),
        description="A chronic inflammatory condition that commonly causes dry, itchy, inflamed skin. Several rashes can look similar, so an image alone may not distinguish them.",
        visual_features=("Dry or scaly areas", "Red or inflamed patches", "Scratch-related thickening in longstanding disease"),
        symptoms=("Itch", "Dryness", "Burning or cracking"),
        contributors=("Skin-barrier vulnerability", "Irritants or fragrance", "Climate and personal triggers"),
        differentials=("Contact dermatitis", "Psoriasis", "Fungal infection", "Bacterial infection"),
        care_options=("Fragrance-free moisturiser", "Gentle bathing and cleanser choices", "Avoid known irritants"),
        medication_topics=(
            {"name": "Topical corticosteroids or calcineurin inhibitors", "access": "Prescription or jurisdiction-dependent", "note": "A clinician chooses the right medicine, site, strength, and duration."},
        ),
        routine=("Moisturise after bathing", "Use fragrance-free products", "Avoid scratching and test new products on a small area first"),
        lifestyle=("Avoid blanket elimination diets unless a clinician identifies a reason", "Record personal triggers rather than assuming a single cause"),
        red_flags=("Fever, spreading redness, pain, pus, or crusting", "Blistering or extensive skin peeling", "Facial or eye involvement"),
        specialty="Dermatologist", source_keys=("eczema_guideline",), timeline="A clinician can tailor treatment when symptoms persist, disrupt sleep, or recur often.",
    ),
    "psoriasis": _education_topic(
        topic_id="psoriasis", name="Psoriasis", health_area="Skin", aliases=("plaque psoriasis", "scaly plaques"),
        description="A chronic immune-mediated inflammatory condition. It is not expected to have one simple permanent cure, and several other conditions can resemble it.",
        visual_features=("Well-demarcated scaly plaques", "Scalp involvement", "Possible nail changes"),
        symptoms=("Scaling", "Itch or burning", "Cracking or pain"),
        contributors=("Immune-mediated inflammation", "Stress, infection, skin trauma, or medication changes can matter for some people"),
        differentials=("Eczema", "Fungal infection", "Contact dermatitis", "Seborrheic dermatitis"),
        care_options=("Emollient skin care", "Avoid trauma and known triggers", "Clinical assessment of extent, location, and impact"),
        medication_topics=(
            {"name": "Topical corticosteroids, vitamin D analogues, or steroid-sparing topical agents", "access": "Clinician-directed treatment", "note": "Site and potency matter, particularly on thin skin or skin folds."},
            {"name": "Phototherapy, systemic therapy, or biologics", "access": "Specialist treatment", "note": "Used only after clinician assessment of severity and health context."},
        ),
        routine=("Use gentle moisturising care", "Avoid picking or harsh scale removal", "Record joint symptoms for medical discussion"),
        lifestyle=("Avoid smoking and manage stress where possible", "No single psoriasis cure diet is established"),
        red_flags=("Joint pain, swelling, or morning stiffness", "Extensive, painful, rapidly worsening, or infected skin", "Eye, genital, or widespread involvement"),
        specialty="Dermatologist", source_keys=("psoriasis_guideline",), timeline="Chronic disease management is individual; seek clinician review for new, extensive, or high-impact symptoms.",
    ),
    "seborrheic-keratosis": _education_topic(
        topic_id="seborrheic-keratosis", name="Seborrheic keratosis", health_area="Skin", aliases=("stuck-on growth", "waxy growth", "keratotic growth"),
        description="A common non-cancerous skin growth that may be brown, rough, waxy, or wart-like. A photo cannot reliably distinguish every changing pigmented lesion from other conditions.",
        visual_features=("Waxy or rough surface", "Stuck-on appearance", "Tan, brown, or darker colour"),
        symptoms=("Often no symptoms", "May itch or become irritated"),
        contributors=("Common with increasing age", "Individual susceptibility"),
        differentials=("Melanoma or other skin cancer", "Actinic keratosis", "Wart"),
        care_options=("Avoid self-removal", "Arrange dermatology review when a lesion changes, bleeds, itches, or looks different"),
        medication_topics=(),
        routine=("Avoid picking or attempting home removal", "Protect surrounding skin from irritation"),
        lifestyle=("No diet or supplement treats a skin growth", "Use professional review for a new, changing, dark, or bleeding lesion"),
        red_flags=("Rapid change, bleeding, persistent itch, or a new unusual lesion", "A lesion that differs from others or concerns the person"),
        specialty="Dermatologist", source_keys=("seborrheic_keratosis",), timeline="A dermatologist can examine a concerning growth and decide whether further assessment is needed.",
    ),
    "tinea": _education_topic(
        topic_id="tinea", name="Fungal skin infection / ringworm", health_area="Skin", aliases=("ringworm", "tinea corporis", "athlete's foot", "jock itch"),
        description="Ringworm is a fungal infection, not an infection caused by worms. Appearance varies by body site and can overlap with other rashes.",
        visual_features=("Scaly or raised border", "Ring-shaped patches on some body sites", "Cracking or peeling on feet"),
        symptoms=("Itch", "Scaling", "Burning or cracking"),
        contributors=("Warm or humid conditions", "Sweating", "Shared towels or footwear", "Close contact or occlusive clothing"),
        differentials=("Eczema", "Psoriasis", "Contact dermatitis", "Candidal/intertriginous rash"),
        care_options=("Keep the area dry", "Do not share towels or clothing", "Wash hands after touching an affected area"),
        medication_topics=(
            {"name": "Topical antifungal treatment", "access": "OTC or prescription availability varies", "note": "A pharmacist or clinician can help confirm whether a local skin infection is a suitable use case."},
            {"name": "Oral antifungal treatment", "access": "Prescription treatment", "note": "Scalp, nail, extensive, recurrent, or uncertain disease needs clinician assessment; do not self-start oral antifungals."},
        ),
        routine=("Keep skin folds and feet dry", "Use breathable footwear or clothing", "Avoid steroid-only self-treatment for a possible fungal rash"),
        lifestyle=("Do not share towels, socks, or footwear", "Clean and dry sports equipment or communal-area footwear"),
        red_flags=("Scalp involvement or widespread disease", "Fever, severe pain, pus, or rapidly spreading rash", "Diabetes, immunosuppression, pregnancy, or recurrent disease requiring tailored advice"),
        specialty="Dermatologist", source_keys=("ringworm",), timeline="A clinician should review uncertain, extensive, scalp, or recurrent infection; treatment duration depends on site and diagnosis.",
    ),
    "seborrheic-dermatitis": _education_topic(
        topic_id="seborrheic-dermatitis", name="Seborrheic dermatitis / dandruff", health_area="Hair", aliases=("dandruff", "scalp flaking", "scalp seborrheic dermatitis"),
        description="An inflammatory scalp and skin condition that can cause flaking, scale, redness, and itch. It can overlap with psoriasis or contact dermatitis.",
        visual_features=("Flaking or greasy scale", "Scalp, eyebrows, beard, or nose-fold involvement", "Redness"),
        symptoms=("Itch", "Flaking", "Scalp discomfort"),
        contributors=("Sebaceous activity and inflammatory response", "Personal susceptibility", "Product irritation can complicate symptoms"),
        differentials=("Scalp psoriasis", "Tinea capitis", "Contact dermatitis"),
        care_options=("Gentle scalp care", "Avoid aggressive scratching", "Review hair products that irritate the scalp"),
        medication_topics=(
            {"name": "Ketoconazole, selenium sulfide, zinc pyrithione, or salicylic-acid shampoo categories", "access": "OTC or prescription availability varies", "note": "Choose and use products according to label and pharmacist/clinician advice, especially with inflamed or broken skin."},
        ),
        routine=("Use a suitable anti-dandruff or gentle shampoo as advised", "Avoid harsh scratching", "Rinse products thoroughly"),
        lifestyle=("No specific supplement is established as a cure", "Seek advice if scalp symptoms are painful, patchy, or associated with hair loss"),
        red_flags=("Patchy hair loss, painful pustules, crusting, or swelling", "Rapid spread or symptoms in a child", "No response or worsening with reasonable care"),
        specialty="Dermatologist", source_keys=("seborrheic_dermatitis",), timeline="Review persistent, painful, or hair-loss-associated scalp symptoms with a dermatologist.",
    ),
    "pattern-hair-loss": _education_topic(
        topic_id="pattern-hair-loss", name="Pattern hair loss", health_area="Hair", aliases=("androgenetic alopecia", "male pattern hair loss", "female pattern hair loss", "crown thinning"),
        description="A common type of gradual hair thinning that often follows a pattern. A hair image alone cannot establish its cause or exclude other forms of hair loss.",
        visual_features=("Gradual crown thinning", "Receding hairline in some people", "Widening part or diffuse central thinning"),
        symptoms=("Hair thinning", "Increased visibility of scalp"),
        contributors=("Genetic and hormonal influences", "Age-related progression"),
        differentials=("Telogen effluvium", "Alopecia areata", "Traction-related loss", "Scalp inflammation or nutritional/systemic causes"),
        care_options=("Gentle hair practices", "Avoid traction and excess heat", "Clinical review to establish cause before medication"),
        medication_topics=(
            {"name": "Topical minoxidil", "access": "OTC availability varies", "note": "May be relevant after a clinician or pharmacist discussion; irritation and an initial shedding phase can occur."},
            {"name": "Finasteride or other hormonal approaches", "access": "Prescription treatment", "note": "Requires clinician assessment of suitability, risks, and interactions; it is never automatically recommended."},
        ),
        routine=("Avoid tight styles and damaging hair practices", "Use gentle scalp care", "Track changes over time rather than judging one photo"),
        lifestyle=("Adequate protein and balanced nutrition are reasonable", "Do not start supplements for a presumed deficiency without appropriate assessment"),
        red_flags=("Sudden or patchy loss", "Scalp pain, scale, redness, or scarring", "Hair loss with systemic symptoms or rapid progression"),
        specialty="Dermatologist", source_keys=("hair_loss",), timeline="Hair changes are slow; a clinician can establish the cause before discussing treatment options.",
    ),
    "alopecia-areata": _education_topic(
        topic_id="alopecia-areata", name="Alopecia areata", health_area="Hair", aliases=("patchy hair loss", "round bald patches"),
        description="An immune-mediated form of hair loss that can cause smooth, round or oval patches. Other causes of patchy hair loss need to be excluded clinically.",
        visual_features=("Smooth round or oval hair-loss patches", "Possible eyebrow or eyelash involvement"),
        symptoms=("Often little discomfort", "Sudden patchy hair loss"),
        contributors=("Immune-mediated process", "Individual health context"),
        differentials=("Tinea capitis", "Traction alopecia", "Scarring alopecia", "Trichotillomania"),
        care_options=("Avoid traumatic hair practices", "Seek a diagnosis before using disease-specific treatment"),
        medication_topics=(
            {"name": "Corticosteroid-based treatment, minoxidil adjunct, or other specialist therapies", "access": "Clinician-directed treatment", "note": "Choice depends on age, area, duration, and amount of hair loss."},
            {"name": "JAK inhibitors for selected extensive disease", "access": "Specialist prescription treatment", "note": "Requires dermatologist assessment and monitoring."},
        ),
        routine=("Protect exposed scalp from sun", "Avoid irritating treatments until the diagnosis is confirmed"),
        lifestyle=("Balanced nutrition is sensible; do not assume a supplement will treat an immune-mediated condition"),
        red_flags=("Rapid extensive loss", "Eyelash or eyebrow loss affecting eye protection", "Scarring, pain, scale, or systemic symptoms"),
        specialty="Dermatologist", source_keys=("alopecia_areata",), timeline="A dermatologist can determine whether observation, testing, or treatment is appropriate.",
    ),
    "onychomycosis": _education_topic(
        topic_id="onychomycosis", name="Nail fungus", health_area="Nails", aliases=("onychomycosis", "tinea unguium", "fungal nail infection"),
        description="A fungal nail infection may cause thickening, discoloration, debris, crumbling, or lifting. Nail psoriasis and trauma can look similar, so confirmation can matter.",
        visual_features=("Yellow, white, or brown discoloration", "Thickening or crumbling", "Nail lifting or debris beneath the nail"),
        symptoms=("Often painless", "Pressure discomfort in thick nails"),
        contributors=("Fungal exposure", "Longstanding athlete's foot", "Warm or moist footwear"),
        differentials=("Nail psoriasis", "Traumatic dystrophy", "Other nail disorders"),
        care_options=("Keep feet dry", "Avoid sharing footwear or nail tools", "Seek confirmation when the cause is uncertain"),
        medication_topics=(
            {"name": "Topical nail antifungal options", "access": "Prescription or jurisdiction-dependent", "note": "A clinician considers the nail area involved and diagnosis; skin antifungal creams do not necessarily treat nail infection."},
            {"name": "Oral terbinafine or itraconazole", "access": "Prescription treatment", "note": "Requires clinician review for interactions, pregnancy considerations, and possible monitoring."},
        ),
        routine=("Keep nails trimmed safely", "Keep feet dry and change socks", "Do not share nail tools"),
        lifestyle=("Do not use a nail image to choose supplements", "Discuss persistent changes with a clinician"),
        red_flags=("Pain, pus, spreading redness, or severe swelling", "Diabetes, poor circulation, immunosuppression, pregnancy, or uncertain diagnosis"),
        specialty="Dermatologist", source_keys=("nail_fungus",), timeline="Nails grow slowly; a confirmed condition can take prolonged clinician-guided treatment and visible change may lag.",
    ),
    "nail-psoriasis": _education_topic(
        topic_id="nail-psoriasis", name="Nail psoriasis", health_area="Nails", aliases=("nail pitting", "nail lifting", "nail dystrophy"),
        description="Psoriasis can cause pitting, discoloration, crumbling, debris under a nail, or nail lifting. Fungal infection and trauma can look similar, so an image alone is insufficient.",
        visual_features=("Tiny pits or grooves", "White, yellow, or brown discolouration", "Crumbling, lifting, or debris under a nail"),
        symptoms=("Nail appearance change", "Pressure discomfort in some cases"),
        contributors=("Psoriasis-related inflammation", "Possible coexistence with skin or joint psoriasis"),
        differentials=("Onychomycosis", "Traumatic nail dystrophy", "Other nail disorders"),
        care_options=("Avoid picking and aggressive manicuring", "Ask a clinician whether fungal testing is needed"),
        medication_topics=(
            {"name": "Topical corticosteroid, vitamin-D analogue, or other topical treatment", "access": "Clinician-directed treatment", "note": "The choice, nail site, and duration need dermatologist guidance."},
            {"name": "Systemic psoriasis treatment for selected disease", "access": "Specialist prescription treatment", "note": "Used only after assessment of skin, nails, joints, and health context."},
        ),
        routine=("Keep nails trimmed safely", "Avoid trauma and harsh cosmetic procedures", "Record pain, lifting, or joint symptoms for clinical discussion"),
        lifestyle=("Do not diagnose psoriasis or deficiency from nail appearance alone", "Do not begin supplements solely from a nail image"),
        red_flags=("Pain, swelling, pus, or spreading redness", "New joint pain or stiffness", "Rapid nail changes or uncertain cause"),
        specialty="Dermatologist", source_keys=("nail_psoriasis",), timeline="Nails grow slowly, so visible improvement often takes months after an accurate diagnosis and appropriate care.",
    ),
    "nail-change-deficiency": _education_topic(
        topic_id="nail-change-deficiency", name="Nail changes and possible deficiency", health_area="Nails", aliases=("koilonychia", "brittle nails", "nail ridging", "vitamin deficiency nails"),
        description="Nail appearance alone cannot confirm a vitamin, mineral, or protein deficiency. Trauma, fungal disease, psoriasis, circulation changes, and other conditions can look similar.",
        visual_features=("Brittleness, ridging, pale appearance, or spoon-like shape may have several causes"),
        symptoms=("Nail fragility or appearance change"),
        contributors=("Trauma", "Nail disease", "Systemic or nutritional factors in some cases"),
        differentials=("Onychomycosis", "Nail psoriasis", "Traumatic nail dystrophy", "Systemic illness"),
        care_options=("Protect nails from trauma and excess water exposure", "Seek clinical assessment if change persists"),
        medication_topics=(),
        routine=("Avoid picking and harsh cosmetic procedures", "Use gentle nail and cuticle protection"),
        lifestyle=("Eat a balanced diet with adequate protein", "Do not start iron, biotin, zinc, or other supplements solely from a nail image; discuss testing if clinically indicated"),
        red_flags=("Sudden widespread nail changes", "Pain, lifting, dark streaks, or changes with fatigue, breathlessness, or other systemic symptoms"),
        specialty="Dermatologist or primary-care clinician", source_keys=("nail_abnormalities",), timeline="The appropriate timeline depends on the cause and may require examination or laboratory testing.",
    ),
    "blue-nails": _education_topic(
        topic_id="blue-nails", name="Blue or violaceous nail discoloration", health_area="Nails", aliases=("blue nails", "purple nails", "cyanotic nail beds"),
        description="Blue or purple nails are not a vitamin-deficiency diagnosis. Cold exposure, circulation, oxygenation, medicine effects, trauma, or pigmentation can contribute.",
        visual_features=("Blue or purple color change of nail or surrounding tissue"),
        symptoms=("Color change",),
        contributors=("Cold exposure", "Circulation or oxygenation changes", "Medication effects or trauma"),
        differentials=("Peripheral cyanosis", "Trauma", "Pigmentation", "Vascular or systemic condition"),
        care_options=("Warm the area if cold exposure is the clear cause", "Seek clinical advice if the change persists or is unexplained"),
        medication_topics=(),
        routine=("Do not try to self-treat as a nutrient deficiency",),
        lifestyle=("Seek prompt care instead of supplementing if symptoms are concerning"),
        red_flags=("Shortness of breath", "Chest pain", "Confusion, severe weakness, or blue lips/face"),
        specialty="Urgent medical care or clinician depending on symptoms", source_keys=("cyanosis",), timeline="Urgent assessment is appropriate with breathing, chest, confusion, or severe weakness symptoms.",
    ),
    "hyperhidrosis": _education_topic(
        topic_id="hyperhidrosis", name="Excessive sweating", health_area="Sweat", aliases=("hyperhidrosis", "sweating pattern"),
        description="Sweating can be normal with heat, exercise, fever, anxiety, or environment. Persistent excessive sweating can be primary focal or secondary and needs context-based assessment.",
        visual_features=(), symptoms=("Sweating that is more frequent, localized, generalized, or disruptive"),
        contributors=("Heat or exercise", "Stress", "Medication or health changes in some people"),
        differentials=("Normal heat/exercise response", "Medication-related sweating", "Systemic causes requiring clinician assessment"),
        care_options=("Use the dedicated questionnaire", "Choose breathable clothing and manage heat exposure"),
        medication_topics=(
            {"name": "Antiperspirant and prescription/specialist treatments", "access": "Varies by treatment", "note": "A clinician should determine the cause and whether a treatment is appropriate."},
        ),
        routine=("Track triggers, body areas, and daily-life impact",),
        lifestyle=("Stay hydrated according to usual health needs", "Do not use an image to assess sweat-gland concerns"),
        red_flags=("New generalized night sweats, fever, weight change, chest symptoms, or a recent medicine/health change"),
        specialty="Qualified clinician", source_keys=("hyperhidrosis",), timeline="Use the questionnaire and seek evaluation if symptoms are new, generalized, severe, or disruptive.",
    ),
}


def educational_condition_catalog(area: str | None = None) -> list[dict]:
    """Return compact, display-safe topic metadata without treatment payloads."""
    records = COMMON_CONDITION_KNOWLEDGE.values()
    if area:
        records = (record for record in records if record["health_area"] == area)
    return [
        {
            "id": record["id"], "name": record["name"], "health_area": record["health_area"],
            "aliases": record["aliases"], "status": record["status"], "medical_notice": record["medical_notice"],
        }
        for record in records
    ]


def educational_condition_topic(topic_id: str) -> dict | None:
    """Return one source-linked education topic; never use it as a prediction."""
    return COMMON_CONDITION_KNOWLEDGE.get(topic_id)


def _research_label(*, code: str, name: str, aliases: tuple[str, ...], source_keys: tuple[str, ...]) -> dict:
    """Build conservative metadata for a class emitted by the research model."""
    return {
        "id": f"ham10000-{code}",
        "name": name,
        "health_area": "Skin",
        "aliases": list(aliases),
        "description": "A HAM10000 dermatoscopic research label. It is available only after the explicitly scoped research model runs and never confirms a diagnosis.",
        "common_symptoms": [],
        "visual_features": ["The only visual evidence exposed by this prototype is the model-derived research ranking and, when available, its Grad-CAM attention map."],
        "possible_causes": [],
        "risk_factors": [],
        "severity_indicators": [],
        "red_flags": [],
        "doctor_specialty": "Dermatologist",
        "self_care_guidance": "No condition-specific self-care or medicine is selected from this research label.",
        "routine_guidance": "Use the existing general routine only after considering personal tolerances and professional advice; it is not a treatment plan for this label.",
        "diet_lifestyle_guidance": "No condition-specific diet, supplement, recovery rate, or cure claim is generated from this label.",
        "treatment_categories": ["Professional evaluation", "Clinician-led treatment discussion if independently diagnosed"],
        "follow_up_guidance": "Timing depends on clinical examination, diagnosis, and change over time; this model does not predict recovery.",
        "prognosis_information": "Not determined by a research image-model label.",
        "product_categories": [],
        "monitoring_guidance": "Save a new assessment or self-reported check-in when a meaningful change occurs. The app does not passively monitor or compare retained images.",
        "urgency_level": "CONTEXT_DEPENDENT",
        "evidence_references": [SOURCE_CATALOG[key] for key in source_keys],
        "version": KNOWLEDGE_VERSION,
        "last_reviewed": LAST_REVIEWED,
        "status": "RESEARCH_LABEL_REFERENCE_ONLY",
    }


CONDITION_ONTOLOGY = {
    "akiec": _research_label(
        code="akiec", name="Actinic keratoses / intraepithelial carcinoma", aliases=("AKIEC",), source_keys=("ham10000", "actinic_keratosis"),
    ),
    "bcc": _research_label(
        code="bcc", name="Basal cell carcinoma", aliases=("BCC",), source_keys=("ham10000", "skin_cancer"),
    ),
    "bkl": _research_label(
        code="bkl", name="Benign keratosis-like lesion", aliases=("BKL",), source_keys=("ham10000",),
    ),
    "df": _research_label(
        code="df", name="Dermatofibroma", aliases=("DF",), source_keys=("ham10000",),
    ),
    "mel": _research_label(
        code="mel", name="Melanoma", aliases=("MEL",), source_keys=("ham10000", "melanoma"),
    ),
    "nv": _research_label(
        code="nv", name="Melanocytic nevus", aliases=("NV", "mole"), source_keys=("ham10000", "moles"),
    ),
    "vasc": _research_label(
        code="vasc", name="Vascular lesion", aliases=("VASC",), source_keys=("ham10000",),
    ),
}


def model_capability_matrix() -> list[dict]:
    """Expose the evidence boundary used by UI, API, and future integrations."""
    return [
        {
            "health_area": "Skin",
            "input": "Attested dermatoscopic single-lesion image",
            "model_supported_conditions": [entry["name"] for entry in CONDITION_ONTOLOGY.values()],
            "knowledge_conditions": [entry["name"] for entry in CONDITION_ONTOLOGY.values()],
            "likelihood": "Only with a version-matched independent-validation calibration artifact",
            "xai": "Grad-CAM only when the configured research model runs",
            "specialty": "Dermatologist",
            "monitoring": "Assessment metadata and self-reported check-ins; no stored-image comparison",
            "status": "RESEARCH_ONLY",
        },
        {
            "health_area": "Hair",
            "input": "Declared scalp or hair image",
            "model_supported_conditions": [],
            "knowledge_conditions": [],
            "likelihood": "Unavailable: no configured validated hair/scalp classifier",
            "xai": "Unavailable without a compatible classifier",
            "specialty": "Dermatologist",
            "monitoring": "Assessment metadata and self-reported check-ins",
            "status": "MODEL_NOT_CONFIGURED",
        },
        {
            "health_area": "Nails",
            "input": "Declared fingernail, toenail, or nail close-up",
            "model_supported_conditions": [],
            "knowledge_conditions": [],
            "likelihood": "Unavailable: no configured validated nail classifier",
            "xai": "Unavailable without a compatible classifier",
            "specialty": "Dermatologist",
            "monitoring": "Assessment metadata and self-reported check-ins",
            "status": "MODEL_NOT_CONFIGURED",
        },
        {
            "health_area": "Sweat",
            "input": "Questionnaire only",
            "model_supported_conditions": [],
            "knowledge_conditions": [],
            "likelihood": "Unavailable: transparent questionnaire prioritisation is not a validated condition model",
            "xai": "Questionnaire contribution summary; not SHAP",
            "specialty": "Qualified clinician determines the appropriate specialty",
            "monitoring": "Questionnaire assessment metadata and self-reported check-ins",
            "status": "RULE_BASED_PROTOTYPE",
        },
    ]


def _model_label_code(classifier: dict) -> str | None:
    predictions = classifier.get("top_predictions") or []
    if predictions and predictions[0].get("code") in CONDITION_ONTOLOGY:
        return predictions[0]["code"]
    code = (classifier.get("explainability") or {}).get("target_class")
    return code if code in CONDITION_ONTOLOGY else None


def _reported_context_factors(area: str, context: dict) -> list[dict]:
    labels = dict(AREA_SYMPTOMS.get(area, ()))
    factors = [
        {
            "type": "reported_symptom",
            "label": labels[symptom],
            "interpretation": "User-reported context for a clinician discussion; the app does not determine its cause.",
        }
        for symptom in context.get("relevant_symptoms", [])
        if symptom in labels
    ]
    if context.get("previous_care_reported"):
        factors.append({"type": "reported_prior_care", "label": "Previous care or treatment was reported", "interpretation": "Context only; it is not used to alter the image-model output."})
    if context.get("past_history_available") or context.get("current_history_available"):
        factors.append({"type": "saved_history_available", "label": "Saved health history is available", "interpretation": "A clinician can consider this context; free-text history is not used as an image-model feature or diagnostic fact."})
    if context.get("previous_assessment_count"):
        factors.append({"type": "prior_assessment_metadata", "label": f"{context['previous_assessment_count']} earlier saved assessment(s)", "interpretation": "Use comparable metadata for discussion only; differing model versions are not treated as progression."})
    return factors


def _follow_up_questions(area: str, context: dict) -> list[str]:
    labels = [label for symptom, label in AREA_SYMPTOMS.get(area, ()) if symptom not in set(context.get("relevant_symptoms", []))]
    if not labels:
        return ["Record a new check-in if the concern changes, persists, becomes painful, or worries you."]
    return [f"For a fuller discussion, record any relevant symptoms you have not yet selected: {', '.join(labels[:3])}."]


def _care_pathway(cdss: dict) -> dict:
    state = cdss.get("status", "UNCERTAIN")
    category = {
        "URGENT_EVALUATION_RECOMMENDED": "PROMPT PROFESSIONAL EVALUATION",
        "PROFESSIONAL_EVALUATION_RECOMMENDED": "PROFESSIONAL EVALUATION",
        "UNCERTAIN": "RETAKE / PROFESSIONAL DISCUSSION",
        "VALID_ASSESSMENT": "GENERAL SELF-CARE AND MONITORING",
    }.get(state, "PROFESSIONAL DISCUSSION")
    return {
        "category": category,
        "next_step": cdss.get("next_step", "Discuss ongoing concerns with a qualified clinician."),
        "prescription_status": "No independent prescription, dosage, diagnosis-specific treatment, or recovery promise is generated by this app.",
    }


def build_assessment_intelligence(*, area: str, classifier: dict, priority: dict, severity: dict, input_validation: dict, context: dict, cdss: dict, recommendations: dict) -> dict:
    """Compose model scope, knowledge metadata, declared context, and next steps.

    The returned object is persisted with an assessment, so every report can
    explain whether a conclusion came from a model, the knowledge registry, or
    user-provided context.  It must remain useful when no image model exists.
    """
    code = _model_label_code(classifier) if classifier.get("available") else None
    knowledge = CONDITION_ONTOLOGY.get(code) if code else None
    likelihood = classifier.get("condition_likelihood") or {}
    if knowledge and likelihood.get("available"):
        finding = {
            "status": "MODEL_SUPPORTED_CALIBRATED_RESEARCH_LABEL",
            "name": knowledge["name"],
            "condition_id": knowledge["id"],
            "model_class": code,
            "estimated_likelihood": likelihood.get("estimated_likelihood"),
            "label": "Calibrated research-model likelihood; not a diagnosis.",
            "notice": "The result remains research-only and requires independent clinical assessment.",
        }
    elif knowledge:
        top_prediction = classifier.get("top_prediction") or {}
        finding = {
            "status": "MODEL_SUPPORTED_RESEARCH_RANKING_ONLY",
            "name": knowledge["name"],
            "condition_id": knowledge["id"],
            "model_class": code,
            "estimated_likelihood": None,
            "relative_score": top_prediction.get("relative_score"),
            "label": "Highest-ranked research label; raw model ranking is not a real-world likelihood or diagnosis.",
            "notice": likelihood.get("notice") or "No calibrated condition likelihood is available.",
        }
    else:
        finding = {
            "status": "NO_MODEL_SUPPORTED_FINDING",
            "name": None,
            "condition_id": None,
            "estimated_likelihood": None,
            "label": "No model-supported condition finding is available for this assessment.",
            "notice": "The app preserves quality, reported symptoms, and next-step guidance without assigning an unsupported condition.",
        }

    doctor_specialty = knowledge["doctor_specialty"] if knowledge else ("Dermatologist" if area in {"Skin", "Hair", "Nails"} else "Qualified clinician")
    product_categories = [item.get("category") for item in recommendations.get("products", []) if item.get("category")]
    return {
        "knowledge_version": KNOWLEDGE_VERSION,
        "last_reviewed": LAST_REVIEWED,
        "finding": finding,
        "model_scope": {
            "input_validation": input_validation.get("status"),
            "model_available": bool(classifier.get("available")),
            "uncertainty": (classifier.get("uncertainty") or {}).get("status", "NOT_AVAILABLE"),
            "explanation": "Grad-CAM is included only when generated by the compatible research image model. It highlights model attention and is not lesion segmentation or proof of disease.",
        },
        "reported_context_factors": _reported_context_factors(area, context),
        "symptom_follow_up": _follow_up_questions(area, context),
        "reported_symptom_severity": {
            "level": severity.get("level"),
            "label": severity.get("label"),
            "validation_status": severity.get("validation_status"),
        },
        "reported_concern_priority": {
            "score": priority.get("score"),
            "level": priority.get("level"),
            "label": priority.get("label"),
            "validation_status": priority.get("validation_status"),
        },
        "care_pathway": _care_pathway(cdss),
        "follow_up": {
            "guidance": knowledge["follow_up_guidance"] if knowledge else cdss.get("monitoring"),
            "timeline": "No recovery timeline is predicted by this prototype.",
            "monitoring": cdss.get("monitoring"),
        },
        "doctor": {
            "recommended": bool(cdss.get("professional_evaluation_recommended")),
            "urgent": bool(cdss.get("urgent_evaluation_recommended")),
            "specialty": doctor_specialty,
            "directory": "Use the existing location-based directory handoff for current listing, rating, contact, and clinic booking details.",
            "appointment": "Appointment availability and confirmation remain with the clinic or external booking provider; no appointment is created by this app.",
        },
        "commerce": {
            "product_categories": product_categories,
            "eligible": recommendations.get("product_guidance") == "GENERAL_SELF_CARE_ONLY",
            "independence": "Products are selected downstream from existing care categories. Affiliate links never alter model output, likelihood, symptom severity, priority, CDSS, or doctor guidance.",
        },
        "knowledge": {
            "condition_available": bool(knowledge),
            "status": knowledge.get("status") if knowledge else "NO_MODEL_SUPPORTED_CONDITION",
            "references": knowledge.get("evidence_references", []) if knowledge else [],
            "condition_version": knowledge.get("version") if knowledge else None,
        },
    }
