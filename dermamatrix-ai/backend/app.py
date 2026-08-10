"""DermaMatrix AI local API with MySQL persistence.

This is an educational screening-support prototype. Its runnable model is not a
validated medical device: it cannot diagnose disease, counsel patients, or
prescribe/recommend medicines. A registered medical practitioner (RMP) must
independently assess every patient before diagnosis, counselling or treatment.
"""

from __future__ import annotations

import io
import os
from datetime import datetime, timezone

import pymysql
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image, ImageStat
from werkzeug.utils import secure_filename

from model_service import run_screening_model
from lesion_classifier import classify_dermoscopic_lesion


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_FILE_BYTES = 10 * 1024 * 1024

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_BYTES


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def database() -> pymysql.Connection:
    """Open a MySQL connection from environment-based local configuration."""
    options = {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "dermamatrix_ai"),
        "charset": "utf8mb4",
        "autocommit": False,
        "cursorclass": pymysql.cursors.DictCursor,
    }
    socket_path = os.getenv("MYSQL_SOCKET")
    if socket_path:
        options["unix_socket"] = socket_path
        options.pop("host")
        options.pop("port")
    return pymysql.connect(**options)


def initialise_database() -> None:
    """Create consent-aware MySQL collections. Uploaded image bytes are never stored."""
    statements = [
        """CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            patient_id VARCHAR(40) UNIQUE NOT NULL,
            full_name VARCHAR(150) NOT NULL,
            phone_number VARCHAR(30) NOT NULL,
            email_address VARCHAR(254) NOT NULL,
            created_at DATETIME NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS medical_histories (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            user_id BIGINT NOT NULL,
            past_history TEXT NOT NULL,
            current_history TEXT NOT NULL,
            updated_at DATETIME NOT NULL,
            CONSTRAINT fk_medical_history_user FOREIGN KEY (user_id) REFERENCES users(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS consent_records (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            user_id BIGINT NOT NULL,
            consent_version VARCHAR(60) NOT NULL,
            purpose VARCHAR(255) NOT NULL,
            accepted_at DATETIME NOT NULL,
            CONSTRAINT fk_consent_user FOREIGN KEY (user_id) REFERENCES users(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS assessments (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            assessment_id VARCHAR(50) UNIQUE NOT NULL,
            user_id BIGINT NULL,
            area VARCHAR(30) NOT NULL,
            risk_score INT NOT NULL,
            quality_score INT NOT NULL,
            clinical_status VARCHAR(60) NOT NULL,
            created_at DATETIME NOT NULL,
            CONSTRAINT fk_assessment_user FOREIGN KEY (user_id) REFERENCES users(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS clinical_review_requests (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            user_id BIGINT NULL,
            assessment_id VARCHAR(50) NOT NULL,
            status VARCHAR(60) NOT NULL,
            requested_at DATETIME NOT NULL,
            INDEX idx_review_assessment (assessment_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]
    connection = database()
    try:
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        connection.commit()
    finally:
        connection.close()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def image_quality(image_bytes: bytes) -> tuple[int, dict]:
    """Non-clinical image-quality features only—never a disease classifier."""
    with Image.open(io.BytesIO(image_bytes)) as image:
        image = image.convert("RGB")
        width, height = image.size
        resized = image.resize((1, 1))
        brightness = sum(ImageStat.Stat(resized).mean) / 3
    resolution_score = min(1.0, (width * height) / (1000 * 1000)) * 10
    light_score = max(0, 10 - abs(brightness - 145) / 17)
    quality = int(max(55, min(98, 74 + resolution_score + light_score)))
    return quality, {"width": width, "height": height, "brightness": round(brightness, 1)}


def screening_summary(area: str, risk_score: int) -> tuple[str, str, str]:
    if risk_score < 40:
        return ("LOWER-PRIORITY REVIEW", "Monitor and discuss if it changes", f"The {area.lower()} screen and symptom details are suitable to monitor. Seek an RMP if the concern changes, becomes painful, or worries you.")
    if risk_score < 65:
        return ("MODERATE REVIEW", "Clinical review recommended", f"The {area.lower()} screen and symptom details indicate a pattern worth discussing with a dermatologist, especially if it is new or changing.")
    return ("PRIORITY CLINICAL REVIEW", "Please arrange clinical review soon", "Your reported symptom details indicate a need for timely RMP review. This tool cannot determine a diagnosis or urgency on its own.")


def personal_care_catalog(area: str, risk_score: int) -> list[dict]:
    """Generic non-medicinal categories; no brands, prescription drugs or doses."""
    if risk_score >= 65:
        return []
    items = [
        {"name": "Fragrance-free moisturiser", "category": "Cosmetic / personal care", "purpose": "Supports the skin barrier for dry-feeling skin.", "guardrail": "Check ingredients against known allergies; stop use if irritation occurs."},
        {"name": "Broad-spectrum sunscreen", "category": "Cosmetic / personal care", "purpose": "Everyday sun-protection product discovery.", "guardrail": "This is not a treatment; choose a labelled product from a licensed seller."},
    ]
    if area == "Hair":
        items.append({"name": "Gentle, fragrance-free scalp cleanser", "category": "Cosmetic / personal care", "purpose": "A low-irritation cleansing option to discuss with a pharmacist.", "guardrail": "Avoid using on broken or painful skin without clinician advice."})
    elif area == "Nails":
        items.append({"name": "Protective nail-care emollient", "category": "Cosmetic / personal care", "purpose": "Helps support dry cuticles and nail surroundings.", "guardrail": "Do not use it to self-treat discoloured, painful, or lifting nails."})
    return items


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/api/health")
def health():
    try:
        connection = database()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 AS connected")
                connected = cursor.fetchone()["connected"] == 1
        finally:
            connection.close()
        return jsonify({"status": "ok", "service": "dermamatrix-api", "mode": "educational-prototype", "database": "mysql-connected" if connected else "unavailable", "model": "screening-triage-v1"})
    except pymysql.MySQLError:
        return jsonify({"status": "degraded", "database": "unavailable"}), 503


@app.post("/api/profiles")
def create_profile():
    payload = request.get_json(silent=True) or {}
    required = ("full_name", "phone_number", "email_address", "past_history", "current_history")
    missing = [field for field in required if not str(payload.get(field, "")).strip()]
    if missing:
        return jsonify({"error": f"Please provide: {', '.join(missing)}."}), 400
    if not payload.get("health_data_consent"):
        return jsonify({"error": "Explicit consent is required before storing health information."}), 400
    if "@" not in str(payload["email_address"]) or len(str(payload["phone_number"]).strip()) < 8:
        return jsonify({"error": "Enter a valid email address and phone number."}), 400

    timestamp = now()
    patient_id = f"DMX-{datetime.now(timezone.utc).strftime('%y%m%d')}-{os.urandom(3).hex().upper()}"
    connection = database()
    try:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO users (patient_id, full_name, phone_number, email_address, created_at) VALUES (%s, %s, %s, %s, %s)", (patient_id, payload["full_name"].strip(), payload["phone_number"].strip(), payload["email_address"].strip().lower(), timestamp))
            user_id = cursor.lastrowid
            cursor.execute("INSERT INTO medical_histories (user_id, past_history, current_history, updated_at) VALUES (%s, %s, %s, %s)", (user_id, payload["past_history"].strip(), payload["current_history"].strip(), timestamp))
            cursor.execute("INSERT INTO consent_records (user_id, consent_version, purpose, accepted_at) VALUES (%s, %s, %s, %s)", (user_id, "india-prototype-v1", "MySQL storage of profile and health-history data for screening support", timestamp))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return jsonify({"patient_id": patient_id, "full_name": payload["full_name"].strip(), "stored_in": "mysql", "consent_recorded": True}), 201


@app.post("/api/clinical-review-requests")
def request_clinical_review():
    payload = request.get_json(silent=True) or {}
    assessment_id = str(payload.get("assessment_id", "")).strip()
    if not assessment_id:
        return jsonify({"error": "An assessment ID is required."}), 400
    patient_id = str(payload.get("patient_id", "")).strip()
    connection = database()
    try:
        with connection.cursor() as cursor:
            user_id = None
            if patient_id:
                cursor.execute("SELECT id FROM users WHERE patient_id = %s", (patient_id,))
                user = cursor.fetchone()
                user_id = user["id"] if user else None
            cursor.execute("INSERT INTO clinical_review_requests (user_id, assessment_id, status, requested_at) VALUES (%s, %s, %s, %s)", (user_id, assessment_id, "awaiting_rmp_review", now()))
        connection.commit()
    finally:
        connection.close()
    return jsonify({"assessment_id": assessment_id, "status": "awaiting_rmp_review", "notice": "An RMP must independently review the patient before issuing any diagnosis, counselling, or prescription."}), 201


@app.get("/api/products")
def products():
    area = request.args.get("area", "Skin").strip()[:30] or "Skin"
    try:
        risk_score = int(request.args.get("risk_score", 28))
    except ValueError:
        return jsonify({"error": "Invalid risk score."}), 400
    items = personal_care_catalog(area, risk_score)
    return jsonify({"items": items, "eligible": bool(items), "policy": "No prescription medicine, diagnosis-specific treatment, dosage, or paid ranking is provided by this prototype.", "pharmacy_notice": "For any medicine or persistent symptom, consult an RMP and use a licensed pharmacy."})


@app.post("/api/assessments")
def create_assessment():
    image_file = request.files.get("image")
    if not image_file or not image_file.filename:
        return jsonify({"error": "An image is required."}), 400
    if not allowed_file(image_file.filename):
        return jsonify({"error": "Use a PNG, JPG, JPEG, or WEBP image."}), 415
    image_bytes = image_file.read()
    if not image_bytes:
        return jsonify({"error": "The uploaded image was empty."}), 400
    try:
        quality, image_features = image_quality(image_bytes)
    except Exception:
        return jsonify({"error": "The selected file could not be read as an image."}), 422
    area = request.form.get("area", "Skin").strip()[:30] or "Skin"
    try:
        duration = int(request.form.get("duration", 0)); discomfort = int(request.form.get("discomfort", 0)); change = int(request.form.get("change", 0))
    except ValueError:
        return jsonify({"error": "Invalid assessment details."}), 400

    model_output = run_screening_model(duration, discomfort, change, quality, image_features)
    image_context = request.form.get("image_context", "general_photo").strip()
    research_classifier = None
    if area == "Skin" and image_context == "dermoscopic_lesion":
        research_classifier = classify_dermoscopic_lesion(image_bytes)
    risk_score = model_output["risk_score"]
    risk_level, title, summary = screening_summary(area, risk_score)
    assessment_id = f"dmx-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.urandom(2).hex()}"
    patient_id = request.form.get("patient_id", "").strip()
    connection = database()
    try:
        with connection.cursor() as cursor:
            user_id = None
            if patient_id:
                cursor.execute("SELECT id FROM users WHERE patient_id = %s", (patient_id,))
                user = cursor.fetchone()
                user_id = user["id"] if user else None
            cursor.execute("INSERT INTO assessments (assessment_id, user_id, area, risk_score, quality_score, clinical_status, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)", (assessment_id, user_id, area, risk_score, quality, "awaiting_rmp_review", now()))
        connection.commit()
    finally:
        connection.close()

    return jsonify({
        "assessment_id": assessment_id, "created_at": datetime.now(timezone.utc).isoformat(), "area": area, "source_file": secure_filename(image_file.filename),
        "quality": {"score": quality, "label": "Good" if quality >= 80 else "Needs clearer image"}, "risk": {"score": risk_score, "level": risk_level}, "screening": {"title": title, "summary": summary},
        "model": model_output, "research_classifier": research_classifier, "model_pipeline": {"image_quality_gate": "completed", "lesion_segmentation": "visual prototype overlay", "classification": "HAM10000 research classifier" if research_classifier else "not run: requires explicit dermatoscopic lesion image selection", "explainability": "Grad-CAM integration point"},
        "medical_disclaimer": "Educational prototype only. This response is not a diagnosis or medical advice.", "clinical_status": "awaiting_rmp_review", "commerce_eligibility": "personal_care_only" if risk_score < 65 else "blocked_pending_clinical_review",
    })


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "The image is larger than 10 MB."}), 413


initialise_database()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
