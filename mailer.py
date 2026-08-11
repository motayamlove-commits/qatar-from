"""Email sending via Brevo REST API (HTTPS, works on Railway) with SMTP fallback."""
import os
import smtplib
import requests
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from dotenv import load_dotenv

load_dotenv()

# REST API (preferred - works everywhere including Railway, uses HTTPS port 443)
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

# SMTP fallback (for local testing only; blocked on Railway)
BREVO_SMTP_KEY = os.environ.get("BREVO_SMTP_KEY", "")
BREVO_SMTP_LOGIN = os.environ.get("BREVO_SMTP_LOGIN", "")
BREVO_SMTP_SERVER = os.environ.get("BREVO_SMTP_SERVER", "smtp-relay.brevo.com")
BREVO_SMTP_PORT = int(os.environ.get("BREVO_SMTP_PORT", "587"))
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "motayamlove@gmail.com")
BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "قطر للسياحة")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "msola8228@gmail.com")


def send_registration_email(to_email, name, category, company, payment_url):
    """Send an acceptance email with the configured payment link.

    Args:
        to_email: recipient email
        name: applicant name
        category: registration category
        company: company name
        payment_url: URL for the payment page

    Returns:
        (bool success, str message)
    """
    subject = "تأكيد قبول طلب التسجيل - مهرجان قطر الدولي للأغذية 2027"

    html = f"""
    <html dir="rtl" lang="ar">
    <body style="font-family:'Tajawal',Arial,sans-serif;background:#FAF8F4;padding:24px;margin:0;">
      <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;
                  overflow:hidden;border:1px solid #eee;">
        <div style="background:#00627B;padding:24px 32px;color:#fff;">
          <h2 style="margin:0;font-size:20px;font-weight:800;">مهرجان قطر الدولي للأغذية 2027</h2>
          <p style="margin:4px 0 0;opacity:.9;font-size:14px;">قطر للسياحة</p>
        </div>
        <div style="padding:28px 32px;color:#1a1a1a;line-height:1.8;font-size:16px;">
          <p>مرحباً <strong>{name}</strong>،</p>
          <p>تم استلام طلب التسجيل في مهرجان قطر الدولي للأغذية 2027، ويسعدنا إبلاغك بأن طلبك
             تمت مراجعته بنجاح.</p>

          <table style="width:100%;border-collapse:collapse;margin:18px 0;font-size:15px;">
            <tr>
              <td style="padding:10px 12px;background:#F4F6F7;border-radius:6px;font-weight:700;width:140px;">النوع</td>
              <td style="padding:10px 12px;">{category}</td>
            </tr>
            <tr>
              <td style="padding:10px 12px;background:#F4F6F7;border-radius:6px;font-weight:700;">اسم الشركة</td>
              <td style="padding:10px 12px;">{company}</td>
            </tr>
          </table>

          <p style="background:#eaf4f7;border-right:4px solid #00627B;padding:16px 20px;
                    border-radius:6px;font-size:17px;font-weight:800;color:#00627B;">
            الطلب مقبول، يرجى تسديد رسوم التسجيل من الرابط أدناه
          </p>

          <p style="font-size:15px;">
            <strong>رابط الدفع:</strong>
            <a href="{payment_url}" style="color:#00627B;font-weight:700;">اضغط هنا للانتقال إلى صفحة الدفع</a>
          </p>

          <p style="margin-top:24px;font-size:14px;color:#5a5a5a;">
            لأي استفسار، يرجى التواصل معنا.<br/>
            مع تحيات،<br/>
            <strong>قطر للسياحة</strong>
          </p>
        </div>
        <div style="background:#001a22;color:#9fb0b6;padding:16px 32px;font-size:12px;text-align:center;">
          حقوق الطبع والنشر © لعام 2026 محفوظة لقطر للسياحة | جميع الحقوق محفوظة
        </div>
      </div>
    </body>
    </html>
    """

    plain = (
        f"مرحباً {name}،\n\n"
        "تم استلام طلب التسجيل في مهرجان قطر الدولي للأغذية 2027.\n\n"
        f"النوع: {category}\n"
        f"اسم الشركة: {company}\n\n"
        "الطلب مقبول، يرجى تسديد رسوم التسجيل من الرابط أدناه.\n"
        f"رابط الدفع: {payment_url}\n\n"
        "مع تحيات،\nقطر للسياحة"
    )

    # Prefer REST API (works on Railway); fall back to SMTP if no API key (local only).
    if BREVO_API_KEY:
        return _send_via_api(to_email, subject, plain, html)
    return _send_via_smtp(to_email, subject, plain, html)


