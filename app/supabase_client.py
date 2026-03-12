import logging
from flask import current_app, g
from supabase import create_client, Client

logger = logging.getLogger(__name__)

def get_supabase() -> Client:
    """
    Returns a Supabase client instance, cached per request.
    Raises RuntimeError if credentials are missing.
    """
    if 'supabase_client' not in g:
        url = current_app.config.get('SUPABASE_URL')
        key = current_app.config.get('SUPABASE_ANON_KEY')
        if not url or not key:
            raise RuntimeError(
                "Supabase credentials not set. "
                "Please configure SUPABASE_URL and SUPABASE_ANON_KEY."
            )
        g.supabase_client = create_client(url, key)
    return g.supabase_client

def sync_user_to_supabase(user):
    """
    Upserts a user's chat profile into Supabase.
    This should be called whenever a user is created or updated.
    """
    try:
        supabase = get_supabase()
        data = {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "profile_image": user.profile_image
        }
        supabase.table("users").upsert(data, on_conflict="id").execute()
    except Exception as e:
        logger.error(f"Failed to sync user {user.id} to Supabase: {e}")
        