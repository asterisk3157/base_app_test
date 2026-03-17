// ------------------------------------------------------------------
// Notifications tab view (Twitter-style, replaces timeline content)
// ------------------------------------------------------------------
function showNotifications(fromPopstate) {
    currentView = 'notifications';
    window.scrollTo(0, 0);
    if (!fromPopstate) pushView('notifications');

    var timeline = document.getElementById('top');
    var tabs = document.getElementById('timeline-tabs');
    if (tabs) tabs.style.display = 'none';
    var composeBox = timeline.querySelector('.compose-box');
    var feed = document.getElementById('tweet-feed');
    if (composeBox) composeBox.style.display = 'none';
    if (feed) feed.style.display = 'none';

    // Remove existing views
    ['profile-view', 'notif-view', 'search-view', 'tweet-detail-view', 'bookmarks-view'].forEach(function(cls) {
        var el = timeline.querySelector('.' + cls);
        if (el) el.remove();
    });

    // Update header
    var header = timeline.querySelector('.timeline-header h1');
    if (header) header.textContent = '通知';

    // Update nav active states
    document.querySelectorAll('.nav-item').forEach(function(btn) {
        btn.classList.remove('active');
    });
    var notifNav = document.getElementById('notif-nav');
    if (notifNav) notifNav.classList.add('active');

    var view = document.createElement('div');
    view.className = 'notif-view';

    // Loading state
    view.innerHTML = '<div style="padding:40px 20px;text-align:center;color:var(--text-secondary)">読み込み中…</div>';
    timeline.appendChild(view);

    // Fetch and render
    fetch('/api/notifications')
        .then(function(res) { return res.json(); })
        .then(function(data) {
            view.innerHTML = '';

            // Auto mark as read
            if (data.unread_count > 0) {
                fetch('/api/notifications/read', { method: 'POST' });
                updateNotifBadge(0);
            }

            if (!data.notifications || data.notifications.length === 0) {
                view.innerHTML = '<div style="padding:60px 20px;text-align:center;color:var(--text-secondary)">まだ通知はありません</div>';
                return;
            }

            data.notifications.forEach(function(n) {
                var item = document.createElement('div');
                item.className = 'notif-item' + (n.read ? '' : ' unread');

                var iconDiv = document.createElement('div');

                if (n.type === 'like') {
                    iconDiv.className = 'notif-icon like-icon';
                    iconDiv.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 21.638h-.014C9.403 21.59 1.95 14.856 1.95 8.478c0-3.064 2.525-5.754 5.403-5.754 2.29 0 3.83 1.58 4.646 2.73.814-1.148 2.354-2.73 4.645-2.73 2.88 0 5.404 2.69 5.404 5.755 0 6.376-7.454 13.11-10.037 13.157H12z"/></svg>';
                } else if (n.type === 'follow') {
                    iconDiv.className = 'notif-icon';
                    iconDiv.style.color = 'var(--accent)';
                    iconDiv.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14" stroke="currentColor" stroke-width="2"/><line x1="23" y1="11" x2="17" y2="11" stroke="currentColor" stroke-width="2"/></svg>';
                } else {
                    iconDiv.className = 'notif-icon reply-icon';
                    iconDiv.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>';
                }

                // Actor avatar — use buildAvatar for consistency
                var actorUser = {
                    id: n.actor_id,
                    display_name: n.actor_name,
                    avatar_url: n.actor_avatar,
                    handle: n.actor_handle
                };
                var avDiv = buildAvatar(actorUser, 40);

                var textDiv = document.createElement('div');
                textDiv.className = 'notif-text';
                var actorSpan = '<span class="notif-actor">' + (n.actor_name || '') + '</span>';
                if (n.type === 'like') {
                    textDiv.innerHTML = actorSpan + 'さんがあなたのツイートにいいねしました';
                } else if (n.type === 'follow') {
                    textDiv.innerHTML = actorSpan + 'さんがあなたをフォローしました';
                } else {
                    textDiv.innerHTML = actorSpan + 'さんがあなたのツイートに返信しました';
                }
                var timeDiv = document.createElement('div');
                timeDiv.className = 'notif-time';
                timeDiv.textContent = timeAgo(n.created_at);
                textDiv.appendChild(timeDiv);

                item.appendChild(iconDiv);
                item.appendChild(avDiv);
                item.appendChild(textDiv);
                item.style.cursor = 'pointer';

                if (n.type === 'follow') {
                    (function(handle) {
                        item.onclick = function() { showProfile(handle); };
                    })(n.actor_handle);
                } else {
                    (function(tweetId) {
                        item.onclick = function() {
                            if (tweetId) showTweetDetail(tweetId);
                        };
                    })(n.tweet_id);
                }

                view.appendChild(item);
            });
        })
        .catch(function(err) {
            console.error('Failed to load notifications:', err);
            view.innerHTML = '<div style="padding:60px 20px;text-align:center;color:var(--text-secondary)">まだ通知はありません</div>';
        });
}

function updateNotifBadge(count) {
    var badge = document.getElementById('notif-badge');
    if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'inline';
    } else {
        badge.style.display = 'none';
    }
}

// Poll for unread notification count every 10 seconds
function pollNotifications() {
    if (!currentUser) return;
    fetch('/api/notifications')
        .then(function(res) { return res.json(); })
        .then(function(data) {
            updateNotifBadge(data.unread_count || 0);
        })
        .catch(function() {});
}
