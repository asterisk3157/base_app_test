// ------------------------------------------------------------------
// Profile view — SPA-style overlay replacing timeline content
// ------------------------------------------------------------------
function showProfile(handle, fromPopstate) {
    fetch('/api/users/' + encodeURIComponent(handle) + '/profile')
        .then(function(res) { return res.json(); })
        .then(function(data) {
            if (data.error) return;
            renderProfileView(data.user, data.tweets, data.reposted_tweets);
            currentView = 'profile';
            window.scrollTo(0, 0);
            if (!fromPopstate) pushView('profile', handle);
            document.querySelectorAll('.nav-item').forEach(function(btn) {
                btn.classList.remove('active');
            });
        })
        .catch(function(err) {
            console.error('Failed to load profile:', err);
        });
}

function renderProfileView(user, tweets, repostedTweets) {
    var timeline = document.getElementById('top');

    var tabs = document.getElementById('timeline-tabs');
    if (tabs) tabs.style.display = 'none';
    var composeBox = timeline.querySelector('.compose-box');
    var feed = document.getElementById('tweet-feed');
    if (composeBox) composeBox.style.display = 'none';
    if (feed) feed.style.display = 'none';

    ['profile-view', 'notif-view', 'search-view', 'tweet-detail-view', 'bookmarks-view'].forEach(function(cls) {
        var el = timeline.querySelector('.' + cls);
        if (el) el.remove();
    });

    var header = timeline.querySelector('.timeline-header h1');
    if (header) header.textContent = user.display_name;

    var view = document.createElement('div');
    view.className = 'profile-view';

    // Banner
    var banner = document.createElement('div');
    banner.className = 'profile-banner';
    if (user.banner_url) {
        banner.style.backgroundImage = 'url(' + user.banner_url + ')';
        banner.style.backgroundSize = 'cover';
        banner.style.backgroundPosition = 'center';
    }
    // else: default gradient stays from CSS
    view.appendChild(banner);

    // Profile info section
    var info = document.createElement('div');
    info.className = 'profile-info';

    // Avatar
    var avatarWrap = document.createElement('div');
    avatarWrap.className = 'profile-avatar';
    if (user.avatar_url) {
        var img = document.createElement('img');
        img.src = user.avatar_url;
        img.alt = user.display_name;
        img.style.cursor = 'pointer';
        img.onclick = function() { showImageModal(user.avatar_url); };
        avatarWrap.appendChild(img);
    } else {
        var circle = buildDefaultAvatar(80);
        circle.style.width = '100%';
        circle.style.height = '100%';
        circle.style.fontSize = '2rem';
        avatarWrap.appendChild(circle);
    }
    // Actions area (settings for own profile, follow button for others)
    var actions = document.createElement('div');
    actions.className = 'profile-actions';
    if (currentUser && currentUser.handle === user.handle) {
        var settingsBtn = document.createElement('button');
        settingsBtn.className = 'profile-settings-btn';
        settingsBtn.textContent = '設定';
        settingsBtn.onclick = function() { showProfileModal(); };
        actions.appendChild(settingsBtn);
    } else if (currentUser && currentUser.handle !== user.handle) {
        var followBtn = document.createElement('button');
        followBtn.className = 'follow-btn';
        if (user.is_following) {
            followBtn.textContent = 'フォロー中';
            followBtn.style.background = 'transparent';
            followBtn.style.color = 'var(--text-primary)';
            followBtn.style.border = '1px solid var(--text-secondary)';
        } else {
            followBtn.textContent = 'フォローする';
        }
        followBtn.onclick = function() {
            fetch('/api/users/' + user.id + '/follow', { method: 'POST' })
                .then(function(res) { return res.json(); })
                .then(function(data) {
                    if (data.following) {
                        followBtn.textContent = 'フォロー中';
                        followBtn.style.background = 'transparent';
                        followBtn.style.color = 'var(--text-primary)';
                        followBtn.style.border = '1px solid var(--text-secondary)';
                    } else {
                        followBtn.textContent = 'フォローする';
                        followBtn.style.background = 'var(--text-primary)';
                        followBtn.style.color = 'var(--bg-main)';
                        followBtn.style.border = 'none';
                    }
                    // Re-fetch profile to update counts
                    var statsEl = document.querySelector('.profile-stats');
                    if (statsEl) {
                        showProfile(user.handle);
                    }
                });
        };
        actions.appendChild(followBtn);
    }

    // Top row: avatar on the left, action button on the right
    var topRow = document.createElement('div');
    topRow.className = 'profile-top-row';
    topRow.appendChild(avatarWrap);
    topRow.appendChild(actions);
    info.appendChild(topRow);

    // Name
    var nameEl = document.createElement('h2');
    nameEl.className = 'profile-name';
    nameEl.textContent = user.display_name;
    info.appendChild(nameEl);

    // Handle
    var handleEl = document.createElement('div');
    handleEl.className = 'profile-handle';
    handleEl.textContent = user.handle;
    info.appendChild(handleEl);

    // Bio — render newlines as <br> (bio comes from DB, not user-injected HTML)
    if (user.bio) {
        var bioEl = document.createElement('div');
        bioEl.className = 'profile-bio';
        bioEl.innerHTML = user.bio.replace(/\n/g, '<br>');
        info.appendChild(bioEl);
    }

    // Location
    if (user.location) {
        var locEl = document.createElement('div');
        locEl.className = 'profile-location';
        locEl.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:text-bottom;flex-shrink:0"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg> ' + user.location;
        info.appendChild(locEl);
    }

    // Birthday
    if (user.birthday) {
        var bdayEl = document.createElement('div');
        bdayEl.className = 'profile-birthday';
        bdayEl.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:text-bottom;flex-shrink:0"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg> ' + user.birthday;
        info.appendChild(bdayEl);
    }

    // Stats — following/follower counts are clickable links
    var statsDiv = document.createElement('div');
    statsDiv.className = 'profile-stats';

    var tweetStat = document.createElement('span');
    tweetStat.innerHTML = '<strong>' + (user.tweet_count || 0) + '</strong> ツイート';
    statsDiv.appendChild(tweetStat);

    var followingStat = document.createElement('span');
    followingStat.className = 'stat-link';
    followingStat.innerHTML = '<strong>' + (user.following_count || 0) + '</strong> フォロー';
    followingStat.onclick = function() { showFollowList(user.id, user.display_name, 'following'); };
    statsDiv.appendChild(followingStat);

    var followersStat = document.createElement('span');
    followersStat.className = 'stat-link';
    followersStat.innerHTML = '<strong>' + (user.followers_count || 0) + '</strong> フォロワー';
    followersStat.onclick = function() { showFollowList(user.id, user.display_name, 'followers'); };
    statsDiv.appendChild(followersStat);

    var likesStat = document.createElement('span');
    likesStat.innerHTML = '<strong>' + (user.likes_received || 0) + '</strong> いいね';
    statsDiv.appendChild(likesStat);

    info.appendChild(statsDiv);

    view.appendChild(info);

    // Profile tabs
    var profileTabs = document.createElement('div');
    profileTabs.className = 'timeline-tabs';

    // Merge and sort all tweets by created_at for use in tab rendering
    var allTweets = (tweets || []).slice();
    if (repostedTweets) {
        repostedTweets.forEach(function(rt) {
            rt._reposted_by = user.display_name;
            allTweets.push(rt);
        });
    }
    allTweets.sort(function(a, b) {
        return new Date(b.created_at) - new Date(a.created_at);
    });

    var tweetsContainer = document.createElement('div');
    tweetsContainer.className = 'profile-tweets';

    // Build reply map for tweet grouping
    var profileRepliesMap = {};
    allTweets.forEach(function(tweet) {
        if (tweet.reply_to_id && !tweet._reposted_by) {
            if (!profileRepliesMap[tweet.reply_to_id]) profileRepliesMap[tweet.reply_to_id] = [];
            profileRepliesMap[tweet.reply_to_id].push(tweet);
        }
    });

    function renderProfileTweets(container, filter) {
        container.innerHTML = '';
        var filtered;
        if (filter === 'ツイート') {
            filtered = allTweets.filter(function(t) { return !t.reply_to_id || t._reposted_by; });
        } else if (filter === '返信') {
            filtered = allTweets.filter(function(t) { return t.reply_to_id && !t._reposted_by; });
        } else if (filter === 'メディア') {
            filtered = allTweets.filter(function(t) { return t.image_url; });
        } else if (filter === 'いいね') {
            container.innerHTML = '<div class="feed-placeholder">いいねしたツイートはここに表示されます</div>';
            return;
        } else {
            filtered = [];
        }

        if (!filtered || filtered.length === 0) {
            container.innerHTML = '<div class="feed-placeholder">まだありません</div>';
            return;
        }

        filtered.forEach(function(tweet) {
            if (tweet._reposted_by) {
                var repostWrapper = document.createElement('div');
                repostWrapper.style.cssText = 'border-bottom:1px solid var(--border)';
                var repostLabel = document.createElement('div');
                repostLabel.style.cssText = 'padding:10px 20px 0 64px;font-size:0.8rem;color:var(--text-secondary);display:flex;align-items:center;gap:6px;font-weight:500';
                repostLabel.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3"/></svg> ' + tweet._reposted_by + 'さんがリポスト';
                var card = buildTweetCard(tweet);
                card.style.borderBottom = 'none';
                card.style.paddingBottom = '10px';
                repostWrapper.appendChild(repostLabel);
                repostWrapper.appendChild(card);
                container.appendChild(repostWrapper);
            } else {
                var card = buildTweetCard(tweet);
                container.appendChild(card);
                if (profileRepliesMap[tweet.id]) {
                    card.classList.add('has-replies');
                    (function renderRepliesR(parentId, cont, depth) {
                        var reps = profileRepliesMap[parentId];
                        if (!reps) return;
                        reps.sort(function(a, b) { return a.id - b.id; });
                        var rc = document.createElement('div');
                        rc.className = 'tweet-replies';
                        if (depth > 1) rc.style.marginLeft = '20px';
                        reps.forEach(function(reply) {
                            rc.appendChild(buildReplyCard(reply));
                            if (depth < 5 && profileRepliesMap[reply.id]) {
                                renderRepliesR(reply.id, rc, depth + 1);
                            }
                        });
                        cont.appendChild(rc);
                    })(tweet.id, container, 1);
                }
            }
        });
    }

    ['ツイート', '返信', 'メディア', 'いいね'].forEach(function(label, idx) {
        var tab = document.createElement('button');
        tab.className = 'timeline-tab' + (idx === 0 ? ' active' : '');
        tab.textContent = label;
        tab.onclick = function() {
            profileTabs.querySelectorAll('.timeline-tab').forEach(function(t) { t.classList.remove('active'); });
            tab.classList.add('active');
            renderProfileTweets(tweetsContainer, label);
        };
        profileTabs.appendChild(tab);
    });
    view.appendChild(profileTabs);

    // Render default tab (ツイート)
    renderProfileTweets(tweetsContainer, 'ツイート');
    view.appendChild(tweetsContainer);

    timeline.appendChild(view);
}

