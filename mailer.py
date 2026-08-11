"""Email sending via Brevo REST API (HTTPS, works on Railway) with SMTP fallback."""
import os
import smtplib
import requests
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


def _send_via_api(to_email, subject, plain, html):
    """Send via Brevo REST API (HTTPS port 443, not blocked on Railway)."""
    payload = {
        "sender": {"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
        "to": [{"email": to_email}],
        "replyTo": {"email": BREVO_SENDER_EMAIL},
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


def _send_via_smtp(to_email, subject, plain, html):
    """Send via Brevo SMTP relay (local fallback; port 587 is blocked on Railway)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{BREVO_SENDER_NAME} <{BREVO_SENDER_EMAIL}>"
    msg["To"] = to_email
    msg["Reply-To"] = BREVO_SENDER_EMAIL
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
