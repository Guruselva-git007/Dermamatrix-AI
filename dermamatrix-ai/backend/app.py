"""DermaMatrix AI local API with MySQL persistence.

This is an educational screening-support prototype. Its runnable model is not a
validated medical device: it cannot diagnose disease, counsel patients, or
prescribe/recommend medicines. A registered medical practitioner (RMP) must
independently assess every patient before diagnosis, counselling or treatment.
"""

from __future__ import annotations

import io
import json
import os
import uuid
from datetime import datetime, timezone

import pymysql
from flask import Flask, jsonify, request, send_file, send_from_directory, session
from PIL import Image, ImageFilter, ImageStat
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from model_service import run_screening_model
from lesion_classifier import classify_dermoscopic_lesion
from model_metadata import SKIN_MODEL_ID, all_model_metadata, model_metadata
from assessment_router import public_workflows, route_image_assessment
from clinical_intelligence_service import clinical_decision_support, normalise_symptoms, patient_context_snapshot, reported_symptom_severity
from condition_knowledge import KNOWLEDGE_VERSION, build_assessment_intelligence, model_capability_matrix
from longitudinal_service import build_progress_comparison
from pirs_service import calculate_pirs
from recommendation_service import build_recommendations
from report_service import build_assessment_report_pdf, build_history_report_pdf
from risk_service import normalise_reported_priority
from segmentation_service import extract_visual_candidate_region, segment_dermoscopic_lesion, unavailable_candidate_region
from sweat_service import sweat_questionnaire_result


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_FILE_BYTES = 10 * 1024 * 1024

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_BYTES
DATABASE_BOOT_ERROR: str | None = None


