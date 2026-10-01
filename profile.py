import os
from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify, current_app
from werkzeug.security import check_password_hash
from routes.auth import login_required
from models.user import (
    get_user_by_id, update_user_profile, update_user_password,
    update_user_settings, toggle_block_user
)
from database.db import get_db

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile')
@login_required
def profile_page():
    user = get_user_by_id(session['user_id'])
    return render_template('profile.html', user=user)

@profile_bp.route('/settings')
@login_required
def settings_page():
    user = get_user_by_id(session['user_id'])
    return render_template('settings.html', user=user)

@profile_bp.route('/api/profile/update', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json() if request.is_json else request.form
    name = data.get('name')
    bio = data.get('bio')
    custom_status = data.get('custom_status')
    profile_picture = data.get('profile_picture')

    # Handle file upload if present
    if 'avatar_file' in request.files:
        file = request.files['avatar_file']
        if file and file.filename:
            ext = file.filename.rsplit('.', 1)[-1].lower()
            if ext in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
                filename = f"avatar_{session['user_id']}_{int(os.times().elapsed*1000)}.{ext}"
                upload_folder = current_app.config['UPLOAD_FOLDER']
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                profile_picture = f"/static/uploads/{filename}"

    updated_user = update_user_profile(
        user_id=session['user_id'],
        name=name,
        bio=bio,
        profile_picture=profile_picture,
        custom_status=custom_status
    )
    
    if name:
        session['name'] = updated_user['name']
        
    return jsonify({'success': True, 'user': updated_user, 'message': 'Profile updated successfully.'})

@profile_bp.route('/api/profile/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json() or {}
    current_pass = data.get('current_password', '')
    new_pass = data.get('new_password', '')
    confirm_pass = data.get('confirm_password', '')

    if not current_pass or not new_pass:
        return jsonify({'success': False, 'error': 'All password fields are required.'}), 400

    if len(new_pass) < 6:
        return jsonify({'success': False, 'error': 'New password must be at least 6 characters long.'}), 400

    if new_pass != confirm_pass:
        return jsonify({'success': False, 'error': 'New passwords do not match.'}), 400

    # Verify current password
    db = get_db()
    user_row = db.execute("SELECT password_hash FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    if not user_row or not check_password_hash(user_row['password_hash'], current_pass):
        return jsonify({'success': False, 'error': 'Incorrect current password.'}), 400

    update_user_password(session['user_id'], new_pass)
    return jsonify({'success': True, 'message': 'Password changed successfully.'})

@profile_bp.route('/api/settings/update', methods=['POST'])
@login_required
def update_settings():
    data = request.get_json() or {}
    
    theme = data.get('theme_preference')
    sound = data.get('sound_notifications')
    desktop = data.get('desktop_notifications')
    privacy_last_seen = data.get('privacy_last_seen')
    privacy_read_receipts = data.get('privacy_read_receipts')
    
    updated_user = update_user_settings(
        user_id=session['user_id'],
        theme_preference=theme,
        sound_notifications=sound,
        desktop_notifications=desktop,
        privacy_last_seen=privacy_last_seen,
        privacy_read_receipts=privacy_read_receipts
    )
    
    return jsonify({'success': True, 'user': updated_user, 'message': 'Settings saved successfully.'})

@profile_bp.route('/api/users/<int:user_id>/block', methods=['POST'])
@login_required
def block_user_toggle(user_id):
    is_blocked = toggle_block_user(session['user_id'], user_id)
    action_text = "blocked" if is_blocked else "unblocked"
    return jsonify({'success': True, 'is_blocked': is_blocked, 'message': f'User {action_text} successfully.'})
