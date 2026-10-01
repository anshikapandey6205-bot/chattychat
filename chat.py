import os
import uuid
from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify, current_app
from werkzeug.utils import secure_filename
from routes.auth import login_required
from models.user import get_user_by_id, get_all_users_except
from models.conversation import (
    get_user_conversations, get_or_create_direct_conversation, create_group_conversation,
    get_conversation_by_id, toggle_pin_conversation, toggle_mute_conversation,
    delete_conversation_for_user, mark_conversation_as_read
)
from models.message import (
    create_message, get_conversation_messages, get_message_by_id,
    edit_message, delete_message, toggle_reaction, get_shared_media, get_unread_count_for_user
)

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/')
def index():
    """Landing page with live preview showcase."""
    current_user = None
    if 'user_id' in session:
        current_user = get_user_by_id(session['user_id'])
    return render_template('index.html', current_user=current_user)

@chat_bp.route('/chat')
@chat_bp.route('/chat/<int:active_conv_id>')
@login_required
def dashboard(active_conv_id=None):
    """Main modern 3-column chat dashboard."""
    current_user = get_user_by_id(session['user_id'])
    if not current_user:
        session.clear()
        return redirect(url_for('auth.login'))
        
    conversations = get_user_conversations(current_user['id'])
    total_unread = get_unread_count_for_user(current_user['id'])
    
    return render_template(
        'chat.html',
        current_user=current_user,
        conversations=conversations,
        active_conv_id=active_conv_id,
        total_unread=total_unread
    )

@chat_bp.route('/api/conversations', methods=['GET'])
@login_required
def list_conversations():
    """List all conversations for the user with latest preview."""
    conversations = get_user_conversations(session['user_id'])
    return jsonify({'success': True, 'conversations': conversations})

@chat_bp.route('/api/conversations/direct', methods=['POST'])
@login_required
def start_direct_chat():
    """Start or open a direct 1-to-1 conversation with a target user."""
    data = request.get_json() or {}
    target_user_id = data.get('user_id')
    
    if not target_user_id:
        return jsonify({'success': False, 'error': 'Target user ID is required.'}), 400
        
    target_user = get_user_by_id(target_user_id)
    if not target_user:
        return jsonify({'success': False, 'error': 'Target user does not exist.'}), 404
        
    conv_id = get_or_create_direct_conversation(session['user_id'], int(target_user_id))
    conv_details = get_conversation_by_id(conv_id, session['user_id'])
    
    return jsonify({'success': True, 'conversation_id': conv_id, 'conversation': conv_details})

@chat_bp.route('/api/conversations/group', methods=['POST'])
@login_required
def create_group_chat():
    """Create a new group chat with specified name and members."""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    members = data.get('members', [])
    description = data.get('description', '').strip()
    avatar = data.get('avatar', '/static/images/avatars/group.svg')
    
    if not name:
        return jsonify({'success': False, 'error': 'Group name is required.'}), 400
        
    if not members or len(members) < 1:
        return jsonify({'success': False, 'error': 'At least one group member must be selected.'}), 400
        
    conv_id = create_group_conversation(
        created_by=session['user_id'],
        name=name,
        member_ids=members,
        description=description,
        avatar=avatar
    )
    conv_details = get_conversation_by_id(conv_id, session['user_id'])
    
    # Also add a system welcome message
    create_message(
        conversation_id=conv_id,
        sender_id=session['user_id'],
        message=f"{session.get('name', 'Admin')} created the group \"{name}\"",
        message_type='system'
    )
    
    return jsonify({'success': True, 'conversation_id': conv_id, 'conversation': conv_details})

@chat_bp.route('/api/conversations/<int:conversation_id>', methods=['GET'])
@login_required
def get_conversation(conversation_id):
    """Get metadata and members for a conversation."""
    conv = get_conversation_by_id(conversation_id, session['user_id'])
    if not conv:
        return jsonify({'success': False, 'error': 'Conversation not found or access denied.'}), 404
    return jsonify({'success': True, 'conversation': conv})

@chat_bp.route('/api/conversations/<int:conversation_id>/messages', methods=['GET'])
@login_required
def get_messages(conversation_id):
    """Get conversation message history."""
    conv = get_conversation_by_id(conversation_id, session['user_id'])
    if not conv:
        return jsonify({'success': False, 'error': 'Conversation not found.'}), 404
        
    limit = min(int(request.args.get('limit', 50)), 100)
    before_id = request.args.get('before_id')
    before_id = int(before_id) if before_id and before_id.isdigit() else None
    
    messages = get_conversation_messages(conversation_id, session['user_id'], limit=limit, before_id=before_id)
    
    # Mark messages as read when fetched
    mark_conversation_as_read(conversation_id, session['user_id'])
    
    return jsonify({'success': True, 'messages': messages})

