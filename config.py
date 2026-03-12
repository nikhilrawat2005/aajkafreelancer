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

    # Optimized connection settings for Vercel + Supabase
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 5,
        "max_overflow": 2,
    }

    # =====================================================
    # SUPABASE CONFIG (REALTIME CHAT)
    # =====================================================
    SUPABASE_URL = os.getenv(
        "SUPABASE_URL"
    )

    SUPABASE_ANON_KEY = os.getenv(
        "SUPABASE_ANON_KEY"
    )

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
    UPLOAD_FOLDER = os.path.join(
        BASE_DIR,
        "static",
        "uploads",
        "profile_images"
    )

    TEMP_UPLOAD_FOLDER = os.path.join(
        BASE_DIR,
        "static",
        "uploads",
        "temp"
    )

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB