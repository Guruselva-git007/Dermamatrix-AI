"""Opt-in exact-file teaching-case mapping for a supervised viva presentation.

This is deliberately not image inference.  When a presenter explicitly enables
the feature, only an exact SHA-256 match to one of the supplied teaching files
receives its pre-authored educational scenario.  Similar, edited, re-encoded,
or ordinary patient images never match and continue through the normal app
boundary without a disease label.
"""

from __future__ import annotations

import hashlib

from condition_knowledge import educational_condition_topic
from recommendation_service import catalog_for_area


PRESENTATION_CASE_VERSION = "viva-case-library-v1.2"

# These are fingerprints of the user-supplied presentation files, not model
# weights, perceptual hashes, training examples, or a general image classifier.
PRESENTATION_CASES = {
    "75faabcc86ef074b1bc0c3720939d56132a8bd4f781495c0b514ee79750df0ca": {
        "case_id": "skin-acneiform-eruption", "area": "Skin", "topic_id": "acne",
        "teaching_label": "Acneiform follicular eruption — teaching differential",
        "teaching_summary": "This pre-labelled review example shows acneiform follicular papules/pustules. Acne and folliculitis can overlap visually, so this is not a confirmed diagnosis.",
    },
    "7b13f2d3e22150f9666b56346bad2a8d6b180b7645195a940fa83f9c8222425d": {
        "case_id": "skin-annular-plaque", "area": "Skin", "topic_id": "tinea",
        "teaching_label": "Annular scaly plaque — possible tinea corporis teaching case",
        "teaching_summary": "This pre-labelled example is used to discuss a tinea corporis (ringworm) pattern. Eczema and other rashes can look similar; confirmation may require clinical assessment or mycology.",
    },
    "fcece504bac6d91c9b982994434c5df67e56e9f0a0e219b0dd501fa6c262f599": {
        "case_id": "skin-plantar-scale", "area": "Skin", "topic_id": "tinea",
        "teaching_label": "Plantar scaling — possible tinea pedis teaching case",
        "teaching_summary": "This pre-labelled example is used to discuss a hyperkeratotic/plantar fungal-foot pattern. Plantar psoriasis and eczema remain important alternatives.",
    },
    "77277e57fc4f4e4d7ee115ac8316e5a5ec1f2255d4da53131a15b8e2e367d073": {
        "case_id": "skin-keratotic-growth", "area": "Skin", "topic_id": "seborrheic-keratosis",
        "teaching_label": "Pigmented keratotic growth — possible seborrheic keratosis teaching case",
        "teaching_summary": "This pre-labelled example is used to discuss a waxy, keratotic, “stuck-on” growth pattern. A changing or concerning pigmented lesion needs in-person assessment.",
    },
    "f229ef0cf5e9318dea63fd500ca3a72d0f9bd7709cbd76912773e8614a2e5733": {
        "case_id": "skin-inflammatory-acne", "area": "Skin", "topic_id": "acne",
        "teaching_label": "Inflammatory acne — teaching case",
        "teaching_summary": "This pre-labelled example is used to discuss inflamed papules and pustules compatible with acne. It is not a prescription or a diagnosis for any other face image.",
    },
    "d191ee0272c0c85db4a1ff073883791208fe37d4cd09ce7f55079a4c8dd956d8": {
        "case_id": "skin-scaly-plaque", "area": "Skin", "topic_id": "psoriasis",
        "teaching_label": "Scaly plaque — psoriasis/eczema teaching differential",
        "teaching_summary": "This pre-labelled example is used to discuss a chronic scaly-plaque pattern. Psoriasis, eczema, and fungal infection need clinical differentiation.",
    },
    "1e17c5e98537c634a357dc5694f88dd23c806788df7d5a870a0939f19482308d": {
        "case_id": "hair-scalp-scale", "area": "Hair", "topic_id": "seborrheic-dermatitis",
        "teaching_label": "Scalp scale — seborrheic dermatitis teaching case",
        "teaching_summary": "This pre-labelled example is used to discuss scalp flaking/scale. Scalp psoriasis, contact dermatitis, and tinea may need to be excluded clinically.",
    },
    "da6f15defbfd929fde6f0580b94df42fb25ed468c8bf012d152c3da49da34de3": {
        "case_id": "hair-inflamed-scalp", "area": "Hair", "topic_id": "psoriasis",
        "teaching_label": "Inflamed scaly scalp plaques — teaching differential",
        "teaching_summary": "This pre-labelled example is used to discuss an inflamed scaly scalp pattern. Psoriasis, fungal infection, and dermatitis are differentials; no one is confirmed by this presentation mapping.",
    },
    "3ed711981adac9c8b03ff646687c06874be701206cd447cb5065100dfde3a5c1": {
        "case_id": "hair-patchy-loss", "area": "Hair", "topic_id": "alopecia-areata",
        "teaching_label": "Patchy hair loss — alopecia areata teaching case",
        "teaching_summary": "This pre-labelled example is used to discuss a smooth patchy hair-loss pattern. Tinea capitis and other causes of patchy loss need clinical exclusion.",
    },
    "bb7de5d7a9dabc41ec40213cdebb37cb73cfa33cddaa4a2ce12f366a4f9fa12a": {
        "case_id": "nail-thickened-yellow", "area": "Nails", "topic_id": "onychomycosis",
        "teaching_label": "Thickened discoloured nail — possible onychomycosis teaching case",
        "teaching_summary": "This pre-labelled example is used to discuss a fungal-nail pattern. Confirmation matters because trauma and nail psoriasis can look similar.",
    },
    "7af6b44ec50552d5112b73679edecf2188d53d08e199c48a8efaae569453ca7d": {
        "case_id": "nail-dystrophy", "area": "Nails", "topic_id": "nail-psoriasis",
        "teaching_label": "Nail dystrophy — nail psoriasis/fungal differential teaching case",
        "teaching_summary": "This pre-labelled example is used to discuss surface change and dystrophy. Nail psoriasis, fungal infection, and trauma require clinical differentiation.",
    },
    "164dc87d538d7e434876bd904867ca7cc590bfd24c7ac3561a9a5ace4a9e18b0": {
        "case_id": "nail-blue-grey", "area": "Nails", "topic_id": "blue-nails",
        "teaching_label": "Blue-grey nail discoloration — prompt-assessment teaching case",
        "teaching_summary": "This pre-labelled example is used to discuss blue/violaceous nails. It is not a vitamin-deficiency finding; persistent discoloration or breathing/chest symptoms need prompt medical assessment.",
    },
    # Additional exact review files from the supplied DermaMatrix image folder.
    # They have no effect on ordinary, edited, or visually similar uploads.
    "6e48c9bfdee255672a7fcb764741a6a2474c40f119f68ac57790c4c5c3147532": {
        "case_id": "hair-dandruff-reference", "area": "Hair", "topic_id": "seborrheic-dermatitis",
        "teaching_label": "Scalp flaking — dandruff / seborrheic dermatitis teaching case",
        "teaching_summary": "This exact supplied reference is used to discuss dandruff or seborrheic-dermatitis patterns. Scalp psoriasis, contact dermatitis, and tinea remain clinical differentials.",
    },
    "5c9be2050a8d25f5cffc60ee14898551918d43e0998fc0fb5aadbaaee1e98ae8": {
        "case_id": "hair-dandruff-symptom-reference", "area": "Hair", "topic_id": "seborrheic-dermatitis",
        "teaching_label": "Scalp flaking and itch — dandruff teaching case",
        "teaching_summary": "This exact supplied reference is used to discuss visible scalp flaking. It does not confirm a cause for any other hair or scalp image.",
    },
    "fa6e23a59cc8a4ba8cc804864610f00f3adaf0ea1337be6dcc0dfa13c593a79c": {
        "case_id": "skin-atrophic-acne-scars", "area": "Skin", "topic_id": "acne",
        "teaching_label": "Atrophic acne scarring — teaching case",
        "teaching_summary": "This exact supplied reference is used to discuss pitted acne scars after prior inflammation. Scarring care is individual and usually needs clinician assessment before procedures or medicines.",
    },
    "fe9213263115f338de662339415a586274a1add9648d47bb9049e05e70f2806e": {
        "case_id": "skin-facial-dark-patches", "area": "Skin", "topic_id": "hyperpigmentation",
        "teaching_label": "Facial dark patches — hyperpigmentation / melasma teaching differential",
        "teaching_summary": "This exact supplied reference is used to discuss facial dark patches. Melasma, post-inflammatory marks, irritation, and other pigmented conditions require clinical differentiation.",
    },
    "2485c6770ac4db417b1f88e25d71b922a143772118bc1dc66bcf0233ef576a08": {
        "case_id": "skin-facial-pigmentation", "area": "Skin", "topic_id": "hyperpigmentation",
        "teaching_label": "Facial pigmentation patch — teaching differential",
        "teaching_summary": "This exact supplied reference is used to discuss a facial pigmentation pattern. It is not a diagnosis and does not establish the cause of any new or changing spot.",
    },
    "8dba72dfc134e89a05525a309b2d02cf063219958d45517c9ca76aedca0b775f": {
        "case_id": "skin-lip-pigmentation", "area": "Skin", "topic_id": "hyperpigmentation",
        "teaching_label": "Lip pigmentation — teaching differential",
        "teaching_summary": "This exact supplied reference is used to discuss lip-colour variation or pigmentation. Irritation, medicines, sun exposure, and other causes need clinical context; it is not a deficiency diagnosis.",
    },
    "e6add51030e175563c8c43cdfad7bf4bde1d90cd320837e7f2cf25eb8465b292": {
        "case_id": "skin-concern-vocabulary-chart", "area": "Skin", "topic_id": None,
        "teaching_label": "Facial skin concerns vocabulary chart — multi-condition teaching overview",
        "teaching_summary": "This exact supplied image is a labelled vocabulary chart containing several different concerns. It is not one patient case, so no single diagnosis, probability, or risk score is assigned.",
        "education": {
            "id": "skin-concern-vocabulary", "name": "Facial skin concerns overview", "visual_features": ["The chart illustrates acne, comedones, pigmentation, dryness, rashes, and other distinct concerns."],
            "common_symptoms": ["Each labelled concern has different symptoms and causes; use the matching individual teaching file or an educational guide for details."],
            "common_contributors": ["Skin conditions can involve inflammation, irritation, sun exposure, products, infection, hormones, or other factors depending on the specific concern."],
            "differential_diagnoses": ["A multi-condition overview is not sufficient to identify one condition in a person."],
            "care_options": ["Use gentle, fragrance-free care and broad-spectrum sun protection as tolerated.", "Open the relevant educational guide or seek clinician advice for a specific concern."],
            "medication_topics": [{"name": "No single medicine applies to this chart", "access": "Clinician or pharmacist discussion", "note": "Medication and treatment depend on the actual condition, location, severity, medical history, and examination."}],
            "daily_routine": ["Use simple gentle cleansing and moisturising as tolerated", "Use sun protection where appropriate", "Avoid picking, harsh scrubs, and unregulated lightening products"],
            "diet_lifestyle": ["Maintain a balanced diet; no one diet treats every concern shown in the chart.", "Do not start supplements or medicine based on a category image."],
            "red_flags": ["Rapid change, severe pain, spreading redness, pus, bleeding, blistering, or systemic symptoms need prompt professional assessment."],
            "doctor_specialty": "Dermatologist", "evidence_references": [],
        },
    },
    "882c972469595ed23ca031c18eb6498ad152e68b6c9c41ef1654c22ea473237d": {
        "case_id": "skin-inflammatory-acne-reference", "area": "Skin", "topic_id": "acne",
        "teaching_label": "Inflammatory acne-pattern reference — teaching case",
        "teaching_summary": "This exact supplied reference is used to discuss inflammatory acne-pattern spots and marks. Acne, folliculitis, and other causes require clinical context; it does not diagnose a different image.",
    },
}


