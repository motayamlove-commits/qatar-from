"""Flask backend for the Qatar International Food Festival registration form.

- Serves the static website (HTML/CSS/JS/assets)
- Handles POST /api/register: saves to PostgreSQL, uploads files, emails applicant
- GET /api/registrations: list saved records
"""
import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from db import init_db, insert_registration, list_registrations, update_email_status
from mailer import send_registration_email

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED = {".png", ".jpg", ".jpeg", ".pdf"}
MAX_BYTES = 10 * 1024 * 1024  # 10MB

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")


def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED


def save_upload(file_storage, prefix):
    """Save an uploaded file and return its relative path, or None."""
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        return None
    if file_storage.content_length and file_storage.content_length > MAX_BYTES:
        return None
    name = secure_filename(file_storage.filename)
    unique = f"{prefix}_{name}"
    path = os.path.join(UPLOAD_DIR, unique)
    file_storage.save(path)
    return unique


@app.route("/")
def root():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(BASE_DIR, filename)


@app.route("/api/register", methods=["POST"])
def register():
    try:
        form = request.form

        # Collect text fields
        data = {
            "name_en": (form.get("name_en") or "").strip(),
            "name_ar": (form.get("name_ar") or "").strip(),
            "category": (form.get("category") or "").strip(),
            "country": (form.get("country") or "").strip(),
            "company": (form.get("company") or "").strip(),
            "contact": (form.get("contact") or "").strip(),
            "phone": (form.get("phone") or "").strip(),
            "email": (form.get("email") or "").strip(),
            "social": (form.get("social") or "").strip(),
            "cuisine": (form.get("cuisine") or "").strip(),
            "booth_size": (form.get("size") or form.get("booth_size") or "").strip(),
            "cart_size": (form.get("cart_size") or "").strip(),
        }

        # Basic validation
        required = [
            "name_en", "name_ar", "category", "company",
            "contact", "phone", "email", "social", "cuisine",
        ]
        missing = [f for f in required if not data[f]]
        if missing:
            return jsonify({"ok": False, "error": f"حقول ناقصة: {', '.join(missing)}"}), 400

        # File uploads
        data["docs_path"] = save_upload(request.files.get("docs"), "docs")
        data["cart_image_path"] = save_upload(request.files.get("cart_image"), "cart")

        # Save to database
        reg_id = insert_registration(data)
        if not reg_id:
            return jsonify({"ok": False, "error": "فشل حفظ البيانات في قاعدة البيانات"}), 500

        # Send email synchronously (reliable across environments incl. Railway)
        display_name = data["name_ar"] or data["name_en"]
        email_ok, email_msg = send_registration_email(
            data["email"], display_name, data["category"], data["company"]
        )
        update_email_status(reg_id, email_ok, "" if email_ok else email_msg)

        return jsonify({
            "ok": True,
            "id": reg_id,
            "email_sent": email_ok,
            "message": "تم استلام طلبك بنجاح. سيصلك بريد التأكيد خلال لحظات.",
        })

    except Exception as e:
        return jsonify({"ok": False, "error": f"خطأ في الخادم: {e}"}), 500


@app.route("/api/registrations", methods=["GET"])
def get_registrations():
    try:
        rows = list_registrations()
        return jsonify({"ok": True, "count": len(rows), "data": rows})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "status": "running"})


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 12000))
    app.run(host="0.0.0.0", port=port, debug=False)
