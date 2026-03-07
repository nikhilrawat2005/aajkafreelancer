# app/chat/routes.py – Minimal version (only template rendering & conversation creation)

from flask import render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime

from app.chat import chat_bp
from app.models import User, HireRequest
from app.chat.models import Conversation, ConversationParticipant
from app.extensions import db


# ===============================
# Chat list – no local data needed, frontend loads from Supabase
# ===============================
@chat_bp.route('/')
@login_required
def index():
    return render_template('chat_list.html')


# ===============================
# Conversation room – verify participant, pass conversation & other user
# ===============================
@chat_bp.route('/<int:conversation_id>')
@login_required
def conversation(conversation_id):
    # Check that current user is a participant
    participant = ConversationParticipant.query.filter_by(
        conversation_id=conversation_id,
        user_id=current_user.id
    ).first()
    if not participant:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('chat.index'))

    conv = participant.conversation

    # Find the other participant (for display name, profile link)
    other_user = None
    for p in conv.participants:
        if p.user_id != current_user.id:
            other_user = p.user
            break

    # Render the room – messages will be loaded by Supabase in the browser
    return render_template(
        'chat_room.html',
        conversation=conv,
        other_user=other_user
    )


# ===============================
# Start a conversation (or get existing one)
# ===============================
@chat_bp.route('/start/<int:user_id>')
@login_required
def start_conversation(user_id):
    if user_id == current_user.id:
        flash('You cannot message yourself.', 'info')
        return redirect(url_for('main.profile', username=current_user.username))

    # Ensure target user exists
    User.query.get_or_404(user_id)

    # Look for an existing conversation between these two users
    subq = db.session.query(
        ConversationParticipant.conversation_id
    ).filter(
        ConversationParticipant.user_id.in_([current_user.id, user_id])
    ).group_by(
        ConversationParticipant.conversation_id
    ).having(db.func.count(ConversationParticipant.user_id) == 2).subquery()

    conv = db.session.query(Conversation).join(
        ConversationParticipant,
        Conversation.id == ConversationParticipant.conversation_id
    ).filter(
        ConversationParticipant.conversation_id.in_(subq)
    ).first()

    if not conv:
        # Create new conversation
        conv = Conversation()
        db.session.add(conv)
        db.session.flush()  # to get conv.id

        participant1 = ConversationParticipant(
            conversation_id=conv.id,
            user_id=current_user.id
        )
        participant2 = ConversationParticipant(
            conversation_id=conv.id,
            user_id=user_id
        )
        db.session.add_all([participant1, participant2])
        db.session.commit()

    return redirect(url_for('chat.conversation', conversation_id=conv.id))


# ===============================
# HIRE REQUEST ENDPOINTS (unchanged, kept for functionality)
# ===============================

@chat_bp.route('/hire/request/<int:conversation_id>', methods=['POST'])
@login_required
def hire_request(conversation_id):
    """Send a hire request to the worker in this conversation."""
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

    # Check for existing pending request in this conversation
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


@chat_bp.route('/hire/status/<int:conversation_id>')
@login_required
def hire_status(conversation_id):
    """Get the current hire request status for this conversation."""
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

    is_requester = (hire.sender_id == current_user.id)

    return jsonify({
        'status': hire.status if hire.active else None,
        'request_id': hire.id,
        'work_title': hire.work_title,
        'work_description': hire.work_description,
        'start_date': hire.start_date.isoformat() if hire.start_date else None,
        'end_date': hire.end_date.isoformat() if hire.end_date else None,
        'record_created': hire.record_created,
        'is_requester': is_requester,
        'active': hire.active
    })


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


@chat_bp.route('/hire/record/<int:request_id>', methods=['POST'])
@login_required
def record_hire(request_id):
    """Save work record (title, dates) after acceptance. Only requester can do this."""
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
    hire.start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date() if data.get('start_date') else None
    hire.end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date() if data.get('end_date') else None
    hire.record_created = True
    hire.active = False
    db.session.commit()

    return jsonify({'success': True})