import os
import json
import firebase_admin
from firebase_admin import credentials

from flask import Flask, render_template, flash, redirect, request, url_for
from config import Config
from werkzeug.exceptions import RequestEntityTooLarge
from flask_wtf.csrf import CSRFError
from sqlalchemy import inspect, text

from app.extensions import db, mail, login_manager, limiter, migrate, csrf
from app.services.skill_service import SkillService
from app.models import HireRequest

# ✅ ADMIN IMPORT

try:
    from app.admin import admin_bp
    HAS_ADMIN = True
except ImportError:
    admin_bp = None
    HAS_ADMIN = False

# ✅ FIREBASE INIT

def init_firebase():
    if not firebase_admin._apps:
        firebase_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

        if firebase_json:
            cred_dict = json.loads(firebase_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        else:
            raise Exception("Firebase credentials missing")

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 🔥 Firebase init
    init_firebase()

    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    limiter.storage_uri = app.config.get('RATELIMIT_STORAGE_URI')
    limiter.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'

    from app.auth.routes import auth_bp
    from app.main.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    if HAS_ADMIN and admin_bp:
        app.register_blueprint(admin_bp)

    @app.errorhandler(404)
    def not_found_error(e):
        return render_template('error.html', error="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('error.html', error="Internal server error"), 500

    @app.errorhandler(RequestEntityTooLarge)
    def file_too_large(e):
        flash("File too large.", "danger")
        return redirect(request.url)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash("Security token expired.", "danger")
        return redirect(url_for('main.index'))

    with app.app_context():
        try:
            inspector = inspect(db.engine)
            columns = [c['name'] for c in inspector.get_columns('user')]

            if 'firebase_uid' not in columns:
                db.session.execute(text('ALTER TABLE "user" ADD COLUMN firebase_uid VARCHAR(128)'))
                db.session.commit()

        except Exception:
            db.session.rollback()

    return app
