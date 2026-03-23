from datetime import datetime
from flask_login import UserMixin
from app.extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=True)  # Nullable for Google-only users
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True)  # Firebase Auth UID

    full_name = db.Column(db.String(100), nullable=False)
    college_name = db.Column(db.String(100), nullable=False)

    year = db.Column(db.String(20), nullable=False)
    class_name = db.Column(db.String(20), nullable=False)
    section = db.Column(db.String(10), nullable=False)

    phone_number = db.Column(db.String(20), nullable=False)

    short_bio = db.Column(db.Text)
    skills = db.Column(db.Text)

    is_worker = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assigned_id = db.Column(db.String(50), unique=True)

    # profile image
    profile_image = db.Column(db.String(255), nullable=False, default='default_profile.png')
    profile_crop_x = db.Column(db.Float, nullable=True)
    profile_crop_y = db.Column(db.Float, nullable=True)
    profile_crop_scale = db.Column(db.Float, nullable=True)

    # admin flag
    is_admin = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.Index('idx_user_username', 'username'),
        db.Index('idx_user_email', 'email'),
        db.Index('idx_user_firebase_uid', 'firebase_uid'),
        db.Index('idx_user_full_name', 'full_name'),
        db.Index('idx_user_college_name', 'college_name'),
    )


class HireRequest(db.Model):

    __tablename__ = 'hire_requests'

    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    worker_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    conversation_id = db.Column(db.String(36), nullable=False)

    status = db.Column(db.String(20), default='pending')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    responded_at = db.Column(db.DateTime, nullable=True)

    work_title = db.Column(db.String(200), nullable=True)

    work_description = db.Column(db.Text, nullable=True)

    active = db.Column(db.Boolean, default=True)

    start_date = db.Column(db.Date, nullable=True)

    end_date = db.Column(db.Date, nullable=True)

    record_created = db.Column(db.Boolean, default=False)

    # relationships (NO backrefs here)
    sender = db.relationship('User', foreign_keys=[sender_id])
    worker = db.relationship('User', foreign_keys=[worker_id])

    __table_args__ = (
        db.Index('idx_hire_sender', 'sender_id'),
        db.Index('idx_hire_worker', 'worker_id'),
        db.Index('idx_hire_conversation', 'conversation_id'),
        db.Index('idx_hire_status', 'status'),
    )

    @staticmethod
    def pending_count_for_worker(worker_id):
        return HireRequest.query.filter_by(
            worker_id=worker_id,
            status='pending',
            active=True
        ).count()