// ------------------------------------------------------------------
// Profile edit modal
// ------------------------------------------------------------------
function showProfileModal() {
    if (!currentUser) {
        showRegistrationModal();
        return;
    }
    document.getElementById('profile-display-name').value = currentUser.display_name;
    document.getElementById('profile-bio').value = currentUser.bio || '';
    document.getElementById('profile-location').value = currentUser.location || '';
    document.getElementById('profile-birthday').value = currentUser.birthday || '';
    document.getElementById('profile-handle-display').textContent = currentUser.handle;
    document.getElementById('profile-error').textContent = '';
    document.getElementById('profile-modal').style.display = 'flex';
}

function hideProfileModal() {
    document.getElementById('profile-modal').style.display = 'none';
}

function saveProfile() {
    var displayName = document.getElementById('profile-display-name').value.trim();
    var bio = document.getElementById('profile-bio').value.trim();
    var location = document.getElementById('profile-location').value.trim();
    var birthday = document.getElementById('profile-birthday').value.trim();
    if (!displayName) {
        document.getElementById('profile-error').textContent = '表示名を入力してください';
        return;
    }

    var avatarFile = document.getElementById('profile-avatar-file').files[0];
    var bannerFile = document.getElementById('profile-banner-file').files[0];

    var uploads = [];

    if (avatarFile) {
        var avatarData = new FormData();
        avatarData.append('file', avatarFile);
        uploads.push(
            fetch('/api/me/avatar', { method: 'POST', body: avatarData })
                .then(function(r) { return r.json(); })
        );
    }

    if (bannerFile) {
        var bannerData = new FormData();
        bannerData.append('file', bannerFile);
        uploads.push(
            fetch('/api/me/banner', { method: 'POST', body: bannerData })
                .then(function(r) { return r.json(); })
        );
    }

    Promise.all(uploads).then(function() {
        return fetch('/api/me', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ display_name: displayName, bio: bio, location: location, birthday: birthday })
        });
    })
    .then(function(res) {
        if (!res.ok) return res.json().then(function(d) { throw new Error(d.error); });
        return res.json();
    })
    .then(function(data) {
        currentUser = data.user;
        updateComposeAvatar();
        hideProfileModal();
        // Clear file inputs
        document.getElementById('profile-avatar-file').value = '';
        document.getElementById('profile-banner-file').value = '';
        // Refresh current view
        if (currentView === 'profile') {
            showProfile(currentUser.handle);
        } else {
            loadTweets();
        }
    })
    .catch(function(err) {
        document.getElementById('profile-error').textContent = err.message;
    });
}

// ------------------------------------------------------------------
// Update compose box avatar to reflect current user
// ------------------------------------------------------------------
function updateComposeAvatar() {
    var container = document.getElementById('compose-avatar');
    if (!container) return;
    // Replace the element entirely with buildAvatar
    var newAv;
    if (currentUser) {
        newAv = buildAvatar(currentUser, 42);
    } else {
        newAv = buildDefaultAvatar(42);
    }
    newAv.id = 'compose-avatar';
    newAv.setAttribute('aria-hidden', 'true');
    container.replaceWith(newAv);
}
