/**
 * Connectly Real-Time Chat Engine
 */

let socket = null;
let currentUserId = null;
let activeConversationId = null;
let activeConversationMeta = null;

let replyingToMessage = null;
let editingMessage = null;
let queuedAttachments = [];

let typingTimeout = null;
let isCurrentlyTyping = false;

let inChatSearchMatches = [];
let currentSearchMatchIndex = -1;

let callTimerInterval = null;
let callDurationSeconds = 0;

// Context Menu State
let activeContextMenuMessage = null;

document.addEventListener('DOMContentLoaded', () => {
    const appEl = document.getElementById('chat-app');
    if (!appEl) return;

    currentUserId = parseInt(appEl.dataset.userId, 10);
    const initialConvId = appEl.dataset.activeConv;

    initSocketConnection();
    initComposerEvents();
    initEmojiPicker();
    initGlobalClickDismissal();

    if (initialConvId && initialConvId !== '') {
        selectConversation(parseInt(initialConvId, 10));
    }
});

/* ==========================================================================
   Socket.IO Connection & Events
   ========================================================================== */
function initSocketConnection() {
    socket = io({
        reconnection: true,
        reconnectionAttempts: 10,
        reconnectionDelay: 1000
    });

    socket.on('connect', () => {
        console.log('⚡ Socket connected:', socket.id);
        if (activeConversationId) {
            socket.emit('join_conversation', { conversation_id: activeConversationId });
        }
    });

    socket.on('new_message', (data) => {
        const { conversation_id, message } = data;
        if (activeConversationId === conversation_id) {
            appendMessageToFlow(message);
            scrollToBottomSmooth();
            // Send read receipt if received from another user
            if (message.sender_id !== currentUserId) {
                socket.emit('mark_read', { conversation_id });
                playNotificationSound();
            }
        }
    });

    socket.on('message_edited', (data) => {
        const { conversation_id, message } = data;
        if (activeConversationId === conversation_id) {
            updateMessageInDOM(message);
        }
    });

    socket.on('message_deleted', (data) => {
        const { conversation_id, message_id, deleted_message } = data;
        if (activeConversationId === conversation_id) {
            updateMessageInDOM(deleted_message);
        }
    });

    socket.on('message_reaction_updated', (data) => {
        const { conversation_id, data: rxData } = data;
        if (activeConversationId === conversation_id) {
            renderMessageReactions(rxData.message_id, rxData.reactions);
        }
    });

    socket.on('user_typing', (data) => {
        const { conversation_id, name, is_typing } = data;
        if (activeConversationId === conversation_id) {
            updateTypingIndicator(name, is_typing);
        }
    });

    socket.on('conversation_updated', (data) => {
        const { conversation_id, last_message, unread_increment } = data;
        updateConversationListItem(conversation_id, last_message, unread_increment);
    });

    socket.on('messages_read', (data) => {
        const { conversation_id } = data;
        if (activeConversationId === conversation_id) {
            markAllSentMessagesReadInDOM();
        }
    });

    socket.on('user_status_change', (data) => {
        const { user_id, status } = data;
        updateUserStatusInDOM(user_id, status);
    });

    socket.on('incoming_call', (data) => {
        handleIncomingCall(data.caller, data.call_type);
    });

    socket.on('call_ended', () => {
        endCallUI();
    });
}

/* ==========================================================================
   Conversation Selection & Loading
   ========================================================================== */
async function selectConversation(convId) {
    if (activeConversationId && activeConversationId !== convId) {
        socket.emit('leave_conversation', { conversation_id: activeConversationId });
    }

    activeConversationId = convId;
    cancelReply();
    cancelEdit();
    clearInChatSearch();

    // Visual indicators
    document.querySelectorAll('.conversation-item').forEach(el => {
        if (parseInt(el.dataset.convId, 10) === convId) {
            el.classList.add('active');
            // Clear unread badge
            const unreadBadge = el.querySelector('.unread-badge');
            if (unreadBadge) {
                unreadBadge.classList.add('hidden');
                unreadBadge.innerText = '0';
            }
        } else {
            el.classList.remove('active');
        }
    });

    // Mobile drawer switch
    const chatApp = document.getElementById('chat-app');
    if (chatApp) chatApp.classList.add('in-conversation');

    // Show active view, hide empty state
    document.getElementById('chat-placeholder').classList.add('hidden');
    document.getElementById('active-chat-container').classList.remove('hidden');

    // Join socket room
    socket.emit('join_conversation', { conversation_id: convId });

    // Fetch conversation metadata & messages in parallel
    try {
        const [metaRes, msgRes] = await Promise.all([
            fetch(`/api/conversations/${convId}`),
            fetch(`/api/conversations/${convId}/messages`)
        ]);

        const metaData = await metaRes.json();
        const msgData = await msgRes.json();

        if (metaData.success) {
            activeConversationMeta = metaData.conversation;
            renderChatHeader(activeConversationMeta);
            renderRightInfoPanel(activeConversationMeta);
        }

        if (msgData.success) {
            renderMessageHistory(msgData.messages);
            scrollToBottom();
        }
    } catch (err) {
        showToast('error', 'Failed to load conversation messages.');
    }
}

function renderChatHeader(conv) {
    const avatar = document.getElementById('chat-header-avatar');
    const title = document.getElementById('chat-header-title');
    const subtitle = document.getElementById('chat-header-subtitle');
    const statusDot = document.getElementById('chat-header-status-dot');

    if (avatar) avatar.src = conv.display_avatar;
    if (title) title.innerText = conv.display_name;

    if (!conv.is_group && conv.partner) {
        if (statusDot) {
            statusDot.className = `status-indicator ${conv.partner.status || 'offline'}`;
            statusDot.classList.remove('hidden');
        }
        if (subtitle) {
            subtitle.innerText = conv.partner.status === 'online' ? '🟢 Online now' : `Last seen recently`;
        }
    } else {
        if (statusDot) statusDot.classList.add('hidden');
        if (subtitle) {
            const memberCount = conv.members ? conv.members.length : 0;
            subtitle.innerText = `${memberCount} members`;
        }
    }
}

