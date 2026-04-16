"""
One-time database setup / repair script.

Use this for production (Vercel) because serverless functions should NOT be relied on
to run migrations automatically.

What it does:
- Creates tables from SQLAlchemy models if missing (db.create_all)
- Ensures hybrid-auth schema: password_hash nullable, firebase_uid column exists

Run:
  Windows (PowerShell):
    $env:DATABASE_URL="postgresql://..."
    $env:SECRET_KEY="..."
    $env:FIREBASE_PROJECT_ID="aaj-ka-freelancer"
    .\venv\Scripts\python scripts\db_setup.py

  Linux/Mac:
    export DATABASE_URL="postgresql://..."
    export SECRET_KEY="..."
    export FIREBASE_PROJECT_ID="aaj-ka-freelancer"
    python scripts/db_setup.py
"""

from sqlalchemy import text

from app import create_app
from config import Config
from app.extensions import db


def main():
    app = create_app(Config)

    with app.app_context():
        # Create tables if missing
        db.create_all()

        # Hybrid auth fix for Postgres
        if db.engine.dialect.name == "postgresql":
            # Make password_hash nullable
            db.session.execute(text('ALTER TABLE "user" ALTER COLUMN password_hash DROP NOT NULL'))

            # Ensure firebase_uid column exists (best-effort)
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS firebase_uid VARCHAR(128)'))

            # Optional: make firebase_uid unique when present (Postgres allows multiple NULLs on UNIQUE)
            db.session.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_user_firebase_uid ON "user"(firebase_uid)'))

            db.session.commit()

    print("DB setup complete.")


if __name__ == "__main__":
    main()

