"""Structured, non-prescription care content for the education prototype.

Content is grouped here instead of being generated from a model prediction or
hard-coded in the browser. It must not be used as a disease treatment plan.
"""

from __future__ import annotations

from commerce_service import materialize_product
from condition_knowledge import COMMON_CONDITION_KNOWLEDGE


# These are education-topic matches to an already emitted model class or an
# explicitly reported/reference pattern. They do not create an image finding.
MODEL_TOPICS = {
    "Eczema / dermatitis": "atopic-dermatitis",
    "Folliculitis / acne-like": "acne",
    "Psoriasis / papulosquamous": "psoriasis",
    "Pitting": "nail-psoriasis",
    "Koilonychia": "nail-change-deficiency",
    "Blue Nail": "blue-nails",
    "Onychogryphosis": "onychogryphosis",
    "Melanonychia": "melanonychia",
}

TOPIC_PRODUCTS = {
    "acne": ("gentle-cleanser", "barrier-moisturiser", "sun-protection", "salicylic-acid", "benzoyl-peroxide", "azelaic-acid"),
    "atopic-dermatitis": ("gentle-cleanser", "barrier-moisturiser", "sun-protection"),
    "psoriasis": ("gentle-cleanser", "barrier-moisturiser", "psoriasis-emollient"),
    "hyperpigmentation": ("gentle-cleanser", "barrier-moisturiser", "sun-protection", "azelaic-acid"),
    "tinea": ("gentle-cleanser", "topical-antifungal"),
    "seborrheic-keratosis": ("gentle-cleanser", "sun-protection"),
    "seborrheic-dermatitis": ("scalp-cleanser", "gentle-conditioner", "ketoconazole-shampoo", "selenium-sulfide-shampoo"),
    "pattern-hair-loss": ("scalp-cleanser", "gentle-conditioner", "minoxidil-category"),
    "alopecia-areata": ("scalp-cleanser", "gentle-conditioner"),
    "scalp-psoriasis": ("scalp-cleanser", "gentle-conditioner"),
    "onychomycosis": ("nail-clippers", "breathable-socks", "nail-antifungal"),
    "onychogryphosis": ("nail-clippers", "breathable-socks"),
    "melanonychia": ("nail-clippers", "nail-emollient"),
    "nail-psoriasis": ("nail-emollient", "protective-gloves", "nail-clippers"),
    "nail-change-deficiency": ("nail-emollient", "protective-gloves", "nail-clippers"),
    "blue-nails": ("nail-emollient", "nail-clippers"),
}

# A topic changes the nutrition discussion only where there is a useful,
# source-linked distinction. None of these statements diagnoses a deficiency.
TOPIC_NUTRITION_CONTEXT = {
    "acne": "If breakouts are the concern, lower-glycemic food choices may help some people; diet alone is not an acne treatment.",
    "atopic-dermatitis": "Avoid blanket food elimination for eczema unless a clinician identifies a specific reason.",
    "psoriasis": "No single diet cures psoriasis; focus on a sustainable balanced eating pattern.",
    "hyperpigmentation": "No supplement or restrictive diet is a proven universal treatment for dark marks.",
    "tinea": "Food or supplements do not replace assessment and appropriate antifungal care for a suspected skin infection.",
    "seborrheic-keratosis": "Diet or supplements do not remove a skin growth; changing lesions need examination.",
    "seborrheic-dermatitis": "No specific supplement is established as a cure for scalp flaking.",
    "pattern-hair-loss": "Adequate protein matters for general hair health; discuss iron or other testing only when history suggests a deficiency.",
    "alopecia-areata": "A balanced diet supports general health, but supplements are not an established treatment for immune-mediated patchy loss.",
    "scalp-psoriasis": "No food or supplement can confirm or treat the cause of scalp scale from a photograph.",
    "onychomycosis": "Diet or supplements do not replace diagnosis and treatment of a suspected fungal nail infection.",
    "onychogryphosis": "A thick curved nail calls for pressure relief and safe nail care; nutrition cannot determine or remove its cause.",
    "melanonychia": "A new or changing dark nail streak needs examination, not a supplement or diet change.",
    "nail-psoriasis": "No supplement can establish or treat nail psoriasis from nail appearance alone.",
    "nail-change-deficiency": "Nail shape alone cannot establish low iron or another nutrient deficiency; discuss testing before supplements.",
    "blue-nails": "Blue nail color is not evidence of a vitamin deficiency; urgent symptoms need prompt medical assessment.",
}


def _education_topic(area: str, classifier: dict, evidence: dict, reference: dict | None) -> tuple[dict | None, str]:
    label = (classifier.get("top_prediction") or {}).get("condition")
    topic_id = None
    source = ""
    if reference and reference.get("matched"):
        topic_id = "scalp-psoriasis" if area == "Hair" and reference.get("topic_id") == "psoriasis" else reference.get("topic_id")
        source = "exact_reference_file"
    if not topic_id and classifier.get("available") and not classifier.get("non_condition_top_class"):
        topic_id, source = MODEL_TOPICS.get(label), "research_model_ranking"
    if not topic_id and area == "Hair":
        symptoms = set(((evidence.get("reported_context") or {}).get("symptoms") or []))
        if "scalp_scaling" in symptoms or "scalp_itching" in symptoms:
            topic_id, source = "seborrheic-dermatitis", "reported_symptom_pattern"
        elif "hair_loss" in symptoms:
            topic_id, source = "pattern-hair-loss", "reported_symptom_pattern"
    topic = COMMON_CONDITION_KNOWLEDGE.get(topic_id)
    return (topic, source) if topic and topic["health_area"] == area else (None, "")


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

