"""Database management for registration records."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

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


if __name__ == "__main__":
    init_db()
