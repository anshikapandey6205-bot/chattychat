/**
 * Connectly Authentication Script
 */

function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const icon = btn.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        if (icon) {
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        }
    } else {
        input.type = 'password';
        if (icon) {
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    }
}

function selectPresetAvatar(element, avatarUrl) {
    document.querySelectorAll('.avatar-preset-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
    
    const hiddenInput = document.getElementById('avatar_preset');
    if (hiddenInput) hiddenInput.value = avatarUrl;
    
    // Clear custom file input if preset selected
    const fileInput = document.getElementById('profile_picture_file');
    if (fileInput) fileInput.value = '';
    const fileText = document.getElementById('custom-avatar-name');
    if (fileText) fileText.innerText = '';
}

function handleCustomAvatarUpload(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const fileText = document.getElementById('custom-avatar-name');
        if (fileText) fileText.innerText = `Selected: ${file.name}`;
        
        // Remove active class from presets
        document.querySelectorAll('.avatar-preset-item').forEach(el => el.classList.remove('active'));
    }
}

function fillDemoCredentials(username, password) {
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    
    if (usernameInput && passwordInput) {
        usernameInput.value = username;
        passwordInput.value = password;
        showToast('info', `Demo credentials filled for ${username}`);
    }
}

function validateRegisterForm(e) {
    const pass = document.getElementById('reg-password');
    const confirm = document.getElementById('confirm_password');
    
    if (pass && confirm && pass.value !== confirm.value) {
        e.preventDefault();
        showToast('error', 'Passwords do not match. Please verify.');
        confirm.focus();
        return false;
    }
    return true;
}

// Forgot Password Modal
function openForgotPasswordModal() {
    const modal = document.getElementById('forgot-modal');
    if (modal) modal.classList.remove('hidden');
}

function closeForgotPasswordModal() {
    const modal = document.getElementById('forgot-modal');
    if (modal) modal.classList.add('hidden');
}

async function submitForgotPassword() {
    const emailInput = document.getElementById('forgot-email');
    const email = emailInput ? emailInput.value.trim() : '';

    if (!email) {
        showToast('error', 'Please enter your registered email address.');
        return;
    }

    try {
        const res = await fetch('/api/auth/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (data.success) {
            showToast('success', data.message);
            closeForgotPasswordModal();
        } else {
            showToast('error', data.error || 'Failed to send reset email.');
        }
    } catch (err) {
        showToast('error', 'An error occurred while contacting the server.');
    }
}
