/**
 * Connectly Theme Manager
 */

document.addEventListener('DOMContentLoaded', () => {
    initThemeButtons();
});

function initThemeButtons() {
    const toggleBtns = document.querySelectorAll('.theme-toggle');
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
        });
    });
}

function setTheme(theme) {
    if (theme === 'system') {
        const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    } else {
        document.documentElement.setAttribute('data-theme', theme);
    }
    
    localStorage.setItem('connectly_theme', theme);
    updateThemeToggleIcons(theme);

    // If on settings page, update card active class
    const themeCards = document.querySelectorAll('.theme-choice-card');
    themeCards.forEach(card => {
        const label = card.innerText.toLowerCase();
        if (label.includes(theme)) {
            card.classList.add('active');
        } else {
            card.classList.remove('active');
        }
    });
}

function updateThemeToggleIcons(theme) {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const toggleBtns = document.querySelectorAll('.theme-toggle i');
    toggleBtns.forEach(icon => {
        if (currentTheme === 'dark') {
            icon.className = 'fa-solid fa-sun';
        } else {
            icon.className = 'fa-solid fa-moon';
        }
    });
}