function renderMessageHistory(messages) {
    const flow = document.getElementById('messages-flow');
    if (!flow) return;
    flow.innerHTML = '';

    let lastDate = null;

    messages.forEach(msg => {
        const msgDate = (msg.created_at || '').substring(0, 10);
        if (msgDate && msgDate !== lastDate) {
            flow.appendChild(createDateSeparator(msgDate));
            lastDate = msgDate;
        }
        flow.appendChild(buildMessageRowElement(msg));
    });
}

function createDateSeparator(dateStr) {
    const div = document.createElement('div');
    div.className = 'date-separator';
    const today = new Date().toISOString().substring(0, 10);
    const label = (dateStr === today) ? 'Today' : dateStr;
    div.innerHTML = `<span>${label}</span>`;
    return div;
}

function buildMessageRowElement(msg) {
    const isSent = msg.sender_id === currentUserId;
    const isSystem = msg.message_type === 'system';

    if (isSystem) {
        const sysDiv = document.createElement('div');
        sysDiv.className = 'message-system';
        sysDiv.innerText = msg.message;
        return sysDiv;
    }

    const row = document.createElement('div');
    row.className = `message-row ${isSent ? 'sent' : 'received'}`;
    row.id = `msg-${msg.id}`;
    row.dataset.msgId = msg.id;

    // Context menu trigger
    row.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        openContextMenu(e, msg);
    });

    let html = '';

    // If received and in group, show avatar
    if (!isSent) {
        html += `<img src="${msg.sender_avatar || '/static/images/avatars/avatar-1.svg'}" alt="${escapeHtml(msg.sender_name)}" class="message-sender-avatar">`;
    }

    html += `<div class="message-bubble-wrapper">`;

    // Group sender name
    if (!isSent && activeConversationMeta && activeConversationMeta.is_group) {
        html += `<span class="message-sender-name">${escapeHtml(msg.sender_name)}</span>`;
    }

    html += `<div class="message-bubble">`;

    // Quoted reply
    if (msg.reply_info) {
        html += `
            <div class="message-reply-quote" onclick="scrollToMessage(${msg.reply_info.id})">
                <span class="quote-sender">${escapeHtml(msg.reply_info.sender_name || 'User')}</span>
                <span class="quote-text">${escapeHtml(msg.reply_info.message || 'Media attachment')}</span>
            </div>
        `;
    }

    // Message text
    if (msg.is_deleted) {
        html += `<em class="text-muted"><i class="fa-solid fa-ban"></i> This message was deleted</em>`;
    } else {
        html += `<div class="msg-text-content">${formatMessageText(msg.message)}</div>`;
    }

    // Attachments
    if (msg.attachments && msg.attachments.length > 0 && !msg.is_deleted) {
        html += `<div class="message-attachments">`;
        msg.attachments.forEach(att => {
            if (att.file_type && att.file_type.startsWith('image/')) {
                html += `<img src="${att.filepath}" alt="${escapeHtml(att.original_name)}" class="msg-image-thumb" onclick="openLightbox('${att.filepath}')">`;
            } else {
                html += `
                    <a href="${att.filepath}" download="${escapeHtml(att.original_name)}" class="msg-file-card">
                        <i class="fa-solid fa-file-arrow-down msg-file-icon text-accent"></i>
                        <div class="msg-file-details">
                            <span class="msg-file-name">${escapeHtml(att.original_name)}</span>
                            <span class="msg-file-size">${formatBytes(att.file_size)}</span>
                        </div>
                    </a>
                `;
            }
        });
        html += `</div>`;
    }

    // Meta (Timestamp, Checks, Edited tag)
    const timeStr = formatTime(msg.created_at);
    html += `
        <div class="message-meta">
            ${msg.edited_at ? '<span class="edited-tag">(edited)</span>' : ''}
            <span class="msg-time">${timeStr}</span>
            ${isSent ? `<span class="read-check ${msg.read_status ? 'read' : ''}"><i class="fa-solid fa-check-double"></i></span>` : ''}
        </div>
    `;

    html += `</div>`; // .message-bubble

    // Reactions container
    html += `<div class="message-reactions-row" id="reactions-for-${msg.id}">`;
    html += renderReactionsHTML(msg.id, msg.reactions || []);
    html += `</div>`;

    html += `</div>`; // .message-bubble-wrapper

    row.innerHTML = html;
    return row;
}

function appendMessageToFlow(msg) {
    const flow = document.getElementById('messages-flow');
    if (!flow) return;
    flow.appendChild(buildMessageRowElement(msg));
}

function updateMessageInDOM(msg) {
    const existing = document.getElementById(`msg-${msg.id}`);
    if (existing) {
        const replacement = buildMessageRowElement(msg);
        existing.parentNode.replaceChild(replacement, existing);
    }
}

function markAllSentMessagesReadInDOM() {
    const checkmarks = document.querySelectorAll('.message-row.sent .read-check');
    checkmarks.forEach(chk => chk.classList.add('read'));
}

/* ==========================================================================
   Composer, Sending & Attachments
   ========================================================================== */
