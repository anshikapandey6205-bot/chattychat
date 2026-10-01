/**
 * Connectly Profile & Settings Controller
 */

function selectProfileAvatarPreset(element, avatarUrl) {
    document.querySelectorAll('.avatar-preset-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');

    const input = document.getElementById('edit-avatar-url');
    if (input) input.value = avatarUrl;

    const displayAvatar = document.getElementById('profile-display-avatar');
    if (displayAvatar) displayAvatar.src = avatarUrl;

    // Reset file input
    const fileInput = document.getElementById('edit-avatar-file');
    if (fileInput) fileInput.value = '';
    const nameEl = document.getElementById('edit-avatar-filename');
    if (nameEl) nameEl.innerText = '';
}

function previewUploadAvatar(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const nameEl = document.getElementById('edit-avatar-filename');
        if (nameEl) nameEl.innerText = `Selected: ${file.name}`;

        const reader = new FileReader();
        reader.onload = function(e) {
            const displayAvatar = document.getElementById('profile-display-avatar');
            if (displayAvatar) displayAvatar.src = e.target.result;
        };
        reader.readAsDataURL(file);

        document.querySelectorAll('.avatar-preset-item').forEach(el => el.classList.remove('active'));
    }
}

async function handleProfileUpdate(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-save-profile');
    if (btn) btn.disabled = true;

    const name = document.getElementById('edit-name').value.trim();
    const bio = document.getElementById('edit-bio').value.trim();
    const customStatus = document.getElementById('edit-custom-status').value.trim();
    const avatarUrl = document.getElementById('edit-avatar-url').value;
    const fileInput = document.getElementById('edit-avatar-file');

    const formData = new FormData();
    formData.append('name', name);
    formData.append('bio', bio);
    formData.append('custom_status', customStatus);
    formData.append('profile_picture', avatarUrl);

    if (fileInput && fileInput.files && fileInput.files[0]) {
        formData.append('avatar_file', fileInput.files[0]);
    }

    try {
        const res = await fetch('/api/profile/update', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            showToast('success', data.message || 'Profile updated successfully!');
            const displayName = document.getElementById('profile-display-name');
            const displayBio = document.getElementById('profile-display-bio');
            if (displayName) displayName.innerText = data.user.name;
            if (displayBio) displayBio.innerText = `"${data.user.bio}"`;
        } else {
            showToast('error', data.error || 'Failed to update profile.');
        }
    } catch (err) {
        showToast('error', 'Profile update failed.');
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function handleChangePassword(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-change-password');
    const currentPass = document.getElementById('current-password').value;
    const newPass = document.getElementById('new-password').value;
    const confirmPass = document.getElementById('confirm-new-password').value;

    if (newPass !== confirmPass) {
        showToast('error', 'New passwords do not match.');
        return;
    }

    if (btn) btn.disabled = true;

    try {
        const res = await fetch('/api/profile/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                current_password: currentPass,
                new_password: newPass,
                confirm_password: confirmPass
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast('success', data.message);
            document.getElementById('change-password-form').reset();
        } else {
            showToast('error', data.error || 'Password change failed.');
        }
    } catch (err) {
        showToast('error', 'Failed to update password.');
    } finally {
        if (btn) btn.disabled = false;
    }
}

/* ==========================================================================
   Settings Tab Navigation & Preferences
   ========================================================================== */
function switchSettingsSection(sectionId, btn) {
    document.querySelectorAll('.settings-nav-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');

    document.querySelectorAll('.settings-section').forEach(sec => sec.classList.add('hidden'));
    const target = document.getElementById(`section-${sectionId}`);
    if (target) target.classList.remove('hidden');
}

function setAppTheme(theme, card) {
    document.querySelectorAll('.theme-choice-card').forEach(c => c.classList.remove('active'));
    if (card) card.classList.add('active');

    setTheme(theme);

    // Save to backend
    fetch('/api/settings/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme_preference: theme })
    }).then(() => {
        showToast('success', `Theme updated to ${theme.toUpperCase()}`);
    });
}

function testNotificationSound() {
    playNotificationSound();
    showToast('info', 'Testing notification sound chime 🔔');
}

function requestDesktopPermission() {
    if (!('Notification' in window)) {
        showToast('warning', 'This browser does not support desktop notifications.');
        return;
    }
    Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
            showToast('success', 'Desktop notifications permitted!');
            new Notification('Connectly', {
                body: 'Notifications are enabled for Connectly.',
                icon: '/static/images/avatars/avatar-1.svg'
            });
            saveNotificationSettings();
        } else {
            showToast('warning', 'Desktop notifications permission denied.');
        }
    });
}

function saveNotificationSettings() {
    const sound = document.getElementById('setting-sound')?.checked;
    const desktop = document.getElementById('setting-desktop')?.checked;

    fetch('/api/settings/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            sound_notifications: sound,
            desktop_notifications: desktop
        })
    }).then(() => {
        showToast('success', 'Notification preferences saved.');
    });
}

function savePrivacySettings() {
    const lastSeen = document.getElementById('setting-last-seen')?.value;
    const readReceipts = document.getElementById('setting-read-receipts')?.checked;

    fetch('/api/settings/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            privacy_last_seen: lastSeen,
            privacy_read_receipts: readReceipts
        })
    }).then(() => {
        showToast('success', 'Privacy preferences updated.');
    });
}

function logoutAllDevices() {
    if (confirm('Are you sure you want to invalidate all sessions and log out?')) {
        window.location.href = '/logout';
    }
}
