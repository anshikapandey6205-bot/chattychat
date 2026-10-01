/**
 * Connectly Global Search Controller
 */

let searchDebounceTimeout = null;
let currentSearchResults = {
    users: [],
    conversations: [],
    messages: []
};
let activeSearchTab = 'all';

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('global-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            const clearBtn = document.getElementById('search-clear-btn');
            if (clearBtn) clearBtn.classList.toggle('hidden', query.length === 0);

            clearTimeout(searchDebounceTimeout);
            if (!query) {
                hideSearchResults();
                return;
            }

            searchDebounceTimeout = setTimeout(() => {
                performGlobalSearch(query);
            }, 250);
        });
    }
});

async function performGlobalSearch(query) {
    const overlay = document.getElementById('search-results-overlay');
    const list = document.getElementById('search-results-list');
    if (!overlay || !list) return;

    overlay.classList.remove('hidden');
    list.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';

    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        if (data.success) {
            currentSearchResults = {
                users: data.users || [],
                conversations: data.conversations || [],
                messages: data.messages || []
            };
            renderSearchResults();
        }
    } catch (e) {
        list.innerHTML = '<p class="text-danger text-center p-3">Search failed.</p>';
    }
}

function switchSearchTab(tab, btn) {
    document.querySelectorAll('.search-tab').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    activeSearchTab = tab;
    renderSearchResults();
}

function renderSearchResults() {
    const list = document.getElementById('search-results-list');
    if (!list) return;

    let html = '';
    const { users, conversations, messages } = currentSearchResults;

    const totalResults = users.length + conversations.length + messages.length;
    if (totalResults === 0) {
        list.innerHTML = '<p class="empty-media-text p-4">No matching results found.</p>';
        return;
    }

    // 1. Users Section
    if ((activeSearchTab === 'all' || activeSearchTab === 'users') && users.length > 0) {
        html += `<div class="info-section-title">People (${users.length})</div>`;
        users.forEach(u => {
            html += `
                <div class="search-result-item" onclick="onSearchResultSelectUser(${u.id})">
                    <img src="${u.profile_picture || '/static/images/avatars/avatar-1.svg'}" alt="${escapeHtml(u.name)}" class="search-result-avatar">
                    <div class="search-result-info">
                        <div class="search-result-title">${escapeHtml(u.name)}</div>
                        <div class="search-result-sub">@${escapeHtml(u.username)} &bull; ${escapeHtml(u.bio || '')}</div>
                    </div>
                    <i class="fa-solid fa-comment-dots text-accent"></i>
                </div>
            `;
        });
    }

    // 2. Conversations Section
    if ((activeSearchTab === 'all' || activeSearchTab === 'conversations') && conversations.length > 0) {
        html += `<div class="info-section-title mt-2">Conversations (${conversations.length})</div>`;
        conversations.forEach(c => {
            html += `
                <div class="search-result-item" onclick="onSearchResultSelectConv(${c.id})">
                    <img src="${c.display_avatar}" alt="${escapeHtml(c.display_name)}" class="search-result-avatar">
                    <div class="search-result-info">
                        <div class="search-result-title">${escapeHtml(c.display_name)}</div>
                        <div class="search-result-sub">${c.last_message ? escapeHtml(c.last_message.message) : 'No messages'}</div>
                    </div>
                    <i class="fa-solid fa-arrow-right text-muted"></i>
                </div>
            `;
        });
    }

    // 3. Messages Section
    if ((activeSearchTab === 'all' || activeSearchTab === 'messages') && messages.length > 0) {
        html += `<div class="info-section-title mt-2">Messages (${messages.length})</div>`;
        messages.forEach(m => {
            html += `
                <div class="search-result-item" onclick="onSearchResultSelectMessage(${m.conversation_id}, ${m.id})">
                    <img src="${m.sender_avatar || '/static/images/avatars/avatar-1.svg'}" alt="${escapeHtml(m.sender_name)}" class="search-result-avatar">
                    <div class="search-result-info">
                        <div class="search-result-title">${escapeHtml(m.sender_name)} <span class="text-muted font-normal">in ${escapeHtml(m.conversation_name || 'Chat')}</span></div>
                        <div class="search-result-sub">${escapeHtml(m.message)}</div>
                    </div>
                    <span class="text-muted font-mono text-xs">${formatTime(m.created_at)}</span>
                </div>
            `;
        });
    }

    list.innerHTML = html;
}

function clearGlobalSearch() {
    const input = document.getElementById('global-search-input');
    if (input) input.value = '';
    const clearBtn = document.getElementById('search-clear-btn');
    if (clearBtn) clearBtn.classList.add('hidden');
    hideSearchResults();
}

function hideSearchResults() {
    const overlay = document.getElementById('search-results-overlay');
    if (overlay) overlay.classList.add('hidden');
}

async function onSearchResultSelectUser(userId) {
    hideSearchResults();
    startDirectChatWith(userId);
}

function onSearchResultSelectConv(convId) {
    hideSearchResults();
    selectConversation(convId);
}

async function onSearchResultSelectMessage(convId, messageId) {
    hideSearchResults();
    await selectConversation(convId);
    setTimeout(() => {
        scrollToMessage(messageId);
    }, 400);
}
