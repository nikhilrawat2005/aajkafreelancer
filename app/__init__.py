import os
import logging

from flask import Flask, render_template, flash, redirect, request, url_for
from config import Config
from werkzeug.exceptions import RequestEntityTooLarge
from flask_wtf.csrf import CSRFError
from sqlalchemy import inspect, text

from app.extensions import db, mail, login_manager, limiter, migrate, csrf
from app.services.skill_service import SkillService
from app.models import HireRequest

logger = logging.getLogger(__name__)

try:
    from app.admin import admin_bp
    HAS_ADMIN = True
except ImportError:
    admin_bp = None
    HAS_ADMIN = False


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config_class)

    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    limiter.storage_uri = app.config.get("RATELIMIT_STORAGE_URI")
    limiter.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"

    # Local uploads only - on Vercel use /tmp (config already points there)
    try:
        if not os.environ.get("VERCEL"):
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            os.makedirs(app.config["TEMP_UPLOAD_FOLDER"], exist_ok=True)
    except Exception as e:
        app.logger.warning(f"Upload folder creation skipped: {e}")

    from app import models
    from app.notifications import models as notif_models  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(models.User, int(user_id))
        except Exception:
            return None

    # Blueprints
    from app.auth.routes import auth_bp
    from app.main.routes import main_bp
    from app.chat import chat_bp
    from app.notifications import notifications_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(notifications_bp)

    if HAS_ADMIN and admin_bp:
        app.register_blueprint(admin_bp)

    # Navbar counters
    @app.context_processor
    def inject_unread_messages():
        from flask_login import current_user

        if current_user.is_authenticated:
            try:
                from app.chat.service import get_unread_count

                count = get_unread_count(current_user.id)
                return dict(unread_messages_count=count)
            except Exception as e:
                app.logger.error(f"Unread count error: {e}")
                return dict(unread_messages_count=0)
        return dict(unread_messages_count=0)

    @app.context_processor
    def inject_pending_requests():
        from flask_login import current_user

        if current_user.is_authenticated and current_user.is_worker:
            try:
                count = HireRequest.pending_count_for_worker(current_user.id)
                return dict(pending_requests_count=count)
            except Exception:
                return dict(pending_requests_count=0)
        return dict(pending_requests_count=0)

    # Jinja helpers
    def skill_description_filter(skill):
        return SkillService.get_description(skill)

    app.jinja_env.filters["skill_description"] = skill_description_filter

    # profile_image_url is used in templates to support Vercel /tmp uploads
    def profile_image_url(filename):
        if not filename:
            filename = "default_profile.png"
        return url_for("main.serve_profile_image", filename=filename)

    app.jinja_env.globals["profile_image_url"] = profile_image_url

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(e):
        return render_template("error.html", error="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("error.html", error="Internal server error"), 500

    @app.errorhandler(RequestEntityTooLarge)
    def file_too_large(e):
        flash("File too large. Max size allowed is 10MB.", "danger")
        return redirect(request.url)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash("Security token expired. Please try again.", "danger")
        return redirect(request.referrer or url_for("main.landing"))

    # DB schema adjustments (best-effort; avoids breaking first deploy)
    with app.app_context():
        if not os.environ.get("VERCEL"):
            db.create_all()
        try:
            inspector = inspect(db.engine)
            columns = [c["name"] for c in inspector.get_columns("user")]

            if "is_admin" not in columns:
                db.session.execute(text('ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN DEFAULT FALSE'))
                db.session.commit()

            if "firebase_uid" not in columns:
                db.session.execute(text('ALTER TABLE "user" ADD COLUMN firebase_uid VARCHAR(128)'))
                db.session.commit()

            # Hybrid auth: make password_hash nullable in Postgres if it isn't already
            if db.engine.dialect.name == "postgresql":
                try:
                    db.session.execute(text('ALTER TABLE "user" ALTER COLUMN password_hash DROP NOT NULL'))
                    db.session.commit()
                except Exception:
                    db.session.rollback()
        except Exception as e:
            app.logger.warning(f"Could not apply schema updates: {e}")
            db.session.rollback()

    return app
