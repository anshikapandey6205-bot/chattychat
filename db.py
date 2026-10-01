import sqlite3
import os
from flask import g, current_app
from config import Config

def get_db():
    """Get or create SQLite connection for the current request context."""
    if 'db' not in g:
        db_path = current_app.config.get('DATABASE_PATH', Config.DATABASE_PATH)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app=None):
    """Initialize the database tables from schema.sql."""
    db_path = app.config['DATABASE_PATH'] if app else Config.DATABASE_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    
    conn.commit()
    conn.close()

def dict_from_row(row):
    """Convert a sqlite3.Row object to a Python dict."""
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}

def dicts_from_rows(rows):
    """Convert a list of sqlite3.Row objects to a list of Python dicts."""
    return [dict_from_row(r) for r in rows]
