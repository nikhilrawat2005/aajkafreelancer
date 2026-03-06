from flask import Flask, render_template, flash, redirect, request, jsonify, url_for
from config import Config
from app.extensions import db, mail, login_manager, limiter, migrate, csrf, socketio
from app.services.skill_service import SkillService
from werkzeug.exceptions import RequestEntityTooLarge
from flask_wtf.csrf import CSRFError
import os
import logging
from app.models import HireRequest
from sqlalchemy import inspect, text

# Try to import admin blueprint; if not available, continue without it
try:
    from app.admin import admin_bp
    HAS_ADMIN = True
except ImportError:
    admin_bp = None
    HAS_ADMIN = False
    logging.warning("Admin blueprint not available – export feature disabled.")


def create_app(config_class=Config):

    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )

    app.config.from_object(config_class)

    # ===============================
    # Initialize Extensions
    # ===============================
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    limiter.storage_uri = app.config['RATELIMIT_STORAGE_URI']
    limiter.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # SocketIO init
    socketio.init_app(app)

    login_manager.login_view = 'auth.login'

    # ===============================
    # Create upload folders (LOCAL ONLY)
    # ===============================
    try:
        if not os.environ.get("VERCEL"):
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            os.makedirs(app.config['TEMP_UPLOAD_FOLDER'], exist_ok=True)
    except Exception as e:
        app.logger.warning(f"Upload folder creation skipped: {e}")

    # ===============================
    # Import Models
    # ===============================
    from app import models
    from app.chat import models as chat_models
    from app.notifications import models as notif_models

    # ===============================
    # USER LOADER
    # ===============================
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(models.User, int(user_id))
        except Exception:
            return None

    # ===============================
    # Register Blueprints
    # ===============================
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

    # ===============================
    # Context Processors
    # ===============================
    @app.context_processor
    def inject_unread_count():
        from flask_login import current_user
        if current_user.is_authenticated:
            from app.chat.service import ChatService
            count = ChatService.get_unread_count(current_user.id)
            return {'unread_messages_count': count}
        return {'unread_messages_count': 0}

    @app.context_processor
    def inject_pending_requests_count():
        from flask_login import current_user
        if current_user.is_authenticated and current_user.is_worker:
            count = HireRequest.pending_count_for_worker(current_user.id)
            return {'pending_requests_count': count}
        return {'pending_requests_count': 0}

    # ===============================
    # Jinja Filter
    # ===============================
    def skill_description_filter(skill):
        return SkillService.get_description(skill)

    app.jinja_env.filters['skill_description'] = skill_description_filter

    # ===============================
    # Error Handlers
    # ===============================
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', error='Page not found'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('error.html', error='Internal server error'), 500

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_file(e):
        flash("Profile image must be under 10MB.", "danger")
        return redirect(request.url)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash('CSRF token missing or invalid', 'danger')
        return redirect(request.url or url_for('main.landing'))

    # ===============================
    # DATABASE INIT
    # ===============================
    with app.app_context():
        db.create_all()

        try:
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user')]

            if 'is_admin' not in columns:
                db.session.execute(
                    text('ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT FALSE')
                )
                db.session.commit()

        except Exception as e:
            app.logger.warning(f"Could not add is_admin column: {e}")
            db.session.rollback()

    return app