EVERYDAY_NUTRITION = [
    {"title": "Build a balanced day", "items": [
        "Include a protein food at regular meals: beans, lentils, tofu, eggs, fish, poultry, dairy, or another food you enjoy.",
        "Vary vegetables and fruit across the week; fresh, frozen, and cooked choices all count.",
        "Choose whole grains often, and add nuts, seeds, or other unsaturated-fat foods when they fit your diet.",
    ]},
    {"title": "Fluids and supplements", "items": [
        "Keep water accessible and drink according to thirst, activity, climate, and any advice for your health conditions.",
        "Use food variety as the starting point; a skin, hair, or nail photo cannot identify a nutrient deficiency.",
        "If your diet is restricted or you suspect a deficiency, discuss it and any supplements with a clinician or dietitian.",
    ]},
]

EVERYDAY_LIFESTYLE = [
    {"title": "Everyday foundations", "items": [
        "Keep a regular sleep schedule; most adults need at least 7 hours of sleep each night.",
        "Build movement into the week. For adults, a practical goal is 150 minutes of moderate activity, adjusted to ability.",
        "Make room for stress relief that works for you, such as a walk, breathing break, or time with people you trust.",
    ]},
]

EVERYDAY_CARE_SOURCES = [
    {"label": "USDA: build balanced meals", "url": "https://www.myplate.gov/sites/default/files/2024-06/Tipsheet-1-Start-Simple-With-MyPlate.pdf"},
    {"label": "CDC: sleep", "url": "https://www.cdc.gov/sleep/about/"},
    {"label": "CDC: adult movement", "url": "https://www.cdc.gov/physical-activity-basics/guidelines/adults.html"},
]

