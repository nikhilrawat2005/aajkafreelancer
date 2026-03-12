from flask import render_template, redirect, url_for, flash, session, request, Blueprint, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
import os
from datetime import datetime, timedelta
import logging

from app.extensions import db, limiter
from app.models import PendingUser, User
from app.forms import SignupForm, LoginForm, VerifyForm, ChangePasswordForm
from app.user_service import UserService
from app.email_service import EmailService
from app.data.services_data import SERVICES_DATA
from app.supabase_client import sync_user_to_supabase

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


# =====================================================
# USER CSV EXPORT
# =====================================================

def append_user_to_csv(user):
    import csv
    os.makedirs('exports', exist_ok=True)
    file_path = 'exports/users.csv'
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                'username',
                'email',
                'full_name',
                'college_name',
                'year',
                'class_name',
                'section',
                'phone_number',
                'is_worker',
                'skills',
                'created_at'
            ])
        writer.writerow([
            user.username,
            user.email,
            user.full_name,
            user.college_name,
            user.year,
            user.class_name,
            user.section,
            user.phone_number,
            user.is_worker,
            user.skills or '',
            user.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])


# =====================================================
# USERNAME / EMAIL AVAILABILITY
# =====================================================

@auth_bp.route('/check-availability')
@limiter.limit("30 per minute")
def check_availability():
    field = request.args.get("field")
    value = request.args.get("value")
    if field not in ["username", "email"] or not value:
        return jsonify({"available": False})

    UserService.cleanup_expired_pending_users()

    user_exists = User.query.filter_by(**{field: value}).first()
    if user_exists:
        return jsonify({"available": False})

    pending = PendingUser.query.filter_by(**{field: value}).first()
    if pending and (datetime.utcnow() - pending.created_at <= timedelta(minutes=15)):
        return jsonify({"available": False})

    return jsonify({"available": True})


# =====================================================
# SIGNUP
# =====================================================

@auth_bp.route('/signup', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def signup():
    UserService.cleanup_expired_pending_users()
    form = SignupForm()
    skill_categories = SERVICES_DATA

    if form.validate_on_submit():
        try:
            existing_user = User.query.filter(
                (User.email == form.email.data) |
                (User.username == form.username.data)
            ).first()
            if existing_user:
                flash("Username or email already registered.", "warning")
                return redirect(url_for('auth.signup'))

            existing_pending = PendingUser.query.filter(
                (PendingUser.email == form.email.data) |
                (PendingUser.username == form.username.data)
            ).first()
            if existing_pending:
                flash("Email or username already waiting for verification.", "warning")
                return redirect(url_for('auth.signup'))

            pending = UserService.create_pending_user(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,
                full_name=form.full_name.data,
                college_name=form.college_name.data,
                year=form.year.data,
                class_name=form.class_name.data,
                section=form.section.data,
                phone_number=form.phone_number.data,
                short_bio=form.short_bio.data,
                is_worker=form.is_worker.data,
                commit=False
            )
            db.session.flush()

            code = UserService.create_verification_code(pending.id, commit=False)
            db.session.commit()

            try:
                EmailService.send_verification_email(pending.email, pending.username, code)
            except Exception as e:
                logger.error(f"EMAIL FAILED: {e}")
                flash("Account created but email failed. Try resend.", "warning")

            session['pending_id'] = pending.id
            session['pending_skills'] = form.skills.data or ''
            flash("Verification code sent to your email.", "success")
            return redirect(url_for('auth.verify', pending_id=pending.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"SIGNUP ERROR: {e}")
            flash("Registration failed.", "danger")

    return render_template("signup.html", form=form, skill_categories=skill_categories)


# =====================================================
# VERIFY EMAIL
# =====================================================

@auth_bp.route('/verify/<int:pending_id>', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def verify(pending_id):
    if session.get("pending_id") != pending_id:
        flash("Invalid verification session.", "warning")
        return redirect(url_for("auth.signup"))

    form = VerifyForm()

    if form.validate_on_submit():
        user, message = UserService.verify_pending_user(pending_id, form.code.data)
        if user:
            user.profile_image = "default_profile.png"
            if "pending_skills" in session:
                user.skills = session.pop("pending_skills")
            db.session.commit()

            login_user(user)
            append_user_to_csv(user)

            # Sync user to Supabase for chat
            sync_user_to_supabase(user)

            try:
                EmailService.send_welcome_email(user.email, user.username)
            except Exception as e:
                logger.error(f"WELCOME EMAIL FAILED: {e}")

            session.pop("pending_id", None)
            flash("Email verified successfully!", "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash(message, "danger")

    return render_template("verify.html", form=form, pending_id=pending_id)


# =====================================================
# LOGIN
# =====================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = UserService.authenticate_user(form.login_input.data, form.password.data)
        if user:
            login_user(user)
            flash("Logged in successfully.", "success")
            return redirect(url_for("main.dashboard"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html", form=form)


# =====================================================
# LOGOUT
# =====================================================

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("main.landing"))


# =====================================================
# CHANGE PASSWORD
# =====================================================

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not check_password_hash(current_user.password_hash, form.old_password.data):
            flash("Incorrect password.", "danger")
            return redirect(url_for("auth.change_password"))
        UserService.change_password(current_user, form.new_password.data)
        flash("Password changed.", "success")
        return redirect(url_for("main.profile", username=current_user.username))
    return render_template("change_password.html", form=form)


# =====================================================
# RESEND CODE
# =====================================================

@auth_bp.route('/resend-code/<int:pending_id>')
@limiter.limit("3 per minute")
def resend_code(pending_id):
    pending = db.session.get(PendingUser, pending_id)
    if not pending:
        flash("Invalid request.", "warning")
        return redirect(url_for("auth.signup"))

    code = UserService.create_verification_code(pending_id, commit=True)
    try:
        EmailService.send_verification_email(pending.email, pending.username, code)
    except Exception as e:
        logger.error(f"RESEND EMAIL ERROR: {e}")
        flash("Email failed to send.", "danger")
        return redirect(url_for("auth.verify", pending_id=pending_id))

    flash("Verification code resent.", "success")
    return redirect(url_for("auth.verify", pending_id=pending_id))