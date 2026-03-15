from flask import current_app
from app.supabase_client import get_supabase


def get_unread_count(user_id):
    """
    Returns the number of unread messages for a given local user ID.
    Designed to be defensive against Supabase type mismatches so it
    never crashes the request context.
    """
    try:
        supabase = get_supabase()

        convs = supabase.table("conversation_members") \
            .select("conversation_id") \
            .eq("user_id", user_id) \
            .execute()

        conv_ids = [c["conversation_id"] for c in (convs.data or [])]
        if not conv_ids:
            return 0

        result = supabase.table("messages") \
            .select("*", count="exact", head=True) \
            .in_("conversation_id", conv_ids) \
            .eq("seen", False) \
            .execute()

        return result.count or 0

    except Exception as e:
        # Fail-safe: never break page rendering because of unread count
        current_app.logger.warning(f"Silent unread-count failure: {e}")
        return 0