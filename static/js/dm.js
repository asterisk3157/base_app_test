// ------------------------------------------------------------------
// DM (Direct Messages) — SPA view replacing timeline content
// ------------------------------------------------------------------

function showDM(fromPopstate) {
    currentView = 'dm';
    window.scrollTo(0, 0);
    if (!fromPopstate) pushView('dm');

    var timeline = document.getElementById('top');
    var tabs = document.getElementById('timeline-tabs');
    if (tabs) tabs.style.display = 'none';
    var composeBox = timeline.querySelector('.compose-box');
    var feed = document.getElementById('tweet-feed');
    if (composeBox) composeBox.style.display = 'none';
    if (feed) feed.style.display = 'none';

    // Remove existing views
    ['profile-view', 'notif-view', 'search-view', 'tweet-detail-view', 'bookmarks-view', 'dm-view'].forEach(function(cls) {
        var el = timeline.querySelector('.' + cls);
        if (el) el.remove();
    });

    var header = document.querySelector('.timeline-header h1');
    if (header) header.textContent = 'メッセージ';

    document.querySelectorAll('.nav-item').forEach(function(b) { b.classList.remove('active'); });
    var dmNav = document.getElementById('dm-nav');
    if (dmNav) dmNav.classList.add('active');

    var view = document.createElement('div');
    view.className = 'dm-view';
    view.innerHTML = '<div style="padding:40px 20px;text-align:center;color:var(--text-secondary)">読み込み中…</div>';
    timeline.appendChild(view);

    fetch('/api/dm/conversations')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            view.innerHTML = '';

            if (!currentUser) {
                view.innerHTML = '<div style="padding:60px 20px;text-align:center;color:var(--text-secondary)">ログインするとメッセージを利用できます</div>';
                return;
            }

            if (!data.conversations || data.conversations.length === 0) {
                view.innerHTML = '<div style="padding:60px 20px;text-align:center;color:var(--text-secondary)">まだメッセージはありません</div>';
                return;
            }

            data.conversations.forEach(function(conv) {
                var item = document.createElement('div');
                item.className = 'dm-conversation-item';

                var av = buildAvatar({ id: conv.other_user_id, display_name: conv.other_name, avatar_url: conv.other_avatar, handle: conv.other_handle }, 44);

                var info = document.createElement('div');
                info.style.flex = '1';
                info.style.minWidth = '0';

                var nameRow = document.createElement('div');
                nameRow.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:2px';

                var nameEl = document.createElement('span');
                nameEl.style.cssText = 'font-weight:700;font-size:0.95rem;color:var(--text-primary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap';
                nameEl.textContent = conv.other_name;

                var timeEl = document.createElement('span');
                timeEl.style.cssText = 'font-size:0.8rem;color:var(--text-secondary);flex-shrink:0;margin-left:8px';
                timeEl.textContent = conv.last_message_at ? timeAgo(conv.last_message_at) : '';

                nameRow.appendChild(nameEl);
                nameRow.appendChild(timeEl);

                var preview = document.createElement('div');
                preview.style.cssText = 'font-size:0.88rem;color:var(--text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap';
                preview.textContent = conv.last_message || '';

                info.appendChild(nameRow);
                info.appendChild(preview);

                item.appendChild(av);
                item.appendChild(info);

                if (conv.unread_count > 0) {
                    var badge = document.createElement('span');
                    badge.className = 'notif-badge';
                    badge.textContent = conv.unread_count;
                    item.appendChild(badge);
                }

                (function(c) {
                    item.onclick = function() { showConversation(c.id, c.other_name, c.other_avatar, c.other_handle, c.other_user_id); };
                })(conv);

                view.appendChild(item);
            });
        })
        .catch(function(err) {
            console.error('Failed to load conversations:', err);
            view.innerHTML = '<div style="padding:60px 20px;text-align:center;color:var(--text-secondary)">メッセージを読み込めませんでした</div>';
        });
}