# Area-based education is shown for every image, including an unclear photo or
# a high-priority reported symptom. It describes common issues, never findings
# inferred from that particular image. Sources are public patient guidance.
AREA_CARE_GUIDANCE = {
    "Skin": {
        "common_symptoms": ["Dryness, tightness, flaking, or itching", "Redness, burning, or sensitivity", "Pimples, clogged pores, or excess oil", "Dark marks or changing color"],
        "cause_sections": [
            {"title": "Everyday triggers", "items": ["Cold or dry weather, frequent washing, and harsh soaps can leave skin dry or irritated.", "A new cosmetic, fragrance, detergent, or topical product can cause irritation or an allergic contact reaction.", "Sweat, friction from clothing or masks, and picking can aggravate existing spots."]},
            {"title": "Common skin patterns", "items": ["Blocked pores and acne can cause blackheads, whiteheads, or inflamed pimples.", "Eczema or other inflammatory skin conditions can cause dry, itchy, sensitive patches.", "Some spreading or persistent rashes may be due to infection; a photo alone cannot tell which kind."]},
            {"title": "Color and change", "items": ["Sun exposure can deepen some dark marks and affect skin over time.", "Inflammation or a healed breakout can leave temporary darker or lighter marks.", "A changing, bleeding, or painful spot needs an in-person examination rather than a cause guessed from color." ]},
        ],
        "care_sections": [
            {"title": "Gentle daily basics", "items": ["Wash with lukewarm water and a mild cleanser, using fingertips rather than a scrub.", "Apply fragrance-free moisturiser to slightly damp skin, especially after washing.", "Use broad-spectrum SPF 30+ sunscreen or protective clothing on exposed skin when outdoors."]},
            {"title": "Adapt to what you notice", "items": ["If skin feels dry or stings, simplify to cleanser, moisturiser, and sun protection until it settles.", "If breakouts are the concern, choose products labelled non-comedogenic and avoid picking spots.", "Introduce one new product at a time so you can tell what helps or irritates."]},
            {"title": "Know when to follow up", "items": ["Record changes in size, color, pain, itching, and any new products.", "Arrange a clinician review for persistent rash, deep painful acne, spreading redness, bleeding, or rapid change."]},
        ],
        "routine": {
            "morning": ["Cleanse skin gently if needed; avoid scrubs and very hot water.", "Apply a moisturiser suited to your skin, focusing on dry areas.", "Finish with broad-spectrum SPF 30+ sunscreen on exposed skin before going outdoors."],
            "evening": ["Remove makeup and sunscreen with a gentle cleanser without rubbing hard.", "Moisturise while skin is slightly damp; leave irritated spots alone.", "If you use an acne active for a confirmed concern, follow its label and avoid adding several actives together."],
            "weekly": ["Review whether a product is helping after consistent use; change only one step at a time.", "Clean items that regularly touch your face, such as makeup tools, without over-washing skin."],
            "follow_up": ["Note new products and whether dryness, itching, breakouts, or color changes improve or worsen.", "Seek an in-person review for a rapidly changing, painful, bleeding, or persistent area."],
        },
        "treatment_sections": [
            {"title": "For dryness or sensitivity", "items": ["A gentle cleanser and richer fragrance-free cream or ointment may help the skin barrier.", "If an itchy, inflamed rash persists, a clinician can decide whether an anti-inflammatory treatment is appropriate."]},
            {"title": "For acne-like breakouts", "items": ["For mild blackheads or pimples, a pharmacist can help you choose one suitable acne ingredient to start with.", "Deep, painful, or scarring acne needs a dermatologist's treatment plan."]},
            {"title": "For spreading or unusual changes", "items": ["A clinician may need to examine a rash before deciding whether an antifungal, antibacterial, or other treatment fits.", "A changing mole or bleeding spot needs direct examination; skin-care products are not a substitute." ]},
        ],
        "nutrition_sections": [
            {"title": "Food choices for skin", "items": [
                "Add vitamin-C-rich produce such as citrus, guava, peppers, tomatoes, or broccoli; vitamin C supports normal collagen formation.",
                "If breakouts are your concern, try replacing frequent sugary drinks and refined snacks with beans, oats, fruit, and vegetables; some people notice fewer breakouts with lower-glycemic choices.",
                "Notice your own food triggers without cutting out entire food groups by default; diet alone does not clear every skin concern.",
            ]},
            {"title": "Simple meal ideas", "items": [
                "Breakfast: oats with yogurt or fortified soy, fruit, and nuts; or eggs and whole-grain toast with fruit.",
                "Lunch: dal or beans with roti or rice and a generous serving of vegetables.",
                "Dinner: fish, tofu, paneer, or chickpeas with colorful vegetables and a whole grain.",
            ]},
        ],
        "lifestyle_sections": [
            {"title": "Skin-friendly habits", "items": [
                "Use shade, clothing, and broad-spectrum SPF 30+ sunscreen when outdoors; reapply as directed.",
                "Wash gently after heavy sweating and keep showers lukewarm if heat or dryness irritates your skin.",
                "Avoid picking spots or scrubbing sensitive areas; use one new skin product at a time.",
            ]},
            {"title": "Notice what changes", "items": [
                "Note new cosmetics, detergents, sun exposure, or friction if a rash or irritation recurs.",
                "Use consistent lighting for future photos and seek care for rapid changes, bleeding, or persistent pain.",
            ]},
        ],
        "medication_topics": [
            {"name": "Benzoyl peroxide", "used_for": "A common option for mild inflammatory pimples; can dry, irritate, or bleach fabric. Follow the label."},
            {"name": "Salicylic acid", "used_for": "Often used for blackheads and clogged pores; reduce use if skin becomes dry or irritated."},
            {"name": "Azelaic acid", "used_for": "Used for some acne and marks after breakouts; availability and strength vary by location."},
            {"name": "Adapalene", "used_for": "A retinoid option for acne in some places; check suitability first, especially if pregnant or planning pregnancy."},
            {"name": "Anti-inflammatory or antifungal cream", "used_for": "A clinician or pharmacist may recommend one after the cause of an itchy or spreading rash is assessed."},
        ],
        "product_ids": ["gentle-cleanser", "barrier-moisturiser", "sun-protection", "salicylic-acid", "benzoyl-peroxide", "azelaic-acid"],
        "sources": [
            {"label": "AAD: simple skin care", "url": "https://www.aad.org/public/everyday-care/skin-care-basics/care/skin-care-budget"},
            {"label": "AAD: acne treatment ingredients", "url": "https://www.aad.org/public/diseases/acne/diy/adult-acne-treatment"},
            {"label": "AAD: eczema skin care", "url": "https://www.aad.org/public/diseases/eczema/types/atopic-dermatitis/atopic-dermatitis-coping"},
            {"label": "AAD: diet and acne", "url": "https://www.aad.org/public/diseases/acne/causes/diet"},
            {"label": "NIH: vitamin C", "url": "https://ods.od.nih.gov/factsheets/VitaminC-Consumer/"},
        ],
    },
    "Hair": {
        "common_symptoms": ["Scalp itching or visible flakes", "Excess oil or scalp dryness", "Increased shedding or thinning", "Hair breakage or tender scalp"],
        "cause_sections": [
            {"title": "Scalp and hair care", "items": ["Dandruff, oiliness, dryness, or sensitivity to a hair product can cause flakes or itching.", "Repeated heat, bleaching, relaxers, or rough brushing can weaken strands and increase breakage.", "Tight hairstyles or extensions can pull on follicles and contribute to hairline loss." ]},
            {"title": "Shedding and thinning", "items": ["Illness, childbirth, surgery, major stress, or rapid weight change can be followed by temporary shedding.", "Inherited pattern hair loss can cause a widening part, receding hairline, or gradual thinning.", "Low protein or iron intake, thyroid changes, hormones, or some medicines can also contribute." ]},
            {"title": "Patterns needing a closer look", "items": ["Round bald patches may have a different cause from diffuse shedding.", "Pain, redness, scale, scarring, or broken hairs can signal a scalp condition or infection.", "The pattern, timing, scalp examination, and sometimes tests help determine the actual cause." ]},
        ],
        "care_sections": [
            {"title": "Keep the scalp comfortable", "items": ["Wash the scalp as often as your hair texture, oiliness, and activity need; massage gently rather than scratching.", "Rinse shampoo thoroughly and stop a product that repeatedly burns or irritates.", "If flakes are the main concern, a labelled dandruff shampoo may help; follow its instructions." ]},
            {"title": "Protect fragile strands", "items": ["Use conditioner mainly on hair lengths to reduce tangles and friction.", "Detangle gently, especially when wet; avoid pulling at knots.", "Reduce tight styles, frequent high heat, or harsh chemical processing if breakage is increasing." ]},
            {"title": "Track meaningful change", "items": ["Note whether loss is gradual, patchy, or sudden and whether the scalp itches or hurts.", "Seek a clinician review for new bald patches, persistent heavy shedding, scalp pain, or scarring." ]},
        ],
        "routine": {
            "morning": ["Style hair with minimal pulling and use a wide-tooth comb or gentle brush where helpful.", "Use a loose hairstyle if the scalp or hairline feels tight.", "Protect exposed scalp from sun with a hat or suitable sun protection."],
            "evening": ["Wash the scalp when needed; apply shampoo to the scalp and conditioner mainly to hair lengths.", "Dry gently rather than rubbing vigorously with a towel.", "Avoid sleeping with tight braids or styles that pull on the hairline."],
            "weekly": ["Review how often the scalp needs washing and adjust to oiliness, sweat, and hair texture.", "If using a dandruff shampoo, use it according to its label and watch for irritation."],
            "follow_up": ["Track shedding, new bald patches, persistent flakes, or scalp discomfort over several weeks.", "Arrange a review for sudden or patchy loss, pain, scarring, or persistent scalp symptoms."],
        },
        "treatment_sections": [
            {"title": "If flakes or itching dominate", "items": ["Dandruff shampoos with labelled active ingredients can help mild flaking when used as directed.", "Persistent redness, thick scale, pain, or hair loss needs an examination to distinguish other scalp conditions." ]},
            {"title": "If thinning is the concern", "items": ["A clinician can help identify whether loss is patterned, temporary shedding, traction-related, or another type.", "Topical minoxidil is an option for some pattern loss; the expected benefit, ongoing use, and suitability should be reviewed." ]},
            {"title": "If the scalp is inflamed", "items": ["Infection or inflammatory scalp disease may need a prescribed treatment chosen after assessment.", "New patchy or scarring hair loss is worth early specialist review." ]},
        ],
        "nutrition_sections": [
            {"title": "Nutrients for hair", "items": [
                "Eat enough overall and include protein regularly; very low-calorie diets and too little protein or iron can contribute to shedding.",
                "Pair iron-rich beans, lentils, spinach, meat, or seafood with vitamin-C foods such as citrus, guava, tomatoes, or peppers; vitamin C helps absorb plant iron.",
                "Use nuts, seeds, beans, eggs, seafood, or meat for a mix of zinc and other nutrients rather than relying on a hair supplement.",
            ]},
            {"title": "Simple meal ideas", "items": [
                "Breakfast: eggs or tofu with whole-grain toast and fruit; or oatmeal with milk or fortified soy and nuts.",
                "Lunch: lentils or chickpeas with roti or rice, greens, and lemon or tomatoes.",
                "Dinner: fish, chicken, tofu, or beans with vegetables; add a snack if meals are small or activity is high.",
            ]},
        ],
        "lifestyle_sections": [
            {"title": "Protect hair and scalp", "items": [
                "Loosen styles that pull at the roots and change tight hairstyles if the hairline feels sore.",
                "Limit high heat and harsh chemical treatments when hair is fragile; comb gently without tugging.",
                "Cleanse the scalp as needed for your hair type, especially if sweat or oil builds up.",
            ]},
            {"title": "Track shedding patterns", "items": [
                "Record recent illness, major stress, weight change, or new medicines if shedding starts or increases.",
                "Seek a review for sudden patches, scalp pain, scarring, or persistent heavy shedding.",
            ]},
        ],
        "medication_topics": [
            {"name": "Ketoconazole shampoo", "used_for": "A medicated shampoo option for dandruff-type flaking; follow the label and check suitability."},
            {"name": "Selenium sulfide shampoo", "used_for": "Another dandruff shampoo option; apply to the scalp as the label directs and stop if irritated."},
            {"name": "Other dandruff shampoos", "used_for": "Zinc pyrithione or salicylic acid shampoos may be available depending on location and scalp need."},
            {"name": "Topical minoxidil", "used_for": "An option for some pattern hair loss, with regular use and clinician or pharmacist guidance about suitability."},
            {"name": "Clinician-directed scalp treatment", "used_for": "An inflammatory or infected scalp may need a prescribed medicine after examination; a photo cannot choose it."},
        ],
        "product_ids": ["scalp-cleanser", "gentle-conditioner", "ketoconazole-shampoo", "selenium-sulfide-shampoo", "minoxidil-category"],
        "sources": [
            {"label": "AAD: dandruff care", "url": "https://www.aad.org/public/everyday-care/hair-scalp-care/scalp/treat-dandruff"},
            {"label": "AAD: managing hair loss", "url": "https://www.aad.org/public/diseases/hair-loss/treatment/tips"},
            {"label": "AAD: hair loss causes", "url": "https://www.aad.org/public/diseases/hair-loss/causes/18-causes"},
            {"label": "AAD: pattern hair loss options", "url": "https://www.aad.org/public/diseases/hair-loss/treatment/male-pattern-hair-loss-treatment"},
            {"label": "NIH: iron-rich foods", "url": "https://ods.od.nih.gov/factsheets/Iron-Consumer/"},
        ],
    },
    "Nails": {
        "common_symptoms": ["Brittle, peeling, or splitting nails", "Thickening, discoloration, or lifting", "Soreness or swelling around a nail", "Ridges or a change in nail shape"],
        "cause_sections": [
            {"title": "Wear and exposure", "items": ["Repeated wet work, detergents, and polish removal can make nails brittle or peeling.", "Nail biting, aggressive manicures, or using nails as tools can injure the nail and cuticle.", "Tight shoes or repeated toe impact can change nail shape or color." ]},
            {"title": "Common nail conditions", "items": ["A fungal infection can cause some nails to thicken, crumble, or discolor, especially toenails.", "Psoriasis and other skin conditions can cause pitting, lifting, or changes in nail texture.", "Redness, warmth, and swelling around a nail may reflect an infection or ingrown nail." ]},
            {"title": "Other changes to check", "items": ["A new medicine or health condition can sometimes affect nail growth or appearance.", "A new or changing dark streak, painful lifting, or persistent swelling needs direct examination.", "Fungus, injury, and psoriasis can look similar; a clinician may need to examine or test a sample." ]},
        ],
        "care_sections": [
            {"title": "Daily nail care", "items": ["Keep nails clean and dry, trim straight across, and gently smooth snagged edges.", "Moisturise the nail plate and surrounding skin after washing.", "Leave cuticles intact and avoid digging under a painful or lifting nail." ]},
            {"title": "Protect hands and feet", "items": ["Wear gloves for prolonged wet work or cleaning, then dry hands thoroughly.", "Choose shoes with enough room for toes and change damp socks.", "Avoid sharing clippers and use clean tools for nail care." ]},
            {"title": "Respond to changes", "items": ["Do not hide a changing nail under artificial nails while trying to understand the cause.", "Arrange a review for pain, swelling, spreading discoloration, lifting, or a new dark streak." ]},
        ],
        "routine": {
            "morning": ["Dry hands and feet well, including around nails.", "Apply a simple moisturiser to nails and surrounding skin.", "Choose comfortable shoes and fresh, dry socks for toenail care."],
            "evening": ["Wash and dry hands or feet gently after the day.", "Check for new pain, swelling, color change, or lifting.", "Moisturise cuticles and surrounding skin; avoid picking or cutting them."],
            "weekly": ["Trim nails as needed with clean clippers and file snagged edges.", "Take a break from polish or artificial nails if nails are dry or splitting."],
            "follow_up": ["Compare a changing nail as it grows out; record pain, spreading discoloration, or swelling.", "Ask a clinician or pharmacist about a persistent thick or discolored nail before treating it as fungus."],
        },
        "treatment_sections": [
            {"title": "If nails are brittle", "items": ["Moisturising and reducing repeated wet work can help protect brittle nails.", "Treating the underlying cause matters if the nail keeps splitting or lifting." ]},
            {"title": "If fungus is suspected", "items": ["A pharmacist can discuss a nail lacquer for a likely fungal problem; treatment may take months.", "A clinician may test a persistent nail before considering prescription tablets." ]},
            {"title": "If painful or inflamed", "items": ["A swollen nail fold, ingrown nail, or dark streak needs an in-person look before treatment is chosen.", "A dermatologist can distinguish nail psoriasis, injury, and infection when appearances overlap." ]},
        ],
        "nutrition_sections": [
            {"title": "Nutrients for nails", "items": [
                "Include protein foods regularly alongside varied vegetables, fruit, and whole grains.",
                "Include iron and zinc foods such as lentils, beans, meat, seafood, nuts, and seeds; add fruit or vegetables with vitamin C to plant-iron meals.",
                "Foods such as eggs, fish, nuts, seeds, and some vegetables contain biotin; routine high-dose biotin pills have limited evidence for healthy nails.",
            ]},
            {"title": "Simple meal ideas", "items": [
                "Breakfast: eggs or yogurt or fortified soy with fruit and whole grains.",
                "Lunch: beans or lentils with vegetables, roti or rice, and lemon or tomatoes.",
                "Dinner: fish, tofu, meat, or chickpeas with cooked greens and a whole grain; nuts or seeds make an easy snack.",
            ]},
        ],
        "lifestyle_sections": [
            {"title": "Protect nails daily", "items": [
                "Wear gloves for repeated dishwashing or cleaning and dry hands well afterward.",
                "Moisturise nails and surrounding skin after handwashing; trim nails and smooth snagged edges.",
                "Avoid biting nails, cutting cuticles, or using nails as tools; take breaks from harsh manicures.",
            ]},
            {"title": "Foot and nail checks", "items": [
                "Keep feet dry, change damp socks, and choose shoes that do not press on toenails.",
                "Do not share clippers; note spreading discoloration, pain, lifting, or swelling for a clinician review.",
            ]},
        ],
        "medication_topics": [
            {"name": "Antifungal nail lacquer", "used_for": "A pharmacist may suggest this for a likely fungal nail; it often takes months and is not suitable for everyone."},
            {"name": "Prescription antifungal tablets", "used_for": "A clinician may consider these for confirmed or persistent fungal nail infection; interactions and liver monitoring can matter."},
            {"name": "Treatment for an infected nail fold", "used_for": "A painful, swollen nail fold may need clinician-directed care, sometimes including an antibiotic."},
            {"name": "Treatment for nail psoriasis", "used_for": "A dermatologist may choose anti-inflammatory treatment if psoriasis is the cause; antifungals would not address it."},
        ],
        "product_ids": ["nail-emollient", "protective-gloves", "nail-antifungal", "nail-clippers", "breathable-socks"],
        "sources": [
            {"label": "AAD: healthy nail care", "url": "https://www.aad.org/public/everyday-care/nail-care-secrets/basics/healthy-nail-tips"},
            {"label": "AAD: nail changes to examine", "url": "https://www.aad.org/public/everyday-care/nail-care-secrets/basics/nail-changes-dermatologist-should-examine"},
            {"label": "NHS: fungal nail infection", "url": "https://www.nhs.uk/conditions/fungal-nail-infection/"},
            {"label": "NIH: biotin evidence", "url": "https://ods.od.nih.gov/factsheets/Biotin-Consumer/"},
        ],
    },
}