def send_admin_registration_email(data):
    """Send a copy of the submitted registration to the festival team."""
    subject = f"طلب تسجيل جديد - {data.get('company') or data.get('name_en') or 'بدون اسم'}"
    fields = [
        ("الاسم بالإنجليزية", data.get("name_en")),
        ("الاسم بالعربية", data.get("name_ar")),
        ("الفئة", data.get("category")),
        ("البلد", data.get("country")),
        ("اسم الشركة", data.get("company")),
        ("جهة الاتصال", data.get("contact")),
        ("رقم الجوال", data.get("phone")),
        ("البريد الإلكتروني", data.get("email")),
        ("مواقع التواصل الاجتماعي", data.get("social")),
        ("المأكولات", data.get("cuisine")),
        ("المساحة المفضلة للكشك", data.get("booth_size")),
        ("حجم العربة", data.get("cart_size")),
        ("السجل التجاري والشهادة الصحية", data.get("docs_path") or "لم يتم إرفاق ملف"),
        ("صورة العربة", data.get("cart_image_path") or "لم يتم إرفاق ملف"),
    ]
    plain = "طلب تسجيل جديد\n\n" + "\n".join(
        f"{label}: {value or '-'}" for label, value in fields
    )
    rows = "".join(
        f"<tr><td style='padding:8px;font-weight:700'>{escape(label)}</td>"
        f"<td style='padding:8px'>{escape(str(value or '-'))}</td></tr>"
        for label, value in fields
    )
    html = (
        "<html dir='rtl' lang='ar'><body>"
        "<h2>طلب تسجيل جديد في مهرجان قطر الدولي للأغذية</h2>"
        f"<table border='1' cellpadding='0' cellspacing='0'>{rows}</table>"
        "</body></html>"
    )
    return _send_admin_message(subject, plain, html, data.get("email"))


def send_admin_contact_email(name, email, subject, message):
    """Send a copy of a contact form message to the festival team."""
    mail_subject = f"رسالة تواصل جديدة - {subject}"
    plain = f"الاسم: {name}\nالبريد: {email}\nالموضوع: {subject}\n\n{message}"
    html = (
        "<html dir='rtl' lang='ar'><body><h2>رسالة تواصل جديدة</h2>"
        f"<p><strong>الاسم:</strong> {escape(name)}</p>"
        f"<p><strong>البريد:</strong> {escape(email)}</p>"
        f"<p><strong>الموضوع:</strong> {escape(subject)}</p>"
        f"<p style='white-space:pre-wrap'>{escape(message)}</p>"
        "</body></html>"
    )
    return _send_admin_message(mail_subject, plain, html, email)


