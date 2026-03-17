// ------------------------------------------------------------------
// Search view — user and tweet search with tabs
// ------------------------------------------------------------------
function showSearch(fromPopstate) {
    currentView = 'search';
    window.scrollTo(0, 0);
    if (!fromPopstate) pushView('search');

    var timeline = document.getElementById('top');
    var tabs = document.getElementById('timeline-tabs');
    if (tabs) tabs.style.display = 'none';
    var composeBox = timeline.querySelector('.compose-box');
    var feed = document.getElementById('tweet-feed');
    if (composeBox) composeBox.style.display = 'none';
    if (feed) feed.style.display = 'none';

    // Remove other views
    ['profile-view', 'notif-view', 'search-view', 'tweet-detail-view', 'bookmarks-view'].forEach(function(cls) {
        var el = timeline.querySelector('.' + cls);
        if (el) el.remove();
    });

    var header = timeline.querySelector('.timeline-header h1');
    if (header) header.textContent = '探索';

    // Update nav active state
    document.querySelectorAll('.nav-item').forEach(function(el) { el.classList.remove('active'); });
    var searchNav = document.getElementById('search-nav');
    if (searchNav) searchNav.classList.add('active');

    var view = document.createElement('div');
    view.className = 'search-view';

    // Search input
    var searchBar = document.createElement('div');
    searchBar.className = 'search-bar';
    var searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'search-input';
    searchInput.placeholder = 'ユーザーまたはツイートを検索';
    searchInput.id = 'search-input';
    searchBar.appendChild(searchInput);
    view.appendChild(searchBar);

    // Search mode tabs: ユーザー / ツイート
    var searchTabs = document.createElement('div');
    searchTabs.className = 'timeline-tabs';
    var userTab = document.createElement('button');
    userTab.className = 'timeline-tab active';
    userTab.textContent = 'ユーザー';
    var tweetTab = document.createElement('button');
    tweetTab.className = 'timeline-tab';
    tweetTab.textContent = 'ツイート';
    searchTabs.appendChild(userTab);
    searchTabs.appendChild(tweetTab);
    view.appendChild(searchTabs);

    var results = document.createElement('div');
    results.id = 'search-results';
    view.appendChild(results);

    timeline.appendChild(view);
    searchInput.focus();

    var searchMode = 'users'; // 'users' or 'tweets'

    userTab.onclick = function() {
        userTab.classList.add('active');
        tweetTab.classList.remove('active');
        searchMode = 'users';
        var q = searchInput.value.trim();
        if (q) runSearch(q);
        else results.innerHTML = '';
    };
    tweetTab.onclick = function() {
        tweetTab.classList.add('active');
        userTab.classList.remove('active');
        searchMode = 'tweets';
        var q = searchInput.value.trim();
        if (q) runSearch(q);
        else results.innerHTML = '';
    };

    function runSearch(q) {
        if (searchMode === 'users') {
            fetch('/api/users/search?q=' + encodeURIComponent(q))
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    results.innerHTML = '';
                    if (!data.users || data.users.length === 0) {
                        results.innerHTML = '<div style="padding:40px 20px;text-align:center;color:var(--text-secondary)">見つかりませんでした</div>';
                        return;
                    }
                    data.users.forEach(function(u) {
                        var item = document.createElement('div');
                        item.className = 'search-result-item';
                        item.onclick = function() { showProfile(u.handle); };
                        var av = buildAvatar(u, 42);

                        var info = document.createElement('div');
                        info.className = 'search-result-info';
                        var name = document.createElement('div');
                        name.className = 'search-result-name';
                        name.textContent = u.display_name;
                        var handle = document.createElement('div');
                        handle.className = 'search-result-handle';
                        handle.textContent = u.handle;
                        info.appendChild(name);
                        info.appendChild(handle);
                        if (u.bio) {
                            var bio = document.createElement('div');
                            bio.className = 'search-result-bio';
                            bio.textContent = u.bio.length > 80 ? u.bio.substring(0, 80) + '...' : u.bio;
                            info.appendChild(bio);
                        }
                        item.appendChild(av);
                        item.appendChild(info);
                        results.appendChild(item);
                    });
                })
                .catch(function(err) { console.error('Search failed:', err); });
        } else {
            // Tweet search — use /api/tweets/search endpoint
            fetch('/api/tweets/search?q=' + encodeURIComponent(q))
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    results.innerHTML = '';
                    if (!data.tweets || data.tweets.length === 0) {
                        results.innerHTML = '<div style="padding:40px 20px;text-align:center;color:var(--text-secondary)">見つかりませんでした</div>';
                        return;
                    }
                    data.tweets.forEach(function(tweet) {
                        results.appendChild(buildTweetCard(tweet));
                    });
                })
                .catch(function(err) { console.error('Tweet search failed:', err); });
        }
    }

    // Debounced search
    var debounceTimer;
    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        var q = searchInput.value.trim();
        if (!q) {
            results.innerHTML = '';
            return;
        }
        debounceTimer = setTimeout(function() { runSearch(q); }, 300);
    });
}

