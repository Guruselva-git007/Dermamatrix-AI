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
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image, ImageFilter, ImageStat
from werkzeug.utils import secure_filename

from model_service import run_screening_model
from lesion_classifier import classify_dermoscopic_lesion
from recommendation_service import build_recommendations
from segmentation_service import extract_visual_candidate_region, segment_dermoscopic_lesion, unavailable_candidate_region


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
    """Resolve a local demo profile; real deployment requires authenticated sessions."""
    if not patient_id:
        return None
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, patient_id, full_name FROM users WHERE patient_id = %s", (patient_id,))
        return cursor.fetchone()


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
    return quality, {
        "width": width, "height": height, "brightness": round(brightness, 1),
        "edge_variance": round(edge_variance, 1), "usable_for_research_model": not issues,
        "issues": issues,
    }


def screening_summary(area: str, risk_score: int) -> tuple[str, str, str]:
    if risk_score < 40:
        return ("TRACK AND REVISIT", "A lower-priority screening snapshot", f"Your reported {area.lower()} concern can be tracked over time. Consider professional advice if it changes, becomes painful, or worries you.")
    if risk_score < 65:
        return ("SCREENING SNAPSHOT", "Keep an eye on reported changes", f"Your reported {area.lower()} details are worth tracking and discussing with a dermatologist if new, changing, persistent, or concerning.")
    return ("PROMPT-CARE FLAG", "Do not rely on the app alone", "Your selected symptom details suggest seeking timely professional care. This tool cannot determine a diagnosis or urgency on its own.")


def research_model_status(area: str, image_context: str, dermoscopy_attested: bool, image_features: dict) -> tuple[bool, str]:
    """Guard research inference to its published image domain."""
    if area != "Skin":
        return False, "The lesion research model is limited to dermatoscopic skin-lesion images."
    if image_context != "dermoscopic_lesion":
        return False, "Choose a dermatoscopic lesion image only if a dermatoscope was used."
    if not dermoscopy_attested:
        return False, "Confirm that this is a single, in-focus dermatoscopic lesion image before research inference."
    if not image_features["usable_for_research_model"]:
        return False, "Retake the image before research inference: " + " ".join(image_features["issues"])
    return True, "Eligible for research-only dermatoscopic lesion inference."


def stored_analysis_summary(response: dict) -> dict:
    """Persist reproducible result metadata without retaining image pixels or base64 assets."""
    classifier = response.get("research_classifier", {})
    segmentation = response.get("segmentation", {})
    candidate = response.get("candidate_region", {})
    return {
        "created_at": response["created_at"], "area": response["area"], "quality": response["quality"], "risk": response["risk"],
        "screening": response["screening"], "manual_context": response["manual_context"],
        "candidate_region": {key: candidate.get(key) for key in ("available", "method", "reliable", "affected_area_percent", "notice", "message")},
        "segmentation": {key: segmentation.get(key) for key in ("available", "status", "model", "affected_area_percent", "segmentation_confidence", "notice", "message")},
        "classification": {key: classifier.get(key) for key in ("available", "top_prediction", "alternatives", "model_confidence", "low_confidence", "below_confidence_threshold", "confidence_threshold", "confidence_notice", "notice")},
        "recommendations": response.get("recommendations", {}), "care_plan": response.get("care_plan", {}),
        "image_stored": False,
    }


def previous_progress_summary(connection: pymysql.Connection, user_id: int | None, area: str) -> dict:
    """Return an honest longitudinal status; no healing inference is made from this prototype."""
    if not user_id:
        return {"status": "insufficient_evidence", "previous_analysis": None, "summary": "Create a profile before saving analysis history. This result can still be saved as a local snapshot."}
    with connection.cursor() as cursor:
        cursor.execute("SELECT result_json, created_at FROM analysis_records WHERE user_id=%s AND area=%s ORDER BY created_at DESC LIMIT 1", (user_id, area))
        previous = cursor.fetchone()
    if not previous:
        return {"status": "insufficient_evidence", "previous_analysis": None, "summary": "This is the first saved analysis for this area. A future upload can be placed alongside it, but the app does not infer healing or cure."}
    return {"status": "insufficient_evidence", "previous_analysis": previous["created_at"].isoformat() if hasattr(previous["created_at"], "isoformat") else str(previous["created_at"]), "summary": "A previous analysis exists. A validated longitudinal model is not configured, so the app does not label image change as improving, stable, or worsening."}


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