def presentation_case_for_digest(digest: str, area: str) -> dict | None:
    """Return a display-safe case only when the selected area also matches."""
    record = PRESENTATION_CASES.get(str(digest or "").casefold())
    if not record or record["area"] != area:
        return None
    topic = educational_condition_topic(record.get("topic_id")) if record.get("topic_id") else record.get("education")
    if not topic:
        raise RuntimeError(f"Presentation case topic is missing: {record.get('topic_id')}")
    return {
        "matched": True,
        "case_id": record["case_id"], "area": record["area"],
        "version": PRESENTATION_CASE_VERSION,
        "matching_method": "EXACT_FILE_SHA256",
        "teaching_label": record["teaching_label"],
        "teaching_summary": record["teaching_summary"],
        "topic_id": topic["id"],
        "topic_name": topic["name"],
        "care_options": topic["care_options"],
        "treatment_topics": topic["medication_topics"],
        "routine": topic["daily_routine"],
        "diet_lifestyle": topic["diet_lifestyle"],
        "red_flags": topic["red_flags"],
        "doctor_specialty": topic["doctor_specialty"],
        "references": topic["evidence_references"],
        "visual_features": topic.get("visual_features", []),
        "common_symptoms": topic.get("common_symptoms", []),
        "common_contributors": topic.get("common_contributors", []),
        "differential_diagnoses": topic.get("differential_diagnoses", []),
        "notice": "Presentation mode matched this exact supplied teaching file. It adds pre-labelled educational reference metadata, not AI inference, a diagnosis, or a condition probability. The shared assessment concern calculation still uses the image and reported input evidence.",
        "medication_notice": "Treatment topics are for a doctor or pharmacist discussion only. No medicine, dose, or personal treatment plan is generated.",
    }


