import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

IS_VERCEL = bool(os.getenv("VERCEL"))


class Config:
    # =====================================================
    # SECURITY
    # =====================================================
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # =====================================================
    # DATABASE
    # =====================================================
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///college_earning.db"
    )

    # ✅ FIX: Supabase/Postgres uses "postgres://" but SQLAlchemy needs "postgresql://"
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ✅ FIX: SQLite does NOT support pool_size/max_overflow — crashes on local dev.
    # Only set pool options for PostgreSQL.
    if DATABASE_URL and "postgresql" in DATABASE_URL:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 280,
            "pool_size": 2 if IS_VERCEL else 5,
            "max_overflow": 1 if IS_VERCEL else 2,
        }
    else:
        # SQLite: no pool options
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
        }

    # =====================================================
    # FIREBASE CONFIG (AUTH + FIRESTORE CHAT)
    # =====================================================
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
    FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
    FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN")
    FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")
    FIREBASE_MESSAGING_SENDER_ID = os.getenv("FIREBASE_MESSAGING_SENDER_ID")
    FIREBASE_APP_ID = os.getenv("FIREBASE_APP_ID")

    # =====================================================
    # MAIL CONFIG
    # =====================================================
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    # =====================================================
    # RATE LIMITING
    # =====================================================
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    # =====================================================
    # FILE UPLOAD SETTINGS
    # =====================================================
    # On Vercel, use /tmp (ephemeral); locally use static/uploads
    _UPLOAD_BASE = "/tmp" if IS_VERCEL else BASE_DIR
    UPLOAD_FOLDER = os.path.join(
        _UPLOAD_BASE,
        "static",
        "uploads",
        "profile_images"
    )
    TEMP_UPLOAD_FOLDER = os.path.join(
        _UPLOAD_BASE,
        "static",
        "uploads",
        "temp"
    )

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