@app.get("/api/profiles/<patient_id>")
def get_profile(patient_id: str):
    """Restore a locally selected profile from MySQL without retaining history in browser storage."""
    connection = database()
    try:
        user = user_for_patient(connection, patient_id.strip())
        if not user:
            return jsonify({"error": "Profile not found in the local project database."}), 404
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT past_history, current_history FROM medical_histories
                   WHERE user_id=%s ORDER BY updated_at DESC, id DESC LIMIT 1""",
                (user["id"],),
            )
            history = cursor.fetchone() or {"past_history": "", "current_history": ""}
        return jsonify({
            "patient_id": user["patient_id"],
            "full_name": user["full_name"],
            "past_history": history["past_history"],
            "current_history": history["current_history"],
            "stored_in": "mysql",
        })
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
    if area not in {"Skin", "Hair", "Nails"}:
        return jsonify({"error": "Choose Skin & sweat, Hair & scalp, or Nail health."}), 400
    try:
        duration = int(request.form.get("duration", 0)); discomfort = int(request.form.get("discomfort", 0)); change = int(request.form.get("change", 0))
    except ValueError:
        return jsonify({"error": "Invalid assessment details."}), 400

    if request.form.get("image_consent") != "true":
        return jsonify({"error": "Confirm that you have consent to upload this image for screening support."}), 400
    urgent_concern = request.form.get("urgent_concern") == "true"
    model_output = run_screening_model(duration, discomfort, change, quality, image_features, urgent_concern)
    image_context = request.form.get("image_context", "general_photo").strip()
    dermoscopy_attested = request.form.get("dermoscopy_attestation") == "true"
    can_run_research_model, research_reason = research_model_status(area, image_context, dermoscopy_attested, image_features)
    research_classifier = {"available": False, "reason": research_reason}
    candidate_region = unavailable_candidate_region(research_reason)
    segmentation = {"available": False, "status": "not_run", "affected_area_percent": None, "segmentation_confidence": None, "overlay": None, "mask": None, "message": research_reason}
    if can_run_research_model:
        candidate_region = extract_visual_candidate_region(image_bytes)
        segmentation = segment_dermoscopic_lesion(image_bytes)
        research_classifier = classify_dermoscopic_lesion(image_bytes)
    manual_symptoms = [value for value in request.form.getlist("symptoms") if value in {"itching", "pain", "redness", "swelling", "scaling", "hair_loss", "nail_change"}]
    previous_treatment = request.form.get("previous_treatment", "").strip()[:500]
    risk_score = model_output["risk_score"]
    risk_level, title, summary = screening_summary(area, risk_score)
    assessment_id = f"dmx-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.urandom(2).hex()}"
    patient_id = request.form.get("patient_id", "").strip()
    user_id = None
    persistence = "mysql"
    response = {
        "assessment_id": assessment_id, "created_at": datetime.now(timezone.utc).isoformat(), "area": area, "source_file": secure_filename(image_file.filename),
        "quality": {"score": quality, "image_quality_score": round(quality / 100, 2), "quality_passed": not image_features["issues"], "label": "Suitable for visual review" if not image_features["issues"] else "Retake recommended", "issues": image_features["issues"], "visibility": "Not automatically assessed; choose the matching image type and ensure the relevant area is centred."}, "risk": {"score": risk_score, "level": risk_level, "label": "Reported-concern priority, not disease risk"}, "screening": {"title": title, "summary": summary},
        "manual_context": {"symptoms": manual_symptoms, "previous_treatment": previous_treatment}, "candidate_region": candidate_region, "segmentation": segmentation, "model": model_output, "research_classifier": research_classifier, "model_pipeline": {"image_quality_gate": "completed", "preprocessing": "RGB conversion, median denoising, resize/centre crop for research classifier", "candidate_region": candidate_region["method"] if candidate_region.get("available") else "not run", "segmentation": segmentation.get("status", "not_run"), "feature_extraction": "ResNet-34 convolutional features" if research_classifier.get("available") else "not run", "attention_map": "Grad-CAM research attention map" if research_classifier.get("available") else "not run", "classification": "HAM10000 research classifier" if research_classifier.get("available") else "not run", "explainability": "Grad-CAM research attention map" if research_classifier.get("available") else "not available outside dermatoscopic lesion research"},
        "recommendations": build_recommendations(area, research_classifier), "medical_disclaimer": "Educational prototype only. This response is not a diagnosis or medical advice.", "clinical_status": "prompt_professional_care_selected" if urgent_concern else "screening_complete", "urgent_notice": "You selected a prompt-care concern. Contact a registered medical practitioner or local urgent/emergency service now if you feel severely unwell; do not wait for app results." if urgent_concern else None, "persistence": persistence, "care_plan": clinician_first_care_plan(risk_score), "commerce_eligibility": "personal_care_only" if not urgent_concern else "general_care_only",
    }
    connection = None
    try:
        connection = database()
        if patient_id:
            user = user_for_patient(connection, patient_id)
            user_id = user["id"] if user else None
        response["progress_comparison"] = previous_progress_summary(connection, user_id, area)
        timestamp = now()
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO assessments (assessment_id, user_id, area, risk_score, quality_score, clinical_status, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (assessment_id, user_id, area, risk_score, quality, "screening_complete", timestamp),
            )
            cursor.execute(
                "INSERT INTO analysis_records (assessment_id, user_id, area, result_json, image_stored, created_at) VALUES (%s, %s, %s, %s, FALSE, %s)",
                (assessment_id, user_id, area, json.dumps(stored_analysis_summary(response)), timestamp),
            )
        connection.commit()
    except pymysql.MySQLError:
        if connection:
            connection.rollback()
        persistence = "not-persisted-mysql-unavailable"
        response["persistence"] = persistence
        response["progress_comparison"] = {"status": "insufficient_evidence", "previous_analysis": None, "summary": "Analysis metadata could not be saved because MySQL is unavailable."}
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


load_local_env()
initialise_database()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