function initComposerEvents() {
    const textarea = document.getElementById('message-input');
    if (textarea) {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });

        // Drag & drop file uploads on chat container
        const chatContainer = document.getElementById('active-chat-container');
        if (chatContainer) {
            chatContainer.addEventListener('dragover', (e) => {
                e.preventDefault();
                chatContainer.classList.add('dragover');
            });
            chatContainer.addEventListener('dragleave', () => {
                chatContainer.classList.remove('dragover');
            });
            chatContainer.addEventListener('drop', (e) => {
                e.preventDefault();
                chatContainer.classList.remove('dragover');
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    uploadAndQueueFiles(e.dataTransfer.files);
                }
            });
        }
    }
}

function handleMessageKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function handleTypingEvent(textarea) {
    if (!socket || !activeConversationId) return;

    if (!isCurrentlyTyping) {
        isCurrentlyTyping = true;
        socket.emit('typing_start', { conversation_id: activeConversationId });
    }

    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
        isCurrentlyTyping = false;
        socket.emit('typing_stop', { conversation_id: activeConversationId });
    }, 1500);
}

function updateTypingIndicator(username, isTyping) {
    const bar = document.getElementById('typing-indicator-bar');
    const text = document.getElementById('typing-text');
    if (!bar || !text) return;

    if (isTyping) {
        text.innerText = `${username} is typing`;
        bar.classList.remove('hidden');
    } else {
        bar.classList.add('hidden');
    }
}

async function sendMessage() {
    const textarea = document.getElementById('message-input');
    if (!textarea || !activeConversationId) return;

    const messageText = textarea.value.trim();

    // If in Edit Mode, dispatch message edit
    if (editingMessage) {
        if (!messageText) {
            showToast('error', 'Message cannot be empty.');
            return;
        }
        socket.emit('edit_message', {
            message_id: editingMessage.id,
            conversation_id: activeConversationId,
            new_content: messageText
        });
        cancelEdit();
        textarea.value = '';
        textarea.style.height = 'auto';
        return;
    }

    if (!messageText && queuedAttachments.length === 0) {
        return;
    }

    // Prepare payload
    const payload = {
        conversation_id: activeConversationId,
        message: messageText,
        message_type: queuedAttachments.length > 0 ? (queuedAttachments[0].file_type.startsWith('image/') ? 'image' : 'file') : 'text',
        reply_to: replyingToMessage ? replyingToMessage.id : null,
        attachments: queuedAttachments
    };

    socket.emit('send_message', payload);

    // Reset Composer
    textarea.value = '';
    textarea.style.height = 'auto';
    cancelReply();
    clearQueuedAttachments();
    textarea.focus();
}

/* ==========================================================================
   Attachments & Upload
   ========================================================================== */
function toggleAttachmentMenu(e) {
    e.stopPropagation();
    const menu = document.getElementById('attachment-dropdown');
    if (menu) menu.classList.toggle('hidden');
}

function handleFileSelection(e, type) {
    const files = e.target.files;
    if (files && files.length > 0) {
        uploadAndQueueFiles(files);
    }
    const menu = document.getElementById('attachment-dropdown');
    if (menu) menu.classList.add('hidden');
}

async function uploadAndQueueFiles(files) {
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        showToast('info', `Uploading ${file.name}...`);
        
        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.success) {
                queuedAttachments.push(data.attachment);
                renderQueuedAttachments();
                showToast('success', `${file.name} uploaded!`);
            } else {
                showToast('error', data.error || 'Upload failed.');
            }
        } catch (err) {
            showToast('error', 'File upload failed.');
        }
    }
}

function renderQueuedAttachments() {
    const bar = document.getElementById('composer-attachment-bar');
    if (!bar) return;

    if (queuedAttachments.length === 0) {
        bar.classList.add('hidden');
        bar.innerHTML = '';
        return;
    }

    bar.classList.remove('hidden');
    bar.innerHTML = '';

    queuedAttachments.forEach((att, idx) => {
        const item = document.createElement('div');
        item.className = 'queued-file-item';
        
        if (att.file_type.startsWith('image/')) {
            item.innerHTML = `
                <img src="${att.filepath}" alt="${escapeHtml(att.original_name)}">
                <span>${escapeHtml(att.original_name)}</span>
                <i class="fa-solid fa-xmark btn-remove-queued" onclick="removeQueuedAttachment(${idx})"></i>
            `;
        } else {
            item.innerHTML = `
                <i class="fa-solid fa-file text-accent"></i>
                <span>${escapeHtml(att.original_name)}</span>
                <i class="fa-solid fa-xmark btn-remove-queued" onclick="removeQueuedAttachment(${idx})"></i>
            `;
        }
        bar.appendChild(item);
    });
}

function removeQueuedAttachment(idx) {
    queuedAttachments.splice(idx, 1);
    renderQueuedAttachments();
}

function clearQueuedAttachments() {
    queuedAttachments = [];
    renderQueuedAttachments();
}

/* ==========================================================================
   Emoji Reactions & Picker
   ========================================================================== */
function initEmojiPicker() {
    renderEmojiGrid('popular');
}

