"""
Firebase client for Auth verification and Firestore (chat, users).
Replaces Supabase. Use Firebase Admin SDK for backend operations.
"""
import json
import logging
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth as firebase_auth

logger = logging.getLogger(__name__)
_firebase_initialized = False
_firestore_client = None  # ✅ FIX: module-level client, not g-based (g fails outside request context on Vercel)


def _get_credentials():
    """Load Firebase credentials from env JSON, file path, or GOOGLE_APPLICATION_CREDENTIALS."""
    cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if cred_json:
        try:
            data = json.loads(cred_json)
            return credentials.Certificate(data)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid FIREBASE_CREDENTIALS_JSON: {e}")

    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if cred_path and os.path.isfile(cred_path):
        return credentials.Certificate(cred_path)

    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return credentials.ApplicationDefault()

    raise RuntimeError(
        "Firebase credentials not configured. Set FIREBASE_CREDENTIALS_PATH, "
        "FIREBASE_CREDENTIALS_JSON, or GOOGLE_APPLICATION_CREDENTIALS."
    )


def get_firebase_app():
    """Get or create Firebase app (singleton). Safe to call multiple times."""
    global _firebase_initialized
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    try:
        cred = _get_credentials()
        app = firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        return app
    except Exception as e:
        logger.error(f"Critical Firebase initialization failure: {e}")
        raise

def get_firestore():
    """Returns Firestore client (module-level singleton)."""
    global _firestore_client
    if _firestore_client is None:
        try:
            get_firebase_app()
            _firestore_client = firestore.client()
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            raise
    return _firestore_client


def create_custom_token(uid: str):
    """Create a Firebase custom token for the given UID (for client-side Firestore access)."""
    get_firebase_app()
    token = firebase_auth.create_custom_token(uid)
    return token.decode('utf-8') if isinstance(token, bytes) else token


def verify_firebase_token(id_token: str):
    """
    Verify Firebase ID token from Google Sign-In.
    Returns decoded token dict or None.
    """
    try:
        get_firebase_app()
        decoded = firebase_auth.verify_id_token(id_token)
        return decoded
    except Exception as e:
        logger.warning(f"Firebase token verification failed: {e}")
        return None


def sync_user_to_firebase(user):
    """
    Upserts a user's chat profile into Firestore.
    Called when user is created or profile is updated.
    """
    try:
        db = get_firestore()
        doc_ref = db.collection("users").document(str(user.id))
        doc_ref.set({
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "profile_image": user.profile_image or "default_profile.png",
        }, merge=True)
    except Exception as e:
        logger.error(f"Failed to sync user {user.id} to Firebase: {e}")


# =========================================================
# FIRESTORE HELPERS
# =========================================================

def _conversation_members():
    return get_firestore().collection("conversation_members")


def _conversations():
    return get_firestore().collection("conversations")


def _messages(conversation_id):
    return get_firestore().collection("conversations").document(conversation_id).collection("messages")


def firestore_get_conversation_members(conversation_id=None, user_id=None):
    """Get conversation_members matching filters."""
    query = _conversation_members()
    if conversation_id:
        query = query.where("conversation_id", "==", conversation_id)
    if user_id is not None:
        query = query.where("user_id", "==", user_id)
    docs = query.stream()
    return [{"conversation_id": d.get("conversation_id"), "user_id": d.get("user_id"), "id": d.id} for d in docs]


def firestore_add_conversation_member(conversation_id, user_id):
    _conversation_members().add({"conversation_id": conversation_id, "user_id": user_id})


def firestore_create_conversation(conv_id, last_message=None, last_message_time=None):
    _conversations().document(conv_id).set({
        "last_message": last_message,
        "last_message_time": last_message_time,
    }, merge=True)


def firestore_update_conversation(conv_id, last_message, last_message_time):
    _conversations().document(conv_id).update({
        "last_message": last_message,
        "last_message_time": last_message_time,
    })


def firestore_get_messages(conversation_id, limit=30, order_desc=True):
    """Get last N messages for a conversation."""
    query = _messages(conversation_id).order_by(
        "created_at",
        direction=firestore.Query.DESCENDING if order_desc else firestore.Query.ASCENDING
    ).limit(limit)
    docs = list(query.stream())
    if order_desc:
        docs.reverse()
    return [{"id": d.id, **d.to_dict()} for d in docs]


def firestore_add_message(conversation_id, sender_id, content, message_type="text", seen=False):
    from datetime import datetime
    data = {
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "content": content,
        "message_type": message_type,
        "seen": seen,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    ref, _ = _messages(conversation_id).add(data)
    return ref.id


def firestore_update_messages_seen(conversation_id, exclude_sender_id, set_seen=True):
    """Mark messages as seen (exclude sender)."""
    for doc in _messages(conversation_id).where("sender_id", "!=", exclude_sender_id).where("seen", "==", False).stream():
        doc.reference.update({"seen": set_seen})


def firestore_update_single_message_seen(message_id, conversation_id):
    doc_ref = _messages(conversation_id).document(message_id)
    doc = doc_ref.get()
    if doc.exists:
        doc_ref.update({"seen": True})


def firestore_get_unread_count(user_id):
    """Count unread messages for user across all their conversations."""
    conv_ids = [m["conversation_id"] for m in firestore_get_conversation_members(user_id=user_id)]
    if not conv_ids:
        return 0
    total = 0
    for cid in conv_ids:
        unread = _messages(cid).where("seen", "==", False).where("sender_id", "!=", user_id).limit(500).stream()
        total += sum(1 for _ in unread)
    return total


def firestore_get_conversation_list(user_id):
    """
    Get list of conversations for user with last_message, other_user, unread_count.
    Returns list of dicts.
    """
    memberships = firestore_get_conversation_members(user_id=user_id)
    if not memberships:
        return []

    conv_ids = list({m["conversation_id"] for m in memberships})
    results = []
    users_coll = get_firestore().collection("users")

    for conv_id in conv_ids:
        conv_doc = _conversations().document(conv_id).get()
        conv_data = conv_doc.to_dict() or {}
        conv_data["id"] = conv_id

        # Get other member
        members = firestore_get_conversation_members(conversation_id=conv_id)
        other = next((m for m in members if m["user_id"] != user_id), None)
        other_user = None
        if other:
            user_doc = users_coll.document(str(other["user_id"])).get()
            other_user = user_doc.to_dict() if user_doc.exists else None

        # Unread count
        unread = sum(1 for d in _messages(conv_id).where("seen", "==", False).where("sender_id", "!=", user_id).stream())

        results.append({
            "id": conv_id,
            "last_message": conv_data.get("last_message"),
            "last_message_time": conv_data.get("last_message_time"),
            "other_user": other_user,
            "unread_count": unread,
        })

    # Sort by last_message_time desc
    results.sort(key=lambda x: x["last_message_time"] or "", reverse=True)
    return results
