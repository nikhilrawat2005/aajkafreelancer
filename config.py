import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


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

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database - serverless-friendly (smaller pool for Vercel)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 2 if os.getenv("VERCEL") else 5,
        "max_overflow": 1 if os.getenv("VERCEL") else 2,
    }

    # =====================================================
    # FIREBASE CONFIG (AUTH + FIRESTORE CHAT)
    # =====================================================
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
    # For frontend (Google Sign-In, Firestore client)
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

    MAIL_DEFAULT_SENDER = os.getenv(
        "MAIL_DEFAULT_SENDER",
        MAIL_USERNAME
    )

    # =====================================================
    # RATE LIMITING
    # =====================================================
    RATELIMIT_STORAGE_URI = os.getenv(
        "RATELIMIT_STORAGE_URI",
        "memory://"
    )

    # =====================================================
    # FILE UPLOAD SETTINGS
    # =====================================================
    # On Vercel, use /tmp (ephemeral); locally use static/uploads
    _UPLOAD_BASE = "/tmp" if os.getenv("VERCEL") else BASE_DIR
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