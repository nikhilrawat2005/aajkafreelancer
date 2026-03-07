# app/chat/routes.py – Improved version (Supabase chat compatible)

from flask import render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import func

from app.chat import chat_bp
from app.models import User, HireRequest
from app.chat.models import Conversation, ConversationParticipant
from app.extensions import db


# =========================================================
# Chat list – messages loaded from Supabase on frontend
# =========================================================

@chat_bp.route('/')
@login_required
def index():
    return render_template('chat_list.html')


# =========================================================
# Conversation room
# =========================================================

@chat_bp.route('/<int:conversation_id>')
@login_required
def conversation(conversation_id):

    participant = ConversationParticipant.query.filter_by(
        conversation_id=conversation_id,
        user_id=current_user.id
    ).first()

    if not participant:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('chat.index'))

    conv = participant.conversation

    other_user = None
    for p in conv.participants:
        if p.user_id != current_user.id:
            other_user = p.user
            break

    return render_template(
        'chat_room.html',
        conversation=conv,
        other_user=other_user
    )


# =========================================================
# Create or find conversation
# =========================================================

def get_or_create_conversation(user1_id, user2_id):

    subq = (
        db.session.query(
            ConversationParticipant.conversation_id
        )
        .filter(
            ConversationParticipant.user_id.in_([user1_id, user2_id])
        )
        .group_by(
            ConversationParticipant.conversation_id
        )
        .having(
            func.count(ConversationParticipant.user_id) == 2
        )
        .subquery()
    )

    conv = (
        db.session.query(Conversation)
        .join(
            ConversationParticipant,
            Conversation.id == ConversationParticipant.conversation_id
        )
        .filter(
            ConversationParticipant.conversation_id.in_(subq)
        )
        .first()
    )

    if conv:
        return conv

    conv = Conversation()
    db.session.add(conv)
    db.session.flush()

    db.session.add_all([
        ConversationParticipant(
            conversation_id=conv.id,
            user_id=user1_id
        ),
        ConversationParticipant(
            conversation_id=conv.id,
            user_id=user2_id
        )
    ])

    db.session.commit()

    return conv


# =========================================================
# Start conversation
# =========================================================

@chat_bp.route('/start/<int:user_id>')
@login_required
def start_conversation(user_id):

    if user_id == current_user.id:
        flash('You cannot message yourself.', 'info')
        return redirect(url_for('main.profile', username=current_user.username))

    target_user = User.query.get_or_404(user_id)

    conv = get_or_create_conversation(
        current_user.id,
        target_user.id
    )

    return redirect(
        url_for('chat.conversation', conversation_id=conv.id)
    )


# =========================================================
# HIRE REQUEST SYSTEM
# =========================================================

@chat_bp.route('/hire/request/<int:conversation_id>', methods=['POST'])
@login_required
def hire_request(conversation_id):

    participant = ConversationParticipant.query.filter_by(
        conversation_id=conversation_id,
        user_id=current_user.id
    ).first()

    if not participant:
        return jsonify({'error': 'Unauthorized'}), 403

    conv = participant.conversation

    other_user = None
    for p in conv.participants:
        if p.user_id != current_user.id:
            other_user = p.user
            break

    if not other_user:
        return jsonify({'error': 'Conversation has no other participant'}), 400

    if not other_user.is_worker:
        return jsonify({'error': 'This user is not a worker'}), 400

    if other_user.id == current_user.id:
        return jsonify({'error': 'You cannot hire yourself'}), 400

    existing = HireRequest.query.filter_by(
        conversation_id=conversation_id,
        status='pending',
        active=True
    ).first()

    if existing:
        return jsonify({'error': 'A pending hire request already exists'}), 400

    hire = HireRequest(
        sender_id=current_user.id,
        worker_id=other_user.id,
        conversation_id=conversation_id,
        status='pending',
        active=True
    )

    db.session.add(hire)
    db.session.commit()

    return jsonify({
        'success': True,
        'request_id': hire.id,
        'status': hire.status
    })


# =========================================================
# Hire request status
# =========================================================

@chat_bp.route('/hire/status/<int:conversation_id>')
@login_required
def hire_status(conversation_id):

    participant = ConversationParticipant.query.filter_by(
        conversation_id=conversation_id,
        user_id=current_user.id
    ).first()

    if not participant:
        return jsonify({'error': 'Unauthorized'}), 403

    hire = HireRequest.query.filter_by(
        conversation_id=conversation_id,
        active=True
    ).order_by(HireRequest.created_at.desc()).first()

    if not hire:
        hire = HireRequest.query.filter_by(
            conversation_id=conversation_id,
            record_created=True
        ).order_by(HireRequest.created_at.desc()).first()

    if not hire:
        return jsonify({'status': None})

    return jsonify({
        'status': hire.status if hire.active else None,
        'request_id': hire.id,
        'work_title': hire.work_title,
        'work_description': hire.work_description,
        'start_date': hire.start_date.isoformat() if hire.start_date else None,
        'end_date': hire.end_date.isoformat() if hire.end_date else None,
        'record_created': hire.record_created,
        'is_requester': hire.sender_id == current_user.id,
        'active': hire.active
    })


# =========================================================
# Accept hire request
# =========================================================

@chat_bp.route('/hire/accept/<int:request_id>', methods=['POST'])
@login_required
def accept_hire(request_id):

    hire = HireRequest.query.get_or_404(request_id)

    if hire.worker_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if hire.status != 'pending':
        return jsonify({'error': 'Request is not pending'}), 400

    hire.status = 'accepted'
    hire.responded_at = datetime.utcnow()
    hire.active = True

    db.session.commit()

    return jsonify({'success': True, 'status': hire.status})


# =========================================================
# Reject hire request
# =========================================================

@chat_bp.route('/hire/reject/<int:request_id>', methods=['POST'])
@login_required
def reject_hire(request_id):

    hire = HireRequest.query.get_or_404(request_id)

    if hire.worker_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if hire.status != 'pending':
        return jsonify({'error': 'Request is not pending'}), 400

    hire.status = 'rejected'
    hire.responded_at = datetime.utcnow()
    hire.active = False

    db.session.commit()

    return jsonify({'success': True})


# =========================================================
# Save work record
# =========================================================

@chat_bp.route('/hire/record/<int:request_id>', methods=['POST'])
@login_required
def record_hire(request_id):

    hire = HireRequest.query.get_or_404(request_id)

    if hire.sender_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if hire.status != 'accepted':
        return jsonify({'error': 'Request is not accepted'}), 400

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    hire.work_title = data.get('title', '').strip()
    hire.work_description = data.get('description', '').strip()

    hire.start_date = datetime.strptime(
        data.get('start_date'), '%Y-%m-%d'
    ).date() if data.get('start_date') else None

    hire.end_date = datetime.strptime(
        data.get('end_date'), '%Y-%m-%d'
    ).date() if data.get('end_date') else None

    hire.record_created = True
    hire.active = False

    db.session.commit()

    return jsonify({'success': True})