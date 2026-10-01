# 💬 Connectly — Modern Real-Time Chat Application

<p align="center">
  <img src="static/images/avatars/group.svg" width="96" height="96" alt="Connectly Logo" />
</p>

<p align="center">
  <strong>Connect. Chat. Share.</strong><br>
  A high-performance real-time messaging platform built with Python, Flask, Flask-SocketIO, SQLite, and modern responsive glassmorphism UI.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/Flask-3.x-black?style=for-the-badge&logo=flask" alt="Flask" />
  <img src="https://img.shields.io/badge/Socket.IO-Real--Time-purple?style=for-the-badge&logo=socketdotio" alt="Socket.IO" />
  <img src="https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite" alt="SQLite" />
  <img src="https://img.shields.io/badge/Theme-Dark%20%2F%20Light-6366f1?style=for-the-badge" alt="Theme" />
</p>

---

## 🌟 Overview

**Connectly** is a production-grade, full-stack real-time communication platform designed to look and feel like a modern startup messaging application (Slack / Discord / Telegram hybrid).

It provides instantaneous bidirectional message delivery over WebSockets, typing presence indicators, emoji reactions, reply threading, message editing/retraction, file & photo attachments with lightbox previews, voice/video call signaling, group channels, global multi-category search, and full dark/light theme customization.

---

## ✨ Key Features

### 🚀 1. Real-Time Engine (WebSockets / Socket.IO)
- **Instant Messaging**: Sub-millisecond local latency with automatic fallback and reconnection.
- **Live Typing Indicators**: "Priya is typing..." animated bubbles.
- **Presence & Status**: Real-time broadcast of `Online`, `Away`, `Do Not Disturb`, and `Invisible` states with `last_seen` timestamps.
- **Live Read Receipts**: Double checkmarks (`✓` Sent, `✓✓` Read in blue) updating dynamically.
- **Dynamic Unread Badges**: Real-time counter increments and resets across sidebar items.

### 💬 2. Rich Message Interactions
- **Message Replies & Quotes**: Quote any message to maintain conversation context.
- **In-Line Editing**: Edit your sent messages in real-time with `(edited)` indicators.
- **Soft Deletion**: Retract messages with friendly placeholders.
- **Emoji Reactions**: React with ❤️, 👍, 😂, 😮, 😢, 🔥 with interactive reaction counts and user tooltips.
- **Clipboard Text Copy**: One-click copying with toast feedback.
- **Message Forwarding**: Forward any message to another direct contact or group channel.
- **Custom Context Menu**: Right-click or touch-hold context actions.

### 🖼️ 3. Media & File Sharing
- **Images & Photos**: Embedded previews with a full-screen Lightbox zoom viewer.
- **Document Attachments**: PDF, DOCX, TXT, ZIP, CSV, MD sharing with file size formatting.
- **Shared Media Gallery**: Collapsible right info panel with tabbed Image & Document galleries.
- **Drag-and-Drop**: Direct file drag-and-drop into chat messages.

### 👥 4. Group Channels & Collaboration
- Create custom group channels with member multiselection and topic descriptions.
- Role badges (`Admin`, `Member`) and participant rosters.
- Channel pinned messages and notification mute settings.

### 🔍 5. Global & In-Chat Search
- **Instant Debounced Global Search**: Queries People, Conversations, and Message contents in real-time.
- **In-Chat Message Highlighter**: Jump between keyword occurrences with Next/Previous navigation within active chats.

### 🎨 6. Modern Glassmorphism & Themes
- **Adaptive Dark / Light / System Mode**: Seamless theme transitions with persistent state.
- **Custom Audio Chimes**: Gentle notification sounds synthesized via Web Audio API (100% offline).
- **Desktop Web Notifications**: Native HTML5 Notifications API support.
- **Responsive Drawer UI**: Optimized for Mobile, Tablet, Laptop, and Desktop viewports.

### 🔒 7. Security & Privacy
- Password hashing with **Werkzeug** (Scrypt / PBKDF2).
- Protected session cookies (`HttpOnly`, `SameSite=Lax`).
- SQLite parameterized queries preventing SQL Injection.
- Sanitized file upload storage with UUID prefixes.
- Privacy controls for `Last Seen` visibility and `Read Receipts`.

---

## 🏗️ Project Architecture

