from flask import render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
import uuid

from app.chat import chat_bp
from app.models import User, HireRequest
from app.extensions import db
from app.supabase_client import get_supabase

@chat_bp.route('/')
@login_required
def index():
    return render_template('chat_list.html')

@chat_bp.route('/<string:conversation_id>')
@login_required
def conversation(conversation_id):
    supabase = get_supabase()
    member = supabase.table('conversation_members') \
        .select('*') \
        .eq('conversation_id', conversation_id) \
        .eq('user_id', current_user.id) \
        .execute()
    if not member.data:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('chat.index'))

    other = supabase.table('conversation_members') \
        .select('user_id') \
        .eq('conversation_id', conversation_id) \
        .neq('user_id', current_user.id) \
        .execute()
    if not other.data:
        flash('Conversation has no other participant.', 'danger')
        return redirect(url_for('chat.index'))

    other_user_id = other.data[0]['user_id']
    other_user = User.query.get(other_user_id)
    if not other_user:
        flash('Other user not found.', 'danger')
        return redirect(url_for('chat.index'))

    return render_template('chat_room.html',
                           conversation={'id': conversation_id},
                           other_user=other_user)

@chat_bp.route('/start/<int:user_id>')
@login_required
def start_conversation(user_id):
    if user_id == current_user.id:
        flash('You cannot message yourself.', 'info')
        return redirect(url_for('main.profile', username=current_user.username))

    target_user = User.query.get_or_404(user_id)
    supabase = get_supabase()

    # Find existing conversation
    user_convs = supabase.table('conversation_members') \
        .select('conversation_id') \
        .eq('user_id', current_user.id) \
        .execute()
    conv_ids = [c['conversation_id'] for c in user_convs.data]
    if conv_ids:
        existing = supabase.table('conversation_members') \
            .select('conversation_id') \
            .in_('conversation_id', conv_ids) \
            .eq('user_id', target_user.id) \
            .execute()
        if existing.data:
            return redirect(url_for('chat.conversation', conversation_id=existing.data[0]['conversation_id']))

    # Create new conversation
    new_id = str(uuid.uuid4())
    supabase.table('conversations').insert({
        'id': new_id,
        'created_at': datetime.utcnow().isoformat(),
        'last_message': None,
        'last_message_time': None
    }).execute()
    supabase.table('conversation_members').insert([
        {'conversation_id': new_id, 'user_id': current_user.id},
        {'conversation_id': new_id, 'user_id': target_user.id}
    ]).execute()
    return redirect(url_for('chat.conversation', conversation_id=new_id))

@chat_bp.route('/hire/request/<string:conversation_id>', methods=['POST'])
@login_required
def hire_request(conversation_id):
    supabase = get_supabase()
    member = supabase.table('conversation_members') \
        .select('*') \
        .eq('conversation_id', conversation_id) \
        .eq('user_id', current_user.id) \
        .execute()
    if not member.data:
        return jsonify({'error': 'Unauthorized'}), 403

    other = supabase.table('conversation_members') \
        .select('user_id') \
        .eq('conversation_id', conversation_id) \
        .neq('user_id', current_user.id) \
        .execute()
    if not other.data:
        return jsonify({'error': 'No other participant'}), 400
    other_user_id = other.data[0]['user_id']
    other_user = User.query.get(other_user_id)
    if not other_user or not other_user.is_worker:
        return jsonify({'error': 'User is not a worker'}), 400

    existing = HireRequest.query.filter_by(conversation_id=conversation_id, status='pending', active=True).first()
    if existing:
        return jsonify({'error': 'Pending request already exists'}), 400

    hire = HireRequest(
        sender_id=current_user.id,
        worker_id=other_user.id,
        conversation_id=conversation_id,
        status='pending',
        active=True
    )
    db.session.add(hire)
    db.session.commit()
    return jsonify({'success': True, 'request_id': hire.id, 'status': hire.status})

@chat_bp.route('/hire/status/<string:conversation_id>')
@login_required
def hire_status(conversation_id):
    supabase = get_supabase()
    member = supabase.table('conversation_members') \
        .select('*') \
        .eq('conversation_id', conversation_id) \
        .eq('user_id', current_user.id) \
        .execute()
    if not member.data:
        return jsonify({'error': 'Unauthorized'}), 403

    hire = HireRequest.query.filter_by(conversation_id=conversation_id, active=True).order_by(HireRequest.created_at.desc()).first()
    if not hire:
        hire = HireRequest.query.filter_by(conversation_id=conversation_id, record_created=True).order_by(HireRequest.created_at.desc()).first()
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

@chat_bp.route('/hire/accept/<int:request_id>', methods=['POST'])
@login_required
def accept_hire(request_id):
    hire = HireRequest.query.get_or_404(request_id)
    if hire.worker_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if hire.status != 'pending':
        return jsonify({'error': 'Request not pending'}), 400
    hire.status = 'accepted'
    hire.responded_at = datetime.utcnow()
    hire.active = True
    db.session.commit()
    return jsonify({'success': True})

@chat_bp.route('/hire/reject/<int:request_id>', methods=['POST'])
@login_required
def reject_hire(request_id):
    hire = HireRequest.query.get_or_404(request_id)
    if hire.worker_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if hire.status != 'pending':
        return jsonify({'error': 'Request not pending'}), 400
    hire.status = 'rejected'
    hire.responded_at = datetime.utcnow()
    hire.active = False
    db.session.commit()
    return jsonify({'success': True})

@chat_bp.route('/hire/record/<int:request_id>', methods=['POST'])
@login_required
def record_hire(request_id):
    hire = HireRequest.query.get_or_404(request_id)
    if hire.sender_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if hire.status != 'accepted':
        return jsonify({'error': 'Request not accepted'}), 400
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400
    hire.work_title = data.get('title', '').strip()
    hire.work_description = data.get('description', '').strip()
    if data.get('start_date'):
        hire.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    if data.get('end_date'):
        hire.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    hire.record_created = True
    hire.active = False
    db.session.commit()
    return jsonify({'success': True})