DERMOSCOPY_DISCUSSION_GUIDANCE = {
    "common_symptoms": ["A spot that changes in size, shape, or color", "Bleeding, crusting, pain, or persistent itching"],
    "cause_sections": [{"title": "What an image cannot establish", "items": ["Several benign and concerning lesions can look alike in a photograph.", "A clinician may need examination, dermoscopy, or tissue sampling to determine the cause."]}],
    "care_sections": [{"title": "Follow-up", "items": ["Record meaningful changes and arrange direct review of a new or changing lesion.", "Seek prompt care for bleeding, rapid change, persistent pain, or other concerning symptoms."]}],
    "treatment_sections": [{"title": "Treatment decisions", "items": ["Do not choose a medicine or remove a lesion from this research ranking.", "A clinician can recommend treatment after establishing what the lesion is."]}],
    "routine": {"morning": ["Protect exposed skin from excess sun with shade, clothing, and appropriate sunscreen."], "evening": ["Avoid picking or self-treating an uncertain lesion."], "weekly": ["Note any change in size, shape, color, or symptoms."], "follow_up": ["Arrange a qualified clinician's review for a new or changing lesion."]},
    "nutrition_sections": [], "lifestyle_sections": [], "medication_topics": [], "product_ids": [],
    "sources": [{"label": "NCI: skin cancer patient information", "url": "https://www.cancer.gov/types/skin/patient/skin-treatment-pdq"}],
}

