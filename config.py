import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'connectly-secret-key-prod-random-2026-xyz!')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', str(BASE_DIR / 'instance' / 'connectly.db'))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', str(BASE_DIR / 'static' / 'uploads'))
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB max file size
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
    ALLOWED_DOC_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'csv', 'zip', 'json', 'md'}
    ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOC_EXTENSIONS | {'mp3', 'wav', 'mp4'}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
