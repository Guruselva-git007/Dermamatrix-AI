"""Semantic content floor for the one persisted Skin/Hair/Nail result contract.

This checks useful populated content, rather than the presence of empty JSON
keys. Missing evidence may be described honestly; it may not erase care cards.
"""

from __future__ import annotations


def _items(sections: object) -> list[str]:
    return [str(item).strip() for section in sections or [] if isinstance(section, dict)
            for item in section.get("items") or [] if str(item).strip()]


def validate_result_content(result: dict) -> dict:
    area = result.get("area")
    consumer = result.get("consumer") or {}
    if area not in {"Skin", "Hair", "Nails"} or not consumer:
        return {"status": "not_applicable", "checks": {}, "missing": []}
    primary = consumer.get("primary_result") or {}
    medicine = consumer.get("medication_information") or {}
    products = consumer.get("products") or []
    checks = {
        "assessment": bool(primary.get("title") and primary.get("summary") and consumer.get("why_this_result")),
        "confidence_or_match_strength": primary.get("confidence") is not None or bool(primary.get("evidence_strength")) or (
            result.get("result_state") == "poor_quality" and primary.get("source") == "available_context"
            and bool((consumer.get("image_quality") or {}).get("issues"))
        ),
        "visible_findings_or_scope": isinstance(consumer.get("visible_findings"), list) and bool(consumer.get("image_quality")),
        "differential_or_scope": isinstance(consumer.get("possible_conditions"), list) and bool(consumer.get("differential_status")),
        "pirs": isinstance(consumer.get("pirs"), dict) and "score" in consumer["pirs"],
        "severity": isinstance(consumer.get("severity"), dict) and "label" in consumer["severity"],
        "concern": isinstance(consumer.get("concern"), dict) and "label" in consumer["concern"],
        "common_symptoms": bool(consumer.get("common_symptoms")),
        "causes": bool(_items(consumer.get("cause_sections"))),
        "treatment": bool(_items(consumer.get("treatment_sections"))),
        "category_care": bool(_items(consumer.get("care_sections"))),
        "routine": bool(_items(consumer.get("routine_sections"))),
        "diet_nutrition": bool(_items(consumer.get("nutrition_sections"))),
        "lifestyle": bool(_items(consumer.get("lifestyle_sections"))),
        "medicines_context": bool(medicine.get("notice")) and isinstance(medicine.get("common_options"), list),
        "products": bool(products) and all(product.get("name") and product.get("commerce", {}).get("primary", {}).get("url") for product in products),
        "professional_support": bool((consumer.get("professional_support") or {}).get("specialty")),
        "monitoring": bool((consumer.get("monitoring") or {}).get("what_to_track")),
        "technical": isinstance(consumer.get("technical_details"), dict),
    }
    # Domain mismatches and stock fallback copy are content regressions even
    # when all the JSON fields are present.
    checks["category_products"] = all(product.get("domain") == area for product in products)
    routine = " ".join(_items(consumer.get("routine_sections"))).casefold()
    checks["category_routine"] = not (
        (area == "Hair" and any(token in routine for token in ("facial cleanser", "face moisturiser", "face sunscreen")))
        or (area == "Nails" and any(token in routine for token in ("scalp shampoo", "face moisturiser", "hairline")))
    )
    checks["no_empty_fallback"] = "no product selected" not in str(consumer).casefold()
    checks["uncertainty_wording"] = not (
        primary.get("confidence_kind") == "raw_softmax" and
        "probability" in str(primary.get("summary") or "").casefold()
    )
    missing = [name for name, passed in checks.items() if not passed]
    return {"status": "complete" if not missing else "incomplete", "checks": checks, "missing": missing}
