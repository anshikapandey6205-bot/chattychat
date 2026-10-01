from flask import Blueprint, request, jsonify, session
from routes.auth import login_required
from models.user import search_users
from models.conversation import get_user_conversations
from models.message import search_messages

search_bp = Blueprint('search', __name__)

@search_bp.route('/api/search', methods=['GET'])
@login_required
def global_search():
    query = request.args.get('q', '').strip()
    conv_id = request.args.get('conversation_id')
    conv_id = int(conv_id) if conv_id and conv_id.isdigit() else None
    
    if not query:
        return jsonify({
            'success': True,
            'query': '',
            'users': [],
            'conversations': [],
            'messages': []
        })

    # Search users
    users = search_users(query, session['user_id'])
    
    # Search conversations
    all_convs = get_user_conversations(session['user_id'])
    matching_convs = []
    q_lower = query.lower()
    for c in all_convs:
        display_name = (c.get('display_name') or '').lower()
        desc = (c.get('group_description') or '').lower()
        if q_lower in display_name or q_lower in desc:
            matching_convs.append(c)

    # Search messages
    messages = search_messages(query, session['user_id'], conversation_id=conv_id)

    return jsonify({
        'success': True,
        'query': query,
        'users': users,
        'conversations': matching_convs,
        'messages': messages
    })