@chat_bp.route('/api/conversations/<int:conversation_id>/messages', methods=['POST'])
@login_required
def send_message_rest(conversation_id):
    """Send message via REST API."""
    conv = get_conversation_by_id(conversation_id, session['user_id'])
    if not conv:
        return jsonify({'success': False, 'error': 'Conversation not found.'}), 404
        
    data = request.get_json() or {}
    content = data.get('message', '').strip()
    msg_type = data.get('message_type', 'text')
    reply_to = data.get('reply_to')
    attachments = data.get('attachments', [])
    
    if not content and not attachments:
        return jsonify({'success': False, 'error': 'Message cannot be empty.'}), 400
        
    msg = create_message(
        conversation_id=conversation_id,
        sender_id=session['user_id'],
        message=content,
        message_type=msg_type,
        reply_to=reply_to,
        attachments=attachments
    )
    
    return jsonify({'success': True, 'message': msg})

@chat_bp.route('/api/conversations/<int:conversation_id>/pin', methods=['POST'])
@login_required
def toggle_pin(conversation_id):
    """Toggle pin state of a conversation."""
    is_pinned = toggle_pin_conversation(conversation_id, session['user_id'])
    return jsonify({'success': True, 'is_pinned': is_pinned})

@chat_bp.route('/api/conversations/<int:conversation_id>/mute', methods=['POST'])
@login_required
def toggle_mute(conversation_id):
    """Toggle mute state of a conversation."""
    is_muted = toggle_mute_conversation(conversation_id, session['user_id'])
    return jsonify({'success': True, 'is_muted': is_muted})

@chat_bp.route('/api/conversations/<int:conversation_id>/read', methods=['POST'])
@login_required
def mark_read(conversation_id):
    """Mark conversation as read."""
    last_id = mark_conversation_as_read(conversation_id, session['user_id'])
    return jsonify({'success': True, 'last_read_id': last_id})

@chat_bp.route('/api/conversations/<int:conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    """Delete conversation or leave group."""
    deleted = delete_conversation_for_user(conversation_id, session['user_id'])
    return jsonify({'success': True, 'deleted': deleted})

@chat_bp.route('/api/conversations/<int:conversation_id>/media', methods=['GET'])
@login_required
def get_media(conversation_id):
    """Get shared images and documents for right sidebar."""
    media = get_shared_media(conversation_id)
    return jsonify({'success': True, 'media': media})

@chat_bp.route('/api/messages/<int:message_id>/react', methods=['POST'])
@login_required
def react_message(message_id):
    """Toggle emoji reaction on a message."""
    data = request.get_json() or {}
    emoji = data.get('reaction', '').strip()
    if not emoji:
        return jsonify({'success': False, 'error': 'Emoji reaction is required.'}), 400
        
    result = toggle_reaction(message_id, session['user_id'], emoji)
    return jsonify({'success': True, 'data': result})

@chat_bp.route('/api/messages/<int:message_id>', methods=['PUT', 'PATCH'])
@login_required
def update_message(message_id):
    """Edit message content."""
    data = request.get_json() or {}
    new_text = data.get('message', '').strip()
    if not new_text:
        return jsonify({'success': False, 'error': 'Message content cannot be empty.'}), 400
        
    msg = edit_message(message_id, session['user_id'], new_text)
    if not msg:
        return jsonify({'success': False, 'error': 'Unable to edit message. You may only edit your own active messages.'}), 403
        
    return jsonify({'success': True, 'message': msg})

@chat_bp.route('/api/messages/<int:message_id>', methods=['DELETE'])
@login_required
def remove_message(message_id):
    """Soft delete message."""
    msg = delete_message(message_id, session['user_id'])
    if not msg:
        return jsonify({'success': False, 'error': 'Unable to delete message.'}), 403
    return jsonify({'success': True, 'message': msg})

@chat_bp.route('/api/upload', methods=['POST'])
@login_required
def upload_file():
    """Securely upload an image or document attachment."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file was provided.'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected.'}), 400
        
    original_filename = secure_filename(file.filename)
    if '.' not in original_filename:
        return jsonify({'success': False, 'error': 'Invalid file format.'}), 400
        
    ext = original_filename.rsplit('.', 1)[1].lower()
    if ext not in current_app.config['ALLOWED_EXTENSIONS']:
        return jsonify({'success': False, 'error': f'File type .{ext} is not supported.'}), 400
        
    # Generate unique stored filename
    unique_name = f"{uuid.uuid4().hex}_{original_filename}"
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    
    file_path_on_disk = os.path.join(upload_folder, unique_name)
    file.save(file_path_on_disk)
    
    file_size = os.path.getsize(file_path_on_disk)
    file_type = file.content_type or ('image/' + ext if ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS'] else 'application/octet-stream')
    
    return jsonify({
        'success': True,
        'attachment': {
            'filename': unique_name,
            'original_name': original_filename,
            'filepath': f'/static/uploads/{unique_name}',
            'file_type': file_type,
            'file_size': file_size
        }
    })

@chat_bp.route('/api/users/available', methods=['GET'])
@login_required
def get_available_users():
    """Get all users except current user for starting new chat or creating group."""
    users = get_all_users_except(session['user_id'])
    return jsonify({'success': True, 'users': users})

@chat_bp.route('/api/users/online', methods=['GET'])
def get_online_users_preview():
    """Get active/online users for landing preview."""
    curr_id = session.get('user_id', 0)
    users = get_all_users_except(curr_id)
    return jsonify({'success': True, 'users': users[:6]})
