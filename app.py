import os
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
from config import Config
from database.db import close_db, init_db
from routes import auth_bp, chat_bp, profile_bp, search_bp
from websocket import register_socket_events

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure uploads folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.dirname(app.config['DATABASE_PATH']), exist_ok=True)

    # Initialize DB
    with app.app_context():
        init_db(app)

    # Database connection teardown
    app.teardown_appcontext(close_db)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(search_bp)

    # Friendly error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('index.html', error="The requested page could not be found."), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({'success': False, 'error': 'File size is too large (maximum 20MB allowed).'}), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({'success': False, 'error': 'An unexpected server error occurred. Please try again.'}), 500

    return app

app = create_app()
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    manage_session=False
)
register_socket_events(socketio)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Connectly server running at http://127.0.0.1:{port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
