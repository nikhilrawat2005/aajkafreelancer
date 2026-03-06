from app.extensions import db
from app.chat.models import Conversation, ConversationParticipant, Message
from app.models import User
from app.notifications.service import NotificationService


class ChatService:

    @staticmethod
    def get_or_create_conversation(user1_id, user2_id):

        subq = db.session.query(
            ConversationParticipant.conversation_id
        ).filter(
            ConversationParticipant.user_id.in_([user1_id, user2_id])
        ).group_by(
            ConversationParticipant.conversation_id
        ).having(
            db.func.count(ConversationParticipant.user_id) == 2
        ).subquery()

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

        participant1 = ConversationParticipant(
            conversation_id=conv.id,
            user_id=user1_id
        )

        participant2 = ConversationParticipant(
            conversation_id=conv.id,
            user_id=user2_id
        )

        db.session.add_all([participant1, participant2])
        db.session.commit()

        return conv


    @staticmethod
    def send_message(conversation_id, sender_id, message_text):

        msg = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            message_text=message_text,
            is_read=False
        )

        db.session.add(msg)
        db.session.commit()

        conv = Conversation.query.get(conversation_id)

        if conv:
            other_user_id = None

            for p in conv.participants:
                if p.user_id != sender_id:
                    other_user_id = p.user_id
                    break

            if other_user_id:
                NotificationService.create_notification(
                    user_id=other_user_id,
                    type='message',
                    reference_id=msg.id
                )

        return msg


    @staticmethod
    def get_conversation_messages(conversation_id, user_id=None):

        messages = (
            Message.query
            .filter_by(conversation_id=conversation_id)
            .order_by(Message.timestamp.desc())
            .limit(50)
            .all()
        )

        messages = list(reversed(messages))

        if user_id:

            Message.query.filter(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.is_read == False
            ).update(
                {'is_read': True},
                synchronize_session=False
            )

            db.session.commit()

        return messages


    @staticmethod
    def get_messages_since(conversation_id, since_id, user_id=None):

        messages = (
            Message.query
            .filter(
                Message.conversation_id == conversation_id,
                Message.id > since_id
            )
            .order_by(Message.timestamp)
            .all()
        )

        if user_id and messages:

            Message.query.filter(
                Message.conversation_id == conversation_id,
                Message.id > since_id,
                Message.sender_id != user_id,
                Message.is_read == False
            ).update(
                {'is_read': True},
                synchronize_session=False
            )

            db.session.commit()

        return messages


    @staticmethod
    def get_user_conversations(user_id):

        from sqlalchemy.orm import joinedload
        from sqlalchemy import func

        convs = (
            Conversation.query
            .join(ConversationParticipant)
            .filter(ConversationParticipant.user_id == user_id)
            .options(
                joinedload(Conversation.participants)
                .joinedload(ConversationParticipant.user)
            )
            .order_by(Conversation.created_at.desc())
            .all()
        )

        result = []

        for conv in convs:

            other = next(
                (p.user for p in conv.participants if p.user_id != user_id),
                None
            )

            if not other:
                continue

            last_msg = (
                db.session.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.timestamp.desc())
                .limit(1)
                .first()
            )

            unread_count = (
                db.session.query(func.count(Message.id))
                .filter(
                    Message.conversation_id == conv.id,
                    Message.sender_id != user_id,
                    Message.is_read == False
                )
                .scalar()
            )

            result.append({
                "conversation": conv,
                "other_user": other,
                "last_message": last_msg,
                "unread_count": unread_count
            })

        return result


    @staticmethod
    def get_unread_count(user_id):

        from sqlalchemy import func

        count = (
            db.session.query(func.count(Message.id))
            .join(Conversation)
            .join(ConversationParticipant)
            .filter(
                ConversationParticipant.user_id == user_id,
                Message.sender_id != user_id,
                Message.is_read == False
            )
            .scalar()
        )

        return count or 0