CLINICAL_SKIN_DISCUSSION_GUIDANCE = {
    **DERMOSCOPY_DISCUSSION_GUIDANCE,
    "common_symptoms": ["Itching, dryness, redness, or raised patches", "Pain, spreading change, bleeding, or a persistent spot"],
    "cause_sections": [{"title": "Several patterns can overlap", "items": ["Eczema, hives, folliculitis, psoriasis, and other conditions can share visible features.", "A photo and five broad research classes cannot determine the cause or rule out an unrelated condition."]}],
    "care_sections": [{"title": "General skin support", "items": ["Avoid harsh scrubbing and stop products that sting or worsen a reaction.", "Arrange a clinician review for a persistent, spreading, painful, or changing concern."]}],
    "treatment_sections": [{"title": "Treatment decisions", "items": ["A clinician or pharmacist can help select treatment after assessing the actual pattern and symptoms.", "Do not choose a medicine from a raw research-model ranking."]}],
    "routine": {"morning": ["Cleanse gently if needed and use only products your skin tolerates."], "evening": ["Avoid harsh scrubbing or adding several new products at once."], "weekly": ["Record meaningful changes in symptoms and appearance."], "follow_up": ["Seek direct review when the concern persists, spreads, hurts, bleeds, or changes."]},
    "sources": [{"label": "AAD: simple skin care", "url": "https://www.aad.org/public/everyday-care/skin-care-basics/care/skin-care-budget"}],
}

