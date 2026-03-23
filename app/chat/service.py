from flask import current_app
from app.firebase_client import firestore_get_unread_count


def get_unread_count(user_id):
    """
    Returns the number of unread messages for a given user.
    Uses Firestore.
    """
    try:
        return firestore_get_unread_count(user_id)
    except Exception as e:
        current_app.logger.warning(f"Silent unread-count failure: {e}")
        return 0
