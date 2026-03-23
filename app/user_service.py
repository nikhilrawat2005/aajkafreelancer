import random
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
from flask import current_app
from app.extensions import db
from app.models import User


class UserService:

    @staticmethod
    def generate_assigned_id(username, length_prefix=3, tries=30):
        prefix = (username.strip().lower() + 'x' * length_prefix)[:length_prefix]

        for _ in range(tries):
            num = f'{random.randint(0, 9999):04d}'
            candidate = prefix + num

            if not User.query.filter_by(assigned_id=candidate).first():
                return candidate

        raise RuntimeError('Failed to generate unique assigned ID')

    @staticmethod
    def get_user_by_firebase_uid(firebase_uid):
        return User.query.filter_by(firebase_uid=firebase_uid).first()

    @staticmethod
    def create_user_from_google(
        firebase_uid,
        email,
        full_name,
        username,
        college_name,
        year,
        class_name,
        section,
        phone_number,
        short_bio,
        is_worker,
        skills=None,
    ):
        """Create a new user from Google Sign-In (no password)."""
        assigned_id = UserService.generate_assigned_id(username)
        user = User(
            firebase_uid=firebase_uid,
            username=username,
            email=email,
            password_hash=None,
            full_name=full_name,
            college_name=college_name,
            year=year,
            class_name=class_name,
            section=section,
            phone_number=phone_number,
            short_bio=short_bio or '',
            skills=skills or '',
            is_worker=is_worker,
            is_verified=True,
            assigned_id=assigned_id,
            profile_image='default_profile.png',
        )
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def authenticate_user(login_input, password):
        """Legacy - only for users with password (Google users have no password)."""
        user = User.query.filter(
            (User.email == login_input)
            | (User.username == login_input)
        ).first()

        if user and user.password_hash and check_password_hash(user.password_hash, password):
            return user

        return None

    @staticmethod
    def get_user_by_id(user_id):
        return User.query.get(user_id)

    @staticmethod
    def get_user_by_username(username):
        return User.query.filter_by(username=username, is_verified=True).first()

    @staticmethod
    def search_users(query):

        if not query:
            return User.query.filter_by(is_verified=True).limit(20).all()

        return User.query.filter(
            (User.username.ilike(f'%{query}%'))
            | (User.full_name.ilike(f'%{query}%'))
            | (User.college_name.ilike(f'%{query}%'))
        ).filter_by(is_verified=True).all()

    @staticmethod
    def update_user_profile(user, data):

        user.full_name = data.get('full_name', user.full_name)
        user.college_name = data.get('college_name', user.college_name)
        user.year = data.get('year', user.year)
        user.class_name = data.get('class_name', user.class_name)
        user.section = data.get('section', user.section)
        user.phone_number = data.get('phone_number', user.phone_number)
        user.short_bio = data.get('short_bio', user.short_bio)
        user.is_worker = data.get('is_worker', user.is_worker)

        if 'skills' in data:
            user.skills = data.get('skills')

        db.session.commit()

    @staticmethod
    def change_password(user, new_password):
        """Change password - only for users with password (Google users may not have one)."""
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()

    @staticmethod
    def get_user_count():
        return User.query.filter_by(is_verified=True).count()

    @staticmethod
    def get_worker_count():
        return User.query.filter_by(is_verified=True, is_worker=True).count()

    # ================= PROFILE IMAGE =================

    @staticmethod
    def save_profile_image(file, user_id):

        if not file or file.filename == '':
            return None

        allowed_extensions = {'png', 'jpg', 'jpeg'}
        ext = file.filename.rsplit('.', 1)[1].lower()

        if ext not in allowed_extensions:
            raise ValueError("Invalid file type")

        filename = f"user_{user_id}.jpg"
        folder = current_app.config['UPLOAD_FOLDER']
        filepath = os.path.join(folder, filename)

        img = Image.open(file)
        img = img.convert('RGB')
        img.thumbnail((500, 500), Image.Resampling.LANCZOS)

        img.save(filepath, format='JPEG', quality=85, optimize=True)

        return filename

    @staticmethod
    def delete_old_profile_image(user):

        if user.profile_image and user.profile_image != 'default_profile.png':

            path = os.path.join(
                current_app.config['UPLOAD_FOLDER'],
                user.profile_image
            )

            if os.path.exists(path):
                os.remove(path)