PRODUCT_CATALOG = [
    {"id": "barrier-moisturiser", "name": "Fragrance-free barrier moisturiser", "domain": "Skin", "category": "Skin care", "key_property": "Fragrance-conscious emollient", "purpose": "Supportive moisturising care for a gentle skin routine.", "precautions": "Check allergies and stop if irritation occurs.", "search_terms": "fragrance free barrier moisturiser", "tags": ["dry skin", "irritation", "barrier", "eczema"], "affiliate_env": "AFFILIATE_MOISTURISER_URL", "product_url_env": "PRODUCT_MOISTURISER_URL"},
    {"id": "sun-protection", "name": "Broad-spectrum sun protection", "domain": "Skin", "category": "Skin care", "key_property": "Broad-spectrum labelled protection", "purpose": "Everyday sun-protection product discovery for a routine discussion.", "precautions": "Not a treatment; choose a labelled product from a licensed seller.", "search_terms": "broad spectrum sunscreen", "tags": ["sun protection", "pigmentation", "hyperpigmentation", "melasma", "acne"], "affiliate_env": "AFFILIATE_SUNSCREEN_URL", "product_url_env": "PRODUCT_SUNSCREEN_URL"},
    {"id": "scalp-cleanser", "name": "Gentle scalp cleanser", "domain": "Hair", "category": "Hair care", "key_property": "Low-irritation cleansing category", "purpose": "Supportive product discovery for routine scalp cleansing.", "precautions": "Avoid using on broken or painful skin without professional advice.", "search_terms": "gentle fragrance free scalp cleanser", "tags": ["hair", "scalp", "dandruff", "flakes"], "affiliate_env": "AFFILIATE_SCALP_CLEANSER_URL", "product_url_env": "PRODUCT_SCALP_CLEANSER_URL"},
    {"id": "gentle-conditioner", "name": "Gentle hair conditioner", "domain": "Hair", "category": "Hair care", "key_property": "Conditioning for hair lengths", "purpose": "A basic conditioning option to reduce tangles and friction during combing.", "precautions": "Choose for your hair type and stop if it irritates your scalp.", "search_terms": "gentle hair conditioner", "tags": ["hair", "conditioner", "breakage"]},
    {"id": "nail-emollient", "name": "Protective nail-care emollient", "domain": "Nails", "category": "Nail care", "key_property": "Cuticle and surrounding-skin comfort", "purpose": "Supportive care for dry cuticles and nail surroundings.", "precautions": "Not for self-treating painful, lifting, or discoloured nails.", "search_terms": "protective cuticle and nail care emollient", "tags": ["nail care", "cuticle", "dry nails"], "affiliate_env": "AFFILIATE_NAIL_CARE_URL", "product_url_env": "PRODUCT_NAIL_CARE_URL"},
    {"id": "protective-gloves", "name": "Protective cleaning gloves", "domain": "Nails", "category": "Nail care", "key_property": "Water and detergent protection", "purpose": "Help limit prolonged wet work that can weaken nails and irritate surrounding skin.", "precautions": "Dry hands after use and check material sensitivity.", "search_terms": "reusable protective cleaning gloves", "tags": ["nails", "water", "gloves"]},
]


