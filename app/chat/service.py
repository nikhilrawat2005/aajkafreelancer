from app.supabase_client import get_supabase

def get_unread_count(user_id):
    supabase = get_supabase()
    convs = supabase.table('conversation_members') \
        .select('conversation_id') \
        .eq('user_id', user_id) \
        .execute()
    conv_ids = [c['conversation_id'] for c in convs.data]
    if not conv_ids:
        return 0
    result = supabase.table('messages') \
        .select('*', count='exact', head=True) \
        .in_('conversation_id', conv_ids) \
        .neq('sender_id', user_id) \
        .eq('seen', False) \
        .execute()
    return result.count