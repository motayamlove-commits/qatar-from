"""Database management for registration records."""
import os
import secrets
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

PAYMENT_TOKEN_TTL_DAYS = 7

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_F8rjiUD0aBXL@ep-icy-rain-ayoep5wg-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
)


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Create the registrations table if it doesn't exist."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS registrations (
                    id SERIAL PRIMARY KEY,
                    name_en TEXT,
                    name_ar TEXT,
                    category TEXT,
                    country TEXT,
                    company TEXT,
                    contact TEXT,
                    phone TEXT,
                    email TEXT,
                    social TEXT,
                    cuisine TEXT,
                    booth_size TEXT,
                    cart_size TEXT,
                    docs_path TEXT,
                    cart_image_path TEXT,
                    status TEXT DEFAULT 'مقبول',
                    payment_link_sent BOOLEAN DEFAULT FALSE,
                    email_error TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                """
            )
            # Ensure new columns exist on pre-existing tables
            cur.execute(
                "ALTER TABLE registrations ADD COLUMN IF NOT EXISTS email_error TEXT;"
            )

            # Per-customer payment tokens (unique, expire after 7 days)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_tokens (
                    id SERIAL PRIMARY KEY,
                    token TEXT UNIQUE NOT NULL,
                    registration_id INTEGER REFERENCES registrations(id) ON DELETE CASCADE,
                    email TEXT,
                    name TEXT,
                    category TEXT,
                    company TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    expires_at TIMESTAMPTZ NOT NULL,
                    revoked BOOLEAN DEFAULT FALSE,
                    attempts INTEGER DEFAULT 0
                );
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_payment_tokens_token ON payment_tokens (token);"
            )

            # Payment form submissions (card data masked — never full number/CVV)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_attempts (
                    id SERIAL PRIMARY KEY,
                    registration_id INTEGER REFERENCES registrations(id) ON DELETE CASCADE,
                    token TEXT,
                    card_last4 CHAR(4),
                    card_brand TEXT,
                    card_holder TEXT,
                    expiry_month CHAR(2),
                    expiry_year CHAR(2),
                    amount NUMERIC(10,2),
                    status TEXT DEFAULT 'submitted',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_payment_attempts_token ON payment_attempts (token);"
            )

            # OTP verification submissions
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS otp_attempts (
                    id SERIAL PRIMARY KEY,
                    payment_attempt_id INTEGER REFERENCES payment_attempts(id) ON DELETE CASCADE,
                    token TEXT,
                    otp_code VARCHAR(6),
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_otp_attempts_token ON otp_attempts (token);"
            )
        conn.commit()
        print("Database initialized: registrations table ready.")
    finally:
        conn.close()


def insert_registration(data):
    """Insert a registration record and return the new id."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO registrations
                    (name_en, name_ar, category, country, company, contact, phone,
                     email, social, cuisine, booth_size, cart_size, docs_path, cart_image_path)
                VALUES (%(name_en)s, %(name_ar)s, %(category)s, %(country)s,
                        %(company)s, %(contact)s, %(phone)s, %(email)s, %(social)s,
                        %(cuisine)s, %(booth_size)s, %(cart_size)s,
                        %(docs_path)s, %(cart_image_path)s)
                RETURNING id;
                """,
                {
                    "name_en": data.get("name_en"),
                    "name_ar": data.get("name_ar"),
                    "category": data.get("category"),
                    "country": data.get("country"),
                    "company": data.get("company"),
                    "contact": data.get("contact"),
                    "phone": data.get("phone"),
                    "email": data.get("email"),
                    "social": data.get("social"),
                    "cuisine": data.get("cuisine"),
                    "booth_size": data.get("booth_size"),
                    "cart_size": data.get("cart_size"),
                    "docs_path": data.get("docs_path"),
                    "cart_image_path": data.get("cart_image_path"),
                },
            )
            row = cur.fetchone()
        conn.commit()
        return row["id"] if row else None
    finally:
        conn.close()


def list_registrations(limit=100):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM registrations ORDER BY created_at DESC LIMIT %s;",
                (limit,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def update_email_status(reg_id, sent, message):
    """Mark whether the confirmation email was sent for a registration, and store any error."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE registrations SET payment_link_sent = %s, email_error = %s WHERE id = %s;",
                (sent, message, reg_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()


def create_payment_token(reg_id, email, name, category, company):
    """Create a unique, time-limited payment token for one registration."""
    token = secrets.token_urlsafe(32)
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO payment_tokens
                    (token, registration_id, email, name, category, company, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s,
                        NOW() + (%s || ' days')::INTERVAL)
                RETURNING token, expires_at;
                """,
                (token, reg_id, email, name, category, company, str(PAYMENT_TOKEN_TTL_DAYS)),
            )
            row = cur.fetchone()
        conn.commit()
        return {"token": row["token"], "expires_at": row["expires_at"]}
    finally:
        conn.close()


def get_payment_token(token):
    """Return the token row if it exists, or None. Expiry/revoked checked by caller."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, registration_id, email, name, category, company,
                       created_at, expires_at, revoked, attempts
                FROM payment_tokens WHERE token = %s;
                """,
                (token,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def increment_payment_attempt(token_id):
    """Record one more payment attempt for a token (retries are allowed)."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE payment_tokens SET attempts = attempts + 1 WHERE id = %s;",
                (token_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()


def insert_payment_attempt(token, data):
    """Insert a masked payment form submission and return the new id.

    Only non-sensitive card data is stored: last 4 digits, brand, holder,
    and expiry. Full card number and CVV are NEVER stored.
    """
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO payment_attempts
                    (registration_id, token, card_last4, card_brand, card_holder,
                     expiry_month, expiry_year, amount, status)
                VALUES (%(registration_id)s, %(token)s, %(card_last4)s, %(card_brand)s,
                        %(card_holder)s, %(expiry_month)s, %(expiry_year)s, %(amount)s,
                        %(status)s)
                RETURNING id;
                """,
                {
                    "registration_id": data.get("registration_id"),
                    "token": token,
                    "card_last4": data.get("card_last4"),
                    "card_brand": data.get("card_brand"),
                    "card_holder": data.get("card_holder"),
                    "expiry_month": data.get("expiry_month"),
                    "expiry_year": data.get("expiry_year"),
                    "amount": data.get("amount"),
                    "status": data.get("status", "submitted"),
                },
            )
            row = cur.fetchone()
        conn.commit()
        return row["id"] if row else None
    except Exception:
        conn.rollback()
        return None
    finally:
        conn.close()


def insert_otp_attempt(token, payment_attempt_id, otp_code, status="pending"):
    """Insert an OTP verification submission and return the new id."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO otp_attempts
                    (payment_attempt_id, token, otp_code, status)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (payment_attempt_id, token, otp_code, status),
            )
            row = cur.fetchone()
        conn.commit()
        return row["id"] if row else None
    except Exception:
        conn.rollback()
        return None
    finally:
        conn.close()


def get_latest_payment_attempt(token):
    """Return the most recent payment attempt row for a token, or None."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, registration_id, token, card_last4, card_brand,
                       card_holder, expiry_month, expiry_year, amount, status, created_at
                FROM payment_attempts WHERE token = %s
                ORDER BY created_at DESC LIMIT 1;
                """,
                (token,),
            )
            return cur.fetchone()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
