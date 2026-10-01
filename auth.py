import os
from functools import wraps
from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify, current_app
from werkzeug.utils import secure_filename
from models.user import (
    create_user, authenticate_user, get_user_by_id, update_user_status, update_user_password
)

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Unauthorized. Please log in.'}), 401
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session and request.method == 'GET':
        return redirect(url_for('chat.dashboard'))

    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
            login_id = data.get('username') or data.get('email', '')
            password = data.get('password', '')
            remember = data.get('remember', False)
        else:
            login_id = request.form.get('username') or request.form.get('email', '')
            password = request.form.get('password', '')
            remember = bool(request.form.get('remember'))

        if not login_id or not password:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Please enter both username/email and password.'}), 400
            return render_template('login.html', error='Please enter both username/email and password.')

        user = authenticate_user(login_id, password)
        if not user:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Invalid username/email or password.'}), 401
            return render_template('login.html', error='Invalid username/email or password.')

        session.permanent = bool(remember)
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['name'] = user['name']

        update_user_status(user['id'], 'online')

        if request.is_json:
            return jsonify({'success': True, 'user': user, 'redirect': url_for('chat.dashboard')})
        
        next_url = request.args.get('next') or url_for('chat.dashboard')
        return redirect(next_url)

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session and request.method == 'GET':
        return redirect(url_for('chat.dashboard'))

    if request.method == 'POST':
        is_json = request.is_json
        data = request.get_json() if is_json else request.form

        name = data.get('name', '').strip()
        username = data.get('username', '').strip().lower()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        avatar_preset = data.get('avatar_preset', '/static/images/avatars/avatar-1.svg')
        bio = data.get('bio', 'Hey there! I am using Connectly 💬').strip()

        # Validation
        if not name or not username or not email or not password:
            msg = 'All required fields must be filled.'
            return jsonify({'success': False, 'error': msg}), 400 if is_json else render_template('register.html', error=msg)

        if len(username) < 3 or len(username) > 30:
            msg = 'Username must be between 3 and 30 characters.'
            return jsonify({'success': False, 'error': msg}), 400 if is_json else render_template('register.html', error=msg)

        if len(password) < 6:
            msg = 'Password must be at least 6 characters long.'
            return jsonify({'success': False, 'error': msg}), 400 if is_json else render_template('register.html', error=msg)

        if password != confirm_password:
            msg = 'Passwords do not match.'
            return jsonify({'success': False, 'error': msg}), 400 if is_json else render_template('register.html', error=msg)

        profile_picture = avatar_preset

        # Handle custom avatar file upload if sent
        if not is_json and 'profile_picture_file' in request.files:
            file = request.files['profile_picture_file']
            if file and file.filename:
                ext = file.filename.rsplit('.', 1)[-1].lower()
                if ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
                    filename = f"avatar_{username}_{int(os.times().elapsed*1000)}.{ext}"
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    os.makedirs(upload_folder, exist_ok=True)
                    file.save(os.path.join(upload_folder, filename))
                    profile_picture = f"/static/uploads/{filename}"

        try:
            user = create_user(
                name=name,
                username=username,
                email=email,
                password=password,
                profile_picture=profile_picture,
                bio=bio
            )
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            update_user_status(user['id'], 'online')

            if is_json:
                return jsonify({'success': True, 'user': user, 'redirect': url_for('chat.dashboard')})
            return redirect(url_for('chat.dashboard'))
        except ValueError as ve:
            msg = str(ve)
            return jsonify({'success': False, 'error': msg}), 400 if is_json else render_template('register.html', error=msg)
        except Exception:
            msg = 'An unexpected error occurred during registration. Please try again.'
            return jsonify({'success': False, 'error': msg}), 500 if is_json else render_template('register.html', error=msg)

    return render_template('register.html')

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    user_id = session.get('user_id')
    if user_id:
        update_user_status(user_id, 'offline')
    session.clear()
    
    if request.is_json:
        return jsonify({'success': True, 'redirect': url_for('auth.login')})
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    user = get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'success': False, 'error': 'User not found'}), 404
    return jsonify({'success': True, 'user': user})

@auth_bp.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'success': False, 'error': 'Please provide your registered email address.'}), 400
        
    return jsonify({
        'success': True,
        'message': f'Password reset link has been dispatched to {email}. For demo accounts, you can use Password123!.'
    })
