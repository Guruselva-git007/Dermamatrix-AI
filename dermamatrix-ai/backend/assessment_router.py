"""Central health-area routing contract for DermaMatrix assessment inputs.

An accepted smartphone photo can receive input-quality and context support, but
only the explicitly attested dermatoscopic workflow may enter the bundled
research classifier. No image type is silently routed to an unrelated model.
"""

from __future__ import annotations


ROUTER_VERSION = "health-area-router-v1"

HEALTH_AREA_WORKFLOWS = {
    "Skin": {
        "input_mode": "image",
        "display_name": "Skin",
        "instruction": "Upload a clear, well-lit photo of facial skin, body skin, or the affected area. Select dermatoscopic lesion only when a dermatoscope was used.",
        "contexts": {
            "face_skin": "Face skin",
            "body_skin": "Body skin",
            "affected_skin": "Affected skin close-up",
            "dermoscopic_lesion": "Dermatoscopic single lesion",
            "general_photo": "General skin photo (legacy selection)",
        },
        "model_scope": "Only the dermatoscopic single-lesion context is compatible with the bundled HAM10000 research adapter.",
    },
    "Hair": {
        "input_mode": "image",
        "display_name": "Hair & scalp",
        "instruction": "Upload a clear image showing the scalp, hair-loss or thinning area, or a relevant hair/scalp close-up.",
        "contexts": {
            "scalp": "Scalp",
            "hair_loss_area": "Hair-loss / thinning area",
            "hair_scalp_close_up": "Hair / scalp close-up",
            "general_photo": "General hair photo (legacy selection)",
        },
        "model_scope": "No trained hair/scalp disorder classifier is configured in this deployment.",
    },
    "Nails": {
        "input_mode": "image",
        "display_name": "Nail health",
        "instruction": "Upload a clear close-up of the affected fingernail, toenail, or surrounding relevant area.",
        "contexts": {
            "fingernail": "Fingernail",
            "toenail": "Toenail",
            "nail_close_up": "Nail / surrounding-area close-up",
            "general_photo": "General nail photo (legacy selection)",
        },
        "model_scope": "No trained nail-disorder classifier is configured in this deployment.",
    },
    "Sweat": {
        "input_mode": "questionnaire",
        "display_name": "Sweat pattern",
        "instruction": "Answer the sweat-pattern questionnaire. Sweat concerns do not use an image in this deployment.",
        "contexts": {},
        "model_scope": "A transparent questionnaire prioritisation engine is available; no validated tabular classifier is configured.",
    },
}


def public_workflows() -> list[dict]:
    """Return display-safe workflow details without model implementation data."""
    return [
        {
            "area": area,
            "input_mode": workflow["input_mode"],
            "display_name": workflow["display_name"],
            "instruction": workflow["instruction"],
            "contexts": [{"id": key, "label": label} for key, label in workflow["contexts"].items()],
            "model_scope": workflow["model_scope"],
        }
        for area, workflow in HEALTH_AREA_WORKFLOWS.items()
    ]


def route_image_assessment(*, area: str, image_context: str, dermoscopy_attested: bool, image_features: dict) -> dict:
    """Validate a declared image route and decide whether research inference may run.

    Selecting a context is not evidence that an anatomy model verified the
    photo. Where no relevance/classification model exists, the route returns
    quality and context support only instead of a forced disease prediction.
    """
    workflow = HEALTH_AREA_WORKFLOWS.get(area)
    if not workflow or workflow["input_mode"] != "image":
        return {"accepted": False, "status": "UNSUPPORTED", "error": "Choose Skin, Hair & scalp, Nail health, or use the separate Sweat questionnaire."}
    if image_context not in workflow["contexts"]:
        return {"accepted": False, "status": "UNSUPPORTED", "error": f"Choose a supported {workflow['display_name'].lower()} image type before continuing."}
    route = {
        "accepted": True,
        "status": "VALID",
        "image_context": image_context,
        "image_context_label": workflow["contexts"][image_context],
        "workflow": f"{area.lower()}-image-support",
        "run_research_classifier": False,
        "relevance_status": "USER_DECLARED_CONTEXT_NOT_AUTOMATICALLY_VERIFIED",
        "classification_status": "NO_COMPATIBLE_CLASSIFIER_CONFIGURED",
        "notice": f"{workflow['instruction']} Automatic anatomy relevance and condition classification are not configured for this image context, so no disease label is generated.",
    }
    if image_features.get("status") == "LOW_QUALITY":
        route.update({
            "status": "LOW_QUALITY",
            "relevance_status": "NOT_ASSESSED_LOW_QUALITY",
            "classification_status": "NOT_RUN_LOW_QUALITY",
            "notice": "Retake the image before any scoped model output. A low-quality image is not forced into a disease classifier.",
        })
        return route
    if area != "Skin" or image_context != "dermoscopic_lesion":
        return route
    route.update({
        "workflow": "skin-dermatoscopic-research",
        "relevance_status": "DERMOSCOPY_NOT_ATTESTED",
        "classification_status": "NOT_RUN_CAPTURE_ATTESTATION_REQUIRED",
        "notice": "Confirm that this is an in-focus dermatoscopic single-lesion image before the scoped research model can run.",
    })
    if dermoscopy_attested:
        route.update({
            "run_research_classifier": True,
            "relevance_status": "ATTESTED_DERMOSCOPIC_SCOPE",
            "classification_status": "ELIGIBLE_FOR_SCOPED_RESEARCH_CLASSIFIER",
            "notice": "Eligible for the dermatoscopic single-lesion research path only. This is not a diagnosis pathway.",
        })
    return route
