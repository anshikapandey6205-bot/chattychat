import sqlite3
import os
from werkzeug.security import generate_password_hash
from config import Config
from database.db import init_db

def seed_database():
    print("Initializing database...")
    init_db()
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    # Check if users already exist
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    if count > 0:
        print("Database already contains data. Skipping seeding.")
        conn.close()
        return

    print("Seeding demo users...")
    password_hash = generate_password_hash("Password123!")
    
    users = [
        ("Aarav Sharma", "aarav", "aarav@connectly.app", "/static/images/avatars/avatar-1.svg", "Full-stack architect & coffee enthusiast ☕", "online"),
        ("Priya Patel", "priya", "priya@connectly.app", "/static/images/avatars/avatar-2.svg", "Product designer building sleek UI/UX ✨", "online"),
        ("Rahul Verma", "rahul", "rahul@connectly.app", "/static/images/avatars/avatar-3.svg", "DevOps ninja & cloud explorer 🚀", "away"),
        ("Sneha Kapoor", "sneha", "sneha@connectly.app", "/static/images/avatars/avatar-4.svg", "AI researcher exploring real-time systems 🤖", "online"),
        ("Riya Sen", "riya", "riya@connectly.app", "/static/images/avatars/avatar-5.svg", "Mobile engineer passionate about Flutter & Swift 📱", "offline"),
    ]
    
    user_ids = {}
    for name, uname, email, avatar, bio, status in users:
        cursor.execute(
            """
            INSERT INTO users (name, username, email, password_hash, profile_picture, bio, status, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (name, uname, email, password_hash, avatar, bio, status)
        )
        user_ids[uname] = cursor.lastrowid
        
    print(f"Created {len(user_ids)} demo users.")

    # 1. Direct conversation between Aarav & Priya
    cursor.execute("INSERT INTO conversations (is_group, created_by) VALUES (0, ?)", (user_ids['aarav'],))
    c_aarav_priya = cursor.lastrowid
    cursor.execute("INSERT INTO conversation_members (conversation_id, user_id, role, is_pinned) VALUES (?, ?, 'member', 1)", (c_aarav_priya, user_ids['aarav']))
    cursor.execute("INSERT INTO conversation_members (conversation_id, user_id, role) VALUES (?, ?, 'member')", (c_aarav_priya, user_ids['priya']))
    
    # Messages between Aarav and Priya
    cursor.execute(
        """
        INSERT INTO messages (conversation_id, sender_id, message, created_at, read_status)
        VALUES (?, ?, 'Hey Priya! Have you checked out the new Connectly UI layout?', datetime('now', '-2 hours'), 1)
        """,
        (c_aarav_priya, user_ids['aarav'])
    )
    m1 = cursor.lastrowid
    
    cursor.execute(
        """
        INSERT INTO messages (conversation_id, sender_id, message, created_at, read_status)
        VALUES (?, ?, 'Hey Aarav! Yes, the glassmorphic aesthetic and dark mode look incredible! 🎨', datetime('now', '-1 hour', '50 minutes'), 1)
        """,
        (c_aarav_priya, user_ids['priya'])
    )
    m2 = cursor.lastrowid
    
    cursor.execute(
        """
        INSERT INTO messages (conversation_id, sender_id, message, reply_to, created_at, read_status)
        VALUES (?, ?, 'Awesome! I also added emoji reactions and instant typing indicators.', ?, datetime('now', '-30 minutes'), 1)
        """,
        (c_aarav_priya, user_ids['aarav'], m2)
    )
    m3 = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO messages (conversation_id, sender_id, message, created_at, read_status)
        VALUES (?, ?, 'Testing out real-time delivery right now. Everything feels super snappy! 🚀', datetime('now', '-5 minutes'), 0)
        """,
        (c_aarav_priya, user_ids['priya'])
    )
    m4 = cursor.lastrowid
    
    # Reactions on m2 and m3
    cursor.execute("INSERT INTO message_reactions (message_id, user_id, reaction) VALUES (?, ?, '🔥')", (m2, user_ids['aarav']))
    cursor.execute("INSERT INTO message_reactions (message_id, user_id, reaction) VALUES (?, ?, '❤️')", (m3, user_ids['priya']))

    # 2. Direct conversation between Aarav & Rahul
    cursor.execute("INSERT INTO conversations (is_group, created_by) VALUES (0, ?)", (user_ids['aarav'],))
    c_aarav_rahul = cursor.lastrowid
    cursor.execute("INSERT INTO conversation_members (conversation_id, user_id, role) VALUES (?, ?, 'member')", (c_aarav_rahul, user_ids['aarav']))
    cursor.execute("INSERT INTO conversation_members (conversation_id, user_id, role) VALUES (?, ?, 'member')", (c_aarav_rahul, user_ids['rahul']))
    
    cursor.execute(
        """
        INSERT INTO messages (conversation_id, sender_id, message, created_at, read_status)
        VALUES (?, ?, 'Rahul, how is the WebSocket connection handling under test loads?', datetime('now', '-4 hours'), 1)
        """,
        (c_aarav_rahul, user_ids['aarav'])
    )
    cursor.execute(
        """
        INSERT INTO messages (conversation_id, sender_id, message, created_at, read_status)
        VALUES (?, ?, 'Sub-millisecond latency on local socket transport. Zero drops recorded! ⚡', datetime('now', '-3 hours'), 1)
        """,
        (c_aarav_rahul, user_ids['rahul'])
    )

    # 3. Direct conversation between Aarav & Sneha
    cursor.execute("INSERT INTO conversations (is_group, created_by) VALUES (0, ?)", (user_ids['aarav'],))
    c_aarav_sneha = cursor.lastrowid
    cursor.execute("INSERT INTO conversation_members (conversation_id, user_id, role) VALUES (?, ?, 'member')", (c_aarav_sneha, user_ids['aarav']))
    cursor.execute("INSERT INTO conversation_members (conversation_id, user_id, role) VALUES (?, ?, 'member')", (c_aarav_sneha, user_ids['sneha']))
    
    cursor.execute(
        """
        INSERT INTO messages (conversation_id, sender_id, message, created_at, read_status)
        VALUES (?, ?, 'Hey Sneha! Let me know when you want to review the global search algorithm.', datetime('now', '-1 day'), 1)
        """,
        (c_aarav_sneha, user_ids['aarav'])
    )
    cursor.execute(
        """
        INSERT INTO messages (conversation_id, sender_id, message, created_at, read_status)
        VALUES (?, ?, 'Just tested it on conversations and users. The instant debounce works like magic! 🪄', datetime('now', '-18 hours'), 1)
        """,
        (c_aarav_sneha, user_ids['sneha'])
    )

    # 4. Group Conversation: Tech Innovators 🚀
    cursor.execute(
        """
        INSERT INTO conversations (name, is_group, group_avatar, group_description, created_by)
        VALUES ('Tech Innovators 🚀', 1, '/static/images/avatars/group.svg', 'Official engineering and product design workspace.', ?)
        """,
        (user_ids['aarav'],)
    )
    c_group = cursor.lastrowid
    
    for uid in user_ids.values():
        role = 'admin' if uid == user_ids['aarav'] else 'member'
        is_pin = 1 if uid == user_ids['aarav'] else 0
        cursor.execute(
            "INSERT INTO conversation_members (conversation_id, user_id, role, is_pinned) VALUES (?, ?, ?, ?)",
            (c_group, uid, role, is_pin)
        )
        
    cursor.execute(
        """
        INSERT INTO messages (conversation_id, sender_id, message, created_at, read_status)
        VALUES (?, ?, 'Welcome everyone to the Connectly collaborative space! 🎉', datetime('now', '-5 hours'), 1)
        """,
        (c_group, user_ids['aarav'])
    )
    gm1 = cursor.lastrowid
    
    cursor.execute(
        """
        INSERT INTO messages (conversation_id, sender_id, message, created_at, read_status)
        VALUES (?, ?, 'Excited to be here! The responsive layout works smoothly on mobile too.', datetime('now', '-4 hours', '30 minutes'), 1)
        """,
        (c_group, user_ids['riya'])
    )
    gm2 = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO messages (conversation_id, sender_id, message, reply_to, created_at, read_status)
        VALUES (?, ?, 'Great job team! Let us test file attachments and reactions today.', ?, datetime('now', '-20 minutes'), 1)
        """,
        (c_group, user_ids['priya'], gm2)
    )
    gm3 = cursor.lastrowid
    
    cursor.execute("INSERT INTO message_reactions (message_id, user_id, reaction) VALUES (?, ?, '🚀')", (gm1, user_ids['rahul']))
    cursor.execute("INSERT INTO message_reactions (message_id, user_id, reaction) VALUES (?, ?, '👍')", (gm1, user_ids['sneha']))
    cursor.execute("INSERT INTO message_reactions (message_id, user_id, reaction) VALUES (?, ?, '❤️')", (gm3, user_ids['aarav']))

    conn.commit()
    conn.close()
    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed_database()
