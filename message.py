import sqlite3
from database.db import get_db, dict_from_row, dicts_from_rows

def create_message(conversation_id, sender_id, message, message_type='text', reply_to=None, attachments=None):
    """Create a new message and optional attachments."""
    db = get_db()
    
    cursor = db.execute(
        """
        INSERT INTO messages (conversation_id, sender_id, message, message_type, reply_to)
        VALUES (?, ?, ?, ?, ?)
        """,
        (conversation_id, sender_id, message, message_type, reply_to)
    )
    message_id = cursor.lastrowid
    
    # Insert attachments if provided
    if attachments:
        for att in attachments:
            db.execute(
                """
                INSERT INTO attachments (message_id, filename, original_name, filepath, file_type, file_size)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    att.get('filename', ''),
                    att.get('original_name', ''),
                    att.get('filepath', ''),
                    att.get('file_type', 'file'),
                    att.get('file_size', 0)
                )
            )
            
    # Update conversation's updated_at timestamp
    db.execute("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conversation_id,))
    
    # Update sender's last_read_message_id to this message
    db.execute(
        "UPDATE conversation_members SET last_read_message_id = ? WHERE conversation_id = ? AND user_id = ?",
        (message_id, conversation_id, sender_id)
    )
    
    db.commit()
    return get_message_by_id(message_id, sender_id)

def get_message_by_id(message_id, current_user_id=None):
    """Fetch complete message object with sender, reply preview, attachments, and reactions."""
    db = get_db()
    query = """
    SELECT m.id, m.conversation_id, m.sender_id, m.message, m.message_type, m.reply_to,
           m.created_at, m.edited_at, m.is_deleted, m.read_status,
           u.name as sender_name, u.username as sender_username, u.profile_picture as sender_avatar
    FROM messages m
    JOIN users u ON m.sender_id = u.id
    WHERE m.id = ?
    """
    row = db.execute(query, (message_id,)).fetchone()
    if not row:
        return None
        
    msg = dict_from_row(row)
    
    # Fetch reply details if any
    if msg['reply_to']:
        reply_row = db.execute(
            """
            SELECT m.id, m.message, m.message_type, m.is_deleted, u.name as sender_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.id = ?
            """,
            (msg['reply_to'],)
        ).fetchone()
        if reply_row:
            msg['reply_info'] = dict_from_row(reply_row)
        else:
            msg['reply_info'] = None
    else:
        msg['reply_info'] = None
        
    # Fetch attachments
    att_rows = db.execute(
        "SELECT id, filename, original_name, filepath, file_type, file_size FROM attachments WHERE message_id = ?",
        (message_id,)
    ).fetchall()
    msg['attachments'] = dicts_from_rows(att_rows)
    
    # Fetch reactions grouped by emoji
    rx_rows = db.execute(
        """
        SELECT mr.reaction, mr.user_id, u.name as user_name
        FROM message_reactions mr
        JOIN users u ON mr.user_id = u.id
        WHERE mr.message_id = ?
        """,
        (message_id,)
    ).fetchall()
    
    reactions_map = {}
    for r in rx_rows:
        emoji = r['reaction']
        if emoji not in reactions_map:
            reactions_map[emoji] = {
                'emoji': emoji,
                'count': 0,
                'users': [],
                'has_reacted': False
            }
        reactions_map[emoji]['count'] += 1
        reactions_map[emoji]['users'].append(r['user_name'])
        if current_user_id and r['user_id'] == current_user_id:
            reactions_map[emoji]['has_reacted'] = True
            
    msg['reactions'] = list(reactions_map.values())
    return msg

def get_conversation_messages(conversation_id, current_user_id, limit=50, before_id=None):
    """Retrieve messages in chronological order for a conversation."""
    db = get_db()
    
    if before_id:
        query = """
        SELECT m.id
        FROM messages m
        WHERE m.conversation_id = ? AND m.id < ?
        ORDER BY m.id DESC
        LIMIT ?
        """
        rows = db.execute(query, (conversation_id, before_id, limit)).fetchall()
    else:
        query = """
        SELECT m.id
        FROM messages m
        WHERE m.conversation_id = ?
        ORDER BY m.id DESC
        LIMIT ?
        """
        rows = db.execute(query, (conversation_id, limit)).fetchall()
        
    message_ids = [r['id'] for r in reversed(rows)]
    
    messages = []
    for msg_id in message_ids:
        msg = get_message_by_id(msg_id, current_user_id)
        if msg:
            messages.append(msg)
            
    return messages

def edit_message(message_id, user_id, new_content):
    """Edit own message."""
    db = get_db()
    row = db.execute(
        "SELECT sender_id, is_deleted FROM messages WHERE id = ?",
        (message_id,)
    ).fetchone()
    
    if not row or row['sender_id'] != user_id or row['is_deleted']:
        return None
        
    db.execute(
        "UPDATE messages SET message = ?, edited_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_content.strip(), message_id)
    )
    db.commit()
    return get_message_by_id(message_id, user_id)

def delete_message(message_id, user_id):
    """Soft delete message."""
    db = get_db()
    row = db.execute(
        "SELECT sender_id, conversation_id FROM messages WHERE id = ?",
        (message_id,)
    ).fetchone()
    
    if not row or row['sender_id'] != user_id:
        return None
        
    db.execute(
        "UPDATE messages SET is_deleted = 1, message = 'This message was deleted' WHERE id = ?",
        (message_id,)
    )
    db.commit()
    return get_message_by_id(message_id, user_id)

def toggle_reaction(message_id, user_id, reaction):
    """Add or remove an emoji reaction on a message."""
    db = get_db()
    
    row = db.execute(
        "SELECT id FROM message_reactions WHERE message_id = ? AND user_id = ? AND reaction = ?",
        (message_id, user_id, reaction)
    ).fetchone()
    
    if row:
        db.execute("DELETE FROM message_reactions WHERE id = ?", (row['id'],))
        action = 'removed'
    else:
        db.execute(
            "INSERT INTO message_reactions (message_id, user_id, reaction) VALUES (?, ?, ?)",
            (message_id, user_id, reaction)
        )
        action = 'added'
        
    db.commit()
    updated_msg = get_message_by_id(message_id, user_id)
    return {
        'message_id': message_id,
        'action': action,
        'reaction': reaction,
        'reactions': updated_msg['reactions'] if updated_msg else []
    }

def get_shared_media(conversation_id):
    """Get all media files and docs shared in this conversation."""
    db = get_db()
    
    image_rows = db.execute(
        """
        SELECT a.id, a.filename, a.original_name, a.filepath, a.file_type, a.file_size, a.created_at, m.id as message_id
        FROM attachments a
        JOIN messages m ON a.message_id = m.id
        WHERE m.conversation_id = ? AND m.is_deleted = 0 AND a.file_type LIKE 'image/%'
        ORDER BY a.id DESC
        """,
        (conversation_id,)
    ).fetchall()
    
    doc_rows = db.execute(
        """
        SELECT a.id, a.filename, a.original_name, a.filepath, a.file_type, a.file_size, a.created_at, m.id as message_id
        FROM attachments a
        JOIN messages m ON a.message_id = m.id
        WHERE m.conversation_id = ? AND m.is_deleted = 0 AND a.file_type NOT LIKE 'image/%'
        ORDER BY a.id DESC
        """,
        (conversation_id,)
    ).fetchall()
    
    return {
        'images': dicts_from_rows(image_rows),
        'files': dicts_from_rows(doc_rows)
    }

def search_messages(query, user_id, conversation_id=None):
    """Search for messages across user conversations or within a single chat."""
    db = get_db()
    search_term = f"%{query.strip()}%"
    
    if conversation_id:
        # Search within single conversation
        rows = db.execute(
            """
            SELECT m.id, m.conversation_id, m.sender_id, m.message, m.message_type, m.created_at,
                   u.name as sender_name, u.profile_picture as sender_avatar
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            JOIN conversation_members cm ON m.conversation_id = cm.conversation_id AND cm.user_id = ?
            WHERE m.conversation_id = ? AND m.is_deleted = 0 AND LOWER(m.message) LIKE LOWER(?)
            ORDER BY m.id DESC
            LIMIT 30
            """,
            (user_id, conversation_id, search_term)
        ).fetchall()
    else:
        # Search globally across all conversations the user is in
        rows = db.execute(
            """
            SELECT m.id, m.conversation_id, m.sender_id, m.message, m.message_type, m.created_at,
                   u.name as sender_name, u.profile_picture as sender_avatar,
                   COALESCE(c.name, (SELECT u2.name FROM conversation_members cm2 JOIN users u2 ON cm2.user_id = u2.id WHERE cm2.conversation_id = c.id AND cm2.user_id != ? LIMIT 1)) as conversation_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            JOIN conversations c ON m.conversation_id = c.id
            JOIN conversation_members cm ON m.conversation_id = cm.conversation_id AND cm.user_id = ?
            WHERE m.is_deleted = 0 AND LOWER(m.message) LIKE LOWER(?)
            ORDER BY m.id DESC
            LIMIT 30
            """,
            (user_id, user_id, search_term)
        ).fetchall()
        
    return dicts_from_rows(rows)

def get_unread_count_for_user(user_id):
    """Get total unread messages count across all chats for the user."""
    db = get_db()
    row = db.execute(
        """
        SELECT COUNT(m.id) as total_unread
        FROM messages m
        JOIN conversation_members cm ON m.conversation_id = cm.conversation_id AND cm.user_id = ?
        WHERE m.id > cm.last_read_message_id
          AND m.sender_id != ?
          AND m.is_deleted = 0
        """,
        (user_id, user_id)
    ).fetchone()
    return row['total_unread'] if row else 0