```text
chattychat/
│
├── app.py                      # Flask & SocketIO application factory
├── config.py                   # Configuration, upload limits, secret keys
├── requirements.txt            # Python dependencies
├── seed_demo.py                # Standalone demo data seeder
├── test_app.py                 # Automated unit and integration tests
├── test_e2e_realtime.py        # Real-time WebSocket E2E test suite
│
├── database/
│   ├── __init__.py
│   ├── db.py                   # SQLite connection & cursor management
│   └── schema.sql              # Database schema definition
│
├── models/
│   ├── __init__.py
│   ├── user.py                 # User authentication, profiles, status, settings
│   ├── conversation.py         # Direct & Group chat models, memberships, pins
│   └── message.py              # Messages, attachments, reactions, search
│
├── routes/
│   ├── __init__.py
│   ├── auth.py                 # Login, Register, Logout, Password Reset, /api/auth/*
│   ├── chat.py                 # Dashboard, Conversation APIs, File Uploads, Media
│   ├── profile.py              # Profile editing, Password changes, Preferences
│   └── search.py               # Global multi-target search endpoint
│
├── websocket/
│   ├── __init__.py
│   └── events.py               # SocketIO real-time event handlers
│
├── templates/
│   ├── base.html               # Base layout, modals, lightbox, audio chime
│   ├── index.html              # Landing page with interactive live dashboard preview
│   ├── login.html              # Modern login page with 1-click demo selectors
│   ├── register.html           # Registration with avatar presets & custom upload
│   ├── chat.html               # 3-Column main chat workspace
│   ├── profile.html            # User profile management
│   └── settings.html           # Settings (Appearance, Notifications, Privacy, Security)
│
├── static/
│   ├── css/
│   │   ├── style.css           # Design tokens, variables, typography, animations
│   │   ├── landing.css         # Hero section, preview widgets, auth cards
│   │   ├── chat.css            # 3-Column layout, bubbles, composer, context menu
│   │   ├── profile.css         # Profile banner, settings categories, toggles
│   │   └── toast.css           # Toasts, modal backdrops, call interface
│   ├── js/
│   │   ├── chat.js             # Real-time WebSocket engine & DOM manager
│   │   ├── search.js           # Debounced global search controller
│   │   ├── profile.js          # Profile updates & settings AJAX dispatcher
│   │   ├── auth.js             # Form validation & demo account filler
│   │   ├── theme.js            # Light/Dark/System theme switcher
│   │   └── toast.js            # Toast notifications & audio chimes
│   ├── images/
│   │   └── avatars/            # Vector gradient avatar presets
│   └── uploads/                # User uploaded attachments & custom photos
│
└── instance/
    └── connectly.db            # SQLite database file
```

---

## ⚡ Quick Start & Installation

### 1. Clone or Open the Repository
```bash
cd /path/to/chattychat
```

### 2. Create and Activate Virtual Environment
```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize and Seed Demo Data
```bash
python seed_demo.py
```

### 5. Run the Application
```bash
python app.py
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🔑 Demo Accounts

The application comes pre-seeded with realistic demo accounts so you can test multi-user messaging right away:

| Name | Username | Password | Role |
| :--- | :--- | :--- | :--- |
| **Aarav Sharma** | `aarav` | `Password123!` | Full-Stack Architect (Admin) |
| **Priya Patel** | `priya` | `Password123!` | Product UI/UX Lead |
| **Rahul Verma** | `rahul` | `Password123!` | DevOps & Cloud Lead |
| **Sneha Kapoor** | `sneha` | `Password123!` | AI Research Lead |
| **Riya Sen** | `riya` | `Password123!` | Mobile Lead |

> **Tip:** You can open two different browser tabs (or one Regular and one Incognito window) and log into `aarav` in one and `priya` in the other to test real-time instant messaging side-by-side!

---

## 🧪 Running Tests

Run the full automated test suite:

```bash
# Unit and REST integration tests
python test_app.py

# Real-time WebSocket event tests
python test_e2e_realtime.py
```

---

## 🛠️ API Reference

### Authentication
- `POST /login` — User authentication
- `POST /register` — New account creation
- `GET /logout` — Invalidate session
- `GET /api/auth/me` — Retrieve current authenticated profile

### Conversations
- `GET /api/conversations` — List all user chats with unread badges
- `POST /api/conversations/direct` — Open or create 1-to-1 conversation
- `POST /api/conversations/group` — Create new group channel
- `GET /api/conversations/<id>` — Retrieve metadata and participant list
- `GET /api/conversations/<id>/messages` — Fetch message stream with pagination
- `POST /api/conversations/<id>/pin` — Toggle conversation pin state
- `POST /api/conversations/<id>/mute` — Toggle notifications mute
- `DELETE /api/conversations/<id>` — Leave or delete conversation
- `GET /api/conversations/<id>/media` — Fetch shared images and files

### Messages & Attachments
- `POST /api/upload` — Secure file & photo upload
- `POST /api/messages/<id>/react` — Toggle emoji reaction
- `PUT /api/messages/<id>` — Edit message text
- `DELETE /api/messages/<id>` — Soft delete message

### Search
- `GET /api/search?q={query}` — Global search for users, conversations, and text history

---

## 🔮 Future Improvements
- End-to-End Encryption (E2EE) with Signal Protocol / WebCrypto.
- WebRTC Peer-to-Peer streaming video/audio calls with STUN/TURN servers.
- Voice audio note recording directly in the browser composer.
- Rich Markdown code snippet formatting with syntax highlighting.

---

## 📄 License
MIT License. Built with ❤️ for modern real-time communication.
