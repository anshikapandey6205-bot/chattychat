import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, dict_from_row, dicts_from_rows

def create_user(name, username, email, password, profile_picture=None, bio=None):
    """Create a new user with hashed password."""
    db = get_db()
    password_hash = generate_password_hash(password)
    
    avatar = profile_picture or '/static/images/avatars/avatar-1.svg'
    user_bio = bio or 'Hey there! I am using Connectly 💬'
    
    try:
        cursor = db.execute(
            """
            INSERT INTO users (name, username, email, password_hash, profile_picture, bio, status, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, 'offline', CURRENT_TIMESTAMP)
            """,
            (name.strip(), username.strip().lower(), email.strip().lower(), password_hash, avatar, user_bio)
        )
        db.commit()
        return get_user_by_id(cursor.lastrowid)
    except sqlite3.IntegrityError as e:
        db.rollback()
        err_msg = str(e).lower()
        if 'users.username' in err_msg or 'unique constraint failed: users.username' in err_msg:
            raise ValueError("Username is already taken. Please choose another.")
        elif 'users.email' in err_msg or 'unique constraint failed: users.email' in err_msg:
            raise ValueError("Email address is already registered.")
        else:
            raise ValueError("Registration failed. A user with these details already exists.")

def get_user_by_id(user_id):
    """Retrieve user details by ID."""
    db = get_db()
    row = db.execute(
        """
        SELECT id, name, username, email, profile_picture, bio, status, custom_status,
               last_seen, theme_preference, sound_notifications, desktop_notifications,
               privacy_last_seen, privacy_read_receipts, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()
    return dict_from_row(row)

def get_user_by_username(username):
    """Retrieve user details by username."""
    db = get_db()
    row = db.execute(
        """
        SELECT id, name, username, email, password_hash, profile_picture, bio, status, custom_status,
               last_seen, theme_preference, sound_notifications, desktop_notifications,
               privacy_last_seen, privacy_read_receipts, created_at
        FROM users
        WHERE LOWER(username) = LOWER(?)
        """,
        (username.strip(),)
    ).fetchone()
    return dict_from_row(row)

def get_user_by_email(email):
    """Retrieve user details by email."""
    db = get_db()
    row = db.execute(
        """
        SELECT id, name, username, email, password_hash, profile_picture, bio, status, custom_status,
               last_seen, theme_preference, sound_notifications, desktop_notifications,
               privacy_last_seen, privacy_read_receipts, created_at
        FROM users
        WHERE LOWER(email) = LOWER(?)
        """,
        (email.strip(),)
    ).fetchone()
    return dict_from_row(row)

def authenticate_user(login_identifier, password):
    """Authenticate user with username or email and password."""
    user = get_user_by_username(login_identifier)
    if not user:
        user = get_user_by_email(login_identifier)
    
    if user and check_password_hash(user['password_hash'], password):
        # Clean up password_hash before returning
        user_safe = {k: v for k, v in user.items() if k != 'password_hash'}
        return user_safe
    return None

def update_user_profile(user_id, name=None, bio=None, profile_picture=None, custom_status=None):
    """Update profile fields."""
    db = get_db()
    fields = []
    values = []
    
    if name is not None:
        fields.append("name = ?")
        values.append(name.strip())
    if bio is not None:
        fields.append("bio = ?")
        values.append(bio.strip())
    if profile_picture is not None:
        fields.append("profile_picture = ?")
        values.append(profile_picture)
    if custom_status is not None:
        fields.append("custom_status = ?")
        values.append(custom_status.strip())
        
    if not fields:
        return get_user_by_id(user_id)
        
    values.append(user_id)
    query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
    db.execute(query, tuple(values))
    db.commit()
    return get_user_by_id(user_id)

def update_user_password(user_id, new_password):
    """Update password hash."""
    db = get_db()
    password_hash = generate_password_hash(new_password)
    db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    db.commit()
    return True

def update_user_status(user_id, status):
    """Update online/offline/away status and last seen timestamp."""
    db = get_db()
    db.execute(
        "UPDATE users SET status = ?, last_seen = CURRENT_TIMESTAMP WHERE id = ?",
        (status, user_id)
    )
    db.commit()

def update_user_settings(user_id, theme_preference=None, sound_notifications=None,
                         desktop_notifications=None, privacy_last_seen=None, privacy_read_receipts=None):
    """Update user preferences."""
    db = get_db()
    fields = []
    values = []
    
    if theme_preference is not None:
        fields.append("theme_preference = ?")
        values.append(theme_preference)
    if sound_notifications is not None:
        fields.append("sound_notifications = ?")
        values.append(1 if sound_notifications else 0)
    if desktop_notifications is not None:
        fields.append("desktop_notifications = ?")
        values.append(1 if desktop_notifications else 0)
    if privacy_last_seen is not None:
        fields.append("privacy_last_seen = ?")
        values.append(privacy_last_seen)
    if privacy_read_receipts is not None:
        fields.append("privacy_read_receipts = ?")
        values.append(1 if privacy_read_receipts else 0)
        
    if not fields:
        return get_user_by_id(user_id)
        
    values.append(user_id)
    query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
    db.execute(query, tuple(values))
    db.commit()
    return get_user_by_id(user_id)

def search_users(query, current_user_id):
    """Search users by name or username excluding the current user and blocked users."""
    db = get_db()
    search_term = f"%{query.strip()}%"
    rows = db.execute(
        """
        SELECT u.id, u.name, u.username, u.profile_picture, u.bio, u.status, u.last_seen
        FROM users u
        WHERE u.id != ?
          AND (LOWER(u.name) LIKE LOWER(?) OR LOWER(u.username) LIKE LOWER(?))
          AND u.id NOT IN (SELECT blocked_user_id FROM blocked_users WHERE user_id = ?)
        ORDER BY u.name ASC
        LIMIT 20
        """,
        (current_user_id, search_term, search_term, current_user_id)
    ).fetchall()
    return dicts_from_rows(rows)

def get_all_users_except(current_user_id):
    """Get all available users except current user."""
    db = get_db()
    rows = db.execute(
        """
        SELECT id, name, username, profile_picture, bio, status, last_seen
        FROM users
        WHERE id != ?
        ORDER BY status = 'online' DESC, name ASC
        """,
        (current_user_id,)
    ).fetchall()
    return dicts_from_rows(rows)

def is_user_blocked(user_id, target_user_id):
    """Check if target user is blocked by user."""
    db = get_db()
    row = db.execute(
        "SELECT 1 FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?",
        (user_id, target_user_id)
    ).fetchone()
    return row is not None

def toggle_block_user(user_id, target_user_id):
    """Block or unblock a user."""
    db = get_db()
    is_blocked = is_user_blocked(user_id, target_user_id)
    if is_blocked:
        db.execute("DELETE FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?", (user_id, target_user_id))
        db.commit()
        return False
    else:
        db.execute("INSERT OR IGNORE INTO blocked_users (user_id, blocked_user_id) VALUES (?, ?)", (user_id, target_user_id))
        db.commit()
        return True