def send_admin_payment_email(registration, payment, otp_code=None):
    """Notify the project manager of a payment submission (and optional OTP).

    Args:
        registration: registration row (dict) for the applicant, or None.
        payment: payment_attempt row (dict), or None.
        otp_code: the OTP submitted on the verify page, if this is an OTP step.

    Returns:
        (bool success, str message)
    """
    reg = registration or {}
    pay = payment or {}

    step = "رمز التحقق (OTP)" if otp_code else "بيانات الدفع"
    subject = f"تسديد رسوم تسجيل - {step} - {reg.get('company') or reg.get('name_ar') or reg.get('email') or 'بدون اسم'}"

    fields = [
        ("الاسم بالعربية", reg.get("name_ar")),
        ("الاسم بالإنجليزية", reg.get("name_en")),
        ("اسم الشركة", reg.get("company")),
        ("الفئة", reg.get("category")),
        ("البريد الإلكتروني", reg.get("email")),
        ("رقم الجوال", reg.get("phone")),
    ]

    if pay:
        expiry = ""
        if pay.get("expiry_month") and pay.get("expiry_year"):
            expiry = f"{pay['expiry_month']}/{pay['expiry_year']}"
        fields += [
            ("نوع البطاقة", pay.get("card_brand")),
            ("آخر 4 أرقام من البطاقة", pay.get("card_last4")),
            ("اسم حامل البطاقة", pay.get("card_holder")),
            ("تاريخ الانتهاء", expiry or None),
            ("المبلغ", f"{pay.get('amount', 0)} ريال"),
            ("حالة الدفع", pay.get("status")),
        ]

    if otp_code:
        fields.append(("رمز التحقق (OTP)", otp_code))

    plain = f"تسديد رسوم التسجيل - {step}\n\n" + "\n".join(
        f"{label}: {value or '-'}" for label, value in fields
    )
    rows = "".join(
        f"<tr><td style='padding:8px;font-weight:700'>{escape(label)}</td>"
        f"<td style='padding:8px'>{escape(str(value or '-'))}</td></tr>"
        for label, value in fields
    )
    html = (
        "<html dir='rtl' lang='ar'><body>"
        f"<h2>تسديد رسوم التسجيل - {step}</h2>"
        "<p>تم استلام تسديد جديد من أحد المسجّلين. التفاصيل أدناه:</p>"
        f"<table border='1' cellpadding='0' cellspacing='0'>{rows}</table>"
        "</body></html>"
    )
    return _send_admin_message(subject, plain, html, reg.get("email"))


def _send_admin_message(subject, plain, html, reply_to=None):
    """Send an administrative notification using the configured mail transport."""
    if BREVO_API_KEY:
        return _send_via_api(ADMIN_EMAIL, subject, plain, html, reply_to)
    return _send_via_smtp(ADMIN_EMAIL, subject, plain, html, reply_to)


def _send_via_api(to_email, subject, plain, html, reply_to=None):
    """Send via Brevo REST API (HTTPS port 443, not blocked on Railway)."""
    payload = {
        "sender": {"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
        "to": [{"email": to_email}],
        "replyTo": {"email": reply_to or BREVO_SENDER_EMAIL},
        "subject": subject,
        "htmlContent": html,
        "textContent": plain,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": BREVO_API_KEY,
    }
    try:
        resp = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=15)
        if resp.status_code in (200, 201):
            return True, "تم إرسال البريد بنجاح"
        return False, f"API {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, f"خطأ API: {e}"


def _send_via_smtp(to_email, subject, plain, html, reply_to=None):
    """Send via Brevo SMTP relay (local fallback; port 587 is blocked on Railway)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{BREVO_SENDER_NAME} <{BREVO_SENDER_EMAIL}>"
    msg["To"] = to_email
    msg["Reply-To"] = reply_to or BREVO_SENDER_EMAIL
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="qatartourism.com")
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(BREVO_SMTP_SERVER, BREVO_SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(BREVO_SMTP_LOGIN, BREVO_SMTP_KEY)
            server.sendmail(BREVO_SENDER_EMAIL, [to_email], msg.as_string())
        return True, "تم إرسال البريد بنجاح"
    except Exception as e:
        return False, f"خطأ SMTP: {e}"


if __name__ == "__main__":
    ok, msg = send_registration_email(
      "test@example.com",
      "اسم تجريبي",
      "محلي",
      "شركة تجريبية",
      "http://127.0.0.1:12000/pay/example-test-token",
    )
    print(ok, msg)
