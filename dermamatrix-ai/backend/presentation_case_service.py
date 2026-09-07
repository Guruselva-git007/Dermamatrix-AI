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


PRESENTATION_CASE_VERSION = "viva-case-library-v1"

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
}


def presentation_case_for_digest(digest: str, area: str) -> dict | None:
    """Return a display-safe case only when the selected area also matches."""
    record = PRESENTATION_CASES.get(str(digest or "").casefold())
    if not record or record["area"] != area:
        return None
    topic = educational_condition_topic(record["topic_id"])
    if not topic:
        raise RuntimeError(f"Presentation case topic is missing: {record['topic_id']}")
    return {
        "matched": True,
        "case_id": record["case_id"],
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
        "notice": "Presentation mode matched this exact supplied teaching file. This is a pre-labelled educational case, not AI inference, a diagnosis, a probability, a risk score, or a result for any other image.",
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