# Product discovery is separate from an assessment recommendation. The
# assessment can surface relevant categories as optional education, while the
# catalogue search itself remains user-initiated and never establishes need.
PRODUCT_DISCOVERY_CATALOG = [
    *PRODUCT_CATALOG,
    {"id": "psoriasis-emollient", "name": "Rich fragrance-free emollient", "domain": "Skin", "category": "Skin care", "key_property": "Comfort for dry scaly skin", "purpose": "Support the skin barrier as part of a clinician-guided scaly-plaque care plan.", "precautions": "This does not replace prescribed anti-inflammatory treatment.", "search_terms": "rich fragrance free emollient ointment", "tags": ["psoriasis", "scaly skin", "emollient"]},
    {"id": "gentle-cleanser", "name": "Gentle facial cleanser", "domain": "Skin", "category": "Skin care", "key_property": "Low-irritation cleansing category", "purpose": "Browse cleanser options as part of a simple routine discussion.", "precautions": "Stop if it burns or worsens irritation; this is not a treatment recommendation.", "search_terms": "gentle facial cleanser", "tags": ["acne", "blackheads", "sensitive skin", "cleanser"]},
    {"id": "salicylic-acid", "name": "Salicylic acid product category", "domain": "Skin", "category": "Ingredient discovery", "key_property": "Over-the-counter active-ingredient category", "purpose": "An option to explore when blackheads or clogged pores are the concern.", "precautions": "This is not a personal recommendation from a photo. Confirm suitability and avoid combining actives without professional advice.", "search_terms": "salicylic acid skin care product", "tags": ["acne", "blackheads", "open comedones", "oil"]},
    {"id": "benzoyl-peroxide", "name": "Benzoyl peroxide product category", "domain": "Skin", "category": "Ingredient discovery", "key_property": "Over-the-counter active-ingredient category", "purpose": "A common option to explore for mild acne-type pimples.", "precautions": "This is not a personal recommendation from a photo. Check labels; it may irritate skin or bleach fabric.", "search_terms": "benzoyl peroxide skin care product", "tags": ["acne", "pimples", "breakouts"]},
    {"id": "azelaic-acid", "name": "Azelaic acid product category", "domain": "Skin", "category": "Ingredient discovery", "key_property": "Acne and post-breakout marks discussion", "purpose": "Browse azelaic-acid skin products when acne or post-breakout marks are the concern.", "precautions": "This is not a personal recommendation from a photo. Check local availability and suitability; stop if significant irritation occurs.", "search_terms": "azelaic acid skin care product", "tags": ["acne", "post acne marks", "azelaic acid"]},
    {"id": "ketoconazole-shampoo", "name": "Ketoconazole shampoo", "domain": "Hair", "category": "Scalp care", "key_property": "Medicated-shampoo category", "purpose": "A labelled medicated shampoo category to explore for persistent dandruff-type flakes.", "precautions": "Scalp flaking has multiple causes. Confirm the cause and suitability with a clinician or pharmacist before use.", "search_terms": "ketoconazole shampoo", "tags": ["dandruff", "seborrheic dermatitis", "scalp flakes"]},
    {"id": "selenium-sulfide-shampoo", "name": "Selenium sulfide shampoo", "domain": "Hair", "category": "Scalp care", "key_property": "Medicated-shampoo category", "purpose": "Another dandruff-shampoo category to compare if flaking is the concern.", "precautions": "Scalp flaking has multiple causes. Confirm the cause and suitability with a clinician or pharmacist before use.", "search_terms": "selenium sulfide shampoo", "tags": ["dandruff", "seborrheic dermatitis", "scalp flakes"]},
    {"id": "zinc-pyrithione-shampoo", "name": "Zinc pyrithione shampoo", "domain": "Hair", "category": "Scalp care", "key_property": "Medicated-shampoo category", "purpose": "User-led product discovery for a zinc-pyrithione shampoo category.", "precautions": "Scalp flaking has multiple causes. Confirm the cause and suitability with a clinician or pharmacist before use.", "search_terms": "zinc pyrithione shampoo", "tags": ["dandruff", "seborrheic dermatitis", "scalp flakes"]},
    {"id": "minoxidil-category", "name": "Minoxidil product category", "domain": "Hair", "category": "Hair-loss discussion", "key_property": "Hair-loss product category", "purpose": "An option to discuss when gradual pattern hair loss has been identified.", "precautions": "Hair loss has many causes. Do not use this page to self-diagnose; check suitability and interactions first.", "search_terms": "minoxidil hair loss product", "tags": ["hair loss", "thinning", "pattern hair loss", "alopecia"]},
    {"id": "topical-antifungal", "name": "Topical antifungal product category", "domain": "Skin", "category": "Pharmacy discussion", "key_property": "Non-prescription antifungal category", "purpose": "User-led discovery of topical antifungal product categories to discuss after a professional confirms the cause.", "precautions": "Do not self-treat an uncertain rash or start oral medication based on an image or this search page.", "search_terms": "topical antifungal skin product", "tags": ["tinea", "ringworm", "fungal infection"]},
    {"id": "nail-antifungal", "name": "Nail antifungal product category", "domain": "Nails", "category": "Pharmacy discussion", "key_property": "Nail-treatment category", "purpose": "A pharmacy category to discuss if a persistent nail change is thought to be fungal.", "precautions": "Nail discoloration and thickening can have several causes. Confirm the cause before choosing a product.", "search_terms": "nail antifungal product", "tags": ["nail fungus", "onychomycosis", "thick nail"]},
    {"id": "nail-clippers", "name": "Clean nail clippers and file", "domain": "Nails", "category": "Nail care", "key_property": "Basic trimming tools", "purpose": "Keep nails trimmed and smooth snagged edges as part of regular care.", "precautions": "Use gently; avoid cutting into sore skin or digging out an ingrown nail.", "search_terms": "nail clippers and nail file", "tags": ["nail care", "clippers", "file"]},
    {"id": "breathable-socks", "name": "Breathable everyday socks", "domain": "Nails", "category": "Foot care", "key_property": "Dry-foot routine", "purpose": "A practical option when socks stay damp or toenails are exposed to friction.", "precautions": "Choose a comfortable fit and change socks when damp; this is not a fungal treatment.", "search_terms": "breathable moisture wicking socks", "tags": ["toenails", "feet", "socks"]},
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
                          assessment_state: str | None = None, canonical_evidence: dict | None = None,
                          presentation_case: dict | None = None) -> dict:
    """Return state-aware education without turning an image into a prescription."""
    research_note = "No condition classification was run for this image type."
    if area == "Sweat":
        research_note = "Sweat guidance is based on questionnaire inputs only. A tabular ML model is not configured in this deployment."
    if research_classifier and research_classifier.get("available"):
        research_note = "The research classifier ranking may guide an educational topic and care categories; it does not confirm a condition or select a personal treatment."
    products = []
    product_guidance = (cdss or {}).get("product_guidance", "GENERAL_SELF_CARE_ONLY")
    if assessment_state == "UNCERTAIN":
        product_guidance = "DEFER_PRODUCT_DECISIONS"
    elif assessment_state == "HEALTHY":
        product_guidance = "HEALTHY_MAINTENANCE_ONLY"
    research_classifier = research_classifier or {}
    topic, topic_source = _education_topic(area, research_classifier, canonical_evidence or {}, presentation_case)
    if assessment_state == "HEALTHY":
        topic, topic_source = None, ""
    if product_guidance in {"GENERAL_SELF_CARE_ONLY", "HEALTHY_MAINTENANCE_ONLY"}:
        products = catalog_for_area(area)
    guidance = (DERMOSCOPY_DISCUSSION_GUIDANCE if research_classifier.get("model_id") == "ham10000-resnet34-research" else
                CLINICAL_SKIN_DISCUSSION_GUIDANCE) if area == "Skin" and research_classifier.get("available") and not topic else AREA_CARE_GUIDANCE.get(area)
    cause_sections = guidance["cause_sections"] if guidance else []
    care_sections = guidance["care_sections"] if guidance else []
    treatment_sections = guidance["treatment_sections"] if guidance else []
    routine_sections = ([{"title": title, "items": guidance["routine"][key]} for title, key in
                         (("Morning", "morning"), ("Evening", "evening"), ("Weekly check", "weekly"), ("Follow-up", "follow_up"))]
                        if guidance else [])
    nutrition_sections = [*EVERYDAY_NUTRITION, *guidance["nutrition_sections"]] if guidance else []
    lifestyle_sections = [*EVERYDAY_LIFESTYLE, *guidance["lifestyle_sections"]] if guidance else []
    # Educational categories follow the supported topic, or the selected area
    # when no topic is supported. Urgent concerns do not erase basic care.
    selected_ids = (TOPIC_PRODUCTS.get(topic["id"]) if topic else None) or (
        ("gentle-cleanser", "barrier-moisturiser", "sun-protection") if area == "Skin" and assessment_state == "HEALTHY" else
        ("scalp-cleanser", "gentle-conditioner") if area == "Hair" and assessment_state == "HEALTHY" else
        ("nail-emollient", "nail-clippers") if area == "Nails" and assessment_state == "HEALTHY" else
        ("gentle-cleanser", "barrier-moisturiser", "sun-protection") if area == "Skin" else
        ("scalp-cleanser", "gentle-conditioner") if area == "Hair" else
        ("nail-emollient", "protective-gloves", "nail-clippers") if area == "Nails" else ())
    educational_products = [materialize_product(item) for item in PRODUCT_DISCOVERY_CATALOG
                            if item["id"] in selected_ids]
    if topic:
        cause_sections = [{"title": f"Possible contributors to {topic['name'].lower()}", "items": topic["common_contributors"]}]
        care_sections = [{"title": f"Care to discuss for {topic['name'].lower()}", "items": topic["care_options"]}]
        treatment_sections = [{"title": "First steps", "items": topic["care_options"]},
                              {"title": "Clinical options", "items": [f"{item['name']}: {item['note']}" for item in topic["medication_topics"]] or ["No medicine is indicated from this image alone; a clinician can assess persistent changes."]}]
        routine_sections = [{"title": "Daily care", "items": topic["daily_routine"]},
                            {"title": "Monitoring", "items": [topic["follow_up_timeline"]]}]
        nutrition_sections = [*EVERYDAY_NUTRITION, {"title": f"Nutrition and {topic['name'].lower()}",
                            "items": [TOPIC_NUTRITION_CONTEXT.get(topic["id"],
                                      "Diet is supportive context and cannot establish or treat this pattern from a photograph."),
                                      "A photograph cannot establish a nutrient deficiency or a need for supplements."]}]
        lifestyle_sections = [*EVERYDAY_LIFESTYLE, {"title": f"Habits relevant to {topic['name'].lower()}", "items": topic["diet_lifestyle"]}]
    healthy = assessment_state == "HEALTHY"
    return {
        "scope": "Healthy-appearance maintenance education" if healthy else "General wellbeing and personal-care education",
        "research_note": research_note,
        "medicine_policy": "No treatment or medicine is needed based on this assessment. This does not replace care for symptoms, a changing concern, or a clinician recommendation." if healthy else "No medicine, dose, or personal treatment is selected from this image. Common options below are for discussion after the cause and suitability are assessed.",
        "product_guidance": product_guidance,
        "product_notice": "These are optional care categories for the selected area or educational topic, not a personal product recommendation; check suitability before use.",
        "general_care_categories": educational_products,
        "general_care_notice": (f"These categories fit an educational discussion of {topic['name'].lower()}; the {topic_source.replace('_', ' ')} does not establish a diagnosis or personal product need." if topic else "These optional everyday-care categories match only the area you selected. The photo did not establish a condition or a product need; check suitability before use.") if educational_products else "No area-based product categories are available.",
        "medication_information": {
            "available": False,
            "status": "NO_MEDICATION_RECOMMENDATION",
            "notice": "Common treatment options depend on the symptom and its cause. This image does not establish which, if any, is suitable for you.",
            "common_options": [] if healthy else ([{"name": item["name"], "used_for": item["note"]} for item in topic["medication_topics"]] if topic else guidance["medication_topics"] if guidance and not research_classifier.get("available") else []),
            "consultation_notice": "Check suitability, interactions, and local availability with a qualified doctor or pharmacist; do not change a prescribed medicine based on this result.",
        },
        "affiliate_disclosure": "Affiliate disclosure appears only when an approved partner URL is configured. It never changes analysis, medical suitability, or product ordering.",
        **GENERAL_WELLBEING,
        "routine": ({"morning": topic["daily_routine"][:2],
                     "evening": topic["daily_routine"][2:] or topic["daily_routine"][:1],
                     "weekly": [topic["follow_up_timeline"]],
                     "follow_up": [topic["follow_up_timeline"]]} if topic else guidance["routine"] if guidance else {
            **GENERAL_WELLBEING["routine"],
            "morning": [AREA_MORNING_CARE.get(area, GENERAL_WELLBEING["routine"]["morning"][0]), *GENERAL_WELLBEING["routine"]["morning"][1:]],
        }),
        "common_symptoms": topic["common_symptoms"] if topic else guidance["common_symptoms"] if guidance else [],
        "knowledge_topic": {"id": topic["id"], "name": topic["name"], "description": topic["description"],
                            "differentials": topic["differential_diagnoses"], "visual_features": topic["visual_features"],
                            "red_flags": topic["red_flags"], "source": topic_source,
                            "follow_up": topic["follow_up_timeline"], "references": topic["evidence_references"]} if topic else None,
        "cause_sections": cause_sections,
        "care_sections": care_sections,
        "treatment_sections": treatment_sections,
        "routine_sections": routine_sections,
        "possible_causes": [item for section in cause_sections for item in section["items"]],
        "care_steps": [item for section in care_sections for item in section["items"]],
        "nutrition_sections": nutrition_sections,
        "lifestyle_sections": lifestyle_sections,
        "diet": [item for section in nutrition_sections for item in section["items"]] if guidance else GENERAL_WELLBEING["diet"],
        "lifestyle": [item for section in lifestyle_sections for item in section["items"]] if guidance else GENERAL_WELLBEING["lifestyle"],
        "sources": ([{"label": item["title"], "url": item["url"]} for item in topic["evidence_references"]] if topic else guidance["sources"] if guidance else []) + EVERYDAY_CARE_SOURCES,
        "products": products,
    }
