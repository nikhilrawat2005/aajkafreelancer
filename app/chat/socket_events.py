from flask_socketio import emit, join_room
from flask_login import current_user
from app.extensions import socketio
from app.chat.service import ChatService


@socketio.on("join")
def on_join(data):
    room = f"chat_{data['conversation_id']}"
    join_room(room)


@socketio.on("send_message")
def handle_message(data):

    msg = ChatService.send_message(
        data["conversation_id"],
        current_user.id,
        data["message"]
    )

    emit(
        "new_message",
        {
            "id": msg.id,
            "text": msg.message_text,
            "sender": msg.sender_id,
            "timestamp": msg.timestamp.strftime("%H:%M")
        },
        room=f"chat_{data['conversation_id']}"
    )


@socketio.on("typing")
def typing(data):

    emit(
        "typing",
        {"user": current_user.id},
        room=f"chat_{data['conversation_id']}",
        include_self=False
    )