import sqlite3
from database.db import get_db, dict_from_row, dicts_from_rows

def get_or_create_direct_conversation(user1_id, user2_id):
    """Retrieve existing 1-on-1 conversation or create a new one."""
    db = get_db()
    
    # Check if a 1-on-1 conversation already exists between these two users
    query = """
    SELECT c.id
    FROM conversations c
    JOIN conversation_members cm1 ON c.id = cm1.conversation_id AND cm1.user_id = ?
    JOIN conversation_members cm2 ON c.id = cm2.conversation_id AND cm2.user_id = ?
    WHERE c.is_group = 0
    LIMIT 1
    """
    row = db.execute(query, (user1_id, user2_id)).fetchone()
    
    if row:
        return row['id']
    
    # Create new direct conversation
    cursor = db.execute("INSERT INTO conversations (is_group, created_by) VALUES (0, ?)", (user1_id,))
    conv_id = cursor.lastrowid
    
    # Add both users as members
    db.execute("INSERT INTO conversation_members (conversation_id, user_id, role) VALUES (?, ?, 'member')", (conv_id, user1_id))
    db.execute("INSERT INTO conversation_members (conversation_id, user_id, role) VALUES (?, ?, 'member')", (conv_id, user2_id))
    
    db.commit()
    return conv_id

def create_group_conversation(created_by, name, member_ids, description='', avatar=''):
    """Create a new group conversation."""
    db = get_db()
    group_avatar = avatar or '/static/images/avatars/group.svg'
    
    cursor = db.execute(
        """
        INSERT INTO conversations (name, is_group, group_avatar, group_description, created_by)
        VALUES (?, 1, ?, ?, ?)
        """,
        (name.strip(), group_avatar, description.strip(), created_by)
    )
    conv_id = cursor.lastrowid
    
    # Add creator as admin
    all_members = set([created_by] + [int(uid) for uid in member_ids if str(uid).isdigit()])
    for uid in all_members:
        role = 'admin' if uid == created_by else 'member'
        db.execute(
            "INSERT INTO conversation_members (conversation_id, user_id, role) VALUES (?, ?, ?)",
            (conv_id, uid, role)
        )
        
    db.commit()
    return conv_id

def get_user_conversations(user_id):
    """Retrieve all conversations for the user with last message info and unread badge count."""
    db = get_db()
    
    # Fetch all conversations the user is part of
    query = """
    SELECT 
        c.id,
        c.name,
        c.is_group,
        c.group_avatar,
        c.group_description,
        c.created_by,
        c.created_at,
        c.updated_at,
        cm.role,
        cm.is_pinned,
        cm.is_muted,
        cm.is_archived,
        cm.last_read_message_id,
        (
            SELECT json_object(
                'id', m.id,
                'message', m.message,
                'message_type', m.message_type,
                'sender_id', m.sender_id,
                'sender_name', u.name,
                'created_at', m.created_at,
                'is_deleted', m.is_deleted,
                'read_status', m.read_status
            )
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.conversation_id = c.id
            ORDER BY m.id DESC
            LIMIT 1
        ) AS last_message_json,
        (
            SELECT COUNT(*)
            FROM messages m
            WHERE m.conversation_id = c.id 
              AND m.id > cm.last_read_message_id
              AND m.sender_id != ?
              AND m.is_deleted = 0
        ) AS unread_count
    FROM conversations c
    JOIN conversation_members cm ON c.id = cm.conversation_id AND cm.user_id = ?
    ORDER BY cm.is_pinned DESC, c.updated_at DESC
    """
    rows = db.execute(query, (user_id, user_id)).fetchall()
    
    import json
    conversations = []
    
    for row in rows:
        conv = dict_from_row(row)
        if conv['last_message_json']:
            try:
                conv['last_message'] = json.loads(conv['last_message_json'])
            except Exception:
                conv['last_message'] = None
        else:
            conv['last_message'] = None
        del conv['last_message_json']
        
        # If it's a direct 1-on-1 chat, populate partner user info
        if not conv['is_group']:
            partner_row = db.execute(
                """
                SELECT u.id, u.name, u.username, u.profile_picture, u.bio, u.status, u.custom_status, u.last_seen,
                       u.privacy_last_seen
                FROM conversation_members cm
                JOIN users u ON cm.user_id = u.id
                WHERE cm.conversation_id = ? AND cm.user_id != ?
                LIMIT 1
                """,
                (conv['id'], user_id)
            ).fetchone()
            if partner_row:
                partner = dict_from_row(partner_row)
                conv['partner'] = partner
                conv['display_name'] = partner['name']
                conv['display_avatar'] = partner['profile_picture']
                conv['partner_status'] = partner['status']
                conv['partner_last_seen'] = partner['last_seen']
            else:
                conv['partner'] = None
                conv['display_name'] = "Direct Message"
                conv['display_avatar'] = "/static/images/avatars/avatar-1.svg"
                conv['partner_status'] = "offline"
                conv['partner_last_seen'] = None
        else:
            conv['display_name'] = conv['name'] or "Group Chat"
            conv['display_avatar'] = conv['group_avatar'] or "/static/images/avatars/group.svg"
            conv['partner'] = None
            
        conversations.append(conv)
        
    return conversations