const EMOJI_DATABASE = {
    popular: ['❤️', '👍', '😂', '🔥', '🎉', '🚀', '👏', '😍', '✨', '🙌', '💯', '😎', '💡', '🥳'],
    smileys: ['😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '😉', '😊', '😇', '🥰', '😍', '🤩', '😘', '😋', '😜', '🤪', '🤫', '🤔', '🤐', '😐', '😑', '😶', '😏', '😒', '🙄', '😬', '😮‍💨', '🤥', '😌', '😔', '😪', '🤤', '😴', '😷', '🤒', '🤕', '🤢', '🤮', '🤧', '🥵', '🥶', '🥴', '😵', '🤯', '🤠', '🥳', '🥸', '😎', '🤓', '🧐'],
    gestures: ['👋', '🤚', '🖐️', '✋', '🖖', '👌', '🤌', '🤏', '✌️', '🤞', '🫰', '🤟', '🤘', '🤙', '👈', '👉', '👆', '🖕', '👇', '☝️', '👍', '👎', '✊', '👊', '🤛', '🤜', '👏', '🙌', '👐', '🤲', '🤝', '🙏', '✍️', '💅', '🤳', '💪'],
    hearts: ['❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❤️‍🔥', '❤️‍🩹', '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '💝'],
    objects: ['🎉', '✨', '🔥', '🚀', '💡', '⭐', '🌟', '⚡', '☕', '💻', '📱', '🕹️', '🏆', '🎯', '🎨', '🍿', '🎈', '🎁']
};

function toggleEmojiPicker(e) {
    e.stopPropagation();
    const picker = document.getElementById('emoji-picker-container');
    if (picker) picker.classList.toggle('hidden');
}

function switchEmojiCategory(category, btn) {
    document.querySelectorAll('.emoji-cat-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    renderEmojiGrid(category);
}

function renderEmojiGrid(category) {
    const grid = document.getElementById('emoji-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const list = EMOJI_DATABASE[category] || EMOJI_DATABASE.popular;
    list.forEach(emoji => {
        const item = document.createElement('span');
        item.className = 'emoji-item';
        item.innerText = emoji;
        item.onclick = () => insertEmojiToComposer(emoji);
        grid.appendChild(item);
    });
}

function insertEmojiToComposer(emoji) {
    const textarea = document.getElementById('message-input');
    if (textarea) {
        textarea.value += emoji;
        textarea.focus();
    }
}

function filterEmojis(query) {
    const q = query.trim();
    if (!q) {
        renderEmojiGrid('popular');
        return;
    }
    const grid = document.getElementById('emoji-grid');
    if (!grid) return;
    grid.innerHTML = '';

    let allEmojis = [];
    Object.values(EMOJI_DATABASE).forEach(arr => allEmojis.push(...arr));
    allEmojis = [...new Set(allEmojis)];

    allEmojis.forEach(emoji => {
        const item = document.createElement('span');
        item.className = 'emoji-item';
        item.innerText = emoji;
        item.onclick = () => insertEmojiToComposer(emoji);
        grid.appendChild(item);
    });
}

function renderReactionsHTML(msgId, reactions) {
    if (!reactions || reactions.length === 0) {
        return `<button class="btn-add-reaction" onclick="openReactionPicker(${msgId}, event)"><i class="fa-regular fa-face-smile"></i></button>`;
    }

    let html = '';
    reactions.forEach(r => {
        html += `
            <span class="reaction-badge ${r.has_reacted ? 'reacted' : ''}" title="${escapeHtml(r.users.join(', '))}" onclick="toggleReactionOnMessage(${msgId}, '${r.emoji}')">
                <span>${r.emoji}</span>
                <span>${r.count}</span>
            </span>
        `;
    });

    html += `<button class="btn-add-reaction" onclick="openReactionPicker(${msgId}, event)"><i class="fa-regular fa-face-smile"></i></button>`;
    return html;
}

function renderMessageReactions(msgId, reactions) {
    const container = document.getElementById(`reactions-for-${msgId}`);
    if (container) {
        container.innerHTML = renderReactionsHTML(msgId, reactions);
    }
}

function toggleReactionOnMessage(msgId, emoji) {
    if (!socket || !activeConversationId) return;
    socket.emit('react_message', {
        message_id: msgId,
        conversation_id: activeConversationId,
        reaction: emoji
    });
}

/* ==========================================================================
   Context Menu Actions
   ========================================================================== */
function openContextMenu(e, msg) {
    activeContextMenuMessage = msg;
    const menu = document.getElementById('message-context-menu');
    if (!menu) return;

    const isOwn = msg.sender_id === currentUserId;
    const editBtn = document.getElementById('ctx-btn-edit');
    const deleteBtn = document.getElementById('ctx-btn-delete');

    if (editBtn) editBtn.classList.toggle('hidden', !isOwn || msg.is_deleted);
    if (deleteBtn) deleteBtn.classList.toggle('hidden', !isOwn || msg.is_deleted);

    menu.style.top = `${Math.min(e.clientY, window.innerHeight - 240)}px`;
    menu.style.left = `${Math.min(e.clientX, window.innerWidth - 240)}px`;
    menu.classList.remove('hidden');
}

function applyQuickReaction(emoji) {
    if (activeContextMenuMessage) {
        toggleReactionOnMessage(activeContextMenuMessage.id, emoji);
    }
    closeContextMenu();
}

function triggerReplyFromContext() {
    if (!activeContextMenuMessage) return;
    startReply(activeContextMenuMessage);
    closeContextMenu();
}

function startReply(msg) {
    replyingToMessage = msg;
    cancelEdit();

    const banner = document.getElementById('reply-context-banner');
    const nameEl = document.getElementById('reply-sender-name');
    const textEl = document.getElementById('reply-message-text');

    if (banner && nameEl && textEl) {
        nameEl.innerText = `Replying to ${msg.sender_name || 'User'}`;
        textEl.innerText = msg.message || 'Media file';
        banner.classList.remove('hidden');
        document.getElementById('message-input').focus();
    }
}

function cancelReply() {
    replyingToMessage = null;
    const banner = document.getElementById('reply-context-banner');
    if (banner) banner.classList.add('hidden');
}

function triggerEditFromContext() {
    if (!activeContextMenuMessage) return;
    startEdit(activeContextMenuMessage);
    closeContextMenu();
}

function startEdit(msg) {
    editingMessage = msg;
    cancelReply();

    const banner = document.getElementById('edit-context-banner');
    const origText = document.getElementById('edit-original-text');
    const input = document.getElementById('message-input');

    if (banner && origText && input) {
        origText.innerText = msg.message;
        banner.classList.remove('hidden');
        input.value = msg.message;
        input.focus();
    }
}

function cancelEdit() {
    editingMessage = null;
    const banner = document.getElementById('edit-context-banner');
    if (banner) banner.classList.add('hidden');
    const input = document.getElementById('message-input');
    if (input && input.value) input.value = '';
}

function triggerCopyTextFromContext() {
    if (activeContextMenuMessage && activeContextMenuMessage.message) {
        navigator.clipboard.writeText(activeContextMenuMessage.message);
        showToast('success', 'Message copied to clipboard!');
    }
    closeContextMenu();
}

function triggerDeleteFromContext() {
    if (!activeContextMenuMessage || !socket || !activeConversationId) return;
    if (confirm('Are you sure you want to delete this message?')) {
        socket.emit('delete_message', {
            message_id: activeContextMenuMessage.id,
            conversation_id: activeConversationId
        });
    }
    closeContextMenu();
}

function triggerForwardFromContext() {
    if (!activeContextMenuMessage) return;
    openForwardModal();
    closeContextMenu();
}

function closeContextMenu() {
    const menu = document.getElementById('message-context-menu');
    if (menu) menu.classList.add('hidden');
}

/* ==========================================================================
   In-Chat Search
   ========================================================================== */
function toggleInChatSearch() {
    const bar = document.getElementById('in-chat-search-bar');
    if (!bar) return;
    bar.classList.toggle('hidden');
    if (!bar.classList.contains('hidden')) {
        const input = document.getElementById('in-chat-search-input');
        if (input) input.focus();
    } else {
        clearInChatSearch();
    }
}

function handleInChatSearch(query) {
    const q = query.trim().toLowerCase();
    inChatSearchMatches = [];
    currentSearchMatchIndex = -1;

    const allMsgNodes = document.querySelectorAll('.message-bubble .msg-text-content');
    allMsgNodes.forEach(node => {
        const originalText = node.innerText;
        if (!q) {
            node.innerHTML = escapeHtml(originalText);
            return;
        }
        if (originalText.toLowerCase().includes(q)) {
            inChatSearchMatches.push(node.closest('.message-row'));
            const regex = new RegExp(`(${escapeRegExp(q)})`, 'gi');
            node.innerHTML = originalText.replace(regex, '<mark class="search-match">$1</mark>');
        } else {
            node.innerHTML = escapeHtml(originalText);
        }
    });

    const countEl = document.getElementById('in-chat-search-count');
    if (countEl) {
        countEl.innerText = inChatSearchMatches.length > 0 ? `1 / ${inChatSearchMatches.length}` : '0 / 0';
    }

    if (inChatSearchMatches.length > 0) {
        currentSearchMatchIndex = 0;
        highlightCurrentSearchMatch();
    }
}

function navigateSearchMatch(direction) {
    if (inChatSearchMatches.length === 0) return;
    currentSearchMatchIndex = (currentSearchMatchIndex + direction + inChatSearchMatches.length) % inChatSearchMatches.length;
    highlightCurrentSearchMatch();
    const countEl = document.getElementById('in-chat-search-count');
    if (countEl) countEl.innerText = `${currentSearchMatchIndex + 1} / ${inChatSearchMatches.length}`;
}

function highlightCurrentSearchMatch() {
    if (currentSearchMatchIndex >= 0 && currentSearchMatchIndex < inChatSearchMatches.length) {
        const targetRow = inChatSearchMatches[currentSearchMatchIndex];
        targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function clearInChatSearch() {
    const input = document.getElementById('in-chat-search-input');
    if (input) input.value = '';
    handleInChatSearch('');
}

/* ==========================================================================
   Right Info Panel & Actions
   ========================================================================== */
function toggleRightInfoPanel() {
    const panel = document.getElementById('chat-right-panel');
    const layout = document.getElementById('chat-app');
    if (panel && layout) {
        panel.classList.toggle('hidden');
        layout.classList.toggle('right-panel-hidden', panel.classList.contains('hidden'));
    }
}

async function renderRightInfoPanel(conv) {
    const avatar = document.getElementById('info-panel-avatar');
    const name = document.getElementById('info-panel-name');
    const username = document.getElementById('info-panel-username');
    const bio = document.getElementById('info-panel-bio');
    const statusPill = document.getElementById('info-panel-status-badge');

    if (avatar) avatar.src = conv.display_avatar;
    if (title) name.innerText = conv.display_name;

    if (!conv.is_group && conv.partner) {
        if (username) username.innerText = `@${conv.partner.username}`;
        if (bio) bio.innerText = conv.partner.bio || 'Hey there! I am using Connectly.';
        if (statusPill) {
            statusPill.innerText = conv.partner.status === 'online' ? 'Active Now' : 'Offline';
            statusPill.className = `info-status-pill ${conv.partner.status || 'offline'}`;
        }
        document.getElementById('info-group-members-section').classList.add('hidden');
        document.getElementById('btn-block-user').classList.remove('hidden');
    } else {
        if (username) username.innerText = 'Group Channel';
        if (bio) bio.innerText = conv.group_description || 'Group conversation';
        if (statusPill) {
            statusPill.innerText = `${conv.members ? conv.members.length : 0} members`;
            statusPill.className = 'info-status-pill online';
        }
        document.getElementById('btn-block-user').classList.add('hidden');
        renderGroupMembersList(conv.members || []);
    }

    // Load shared media
    loadSharedMedia(conv.id);
}

function renderGroupMembersList(members) {
    const section = document.getElementById('info-group-members-section');
    const list = document.getElementById('info-members-list');
    const count = document.getElementById('info-member-count');
    if (!section || !list) return;

    section.classList.remove('hidden');
    if (count) count.innerText = members.length;
    list.innerHTML = '';

    members.forEach(m => {
        const item = document.createElement('div');
        item.className = 'info-member-item';
        item.innerHTML = `
            <img src="${m.profile_picture || '/static/images/avatars/avatar-1.svg'}" alt="${escapeHtml(m.name)}">
            <span>${escapeHtml(m.name)}</span>
            ${m.role === 'admin' ? '<span class="badge badge-accent">Admin</span>' : ''}
        `;
        list.appendChild(item);
    });
}

async function loadSharedMedia(convId) {
    try {
        const res = await fetch(`/api/conversations/${convId}/media`);
        const data = await res.json();
        if (data.success) {
            const imgGrid = document.getElementById('shared-images-grid');
            const docsList = document.getElementById('shared-docs-list');

            if (imgGrid) {
                if (data.media.images.length === 0) {
                    imgGrid.innerHTML = '<p class="empty-media-text">No shared images yet.</p>';
                } else {
                    imgGrid.innerHTML = data.media.images.map(img => `
                        <img src="${img.filepath}" alt="${escapeHtml(img.original_name)}" class="shared-img-thumb" onclick="openLightbox('${img.filepath}')">
                    `).join('');
                }
            }

            if (docsList) {
                if (data.media.files.length === 0) {
                    docsList.innerHTML = '<p class="empty-media-text">No shared documents yet.</p>';
                } else {
                    docsList.innerHTML = data.media.files.map(f => `
                        <a href="${f.filepath}" download="${escapeHtml(f.original_name)}" class="msg-file-card">
                            <i class="fa-solid fa-file-arrow-down msg-file-icon text-accent"></i>
                            <div class="msg-file-details">
                                <span class="msg-file-name">${escapeHtml(f.original_name)}</span>
                                <span class="msg-file-size">${formatBytes(f.file_size)}</span>
                            </div>
                        </a>
                    `).join('');
                }
            }
        }
    } catch (e) {
        console.warn('Failed to load shared media', e);
    }
}

function switchMediaTab(tab, btn) {
    document.querySelectorAll('.media-tab').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');

    const imgGrid = document.getElementById('shared-images-grid');
    const docsList = document.getElementById('shared-docs-list');

    if (tab === 'images') {
        imgGrid.classList.remove('hidden');
        docsList.classList.add('hidden');
    } else {
        imgGrid.classList.add('hidden');
        docsList.classList.remove('hidden');
    }
}

async function togglePinActiveChat() {
    if (!activeConversationId) return;
    try {
        const res = await fetch(`/api/conversations/${activeConversationId}/pin`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('info', data.is_pinned ? 'Conversation pinned.' : 'Conversation unpinned.');
            reloadConversationsSidebar();
        }
    } catch (e) {
        showToast('error', 'Action failed.');
    }
}

async function toggleMuteActiveChat() {
    if (!activeConversationId) return;
    try {
        const res = await fetch(`/api/conversations/${activeConversationId}/mute`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('info', data.is_muted ? 'Notifications muted.' : 'Notifications unmuted.');
        }
    } catch (e) {
        showToast('error', 'Action failed.');
    }
}

async function blockCurrentChatUser() {
    if (!activeConversationMeta || activeConversationMeta.is_group || !activeConversationMeta.partner) return;
    const partnerId = activeConversationMeta.partner.id;
    if (confirm(`Are you sure you want to block ${activeConversationMeta.partner.name}?`)) {
        try {
            const res = await fetch(`/api/users/${partnerId}/block`, { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                showToast('info', data.message);
            }
        } catch (e) {
            showToast('error', 'Failed to block user.');
        }
    }
}

async function deleteActiveChat() {
    if (!activeConversationId) return;
    if (confirm('Are you sure you want to delete/leave this conversation?')) {
        try {
            const res = await fetch(`/api/conversations/${activeConversationId}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.success) {
                showToast('success', 'Conversation removed.');
                window.location.href = '/chat';
            }
        } catch (e) {
            showToast('error', 'Failed to delete conversation.');
        }
    }
}

/* ==========================================================================
   Modals & Creation Flows (New Chat, New Group, Forward)
   ========================================================================== */
function openNewChatModal() {
    const modal = document.getElementById('new-chat-modal');
    if (modal) {
        modal.classList.remove('hidden');
        loadAvailableUsersForDirectChat();
    }
}

function closeNewChatModal() {
    const modal = document.getElementById('new-chat-modal');
    if (modal) modal.classList.add('hidden');
}

async function loadAvailableUsersForDirectChat() {
    const list = document.getElementById('available-users-list');
    if (!list) return;
    list.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';

    try {
        const res = await fetch('/api/users/available');
        const data = await res.json();
        if (data.success) {
            if (data.users.length === 0) {
                list.innerHTML = '<p class="empty-media-text">No other users found.</p>';
                return;
            }
            list.innerHTML = data.users.map(u => `
                <div class="user-select-row" onclick="startDirectChatWith(${u.id})">
                    <img src="${u.profile_picture || '/static/images/avatars/avatar-1.svg'}" alt="${escapeHtml(u.name)}">
                    <div class="user-select-info">
                        <div class="user-select-name">${escapeHtml(u.name)}</div>
                        <div class="user-select-handle">@${escapeHtml(u.username)} &bull; ${u.status}</div>
                    </div>
                    <i class="fa-solid fa-paper-plane text-accent"></i>
                </div>
            `).join('');
        }
    } catch (e) {
        list.innerHTML = '<p class="text-danger text-center">Failed to load users.</p>';
    }
}

function filterAvailableUsers(query) {
    const q = query.toLowerCase();
    document.querySelectorAll('.user-select-row').forEach(row => {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(q) ? 'flex' : 'none';
    });
}

async function startDirectChatWith(userId) {
    closeNewChatModal();
    try {
        const res = await fetch('/api/conversations/direct', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        const data = await res.json();
        if (data.success) {
            await reloadConversationsSidebar();
            selectConversation(data.conversation_id);
        }
    } catch (e) {
        showToast('error', 'Could not open direct chat.');
    }
}

function openNewGroupModal() {
    const modal = document.getElementById('new-group-modal');
    if (modal) {
        modal.classList.remove('hidden');
        loadAvailableUsersForGroupPicker();
    }
}

function closeNewGroupModal() {
    const modal = document.getElementById('new-group-modal');
    if (modal) modal.classList.add('hidden');
}

async function loadAvailableUsersForGroupPicker() {
    const list = document.getElementById('group-members-picker-list');
    if (!list) return;
    list.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';

    try {
        const res = await fetch('/api/users/available');
        const data = await res.json();
        if (data.success) {
            list.innerHTML = data.users.map(u => `
                <label class="member-checkbox-row">
                    <input type="checkbox" name="group_member" value="${u.id}">
                    <img src="${u.profile_picture || '/static/images/avatars/avatar-1.svg'}" alt="${escapeHtml(u.name)}">
                    <span>${escapeHtml(u.name)} (@${escapeHtml(u.username)})</span>
                </label>
            `).join('');
        }
    } catch (e) {
        list.innerHTML = '<p class="text-danger text-center">Failed to load users.</p>';
    }
}

async function submitCreateGroup() {
    const nameInput = document.getElementById('group-name-input');
    const descInput = document.getElementById('group-desc-input');
    const selectedBoxes = document.querySelectorAll('input[name="group_member"]:checked');

    const name = nameInput ? nameInput.value.trim() : '';
    const desc = descInput ? descInput.value.trim() : '';
    const members = Array.from(selectedBoxes).map(b => parseInt(b.value, 10));

    if (!name) {
        showToast('error', 'Please provide a group name.');
        return;
    }
    if (members.length === 0) {
        showToast('error', 'Please select at least one member.');
        return;
    }

    try {
        const res = await fetch('/api/conversations/group', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                description: desc,
                members
            })
        });
        const data = await res.json();
        if (data.success) {
            closeNewGroupModal();
            showToast('success', `Group "${name}" created!`);
            await reloadConversationsSidebar();
            selectConversation(data.conversation_id);
        } else {
            showToast('error', data.error || 'Failed to create group.');
        }
    } catch (e) {
        showToast('error', 'Group creation failed.');
    }
}

function openForwardModal() {
    const modal = document.getElementById('forward-modal');
    const list = document.getElementById('forward-conv-list');
    if (modal && list) {
        modal.classList.remove('hidden');
        list.innerHTML = document.getElementById('conversation-list').innerHTML;
        // Make items forward triggers
        list.querySelectorAll('.conversation-item').forEach(item => {
            const cid = parseInt(item.dataset.convId, 10);
            item.onclick = () => forwardMessageTo(cid);
        });
    }
}

function closeForwardModal() {
    const modal = document.getElementById('forward-modal');
    if (modal) modal.classList.add('hidden');
}

function forwardMessageTo(targetConvId) {
    if (!activeContextMenuMessage || !socket) return;
    socket.emit('send_message', {
        conversation_id: targetConvId,
        message: activeContextMenuMessage.message,
        message_type: activeContextMenuMessage.message_type,
        attachments: activeContextMenuMessage.attachments
    });
    closeForwardModal();
    showToast('success', 'Message forwarded!');
    selectConversation(targetConvId);
}

/* ==========================================================================
   Voice & Video Calling Simulation
   ========================================================================== */
function startCall(type) {
    if (!activeConversationMeta) return;

    const modal = document.getElementById('call-modal');
    const avatar = document.getElementById('call-avatar');
    const name = document.getElementById('call-name');
    const statusText = document.getElementById('call-status-text');
    const timer = document.getElementById('call-timer');

    if (modal && avatar && name && statusText) {
        avatar.src = activeConversationMeta.display_avatar;
        name.innerText = activeConversationMeta.display_name;
        statusText.innerText = type === 'video' ? 'Connecting video call...' : 'Ringing voice call...';
        modal.classList.remove('hidden');

        // Trigger socket call_start
        if (!activeConversationMeta.is_group && activeConversationMeta.partner) {
            socket.emit('call_start', {
                target_user_id: activeConversationMeta.partner.id,
                call_type: type
            });
        }

        // Simulate connection after 2 seconds
        setTimeout(() => {
            statusText.innerText = 'Connected';
            if (timer) {
                timer.classList.remove('hidden');
                callDurationSeconds = 0;
                clearInterval(callTimerInterval);
                callTimerInterval = setInterval(() => {
                    callDurationSeconds++;
                    const mins = String(Math.floor(callDurationSeconds / 60)).padStart(2, '0');
                    const secs = String(callDurationSeconds % 60).padStart(2, '0');
                    timer.innerText = `${mins}:${secs}`;
                }, 1000);
            }
        }, 2200);

        document.getElementById('btn-call-hangup').onclick = () => {
            if (!activeConversationMeta.is_group && activeConversationMeta.partner) {
                socket.emit('call_end', { target_user_id: activeConversationMeta.partner.id });
            }
            endCallUI();
        };
    }
}

function handleIncomingCall(caller, type) {
    playNotificationSound();
    const modal = document.getElementById('call-modal');
    const avatar = document.getElementById('call-avatar');
    const name = document.getElementById('call-name');
    const statusText = document.getElementById('call-status-text');

    if (modal && avatar && name && statusText) {
        avatar.src = caller.profile_picture;
        name.innerText = caller.name;
        statusText.innerText = `Incoming ${type} call...`;
        modal.classList.remove('hidden');
    }
}

function endCallUI() {
    clearInterval(callTimerInterval);
    const modal = document.getElementById('call-modal');
    const timer = document.getElementById('call-timer');
    if (modal) modal.classList.add('hidden');
    if (timer) {
        timer.classList.add('hidden');
        timer.innerText = '00:00';
    }
}

/* ==========================================================================
   Sidebar, Status & Utilities
   ========================================================================== */
function changeUserStatus(status) {
    if (socket) {
        socket.emit('set_user_status', { status });
    }
}

function updateUserStatusInDOM(userId, status) {
    const dot = document.getElementById(`status-user-${userId}`);
    if (dot) {
        dot.className = `status-indicator ${status}`;
    }
}

function filterConversations(filter, btn) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');

    document.querySelectorAll('.conversation-item').forEach(item => {
        const isGroup = item.dataset.isGroup === '1';
        const unread = parseInt(item.dataset.unread || '0', 10);

        if (filter === 'all') item.style.display = 'flex';
        else if (filter === 'direct') item.style.display = !isGroup ? 'flex' : 'none';
        else if (filter === 'group') item.style.display = isGroup ? 'flex' : 'none';
        else if (filter === 'unread') item.style.display = unread > 0 ? 'flex' : 'none';
    });
}

function updateConversationListItem(convId, lastMsg, unreadIncrement) {
    const item = document.querySelector(`.conversation-item[data-conv-id="${convId}"]`);
    if (item && lastMsg) {
        const snippet = item.querySelector('.conv-snippet');
        const timeEl = item.querySelector('.conv-time');
        const badge = item.querySelector('.unread-badge');

        if (snippet) snippet.innerText = lastMsg.message || 'Media file';
        if (timeEl) timeEl.innerText = formatTime(lastMsg.created_at);

        if (unreadIncrement > 0 && activeConversationId !== convId) {
            let currentUnread = parseInt(item.dataset.unread || '0', 10) + unreadIncrement;
            item.dataset.unread = currentUnread;
            if (badge) {
                badge.innerText = currentUnread;
                badge.classList.remove('hidden');
            }
        }
    }
}

async function reloadConversationsSidebar() {
    try {
        const res = await fetch('/api/conversations');
        const data = await res.json();
        if (data.success) {
            // Re-render conversation list items
            const list = document.getElementById('conversation-list');
            if (list) {
                list.innerHTML = data.conversations.map(c => `
                    <div class="conversation-item ${c.is_pinned ? 'pinned' : ''} ${c.id === activeConversationId ? 'active' : ''}"
                         data-conv-id="${c.id}"
                         data-is-group="${c.is_group}"
                         data-unread="${c.unread_count}"
                         onclick="selectConversation(${c.id})">
                        <div class="conv-avatar-wrap">
                            <img src="${c.display_avatar}" alt="${escapeHtml(c.display_name)}" class="conv-avatar">
                            ${!c.is_group ? `<span class="status-indicator ${c.partner_status || 'offline'}" id="status-user-${c.partner ? c.partner.id : ''}"></span>` : ''}
                        </div>
                        <div class="conv-details">
                            <div class="conv-top-row">
                                <span class="conv-title">${escapeHtml(c.display_name)}</span>
                                <span class="conv-time">${c.last_message ? formatTime(c.last_message.created_at) : ''}</span>
                            </div>
                            <div class="conv-bottom-row">
                                <p class="conv-snippet">${c.last_message ? escapeHtml(c.last_message.message) : 'No messages yet'}</p>
                                <div class="conv-meta-badges">
                                    ${c.is_pinned ? '<i class="fa-solid fa-thumbtack text-accent icon-pin"></i>' : ''}
                                    <span class="unread-badge ${c.unread_count === 0 ? 'hidden' : ''}">${c.unread_count}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
        }
    } catch (e) {
        console.warn('Sidebar reload error', e);
    }
}

function scrollToBottom() {
    const container = document.getElementById('chat-messages-container');
    if (container) container.scrollTop = container.scrollHeight;
}

function scrollToBottomSmooth() {
    const container = document.getElementById('chat-messages-container');
    if (container) container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
}

function scrollToMessage(msgId) {
    const el = document.getElementById(`msg-${msgId}`);
    if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('animate-shake');
        setTimeout(() => el.classList.remove('animate-shake'), 1000);
    }
}

function toggleMobileSidebar() {
    const chatApp = document.getElementById('chat-app');
    if (chatApp) chatApp.classList.remove('in-conversation');
}

function initGlobalClickDismissal() {
    document.addEventListener('click', () => {
        closeContextMenu();
        const picker = document.getElementById('emoji-picker-container');
        if (picker) picker.classList.add('hidden');
        const attachMenu = document.getElementById('attachment-dropdown');
        if (attachMenu) attachMenu.classList.add('hidden');
    });
}

function formatMessageText(text) {
    if (!text) return '';
    const escaped = escapeHtml(text);
    // Convert URLs to clickable links
    const urlPattern = /(https?:\/\/[^\s]+)/g;
    return escaped.replace(urlPattern, '<a href="$1" target="_blank" rel="noopener noreferrer" class="chat-inline-link">$1</a>');
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    try {
        const d = new Date(timestamp.includes('Z') ? timestamp : timestamp + 'Z');
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return timestamp.substring(11, 16);
    }
}

function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