def presentation_case_for_image(image_bytes: bytes, area: str, enabled: bool) -> dict | None:
    """Match only explicit presentation mode and an unchanged original file."""
    if not enabled:
        return None
    digest = hashlib.sha256(image_bytes).hexdigest()
    return presentation_case_for_digest(digest, area)


def presentation_case_recommendations(case: dict, base: dict) -> dict:
    """Adapt existing education fields; never convert a case label into a prescription."""
    guidance = dict(base)
    routine = list(case.get("routine") or [])
    guidance.update({
        "scope": "Pre-labelled presentation-case education; not model output or patient-specific treatment.",
        "research_note": case["notice"],
        "medicine_policy": case["medication_notice"],
        "product_guidance": "PRESENTATION_CASE_EDUCATION_ONLY",
        "product_notice": "Any product discovery remains user-led and should be discussed with a pharmacist or registered medical practitioner.",
        "medication_information": {
            "available": False,
            "status": "EDUCATIONAL_DISCUSSION_ONLY",
            "notice": case["medication_notice"],
            "consultation_notice": "Do not start, stop, or change medication based on this teaching case.",
        },
        "routine": {"morning": routine[:2], "evening": routine[2:] or routine[:1]},
        "diet": list(case.get("diet_lifestyle") or []),
        "lifestyle": ["Do not use supplements or restrictive diets to self-treat a presumed condition.", "Use the red flags and clinician discussion points in this teaching case."],
        "supplements": ["No supplement is selected by a presentation image. Discuss testing and any supplement with a qualified clinician or pharmacist."],
        "products": base.get("products") or catalog_for_area(case["area"]),
    })
    return guidance


def presentation_case_care_plan(case: dict) -> dict:
    return {
        "heading": "Presentation-case discussion guide",
        "next_step": f"Discuss the teaching scenario with a {case['doctor_specialty']}; use professional examination or testing to establish an actual diagnosis.",
        "routine_guardrail": case["notice"],
        "product_guardrail": "Products and medicines are not selected from the case label. Confirm suitability with a doctor or pharmacist before use.",
        "diet_guidance": " ".join(case.get("diet_lifestyle") or []),
    }
