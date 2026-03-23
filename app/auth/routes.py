"""
Authentication routes - Google Sign-In + Complete Profile flow.
No email verification. Two steps: 1) Google Sign-In, 2) Form filling (if new user).
"""
from flask import render_template, redirect, url_for, flash, session, request, Blueprint, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
import logging

from app.extensions import db, limiter
from app.models import User
from app.forms import CompleteProfileForm
from app.data.services_data import SERVICES_DATA
from app.user_service import UserService
from app.firebase_client import verify_firebase_token, sync_user_to_firebase, create_custom_token

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


# =====================================================
# LEGACY REDIRECTS (old signup/verify flow removed)
# =====================================================

@auth_bp.route('/signup')
def signup_redirect():
    return redirect(url_for('auth.login'))


@auth_bp.route('/verify/<int:pending_id>')
def verify_redirect(pending_id):
    return redirect(url_for('auth.login'))


@auth_bp.route('/resend-code/<int:pending_id>')
def resend_code_redirect(pending_id):
    return redirect(url_for('auth.login'))


# =====================================================
# CHECK USERNAME AVAILABILITY (for complete profile)
# =====================================================

@auth_bp.route('/check-availability')
@limiter.limit("30 per minute")
def check_availability():
    field = request.args.get("field")
    value = request.args.get("value")
    if field not in ["username", "email"] or not value:
        return jsonify({"available": False})

    user_exists = User.query.filter_by(**{field: value}).first()
    if user_exists:
        return jsonify({"available": False})

    return jsonify({"available": True})


# =====================================================
# LOGIN (Google Sign-In button)
# =====================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with Google Sign-In. No traditional form - Google only."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    return render_template('login.html')


# =====================================================
# GOOGLE AUTH CALLBACK
# =====================================================

@auth_bp.route('/google/callback', methods=['POST'])
@limiter.limit("10 per minute")
def google_callback():
    """
    Receives Firebase ID token from Google Sign-In.
    Verifies token, finds or creates user, redirects to complete-profile or dashboard.
    """
    data = request.get_json()
    id_token = data.get('id_token') if data else None

    if not id_token:
        return jsonify({'error': 'Missing id_token'}), 400

    decoded = verify_firebase_token(id_token)
    if not decoded:
        return jsonify({'error': 'Invalid token'}), 401

    firebase_uid = decoded.get('uid')
    email = decoded.get('email')
    name = decoded.get('name') or decoded.get('email', '').split('@')[0]

    if not firebase_uid or not email:
        return jsonify({'error': 'Invalid token data'}), 400

    # Check if user already exists
    user = UserService.get_user_by_firebase_uid(firebase_uid)
    if user:
        login_user(user)
        return jsonify({
            'success': True,
            'redirect': url_for('main.dashboard'),
        })

    # New user - store in session, redirect to complete profile
    session['google_signup'] = {
        'firebase_uid': firebase_uid,
        'email': email,
        'name': name,
    }
    session.permanent = True

    return jsonify({
        'success': True,
        'redirect': url_for('auth.complete_profile'),
    })


# =====================================================
# COMPLETE PROFILE (Step 2 for new Google users)
# =====================================================

@auth_bp.route('/complete-profile', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def complete_profile():
    """
    Form for new users to fill after Google Sign-In.
    Collects: username, full_name, college, year, branch, section, phone, bio, is_worker, skills.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    google_data = session.get('google_signup')
    if not google_data:
        flash('Please sign in with Google first.', 'warning')
        return redirect(url_for('auth.login'))

    form = CompleteProfileForm()
    skill_categories = SERVICES_DATA

    if form.validate_on_submit():
        try:
            # Check username availability
            if User.query.filter_by(username=form.username.data).first():
                flash('Username already taken. Please choose another.', 'danger')
                return redirect(url_for('auth.complete_profile'))

            if User.query.filter_by(email=google_data['email']).first():
                flash('This email is already registered.', 'danger')
                session.pop('google_signup', None)
                return redirect(url_for('auth.login'))

            user = UserService.create_user_from_google(
                firebase_uid=google_data['firebase_uid'],
                email=google_data['email'],
                full_name=form.full_name.data,
                username=form.username.data,
                college_name=form.college_name.data,
                year=form.year.data,
                class_name=form.class_name.data,
                section=form.section.data,
                phone_number=form.phone_number.data,
                short_bio=form.short_bio.data or '',
                is_worker=form.is_worker.data,
                skills=form.skills.data or '',
            )
            session.pop('google_signup', None)
            login_user(user)
            sync_user_to_firebase(user)
            flash('Profile created successfully! Welcome.', 'success')
            return redirect(url_for('main.dashboard'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Complete profile error: {e}")
            flash('Registration failed. Please try again.', 'danger')

    # Pre-fill name from Google
    if request.method == 'GET' and not form.full_name.data:
        form.full_name.data = google_data.get('name', '')

    return render_template(
        'complete_profile.html',
        form=form,
        skill_categories=skill_categories,
        google_email=google_data.get('email', ''),
    )


# =====================================================
# LOGOUT
# =====================================================

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('google_signup', None)
    flash('Logged out.', 'info')
    return redirect(url_for('main.landing'))


# =====================================================
# FIREBASE CUSTOM TOKEN (for chat Firestore access)
# =====================================================

@auth_bp.route('/firebase-token')
@login_required
def firebase_token():
    """Returns a Firebase custom token for the current user to access Firestore from client."""
    if not current_user.firebase_uid:
        return jsonify({'error': 'User not linked to Firebase'}), 400
    try:
        token = create_custom_token(current_user.firebase_uid)
        return jsonify({'token': token})
    except Exception as e:
        logger.error(f"Firebase custom token error: {e}")
        return jsonify({'error': 'Failed to create token'}), 500


# =====================================================
# CHANGE PASSWORD (only for users with password)
# =====================================================

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    from app.forms import ChangePasswordForm
    if not current_user.password_hash:
        flash('You signed in with Google. Password change is not available.', 'info')
        return redirect(url_for('main.profile', username=current_user.username))

    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not check_password_hash(current_user.password_hash, form.old_password.data):
            flash('Incorrect password.', 'danger')
            return redirect(url_for('auth.change_password'))
        UserService.change_password(current_user, form.new_password.data)
        flash('Password changed.', 'success')
        return redirect(url_for('main.profile', username=current_user.username))
    return render_template('change_password.html', form=form)