function showConversation(convId, otherName, otherAvatar, otherHandle, otherUserId) {
    var timeline = document.getElementById('top');
    var view = timeline.querySelector('.dm-view');
    if (!view) return;

    var header = document.querySelector('.timeline-header h1');
    if (header) header.textContent = otherName;

    view.innerHTML = '<div style="padding:40px 20px;text-align:center;color:var(--text-secondary)">読み込み中…</div>';

    fetch('/api/dm/conversations/' + convId + '/messages')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            view.innerHTML = '';

            // Back button row
            var backRow = document.createElement('div');
            backRow.style.cssText = 'display:flex;align-items:center;gap:12px;padding:12px 20px;border-bottom:1px solid var(--border);cursor:pointer';
            backRow.onclick = function() { showDM(false); };

            var backSvg = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>';
            backRow.innerHTML = backSvg + '<span style="font-weight:700;font-size:0.95rem">' + otherName + '</span>';
            view.appendChild(backRow);

            // Messages container
            var messagesEl = document.createElement('div');
            messagesEl.className = 'dm-messages';
            messagesEl.style.cssText = 'padding:12px 20px;min-height:200px;display:flex;flex-direction:column;gap:8px';

            if (!data.messages || data.messages.length === 0) {
                messagesEl.innerHTML = '<div style="padding:40px 20px;text-align:center;color:var(--text-secondary)">まだメッセージはありません。最初のメッセージを送りましょう。</div>';
            } else {
                data.messages.forEach(function(msg) {
                    var wrap = document.createElement('div');
                    wrap.style.cssText = 'display:flex;flex-direction:column';

                    var bubble = document.createElement('div');
                    var isSent = currentUser && msg.sender_id === currentUser.id;
                    bubble.className = 'dm-message ' + (isSent ? 'sent' : 'received');
                    bubble.textContent = msg.content;

                    var timeEl = document.createElement('div');
                    timeEl.style.cssText = 'font-size:0.75rem;color:var(--text-secondary);margin-top:2px;' + (isSent ? 'text-align:right' : '');
                    timeEl.textContent = timeAgo(msg.created_at);

                    wrap.appendChild(bubble);
                    wrap.appendChild(timeEl);
                    messagesEl.appendChild(wrap);
                });
            }

            view.appendChild(messagesEl);

            // Scroll to bottom
            messagesEl.scrollTop = messagesEl.scrollHeight;

            // Input bar
            var inputBar = document.createElement('div');
            inputBar.className = 'dm-input-bar';

            var textarea = document.createElement('textarea');
            textarea.className = 'reply-textarea';
            textarea.placeholder = 'メッセージを入力...';
            textarea.maxLength = 500;
            textarea.rows = 1;
            textarea.style.cssText += ';flex:1;resize:none;min-height:40px;max-height:120px';

            var sendBtn = document.createElement('button');
            sendBtn.className = 'compose-submit';
            sendBtn.style.cssText = 'padding:8px 18px;font-size:0.9rem;align-self:flex-end';
            sendBtn.textContent = '送信';

            var doSend = function() {
                var content = textarea.value.trim();
                if (!content) return;
                textarea.value = '';
                sendDMMessage(convId, content, otherUserId, messagesEl);
            };

            sendBtn.onclick = doSend;
            textarea.addEventListener('keydown', function(e) {
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { doSend(); }
            });

            inputBar.appendChild(textarea);
            inputBar.appendChild(sendBtn);
            view.appendChild(inputBar);

            setTimeout(function() { textarea.focus(); }, 50);
        })
        .catch(function(err) {
            console.error('Failed to load messages:', err);
            view.innerHTML = '<div style="padding:60px 20px;text-align:center;color:var(--text-secondary)">メッセージを読み込めませんでした</div>';
        });
}

function sendDMMessage(convId, content, otherUserId, messagesEl) {
    fetch('/api/dm/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: convId, to_user_id: otherUserId, content: content })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (!data || data.error) return;
        if (!messagesEl) return;

        var wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex;flex-direction:column';

        var bubble = document.createElement('div');
        bubble.className = 'dm-message sent';
        bubble.textContent = content;

        var timeEl = document.createElement('div');
        timeEl.style.cssText = 'font-size:0.75rem;color:var(--text-secondary);margin-top:2px;text-align:right';
        timeEl.textContent = 'たった今';

        wrap.appendChild(bubble);
        wrap.appendChild(timeEl);
        messagesEl.appendChild(wrap);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    })
    .catch(function(err) {
        console.error('Failed to send DM:', err);
    });
}

// ------------------------------------------------------------------
// Start a new DM conversation from a user profile
// ------------------------------------------------------------------
function startDM(userId, otherName, otherAvatar, otherHandle) {
    if (!currentUser) { showRegistrationModal(); return; }

    fetch('/api/dm/conversations/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to_user_id: userId })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.conversation_id) {
            showDM(false);
            // Wait for view to render then open conversation
            setTimeout(function() {
                showConversation(data.conversation_id, otherName, otherAvatar, otherHandle, userId);
            }, 100);
        } else {
            showDM(false);
        }
    })
    .catch(function(err) {
        console.error('Failed to start DM:', err);
        showDM(false);
    });
}

// ------------------------------------------------------------------
// Poll for unread DM count
// ------------------------------------------------------------------
function pollDMUnread() {
    if (!currentUser) return;
    fetch('/api/dm/unread')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var badge = document.getElementById('dm-badge');
            if (!badge) return;
            if (data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        })
        .catch(function() {});
}