// ------------------------------------------------------------------
// Hashtag click — open search view with hashtag pre-filled
// ------------------------------------------------------------------
function searchHashtag(tag) {
    showSearch();
    setTimeout(function() {
        var input = document.getElementById('search-input');
        if (input) {
            input.value = '#' + tag;
            input.dispatchEvent(new Event('input'));
        }
    }, 100);
}

// ------------------------------------------------------------------
// Load recommended users into the right sidebar
// ------------------------------------------------------------------
function buildBotItem(bot) {
    var item = document.createElement('div');
    item.className = 'bot-item';
    item.style.cursor = 'pointer';
    item.onclick = function(e) {
        if (e.target.classList.contains('follow-btn')) return;
        showProfile(bot.handle);
    };

    var av = buildAvatar(bot, 40);

    var info = document.createElement('div');
    info.className = 'bot-info';

    var name = document.createElement('div');
    name.className = 'bot-name';
    name.textContent = bot.display_name;

    var handle = document.createElement('div');
    handle.className = 'bot-handle';
    handle.textContent = bot.handle;

    info.appendChild(name);
    info.appendChild(handle);
    // No bio in sidebar — too cramped

    var followBtn = document.createElement('button');
    followBtn.className = 'follow-btn';
    followBtn.setAttribute('aria-label', bot.display_name + 'をフォローする');
    if (bot.is_following) {
        followBtn.textContent = 'フォロー中';
        followBtn.style.background = 'transparent';
        followBtn.style.color = 'var(--text-primary)';
        followBtn.style.border = '1px solid var(--text-secondary)';
    } else {
        followBtn.textContent = 'フォローする';
    }
    followBtn.onclick = function(e) {
        e.stopPropagation();
        fetch('/api/users/' + bot.id + '/follow', { method: 'POST' })
            .then(function(r) {
                if (r.status === 401) { showRegistrationModal(); return null; }
                return r.json();
            })
            .then(function(data) {
                if (!data) return;
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
            });
    };

    item.appendChild(av);
    item.appendChild(info);
    item.appendChild(followBtn);
    return item;
}

function loadBotAccounts() {
    fetch('/api/users')
        .then(function(res) { return res.json(); })
        .then(function(data) {
            var botList = document.getElementById('bot-list');
            botList.innerHTML = '';
            var bots = data.users.filter(function(u) { return u.is_bot; });
            // Shuffle randomly
            for (var i = bots.length - 1; i > 0; i--) {
                var j = Math.floor(Math.random() * (i + 1));
                var tmp = bots[i]; bots[i] = bots[j]; bots[j] = tmp;
            }
            var showCount = Math.min(bots.length, 5);

            for (var i = 0; i < showCount; i++) {
                botList.appendChild(buildBotItem(bots[i]));
            }

            if (bots.length > 5) {
                var expanded = false;
                var extraItems = [];
                var toggle = document.createElement('div');
                toggle.className = 'show-more-link';
                toggle.textContent = 'さらに表示';
                toggle.onclick = function() {
                    if (!expanded) {
                        for (var j = 5; j < bots.length; j++) {
                            var item = buildBotItem(bots[j]);
                            extraItems.push(item);
                            botList.insertBefore(item, toggle);
                        }
                        toggle.textContent = '閉じる';
                        expanded = true;
                    } else {
                        extraItems.forEach(function(el) { el.remove(); });
                        extraItems = [];
                        toggle.textContent = 'さらに表示';
                        expanded = false;
                    }
                };
                botList.appendChild(toggle);
            }
        })
        .catch(function(err) {
            console.error('Failed to load users:', err);
        });
}