def load_local_env() -> None:
    """Load simple KEY=VALUE local demo settings without committing secrets."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


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
        "connect_timeout": 5,
        "read_timeout": 15,
        "write_timeout": 15,
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
        """CREATE TABLE IF NOT EXISTS auth_accounts (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            user_id BIGINT UNIQUE NOT NULL,
            email_address VARCHAR(254) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at DATETIME NOT NULL,
            CONSTRAINT fk_auth_account_user FOREIGN KEY (user_id) REFERENCES users(id)
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
        """CREATE TABLE IF NOT EXISTS analysis_records (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            assessment_id VARCHAR(50) UNIQUE NOT NULL,
            user_id BIGINT NULL,
            area VARCHAR(30) NOT NULL,
            result_json LONGTEXT NOT NULL,
            image_stored BOOLEAN NOT NULL DEFAULT FALSE,
            created_at DATETIME NOT NULL,
            CONSTRAINT fk_analysis_user FOREIGN KEY (user_id) REFERENCES users(id),
            INDEX idx_analysis_user_area (user_id, area, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS clinical_review_requests (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            user_id BIGINT NULL,
            assessment_id VARCHAR(50) NOT NULL,
            status VARCHAR(60) NOT NULL,
            requested_at DATETIME NOT NULL,
            INDEX idx_review_assessment (assessment_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS care_routines (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            routine_id VARCHAR(50) UNIQUE NOT NULL,
            user_id BIGINT NOT NULL,
            condition_label VARCHAR(180) NOT NULL,
            routine_name VARCHAR(180) NOT NULL,
            start_date DATE NOT NULL,
            notes TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            CONSTRAINT fk_routine_user FOREIGN KEY (user_id) REFERENCES users(id),
            INDEX idx_routine_user (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS progress_checkins (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            checkin_id VARCHAR(50) UNIQUE NOT NULL,
            user_id BIGINT NOT NULL,
            routine_id VARCHAR(50) NOT NULL,
            checkin_date DATE NOT NULL,
            reported_trend VARCHAR(30) NOT NULL,
            discomfort_score INT NOT NULL,
            change_score INT NOT NULL,
            priority_score INT NOT NULL,
            note TEXT NOT NULL,
            image_stored BOOLEAN NOT NULL DEFAULT FALSE,
            created_at DATETIME NOT NULL,
            CONSTRAINT fk_checkin_user FOREIGN KEY (user_id) REFERENCES users(id),
            INDEX idx_checkin_routine (routine_id),
            INDEX idx_checkin_user_date (user_id, checkin_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """CREATE TABLE IF NOT EXISTS reports (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            report_id VARCHAR(50) UNIQUE NOT NULL,
            assessment_id VARCHAR(50) UNIQUE NOT NULL,
            user_id BIGINT NOT NULL,
            report_type VARCHAR(40) NOT NULL,
            generated_at DATETIME NOT NULL,
            CONSTRAINT fk_report_user FOREIGN KEY (user_id) REFERENCES users(id),
            INDEX idx_report_user_generated (user_id, generated_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    ]
    global DATABASE_BOOT_ERROR
    try:
        connection = database()
    except pymysql.MySQLError as error:
        DATABASE_BOOT_ERROR = str(error)
        app.logger.warning("MySQL is unavailable; assessments will run without persistence: %s", error)
        return
    try:
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        connection.commit()
    except pymysql.MySQLError as error:
        DATABASE_BOOT_ERROR = str(error)
        app.logger.warning("MySQL schema initialisation failed: %s", error)
    finally:
        connection.close()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def user_for_patient(connection: pymysql.Connection, patient_id: str) -> dict | None:
    """Resolve only the profile bound to the active signed-in browser session."""
    session_user_id = session.get("user_id")
    if not patient_id or not session_user_id or session.get("patient_id") != patient_id:
        return None
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, patient_id, full_name, phone_number, email_address FROM users WHERE patient_id=%s AND id=%s", (patient_id, session_user_id))
        return cursor.fetchone()


def account_response(user: dict, history: dict | None = None) -> dict:
    """Return the minimum account data the browser needs; password hashes never leave MySQL."""
    result = {
        "patient_id": user["patient_id"],
        "full_name": user["full_name"],
        "phone_number": user["phone_number"],
        "email_address": user["email_address"],
        "stored_in": "mysql",
    }
    if history is not None:
        result.update({"past_history": history["past_history"], "current_history": history["current_history"]})
    return result


def account_history(connection: pymysql.Connection, user_id: int) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT past_history, current_history FROM medical_histories
               WHERE user_id=%s ORDER BY updated_at DESC, id DESC LIMIT 1""",
            (user_id,),
        )
        return cursor.fetchone() or {"past_history": "", "current_history": ""}


def routine_payload(payload: dict) -> tuple[str, str, str, str] | None:
    condition_label = str(payload.get("condition_label", "")).strip()[:180]
    routine_name = str(payload.get("routine_name", "")).strip()[:180]
    start_date = str(payload.get("start_date", "")).strip()[:10]
    notes = str(payload.get("notes", "")).strip()[:2000]
    if not condition_label or not routine_name or len(start_date) != 10:
        return None
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        return None
    return condition_label, routine_name, start_date, notes


def image_quality(image_bytes: bytes) -> tuple[int, dict]:
    """Return non-diagnostic image usability checks; never a disease classifier."""
    with Image.open(io.BytesIO(image_bytes)) as image:
        image = image.convert("RGB")
        width, height = image.size
        resized = image.resize((1, 1))
        brightness = sum(ImageStat.Stat(resized).mean) / 3
        edge_variance = ImageStat.Stat(image.filter(ImageFilter.FIND_EDGES).convert("L")).var[0]
    issues = []
    if min(width, height) < 450:
        issues.append("The image is too small; retake it at a higher resolution.")
    if brightness < 55:
        issues.append("The image is too dark; use even, indirect light.")
    elif brightness > 220:
        issues.append("The image is overexposed; avoid flash glare.")
    if edge_variance < 90:
        issues.append("The image may be out of focus; retake it sharply.")
    resolution_score = min(1.0, (width * height) / (1000 * 1000)) * 18
    light_score = max(0, 18 - abs(brightness - 145) / 8)
    focus_score = min(18, edge_variance / 11)
    quality = int(max(0, min(98, 46 + resolution_score + light_score + focus_score)))
    quality_status = "LOW_QUALITY" if issues else "GOOD" if quality >= 85 else "ACCEPTABLE"
    return quality, {
        "width": width, "height": height, "brightness": round(brightness, 1),
        "edge_variance": round(edge_variance, 1), "usable_for_research_model": not issues,
        "status": quality_status, "issues": issues,
    }


def reported_priority(area: str, score: int, urgent_selected: bool) -> dict:
    """Add modality context to the shared non-diagnostic priority vocabulary."""
    result = normalise_reported_priority(score, urgent_selected)
    if result["severity"] == "LOW":
        result["summary"] = f"Your reported {area.lower()} concern can be tracked over time. Seek professional advice if it changes, becomes painful, persists, or worries you."
    elif result["severity"] == "MODERATE":
        result["summary"] = f"Your reported {area.lower()} details are worth tracking and discussing with a clinician if new, changing, persistent, or concerning."
    return result


def priority_payload(priority: dict, label: str) -> dict:
    """Keep the API's reported-concern priority separate from likelihood."""
    return {
        "score": priority["score"],
        "level": priority["level"],
        "severity": priority["severity"],
        "label": label,
        "professional_evaluation_recommended": priority["professional_evaluation_recommended"],
        "urgent_attention_recommended": priority["urgent_attention_recommended"],
        "version": priority["version"],
        "method": priority["method"],
        "thresholds": priority["thresholds"],
        "validation_status": priority["validation_status"],
        "factors": priority["factors"],
    }


def attach_condition_intelligence(response: dict) -> dict:
    """Attach the versioned knowledge/CDSS view without changing model output."""
    response["condition_intelligence"] = build_assessment_intelligence(
        area=response["area"],
        classifier=response.get("research_classifier", {}),
        priority=response.get("risk", {}),
        severity=response.get("severity", {}),
        input_validation=response.get("input_validation", {}),
        context=response.get("patient_context", {}),
        cdss=response.get("clinical_decision_support", {}),
        recommendations=response.get("recommendations", {}),
    )
    return response


def stored_analysis_summary(response: dict) -> dict:
    """Persist reproducible result metadata without retaining image pixels or base64 assets."""
    classifier = response.get("research_classifier", {})
    segmentation = response.get("segmentation", {})
    candidate = response.get("candidate_region", {})
    return {
        "created_at": response["created_at"], "area": response["area"], "input_type": response.get("input_type", "image"), "quality": response["quality"], "input_validation": response.get("input_validation", {}), "risk": response["risk"], "pirs": response.get("pirs", {}), "model_metadata": response.get("model_metadata", {}), "model_pipeline": response.get("model_pipeline", {}),
        "screening": response["screening"], "manual_context": response["manual_context"], "patient_context": response.get("patient_context", {}), "severity": response.get("severity", {}), "clinical_decision_support": response.get("clinical_decision_support", {}), "progress_comparison": response.get("progress_comparison", {}), "journey": response.get("journey"),
        "candidate_region": {key: candidate.get(key) for key in ("available", "method", "reliable", "affected_area_percent", "notice", "message")},
        "segmentation": {key: segmentation.get(key) for key in ("available", "status", "model", "affected_area_percent", "segmentation_confidence", "notice", "message")},
        "classification": {key: classifier.get(key) for key in ("available", "model", "model_id", "model_version", "dataset_version", "pipeline_version", "top_prediction", "top_predictions", "alternatives", "condition_likelihood", "calibration", "uncertainty", "explainability", "model_confidence", "raw_top_score", "low_confidence", "below_confidence_threshold", "confidence_threshold", "confidence_notice", "notice")},
        "recommendations": response.get("recommendations", {}), "care_plan": response.get("care_plan", {}), "explainability": response.get("explainability", {}), "condition_intelligence": response.get("condition_intelligence", {}),
        "image_stored": False,
    }


def versioned_progress_summary(connection: pymysql.Connection, user_id: int | None, area: str, current: dict) -> dict:
    """Extend the existing saved-analysis history without creating a second history system."""
    if not user_id:
        return build_progress_comparison(user_id=None, area=area, current=current, historical=[])
    with connection.cursor() as cursor:
        cursor.execute("SELECT assessment_id, result_json, created_at FROM analysis_records WHERE user_id=%s AND area=%s ORDER BY created_at ASC, id ASC", (user_id, area))
        records = cursor.fetchall()
    historical = []
    for record in records:
        try:
            summary = json.loads(record["result_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            summary = {}
        historical.append({"assessment_id": record["assessment_id"], "created_at": record["created_at"].isoformat() if hasattr(record["created_at"], "isoformat") else str(record["created_at"]), "summary": summary})
    return build_progress_comparison(user_id=user_id, area=area, current=current, historical=historical)


def clinician_first_care_plan(risk_score: int) -> dict:
    """Return safe next steps; never a diagnosis, prescription, or treatment plan."""
    if risk_score >= 65:
        timing = "Avoid relying on app suggestions for a painful, rapidly changing, or severe concern; seek timely professional care."
    elif risk_score >= 40:
        timing = "Keep a simple, non-irritating routine and consider professional advice before changing products."
    else:
        timing = "Track changes with the local progress report and seek professional advice if the concern persists, changes, or worries you."
    return {
        "heading": "Personal care suggestions",
        "next_step": timing,
        "routine_guardrail": "Use gentle cleansing, avoid picking or harsh scrubs, and stop any product that stings or irritates. This is general self-care, not a treatment plan.",
        "product_guardrail": "Personal-care categories are not chosen for a disease or a deficiency. Discuss new products, supplements, allergies, pregnancy, broken skin, and ongoing treatment with a pharmacist or registered medical practitioner.",
        "diet_guidance": "For general wellbeing, aim for regular meals with protein, fruits or vegetables, and hydration. Do not use supplements or diet changes to self-treat a suspected condition.",
        "diagnosis_notice": "The app reports screening support and, only in dermatoscopic lesion mode, a research label—not a verified diagnosis.",
    }


def personal_care_catalog(area: str, risk_score: int) -> list[dict]:
    """Generic non-medicinal categories; no brands, prescription drugs or doses."""
    items = [
        {"name": "Fragrance-free moisturiser", "category": "Cosmetic / personal care", "purpose": "Supports the skin barrier for dry-feeling skin.", "guardrail": "Check ingredients against known allergies; stop use if irritation occurs.", "affiliate_url": os.getenv("AFFILIATE_MOISTURISER_URL", "")},
        {"name": "Broad-spectrum sunscreen", "category": "Cosmetic / personal care", "purpose": "Everyday sun-protection product discovery.", "guardrail": "This is not a treatment; choose a labelled product from a licensed seller.", "affiliate_url": os.getenv("AFFILIATE_SUNSCREEN_URL", "")},
    ]
    if area == "Hair":
        items.append({"name": "Gentle, fragrance-free scalp cleanser", "category": "Cosmetic / personal care", "purpose": "A low-irritation cleansing option to discuss with a pharmacist.", "guardrail": "Avoid using on broken or painful skin without clinician advice.", "affiliate_url": os.getenv("AFFILIATE_SCALP_CLEANSER_URL", "")})
    elif area == "Nails":
        items.append({"name": "Protective nail-care emollient", "category": "Cosmetic / personal care", "purpose": "Helps support dry cuticles and nail surroundings.", "guardrail": "Do not use it to self-treat discoloured, painful, or lifting nails.", "affiliate_url": os.getenv("AFFILIATE_NAIL_CARE_URL", "")})
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
        return jsonify({"status": "ok", "service": "dermamatrix-api", "mode": "educational-prototype", "database": "mysql-connected" if connected else "unavailable", "model": "screening-triage-v1.1-demo"})
    except pymysql.MySQLError:
        return jsonify({
            "status": "ok",
            "service": "dermamatrix-api",
            "mode": "educational-prototype",
            "database": "mysql-unavailable-no-persistence",
            "model": "screening-triage-v1.1-demo",
            "notice": "Screening demo is active. Configure MYSQL_USER and MYSQL_PASSWORD to enable profile and assessment persistence.",
        })


@app.get("/api/model-registry")
def model_registry():
    """Expose real module readiness without claiming that missing models are available."""
    return jsonify({
        "shared_components": ["input validation", "reported-concern priority", "care guidance", "progress metadata", "doctor-directory handoff"],
        "health_area_workflows": public_workflows(),
        "condition_knowledge": {"version": KNOWLEDGE_VERSION, "capability_matrix": model_capability_matrix()},
        "modalities": [
            {"area": "Skin", "input": "dermatoscopic single-lesion image", "adapter": "HAM10000 ResNet-34 research adapter", "available": os.path.isfile(os.path.join(os.path.dirname(__file__), "models", "ham10000_resnet34_research.ptw")), "explainability": "Grad-CAM when the research model runs", "notice": "Research-only; not a diagnosis."},
            {"area": "Hair", "input": "scalp / hair image", "adapter": "Hair/scalp image-model adapter", "available": False, "explainability": "Grad-CAM available after compatible trained weights are configured", "notice": "No trained hair/scalp model is bundled with this deployment."},
            {"area": "Nails", "input": "nail image", "adapter": "Nail image-model adapter", "available": False, "explainability": "Grad-CAM available after compatible trained weights are configured", "notice": "No trained nail model is bundled with this deployment."},
            {"area": "Sweat", "input": "symptom questionnaire", "adapter": "Sweat tabular-model adapter", "available": False, "explainability": "Questionnaire input-contribution summary", "notice": "The runnable prototype is rule-based; no validated XGBoost model or SHAP explainer is bundled."},
        ],
        "model_metadata": all_model_metadata(),
    })


@app.get("/api/auth/session")
def auth_session():
    """Restore an authenticated account from the signed, HTTP-only session cookie."""
    patient_id = str(session.get("patient_id", "")).strip()
    if not patient_id:
        return jsonify({"authenticated": False})
    connection = database()
    try:
        user = user_for_patient(connection, patient_id)
        if not user:
            session.clear()
            return jsonify({"authenticated": False})
        return jsonify({"authenticated": True, "account": account_response(user)})
    finally:
        connection.close()


@app.post("/api/auth/register")
def register_account():
    """Create a local account. Only a salted password hash is persisted."""
    payload = request.get_json(silent=True) or {}
    full_name = str(payload.get("full_name", "")).strip()[:150]
    email_address = str(payload.get("email_address", "")).strip().lower()[:254]
    phone_number = str(payload.get("phone_number", "")).strip()[:30]
    password = str(payload.get("password", ""))
    confirm_password = str(payload.get("confirm_password", ""))
    if not full_name or "@" not in email_address or len(phone_number) < 8:
        return jsonify({"error": "Enter your full name, a valid email address, and a valid phone number."}), 400
    if len(password) < 8:
        return jsonify({"error": "Use a password with at least 8 characters."}), 400
    if password != confirm_password:
        return jsonify({"error": "Password confirmation does not match."}), 400
    if not payload.get("account_consent"):
        return jsonify({"error": "Confirm the account and privacy acknowledgement to continue."}), 400

    patient_id = f"DMX-{datetime.now(timezone.utc).strftime('%y%m%d')}-{os.urandom(3).hex().upper()}"
    timestamp = now()
    connection = database()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM auth_accounts WHERE email_address=%s", (email_address,))
            if cursor.fetchone():
                return jsonify({"error": "An account already exists for this email. Sign in instead."}), 409
            password_hash = generate_password_hash(password)
            cursor.execute(
                """INSERT INTO users (patient_id, full_name, phone_number, email_address, created_at)
                   VALUES (%s, %s, %s, %s, %s)""",
                (patient_id, full_name, phone_number, email_address, timestamp),
            )
            user_id = cursor.lastrowid
            cursor.execute("INSERT INTO auth_accounts (user_id, email_address, password_hash, created_at) VALUES (%s, %s, %s, %s)", (user_id, email_address, password_hash, timestamp))
            cursor.execute("INSERT INTO medical_histories (user_id, past_history, current_history, updated_at) VALUES (%s, %s, %s, %s)", (user_id, "", "", timestamp))
            cursor.execute("INSERT INTO consent_records (user_id, consent_version, purpose, accepted_at) VALUES (%s, %s, %s, %s)", (user_id, "local-auth-v1", "Local account authentication and secure session", timestamp))
        connection.commit()
        session.clear(); session["user_id"] = user_id; session["patient_id"] = patient_id
        return jsonify({"authenticated": True, "account": {"patient_id": patient_id, "full_name": full_name, "phone_number": phone_number, "email_address": email_address, "stored_in": "mysql"}}), 201
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.post("/api/auth/login")
def login_account():
    payload = request.get_json(silent=True) or {}
    email_address = str(payload.get("email_address", "")).strip().lower()[:254]
    password = str(payload.get("password", ""))
    if not email_address or not password:
        return jsonify({"error": "Enter your email address and password."}), 400
    connection = database()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT u.id, u.patient_id, u.full_name, u.phone_number, u.email_address, a.password_hash
                   FROM auth_accounts a JOIN users u ON u.id=a.user_id WHERE a.email_address=%s""",
                (email_address,),
            )
            user = cursor.fetchone()
        if not user or not user.get("password_hash") or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "That email and password do not match."}), 401
        session.clear(); session["user_id"] = user["id"]; session["patient_id"] = user["patient_id"]
        return jsonify({"authenticated": True, "account": account_response(user)})
    finally:
        connection.close()


@app.post("/api/auth/logout")
def logout_account():
    session.clear()
    return jsonify({"authenticated": False})


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

    connection = database()
    try:
        patient_id = str(session.get("patient_id", "")).strip()
        user = user_for_patient(connection, patient_id)
        if not user:
            return jsonify({"error": "Sign in before saving health details."}), 401
        if str(payload["email_address"]).strip().lower() != user["email_address"]:
            return jsonify({"error": "Email address changes are not supported in this local prototype."}), 400
        timestamp = now()
        with connection.cursor() as cursor:
            cursor.execute("UPDATE users SET full_name=%s, phone_number=%s WHERE id=%s", (payload["full_name"].strip(), payload["phone_number"].strip(), user["id"]))
            cursor.execute("INSERT INTO medical_histories (user_id, past_history, current_history, updated_at) VALUES (%s, %s, %s, %s)", (user["id"], payload["past_history"].strip(), payload["current_history"].strip(), timestamp))
            cursor.execute("INSERT INTO consent_records (user_id, consent_version, purpose, accepted_at) VALUES (%s, %s, %s, %s)", (user["id"], "india-prototype-v1", "MySQL storage of profile and health-history data for screening support", timestamp))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return jsonify({"patient_id": patient_id, "full_name": payload["full_name"].strip(), "email_address": user["email_address"], "phone_number": payload["phone_number"].strip(), "stored_in": "mysql", "consent_recorded": True})


@app.get("/api/profiles/<patient_id>")
def get_profile(patient_id: str):
    """Restore a locally selected profile from MySQL without retaining history in browser storage."""
    connection = database()
    try:
        user = user_for_patient(connection, patient_id.strip())
        if not user:
            return jsonify({"error": "Profile not found in the local project database."}), 404
        return jsonify(account_response(user, account_history(connection, user["id"])))
    finally:
        connection.close()


@app.get("/api/routines")
def list_routines():
    patient_id = request.args.get("patient_id", "").strip()
    connection = database()
    try:
        user = user_for_patient(connection, patient_id)
        if not user:
            return jsonify({"error": "Create or open a local profile before viewing progress."}), 401
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT r.routine_id, r.condition_label, r.routine_name, DATE_FORMAT(r.start_date, '%%Y-%%m-%%d') AS start_date, r.notes,
                   DATE_FORMAT(r.updated_at, '%%Y-%%m-%%dT%%H:%%i:%%sZ') AS updated_at,
                   COUNT(c.id) AS checkin_count, MAX(c.checkin_date) AS latest_checkin_date
                   FROM care_routines r LEFT JOIN progress_checkins c ON c.routine_id = r.routine_id
                   WHERE r.user_id = %s GROUP BY r.id ORDER BY r.updated_at DESC""",
                (user["id"],),
            )
            routines = cursor.fetchall()
        return jsonify({"routines": routines, "image_policy": "Uploaded comparison photos are not stored."})
    finally:
        connection.close()


@app.post("/api/routines")
def create_routine():
    payload = request.get_json(silent=True) or {}
    values = routine_payload(payload)
    if not values:
        return jsonify({"error": "Provide a clinician-recorded condition, routine name, and valid start date."}), 400
    connection = database()
    try:
        user = user_for_patient(connection, str(payload.get("patient_id", "")).strip())
        if not user:
            return jsonify({"error": "Create a local profile before adding routines."}), 401
        routine_id = f"routine-{uuid.uuid4().hex[:12]}"
        timestamp = now()
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO care_routines (routine_id, user_id, condition_label, routine_name, start_date, notes, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (routine_id, user["id"], *values, timestamp, timestamp),
            )
        connection.commit()
        return jsonify({"routine_id": routine_id, "message": "Routine saved. The app does not verify diagnoses; record only clinician-confirmed information."}), 201
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.patch("/api/routines/<routine_id>")
def update_routine(routine_id: str):
    payload = request.get_json(silent=True) or {}
    values = routine_payload(payload)
    if not values:
        return jsonify({"error": "Provide a clinician-recorded condition, routine name, and valid start date."}), 400
    connection = database()
    try:
        user = user_for_patient(connection, str(payload.get("patient_id", "")).strip())
        if not user:
            return jsonify({"error": "Create a local profile before editing routines."}), 401
        with connection.cursor() as cursor:
            cursor.execute("UPDATE care_routines SET condition_label=%s, routine_name=%s, start_date=%s, notes=%s, updated_at=%s WHERE routine_id=%s AND user_id=%s", (*values, now(), routine_id, user["id"]))
            if cursor.rowcount != 1:
                return jsonify({"error": "Routine not found."}), 404
        connection.commit()
        return jsonify({"routine_id": routine_id, "message": "Routine updated."})
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.delete("/api/routines/<routine_id>")
def delete_routine(routine_id: str):
    patient_id = request.args.get("patient_id", "").strip()
    connection = database()
    try:
        user = user_for_patient(connection, patient_id)
        if not user:
            return jsonify({"error": "Create a local profile before deleting routines."}), 401
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM progress_checkins WHERE routine_id=%s AND user_id=%s", (routine_id, user["id"]))
            cursor.execute("DELETE FROM care_routines WHERE routine_id=%s AND user_id=%s", (routine_id, user["id"]))
            if cursor.rowcount != 1:
                return jsonify({"error": "Routine not found."}), 404
        connection.commit()
        return jsonify({"routine_id": routine_id, "message": "Routine and its local progress history deleted."})
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.get("/api/progress-checkins")
def list_progress_checkins():
    patient_id = request.args.get("patient_id", "").strip()
    connection = database()
    try:
        user = user_for_patient(connection, patient_id)
        if not user:
            return jsonify({"error": "Create or open a local profile before viewing progress."}), 401
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT c.checkin_id, c.routine_id, DATE_FORMAT(c.checkin_date, '%%Y-%%m-%%d') AS checkin_date, c.reported_trend,
                   c.discomfort_score, c.change_score, c.priority_score, c.note, c.image_stored, r.condition_label, r.routine_name
                   FROM progress_checkins c JOIN care_routines r ON r.routine_id=c.routine_id
                   WHERE c.user_id=%s ORDER BY c.checkin_date DESC, c.id DESC LIMIT 100""",
                (user["id"],),
            )
            checkins = cursor.fetchall()
        return jsonify({"checkins": checkins, "score_label": "Reported-concern priority, not disease risk", "image_policy": "Comparison images are processed in the browser and are not stored."})
    finally:
        connection.close()


@app.get("/api/analysis-history")
def list_analysis_history():
    """Return saved analysis metadata for a profile; uploaded image bytes are never returned or stored."""
    patient_id = request.args.get("patient_id", "").strip()
    connection = database()
    try:
        user = user_for_patient(connection, patient_id)
        if not user:
            return jsonify({"error": "Create or open a local profile before viewing saved analyses."}), 401
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT assessment_id, area, result_json, image_stored, created_at FROM analysis_records WHERE user_id=%s ORDER BY created_at DESC LIMIT 50",
                (user["id"],),
            )
            records = cursor.fetchall()
        analyses = []
        for record in records:
            summary = json.loads(record["result_json"])
            analyses.append({
                "assessment_id": record["assessment_id"], "area": record["area"], "created_at": record["created_at"].isoformat() if hasattr(record["created_at"], "isoformat") else str(record["created_at"]),
                "image_stored": bool(record["image_stored"]), "summary": summary,
            })
        return jsonify({"analyses": analyses, "image_policy": "Analysis metadata is stored for registered profiles. Uploaded image bytes are not stored in this prototype."})
    finally:
        connection.close()


@app.get("/api/reports/<assessment_id>/download")
def download_assessment_report(assessment_id: str):
    """Generate a PDF from one account-scoped stored assessment record."""
    connection = database()
    try:
        user = user_for_patient(connection, str(session.get("patient_id", "")).strip())
        if not user:
            return jsonify({"error": "Sign in to download a saved report."}), 401
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT assessment_id, area, result_json, created_at FROM analysis_records WHERE assessment_id=%s AND user_id=%s",
                (assessment_id, user["id"]),
            )
            record = cursor.fetchone()
        if not record:
            return jsonify({"error": "Saved assessment not found in your local account."}), 404
        try:
            summary = json.loads(record["result_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            return jsonify({"error": "The saved assessment record is incomplete and cannot be exported."}), 409
        assessment = {
            "assessment_id": record["assessment_id"],
            "area": record["area"],
            "created_at": record["created_at"].isoformat() if hasattr(record["created_at"], "isoformat") else str(record["created_at"]),
            "summary": summary,
        }
        report_bytes = build_assessment_report_pdf(account=account_response(user), assessment=assessment)
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO reports (report_id, assessment_id, user_id, report_type, generated_at)
                   VALUES (%s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE report_id=VALUES(report_id), generated_at=VALUES(generated_at)""",
                (f"report-{uuid.uuid4().hex[:12]}", assessment_id, user["id"], "assessment_discussion_pdf", now()),
            )
        connection.commit()
        date_label = str(assessment["created_at"])[:10] or "report"
        return send_file(
            io.BytesIO(report_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"dermamatrix-discussion-brief-{date_label}.pdf",
            max_age=0,
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.get("/api/history/download")
def download_history_export():
    """Download one signed-in account's saved metadata as a printable PDF.

    This is deliberately not a bulk image export: source photos and visual
    overlays are never stored by the local prototype.
    """
    connection = database()
    try:
        user = user_for_patient(connection, str(session.get("patient_id", "")).strip())
        if not user:
            return jsonify({"error": "Sign in to download your saved history."}), 401
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT assessment_id, area, result_json, created_at FROM analysis_records WHERE user_id=%s ORDER BY created_at DESC LIMIT 50",
                (user["id"],),
            )
            raw_analyses = cursor.fetchall()
            cursor.execute(
                """SELECT r.condition_label, r.routine_name, DATE_FORMAT(r.start_date, '%%Y-%%m-%%d') AS start_date,
                   COUNT(c.id) AS checkin_count FROM care_routines r
                   LEFT JOIN progress_checkins c ON c.routine_id=r.routine_id AND c.user_id=r.user_id
                   WHERE r.user_id=%s GROUP BY r.routine_id ORDER BY r.start_date DESC, r.id DESC LIMIT 50""",
                (user["id"],),
            )
            routines = cursor.fetchall()
            cursor.execute(
                """SELECT DATE_FORMAT(c.checkin_date, '%%Y-%%m-%%d') AS checkin_date, c.reported_trend, c.priority_score,
                   r.condition_label FROM progress_checkins c JOIN care_routines r ON r.routine_id=c.routine_id
                   WHERE c.user_id=%s ORDER BY c.checkin_date DESC, c.id DESC LIMIT 100""",
                (user["id"],),
            )
            checkins = cursor.fetchall()
        analyses = []
        for record in raw_analyses:
            try:
                summary = json.loads(record["result_json"])
            except (TypeError, ValueError, json.JSONDecodeError):
                summary = {}
            analyses.append({
                "assessment_id": record["assessment_id"],
                "area": record["area"],
                "created_at": record["created_at"].isoformat() if hasattr(record["created_at"], "isoformat") else str(record["created_at"]),
                "summary": summary,
            })
        report_bytes = build_history_report_pdf(
            account=account_response(user, account_history(connection, user["id"])),
            analyses=analyses,
            routines=routines,
            checkins=checkins,
        )
        return send_file(
            io.BytesIO(report_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"dermamatrix-personal-history-{datetime.now(timezone.utc).date().isoformat()}.pdf",
            max_age=0,
        )
    finally:
        connection.close()


@app.post("/api/progress-checkins")
def create_progress_checkin():
    payload = request.get_json(silent=True) or {}
    patient_id = str(payload.get("patient_id", "")).strip()
    routine_id = str(payload.get("routine_id", "")).strip()[:50]
    trend = str(payload.get("reported_trend", "")).strip()
    checkin_date = str(payload.get("checkin_date", "")).strip()[:10]
    note = str(payload.get("note", "")).strip()[:2000]
    if trend not in {"improving", "unchanged", "worsening"} or not routine_id:
        return jsonify({"error": "Choose a routine and a self-reported trend."}), 400
    try:
        datetime.strptime(checkin_date, "%Y-%m-%d")
        discomfort = int(payload.get("discomfort", 0)); change = int(payload.get("change", 0))
    except ValueError:
        return jsonify({"error": "Provide valid check-in details."}), 400
    connection = database()
    try:
        user = user_for_patient(connection, patient_id)
        if not user:
            return jsonify({"error": "Create a local profile before adding a check-in."}), 401
        with connection.cursor() as cursor:
            cursor.execute("SELECT routine_id FROM care_routines WHERE routine_id=%s AND user_id=%s", (routine_id, user["id"]))
            if not cursor.fetchone():
                return jsonify({"error": "Routine not found."}), 404
        model = run_screening_model(0, max(0, discomfort), max(0, change), 80, {"width": 0, "height": 0}, urgent_concern=False)
        checkin_id = f"checkin-{uuid.uuid4().hex[:12]}"
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO progress_checkins (checkin_id, user_id, routine_id, checkin_date, reported_trend, discomfort_score, change_score, priority_score, note, image_stored, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s)",
                (checkin_id, user["id"], routine_id, checkin_date, trend, discomfort, change, model["risk_score"], note, now()),
            )
        connection.commit()
        trend_label = {"improving": "Improving — self-reported", "unchanged": "No change — self-reported", "worsening": "Worsening — self-reported"}[trend]
        return jsonify({"checkin_id": checkin_id, "priority_score": model["risk_score"], "priority_label": "Reported-concern priority, not disease risk", "progress_label": trend_label, "image_stored": False}), 201
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.post("/api/clinical-review-requests")
def request_clinical_review():
    payload = request.get_json(silent=True) or {}
    assessment_id = str(payload.get("assessment_id", "")).strip()
    if not assessment_id:
        return jsonify({"error": "An assessment ID is required."}), 400
    connection = database()
    try:
        patient_id = str(payload.get("patient_id", "")).strip()
        user = user_for_patient(connection, patient_id)
        if not user:
            return jsonify({"error": "Sign in to save a clinician-review request."}), 401
        with connection.cursor() as cursor:
            cursor.execute("SELECT assessment_id FROM analysis_records WHERE assessment_id=%s AND user_id=%s", (assessment_id, user["id"]))
            if not cursor.fetchone():
                return jsonify({"error": "Assessment not found in your local account."}), 404
            cursor.execute("INSERT INTO clinical_review_requests (user_id, assessment_id, status, requested_at) VALUES (%s, %s, %s, %s)", (user["id"], assessment_id, "awaiting_rmp_review", now()))
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
    return jsonify({"items": items, "eligible": bool(items), "consultation_required": True, "affiliate_disclosure": "Some links may be affiliate links. This does not change clinical suitability, ordering, or access to care.", "policy": "No prescription medicine, diagnosis-specific treatment, dosage, or paid ranking is provided by this prototype.", "pharmacy_notice": "Before using a suggested product or routine, consult an RMP or pharmacist and use a licensed pharmacy."})


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

    if request.form.get("image_consent") != "true":
        return jsonify({"error": "Confirm that you have consent to upload this image for screening support."}), 400
    urgent_concern = request.form.get("urgent_concern") == "true"
    image_context = request.form.get("image_context", "general_photo").strip()
    dermoscopy_attested = request.form.get("dermoscopy_attestation") == "true"
    route = route_image_assessment(area=area, image_context=image_context, dermoscopy_attested=dermoscopy_attested, image_features=image_features)
    if not route["accepted"]:
        return jsonify({"error": route["error"], "input_validation": {"status": route["status"]}}), 400
    model_output = run_screening_model(duration, discomfort, change, quality, image_features, urgent_concern)
    can_run_research_model, research_reason = route["run_research_classifier"], route["notice"]
    assessment_metadata = model_metadata(SKIN_MODEL_ID if area == "Skin" else "hair-model-adapter" if area == "Hair" else "nail-model-adapter")
    validation = {
        "status": route["status"],
        "image_context": route["image_context"],
        "image_context_label": route["image_context_label"],
        "workflow": route["workflow"],
        "category_relevance": route["notice"],
        "relevance_status": route["relevance_status"],
        "classification_status": route["classification_status"],
        "normal_appearance": "NOT_ASSESSED",
        "notice": "A usable image is not evidence of a condition. The app does not infer normality or disease from an unsupported input.",
    }
    research_classifier = {
        "available": False,
        "reason": research_reason,
        "model_id": assessment_metadata.get("model_id"),
        "model_version": assessment_metadata.get("model_version"),
        "dataset_version": assessment_metadata.get("dataset_version"),
        "pipeline_version": assessment_metadata.get("pipeline_version"),
        "condition_likelihood": {"available": False, "status": "NOT_RUN", "estimated_likelihood": None, "notice": "No classifier ran for this input, so no condition likelihood is available."},
        "calibration": {"available": False, "status": "NOT_RUN", "calibration_version": None},
        "uncertainty": {"status": "UNCERTAIN" if route["status"] == "LOW_QUALITY" else "NOT_APPLICABLE_NO_CLASSIFIER", "certainty": "NOT_AVAILABLE", "ood_status": "OOD_NOT_EVALUATED", "notice": "No classifier ran, so condition uncertainty and OOD cannot be assessed."},
    }
    candidate_region = unavailable_candidate_region(research_reason)
    segmentation = {"available": False, "status": "not_run", "affected_area_percent": None, "segmentation_confidence": None, "overlay": None, "mask": None, "message": research_reason}
    if can_run_research_model:
        candidate_region = extract_visual_candidate_region(image_bytes)
        segmentation = segment_dermoscopic_lesion(image_bytes)
        research_classifier = classify_dermoscopic_lesion(image_bytes)
        if not research_classifier.get("available"):
            validation["classification_status"] = "RESEARCH_CLASSIFIER_NOT_AVAILABLE"
            validation["notice"] = "The image met the declared dermatoscopic research route, but no approved research-model weights are configured in this deployment. No condition label was generated."
    manual_symptoms = normalise_symptoms(area, request.form.getlist("symptoms"))
    previous_treatment = request.form.get("previous_treatment", "").strip()[:500]
    risk_score = model_output["risk_score"]
    priority = reported_priority(area, risk_score, urgent_concern)
    severity = reported_symptom_severity(discomfort=discomfort, change=change, symptoms=manual_symptoms, urgent_selected=urgent_concern)
    patient_context = patient_context_snapshot(area=area, symptoms=manual_symptoms, previous_treatment=previous_treatment)
    cdss = clinical_decision_support(area=area, risk=priority, severity=severity, input_validation=validation, classifier=research_classifier, context=patient_context, urgent_selected=urgent_concern)
    pirs = calculate_pirs(
        area=area,
        priority=priority,
        model_confidence=model_output.get("confidence"),
        image_quality=quality,
        reported_factors=manual_symptoms,
    )
    assessment_id = f"dmx-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.urandom(2).hex()}"
    patient_id = request.form.get("patient_id", "").strip()
    user_id = None
    persistence = "mysql"
    response = {
        "assessment_id": assessment_id, "created_at": datetime.now(timezone.utc).isoformat(), "area": area, "input_type": "image", "source_file": secure_filename(image_file.filename),
        "quality": {"score": quality, "image_quality_score": round(quality / 100, 2), "quality_passed": not image_features["issues"], "status": image_features["status"], "label": "Suitable for visual review" if not image_features["issues"] else "Retake recommended", "issues": image_features["issues"], "visibility": "Not automatically assessed; choose the matching image type and ensure the relevant area is centred."}, "input_validation": validation, "risk": priority_payload(priority, "Reported-concern priority, not disease risk"), "pirs": pirs, "screening": {"title": priority["title"], "summary": priority["summary"]},
        "manual_context": {"symptoms": manual_symptoms, "previous_treatment": previous_treatment}, "patient_context": patient_context, "severity": severity, "clinical_decision_support": cdss, "candidate_region": candidate_region, "segmentation": segmentation, "model": model_output, "model_metadata": assessment_metadata, "research_classifier": research_classifier, "model_pipeline": {"workflow": route["workflow"], "input_validation": validation["status"], "category_relevance": validation["category_relevance"], "anatomical_relevance": validation["relevance_status"], "image_quality_gate": image_features["status"], "preprocessing": "RGB conversion, median denoising, resize/centre crop for research classifier" if can_run_research_model else "RGB conversion and image-quality evaluation", "candidate_region": candidate_region["method"] if candidate_region.get("available") else "not run", "segmentation": segmentation.get("status", "not_run"), "feature_extraction": "ResNet-34 convolutional features" if research_classifier.get("available") else "not run", "attention_map": "Grad-CAM research attention map" if research_classifier.get("available") else "not run", "classification": "HAM10000 research classifier" if research_classifier.get("available") else route["classification_status"], "calibration": research_classifier.get("calibration", {}).get("status", "NOT_RUN"), "uncertainty": research_classifier.get("uncertainty", {}).get("status", "NOT_RUN"), "explainability": "Grad-CAM research attention map" if research_classifier.get("available") else "not available because no compatible classifier ran", "model_lineage": {key: assessment_metadata.get(key) for key in ("model_id", "model_version", "dataset_version", "pipeline_version", "status")}},
        "recommendations": build_recommendations(area, research_classifier, cdss=cdss), "medical_disclaimer": "Educational prototype only. This response is not a diagnosis or medical advice.", "clinical_status": "prompt_professional_care_selected" if urgent_concern else "screening_complete", "urgent_notice": "You selected a prompt-care concern. Contact a registered medical practitioner or local urgent/emergency service now if you feel severely unwell; do not wait for app results." if urgent_concern else None, "persistence": persistence, "care_plan": clinician_first_care_plan(risk_score), "commerce_eligibility": "personal_care_only" if cdss["product_guidance"] == "GENERAL_SELF_CARE_ONLY" else "general_care_only",
    }
    if area in {"Hair", "Nails"}:
        modality = "Hair/scalp" if area == "Hair" else "Nail"
        response["modality_score"] = {"score": quality, "label": "Image readiness score, not a hair/nail health score or diagnosis."}
        response["model_pipeline"] = {
            "workflow": route["workflow"],
            "image_quality_gate": "completed",
            "category_relevance": validation["category_relevance"],
            "anatomical_relevance": validation["relevance_status"],
            "preprocessing": "RGB conversion and image-quality evaluation",
            "candidate_region": f"{modality} region detector not configured",
            "segmentation": "not configured",
            "feature_extraction": f"{modality} image-model adapter not configured",
            "attention_map": "Grad-CAM unavailable until a compatible trained model is configured",
            "classification": f"{modality} disorder classifier not configured",
            "calibration": "NOT_APPLICABLE_NO_CLASSIFIER",
            "uncertainty": "NOT_APPLICABLE_NO_CLASSIFIER",
            "explainability": "Unavailable because no modality-specific classifier ran",
            "model_lineage": {key: assessment_metadata.get(key) for key in ("model_id", "model_version", "dataset_version", "pipeline_version", "status")},
    }
    if not patient_id:
        attach_condition_intelligence(response)
        response["persistence"] = "not-persisted-guest"
        response["progress_comparison"] = versioned_progress_summary(None, None, area, response)
        response["journey"] = response["progress_comparison"].get("journey")
        return jsonify(response)

    connection = None
    try:
        connection = database()
        user = user_for_patient(connection, patient_id)
        if not user:
            return jsonify({"error": "Your session is no longer available. Sign in again before saving an assessment."}), 401
        user_id = user["id"]
        history = account_history(connection, user_id)
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS count FROM analysis_records WHERE user_id=%s AND area=%s", (user_id, area))
            previous_count = int(cursor.fetchone()["count"])
        response["patient_context"] = patient_context_snapshot(area=area, symptoms=manual_symptoms, previous_treatment=previous_treatment, history=history, previous_assessment_count=previous_count)
        response["clinical_decision_support"] = clinical_decision_support(area=area, risk=priority, severity=severity, input_validation=validation, classifier=research_classifier, context=response["patient_context"], urgent_selected=urgent_concern)
        response["recommendations"] = build_recommendations(area, research_classifier, cdss=response["clinical_decision_support"])
        response["commerce_eligibility"] = "personal_care_only" if response["clinical_decision_support"]["product_guidance"] == "GENERAL_SELF_CARE_ONLY" else "general_care_only"
        attach_condition_intelligence(response)
        response["progress_comparison"] = versioned_progress_summary(connection, user_id, area, response)
        response["journey"] = response["progress_comparison"].get("journey")
        timestamp = now()
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO assessments (assessment_id, user_id, area, risk_score, quality_score, clinical_status, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (assessment_id, user_id, area, priority["score"], quality, response["clinical_status"], timestamp),
            )
            cursor.execute(
                "INSERT INTO analysis_records (assessment_id, user_id, area, result_json, image_stored, created_at) VALUES (%s, %s, %s, %s, FALSE, %s)",
                (assessment_id, user_id, area, json.dumps(stored_analysis_summary(response)), timestamp),
            )
        connection.commit()
    except pymysql.MySQLError:
        if connection:
            connection.rollback()
        response["persistence"] = "not-persisted-mysql-unavailable"
        response["progress_comparison"] = {"status": "NOT_SAVED", "summary": "Analysis metadata could not be saved because MySQL is unavailable.", "journey": None}
    finally:
        if connection:
            connection.close()
    return jsonify(response)


@app.post("/api/sweat-assessments")
def create_sweat_assessment():
    """Keep tabular sweat inputs out of the image-model route."""
    payload = request.get_json(silent=True) or {}
    if payload.get("questionnaire_consent") is not True:
        return jsonify({"error": "Confirm questionnaire consent before continuing."}), 400
    pattern = str(payload.get("pattern", "usual")).strip().lower()
    if pattern not in {"usual", "excessive", "reduced"}:
        return jsonify({"error": "Choose the reported sweating pattern."}), 400
    sweat = sweat_questionnaire_result(payload)
    assessment_id = f"dmx-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.urandom(2).hex()}"
    urgent_concern = bool(payload.get("urgent_concern"))
    risk_score = max(sweat["risk_score"], 65) if urgent_concern else sweat["risk_score"]
    priority = reported_priority("Sweat", risk_score, urgent_concern)
    assessment_metadata = model_metadata("sweat-questionnaire-v1")
    sweat_symptoms = normalise_symptoms("Sweat", [
        "excessive_sweating" if pattern == "excessive" else "reduced_sweating" if pattern == "reduced" else "",
        "daily_impact" if payload.get("daily_impact") else "",
        "medication_change" if payload.get("medication_change") else "",
    ])
    severity = reported_symptom_severity(discomfort=0, change=0, symptoms=sweat_symptoms, urgent_selected=urgent_concern)
    patient_context = patient_context_snapshot(area="Sweat", symptoms=sweat_symptoms, previous_treatment="")
    sweat_classifier = {"available": False, "uncertainty": {"status": "NOT_AVAILABLE_NO_VALIDATED_TABULAR_MODEL"}}
    cdss = clinical_decision_support(area="Sweat", risk=priority, severity=severity, input_validation={"status": "VALID_RELEVANT"}, classifier=sweat_classifier, context=patient_context, urgent_selected=urgent_concern)
    pirs = calculate_pirs(
        area="Sweat",
        priority=priority,
        reported_factors=[
            f"Pattern: {pattern}",
            f"Body location: {str(payload.get('body_location', '')).strip()[:120]}" if str(payload.get("body_location", "")).strip() else "",
        ],
    )
    patient_id = str(payload.get("patient_id", "")).strip()
    response = {
        "assessment_id": assessment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "area": "Sweat",
        "input_type": "questionnaire",
        "quality": {"score": None, "image_quality_score": None, "quality_passed": True, "label": "Questionnaire complete", "issues": [], "visibility": "Not applicable to questionnaire input."},
        "input_validation": {"status": "VALID_RELEVANT", "category_relevance": "Sweat concerns use the dedicated questionnaire pathway; no image is accepted.", "normal_appearance": "NOT_APPLICABLE", "notice": "Questionnaire completion does not determine a diagnosis or a sweat-gland disorder."},
        "risk": priority_payload(priority, "Questionnaire-based reported-concern priority, not disease risk"),
        "pirs": pirs,
        "screening": {"title": priority["title"], "summary": sweat["summary"] if not urgent_concern else priority["summary"]},
        "manual_context": {"symptoms": sweat_symptoms, "previous_treatment": "", "sweat_questionnaire": {"pattern": pattern, "body_location": str(payload.get("body_location", "")).strip()[:120]}},
        "patient_context": patient_context,
        "severity": severity,
        "clinical_decision_support": cdss,
        "candidate_region": unavailable_candidate_region("Questionnaire inputs do not have an image region."),
        "segmentation": {"available": False, "status": "not_applicable", "affected_area_percent": None, "segmentation_confidence": None, "overlay": None, "mask": None, "message": "Segmentation is not applicable to questionnaire input."},
        "research_classifier": {"available": False, "reason": "No image classifier runs for the sweat questionnaire.", "uncertainty": sweat_classifier["uncertainty"]},
        "model": sweat["engine"],
        "model_metadata": assessment_metadata,
        "explainability": sweat["explainability"],
        "model_pipeline": {
            "input_validation": "completed",
            "category_relevance": "Questionnaire-only modality",
            "preprocessing": "Questionnaire values bounded and normalised",
            "classification": "No validated XGBoost model configured",
            "calibration": "NOT_APPLICABLE_NO_SUPERVISED_MODEL",
            "uncertainty": "NOT_AVAILABLE_NO_VALIDATED_TABULAR_MODEL",
            "explainability": "Questionnaire input-contribution summary",
            "segmentation": "not applicable",
            "attention_map": "not applicable",
            "model_lineage": {key: assessment_metadata.get(key) for key in ("model_id", "model_version", "dataset_version", "pipeline_version", "status")},
        },
        "recommendations": build_recommendations("Sweat", None, cdss=cdss),
        "medical_disclaimer": "Educational prototype only. This response is not a diagnosis or medical advice.",
        "clinical_status": "prompt_professional_care_selected" if urgent_concern else "screening_complete",
        "urgent_notice": "You selected a prompt-care concern. Contact a registered medical practitioner or local urgent/emergency service now if you feel severely unwell; do not wait for app results." if urgent_concern else None,
        "persistence": "mysql",
        "care_plan": clinician_first_care_plan(risk_score),
        "commerce_eligibility": "personal_care_only" if cdss["product_guidance"] == "GENERAL_SELF_CARE_ONLY" else "general_care_only",
    }
    if not patient_id:
        attach_condition_intelligence(response)
        response["persistence"] = "not-persisted-guest"
        response["progress_comparison"] = versioned_progress_summary(None, None, "Sweat", response)
        response["journey"] = response["progress_comparison"].get("journey")
        return jsonify(response)

    connection = None
    try:
        connection = database()
        user = user_for_patient(connection, patient_id)
        if not user:
            return jsonify({"error": "Your session is no longer available. Sign in again before saving an assessment."}), 401
        history = account_history(connection, user["id"])
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS count FROM analysis_records WHERE user_id=%s AND area=%s", (user["id"], "Sweat"))
            previous_count = int(cursor.fetchone()["count"])
        response["patient_context"] = patient_context_snapshot(area="Sweat", symptoms=sweat_symptoms, previous_treatment="", history=history, previous_assessment_count=previous_count)
        response["clinical_decision_support"] = clinical_decision_support(area="Sweat", risk=priority, severity=severity, input_validation=response["input_validation"], classifier=sweat_classifier, context=response["patient_context"], urgent_selected=urgent_concern)
        response["recommendations"] = build_recommendations("Sweat", None, cdss=response["clinical_decision_support"])
        response["commerce_eligibility"] = "personal_care_only" if response["clinical_decision_support"]["product_guidance"] == "GENERAL_SELF_CARE_ONLY" else "general_care_only"
        attach_condition_intelligence(response)
        response["progress_comparison"] = versioned_progress_summary(connection, user["id"], "Sweat", response)
        response["journey"] = response["progress_comparison"].get("journey")
        timestamp = now()
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO assessments (assessment_id, user_id, area, risk_score, quality_score, clinical_status, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (assessment_id, user["id"], "Sweat", priority["score"], 0, response["clinical_status"], timestamp),
            )
            cursor.execute(
                "INSERT INTO analysis_records (assessment_id, user_id, area, result_json, image_stored, created_at) VALUES (%s, %s, %s, %s, FALSE, %s)",
                (assessment_id, user["id"], "Sweat", json.dumps(stored_analysis_summary(response)), timestamp),
            )
        connection.commit()
    except pymysql.MySQLError:
        if connection:
            connection.rollback()
        response["persistence"] = "not-persisted-mysql-unavailable"
        response["progress_comparison"] = {"status": "NOT_SAVED", "summary": "Questionnaire history could not be saved because MySQL is unavailable.", "journey": None}
    finally:
        if connection:
            connection.close()
    return jsonify(response)


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "The image is larger than 10 MB."}), 413


@app.errorhandler(pymysql.MySQLError)
def mysql_unavailable(_error):
    return jsonify({"error": "MySQL is temporarily unavailable. Screening can continue without saving a profile; retry persistence after database access is restored."}), 503


@app.after_request
def prevent_stale_local_assets(response):
    """Keep the local demo browser from retaining an old client after a live update."""
    if request.path in {"/", "/index.html"} or request.path.endswith((".css", ".js")):
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


load_local_env()
app.config.update(
    SECRET_KEY=os.getenv("FLASK_SECRET_KEY") or os.urandom(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("FLASK_SESSION_SECURE", "false").lower() == "true",
)
initialise_database()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