def get_conversation_by_id(conversation_id, user_id):
    """Get single conversation metadata for active chat header/info panel."""
    db = get_db()
    query = """
    SELECT c.id, c.name, c.is_group, c.group_avatar, c.group_description, c.created_by, c.created_at,
           cm.role, cm.is_pinned, cm.is_muted, cm.is_archived, cm.last_read_message_id
    FROM conversations c
    JOIN conversation_members cm ON c.id = cm.conversation_id AND cm.user_id = ?
    WHERE c.id = ?
    """
    row = db.execute(query, (user_id, conversation_id)).fetchone()
    if not row:
        return None
        
    conv = dict_from_row(row)
    if not conv['is_group']:
        partner_row = db.execute(
            """
            SELECT u.id, u.name, u.username, u.email, u.profile_picture, u.bio, u.status, u.custom_status,
                   u.last_seen, u.privacy_last_seen, u.privacy_read_receipts
            FROM conversation_members cm
            JOIN users u ON cm.user_id = u.id
            WHERE cm.conversation_id = ? AND cm.user_id != ?
            LIMIT 1
            """,
            (conversation_id, user_id)
        ).fetchone()
        if partner_row:
            partner = dict_from_row(partner_row)
            conv['partner'] = partner
            conv['display_name'] = partner['name']
            conv['display_avatar'] = partner['profile_picture']
            conv['partner_status'] = partner['status']
            conv['partner_last_seen'] = partner['last_seen']
    else:
        conv['display_name'] = conv['name'] or "Group Chat"
        conv['display_avatar'] = conv['group_avatar'] or "/static/images/avatars/group.svg"
        conv['partner'] = None
        
    conv['members'] = get_conversation_members(conversation_id)
    return conv

def get_conversation_members(conversation_id):
    """List all members of a conversation."""
    db = get_db()
    rows = db.execute(
        """
        SELECT u.id, u.name, u.username, u.profile_picture, u.status, u.last_seen, cm.role, cm.joined_at
        FROM conversation_members cm
        JOIN users u ON cm.user_id = u.id
        WHERE cm.conversation_id = ?
        ORDER BY cm.role = 'admin' DESC, u.name ASC
        """,
        (conversation_id,)
    ).fetchall()
    return dicts_from_rows(rows)

def toggle_pin_conversation(conversation_id, user_id):
    """Pin or unpin a conversation for the user."""
    db = get_db()
    row = db.execute(
        "SELECT is_pinned FROM conversation_members WHERE conversation_id = ? AND user_id = ?",
        (conversation_id, user_id)
    ).fetchone()
    if not row:
        return False
    new_state = 0 if row['is_pinned'] else 1
    db.execute(
        "UPDATE conversation_members SET is_pinned = ? WHERE conversation_id = ? AND user_id = ?",
        (new_state, conversation_id, user_id)
    )
    db.commit()
    return bool(new_state)

def toggle_mute_conversation(conversation_id, user_id):
    """Mute or unmute notifications for a conversation."""
    db = get_db()
    row = db.execute(
        "SELECT is_muted FROM conversation_members WHERE conversation_id = ? AND user_id = ?",
        (conversation_id, user_id)
    ).fetchone()
    if not row:
        return False
    new_state = 0 if row['is_muted'] else 1
    db.execute(
        "UPDATE conversation_members SET is_muted = ? WHERE conversation_id = ? AND user_id = ?",
        (new_state, conversation_id, user_id)
    )
    db.commit()
    return bool(new_state)

def delete_conversation_for_user(conversation_id, user_id):
    """Leave group or remove conversation membership."""
    db = get_db()
    db.execute(
        "DELETE FROM conversation_members WHERE conversation_id = ? AND user_id = ?",
        (conversation_id, user_id)
    )
    
    # If no members left in conversation, clean up messages and conversation
    count_row = db.execute(
        "SELECT COUNT(*) as cnt FROM conversation_members WHERE conversation_id = ?",
        (conversation_id,)
    ).fetchone()
    if count_row and count_row['cnt'] == 0:
        db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        
    db.commit()
    return True

def mark_conversation_as_read(conversation_id, user_id):
    """Mark all messages in conversation up to the latest one as read for user."""
    db = get_db()
    latest_msg = db.execute(
        "SELECT id FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT 1",
        (conversation_id,)
    ).fetchone()
    
    if latest_msg:
        latest_id = latest_msg['id']
        db.execute(
            "UPDATE conversation_members SET last_read_message_id = ? WHERE conversation_id = ? AND user_id = ?",
            (latest_id, conversation_id, user_id)
        )
        # Also update read_status flag on messages sent by other members
        db.execute(
            "UPDATE messages SET read_status = 1 WHERE conversation_id = ? AND sender_id != ? AND id <= ?",
            (conversation_id, user_id, latest_id)
        )
        db.commit()
        return latest_id
    return 0
