// ------------------------------------------------------------------
// Current logged-in user (set by initApp)
// ------------------------------------------------------------------
var currentUser = null;

// ------------------------------------------------------------------
// Current view state — 'timeline' or 'profile'
// ------------------------------------------------------------------
var currentView = 'timeline';

// ------------------------------------------------------------------
// Current timeline tab — 'all' or 'following'
// ------------------------------------------------------------------
var currentTab = 'all';

// ------------------------------------------------------------------
// Image upload for compose box
// ------------------------------------------------------------------
var composeImageFile = null;

function previewComposeImage(input) {
    if (input.files && input.files[0]) {
        composeImageFile = input.files[0];
        var reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('compose-image-thumb').src = e.target.result;
            document.getElementById('compose-image-preview').style.display = 'block';
        };
        reader.readAsDataURL(input.files[0]);
        // Update submit button state since an image is now attached
        updateCharCounter();
    }
}

function clearComposeImage() {
    composeImageFile = null;
    document.getElementById('compose-image-input').value = '';
    document.getElementById('compose-image-preview').style.display = 'none';
    updateCharCounter();
}

// ------------------------------------------------------------------
// Character counter — SVG progress ring
// ------------------------------------------------------------------
function updateCharCounter() {
    var textarea = document.getElementById('compose-input');
    var counter = document.getElementById('char-counter');
    var submitBtn = document.getElementById('compose-submit');
    var remaining = 280 - textarea.value.length;
    var progress = textarea.value.length / 280;

    // SVG circle progress ring
    var radius = 10;
    var circumference = 2 * Math.PI * radius;
    var offset = circumference * (1 - Math.min(progress, 1));

    var color = remaining <= 0 ? 'var(--like-color)' : remaining <= 20 ? '#fbbf24' : 'var(--accent)';

    counter.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">'
        + '<circle cx="12" cy="12" r="' + radius + '" fill="none" stroke="var(--border)" stroke-width="2"/>'
        + '<circle cx="12" cy="12" r="' + radius + '" fill="none" stroke="' + color + '" stroke-width="2" '
        + 'stroke-dasharray="' + circumference + '" stroke-dashoffset="' + offset + '" '
        + 'transform="rotate(-90 12 12)" stroke-linecap="round"/>'
        + (remaining <= 20 ? '<text x="12" y="16" text-anchor="middle" font-size="8" fill="' + color + '">' + remaining + '</text>' : '')
        + '</svg>';

    submitBtn.disabled = remaining < 0 || (textarea.value.trim().length === 0 && !composeImageFile);
}

// ------------------------------------------------------------------
// Scroll to top helper (used by left sidebar nav + Tweet button)
// ------------------------------------------------------------------
function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    document.getElementById('compose-input').focus();
}

// ------------------------------------------------------------------
// Timeline tab switching — updates currentTab and reloads feed
// ------------------------------------------------------------------
function switchTab(el) {
    document.querySelectorAll('.timeline-tab').forEach(function(t) { t.classList.remove('active'); });
    el.classList.add('active');

    if (el.textContent.trim() === 'フォロー中') {
        currentTab = 'following';
    } else {
        currentTab = 'all';
    }

    // Reset pagination state and do a fresh load
    hasMoreTweets = true;
    document.getElementById('new-tweets-bar').style.display = 'none';
    loadTweets();
}

// ------------------------------------------------------------------
// Dark / Light theme toggle
// ------------------------------------------------------------------
function applyTheme(theme) {
    var html = document.documentElement;
    var icon = document.getElementById('theme-icon');
    var label = document.getElementById('theme-label');

    if (theme === 'light') {
        html.setAttribute('data-theme', 'light');
        // Switch to sun icon
        icon.innerHTML = '<circle cx="12" cy="12" r="5" stroke="currentColor" stroke-width="2" fill="none"/>'
            + '<line x1="12" y1="2" x2="12" y2="4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
            + '<line x1="12" y1="20" x2="12" y2="22" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
            + '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
            + '<line x1="18.36" y1="18.36" x2="19.78" y2="19.78" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
            + '<line x1="2" y1="12" x2="4" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
            + '<line x1="20" y1="12" x2="22" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
            + '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
            + '<line x1="18.36" y1="5.64" x2="19.78" y2="4.22" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>';
        if (label) label.textContent = 'ダークモード';
    } else {
        html.removeAttribute('data-theme');
        // Restore moon icon
        icon.innerHTML = '<path id="theme-icon-path" d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
        if (label) label.textContent = 'ライトモード';
    }
}

function toggleTheme() {
    var current = document.documentElement.getAttribute('data-theme');
    var next = current === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', next);
    applyTheme(next);
}

// On page load, read saved preference — default to dark
(function initTheme() {
    var saved = localStorage.getItem('theme') || 'dark';
    applyTheme(saved);
})();

// ------------------------------------------------------------------
// Registration modal — show / hide
// ------------------------------------------------------------------
function showRegistrationModal() {
    document.getElementById('registration-modal').style.display = 'flex';
    document.getElementById('reg-display-name').focus();
}

function hideRegistrationModal() {
    document.getElementById('registration-modal').style.display = 'none';
}

function submitRegistration() {
    var displayName = document.getElementById('reg-display-name').value.trim();
    var handle = document.getElementById('reg-handle').value.trim();
    var errorEl = document.getElementById('reg-error');
    var submitBtn = document.getElementById('reg-submit');

    errorEl.textContent = '';

    if (!displayName) {
        errorEl.textContent = '表示名を入力してください。';
        return;
    }
    if (!handle) {
        errorEl.textContent = 'ハンドルを入力してください。';
        return;
    }

    // Auto-prepend @ if user forgot it
    if (!handle.startsWith('@')) {
        handle = '@' + handle;
    }

    submitBtn.disabled = true;

    fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ display_name: displayName, handle: handle })
    })
    .then(function(res) { return res.json().then(function(data) { return { status: res.status, data: data }; }); })
    .then(function(result) {
        if (result.status === 200 || result.status === 201) {
            currentUser = result.data.user;
            hideRegistrationModal();
            updateComposeAvatar();
            loadTweets();
            loadBotAccounts();
        } else {
            errorEl.textContent = result.data.error || '登録に失敗しました。もう一度お試しください。';
        }
    })
    .catch(function(err) {
        console.error('Registration failed:', err);
        errorEl.textContent = '登録に失敗しました。もう一度お試しください。';
    })
    .finally(function() {
        submitBtn.disabled = false;
    });
}

// ------------------------------------------------------------------
// Show timeline (home view)
// ------------------------------------------------------------------
function showTimeline(fromPopstate) {
    var timeline = document.getElementById('top');

    // Remove profile, notification, search, tweet-detail, and bookmarks views
    var profileView = timeline.querySelector('.profile-view');
    if (profileView) profileView.remove();
    var notifView = timeline.querySelector('.notif-view');
    if (notifView) notifView.remove();
    var searchView = timeline.querySelector('.search-view');
    if (searchView) searchView.remove();
    var detailView = timeline.querySelector('.tweet-detail-view');
    if (detailView) detailView.remove();
    var bookmarksView = timeline.querySelector('.bookmarks-view');
    if (bookmarksView) bookmarksView.remove();

    // Show tabs, compose box and feed
    var tabs = document.getElementById('timeline-tabs');
    if (tabs) tabs.style.display = 'flex';
    // Re-highlight current tab
    document.querySelectorAll('.timeline-tab').forEach(function(t) {
        t.classList.remove('active');
        if ((currentTab === 'all' && t.textContent.trim() === 'おすすめ') ||
            (currentTab === 'following' && t.textContent.trim() === 'フォロー中')) {
            t.classList.add('active');
        }
    });
    var composeBox = timeline.querySelector('.compose-box');
    var feed = document.getElementById('tweet-feed');
    if (composeBox) composeBox.style.display = 'flex';
    if (feed) feed.style.display = 'flex';

    // Restore header
    var header = timeline.querySelector('.timeline-header h1');
    if (header) header.textContent = 'ホーム';

    // Update nav active states
    document.querySelectorAll('.nav-item').forEach(function(btn) {
        btn.classList.remove('active');
    });
    var homeNav = document.getElementById('home-nav');
    if (homeNav) homeNav.classList.add('active');

    currentView = 'timeline';
    if (!fromPopstate) pushView('timeline');
    loadTweets();
}

// ------------------------------------------------------------------
// Poll for new tweets — show "新しいツイートがあります" bar
// ------------------------------------------------------------------
function pollNewTweets() {
    if (currentView !== 'timeline') return;
    fetch('/api/tweets?page=1&limit=1')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.tweets && data.tweets.length > 0
                    && data.tweets[0].id > lastKnownLatestId
                    && lastKnownLatestId > 0) {
                document.getElementById('new-tweets-bar').style.display = 'block';
            }
        })
        .catch(function() {});
}

function loadNewTweets() {
    document.getElementById('new-tweets-bar').style.display = 'none';
    window.scrollTo(0, 0);
    hasMoreTweets = true;
    loadTweets(false); // fresh load
}

// ------------------------------------------------------------------
// SPA history management (browser back/forward)
// ------------------------------------------------------------------
function pushView(view, params) {
    var state = { view: view };
    if (params) state.params = params;
    history.pushState(state, '', '');
}

window.addEventListener('popstate', function(e) {
    var state = e.state;
    if (!state || !state.view || state.view === 'timeline') {
        showTimeline(true);
    } else if (state.view === 'profile' && state.params) {
        showProfile(state.params, true);
    } else if (state.view === 'notifications') {
        showNotifications(true);
    } else if (state.view === 'search') {
        showSearch(true);
    } else if (state.view === 'tweet-detail' && state.params) {
        showTweetDetail(state.params, true);
    } else if (state.view === 'bookmarks') {
        showBookmarks(true);
    } else {
        showTimeline(true);
    }
});

// ------------------------------------------------------------------
// App initialisation — check cookie auth first
// ------------------------------------------------------------------
function initApp() {
    fetch('/api/me')
        .then(function(res) { return res.json(); })
        .then(function(data) {
            if (data.user) {
                currentUser = data.user;
                updateComposeAvatar();
                loadTweets();
                loadBotAccounts();
                pollNotifications();
            } else {
                showRegistrationModal();
                // Still load tweets and bots in the background so they
                // are ready when the modal closes
                loadTweets();
                loadBotAccounts();
            }
        })
        .catch(function(err) {
            console.error('Failed to check auth status:', err);
            // Fall through — show app anyway and let tweet / like fail with 401
            loadTweets();
            loadBotAccounts();
        });
}

// ------------------------------------------------------------------
// Infinite scroll — load more tweets when near the bottom
// ------------------------------------------------------------------
window.addEventListener('scroll', function() {
    if (currentView !== 'timeline') return;
    if (isLoadingMore || !hasMoreTweets) return;

    // Load more when user is within 500px of the bottom
    if (window.innerHeight + window.scrollY >= document.body.scrollHeight - 500) {
        loadTweets(true);
    }
});

// ------------------------------------------------------------------
// Event listeners set up after DOM is ready
// ------------------------------------------------------------------
document.getElementById('compose-input').addEventListener('input', updateCharCounter);
// Initialize the ring on page load
updateCharCounter();

// Allow Ctrl+Enter / Cmd+Enter to submit
document.getElementById('compose-input').addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        postTweet();
    }
});

// Allow Enter key in registration inputs to submit
document.getElementById('reg-display-name').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') { document.getElementById('reg-handle').focus(); }
});
document.getElementById('reg-handle').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') { submitRegistration(); }
});

// "さらに表示" link in the trending panel — toggles 4 hidden extra items
var trendExpanded = false;
document.getElementById('trend-show-more').addEventListener('click', function() {
    var panel = this.closest('.panel');
    var extras = panel.querySelectorAll('.trending-extra');
    if (!trendExpanded) {
        extras.forEach(function(el) { el.style.display = ''; });
        this.textContent = '閉じる';
        trendExpanded = true;
    } else {
        extras.forEach(function(el) { el.style.display = 'none'; });
        this.textContent = 'さらに表示';
        trendExpanded = false;
    }
});

// Close users-list modal when clicking the overlay background
document.getElementById('users-list-modal').addEventListener('click', function(e) {
    if (e.target === this) this.style.display = 'none';
});

// ------------------------------------------------------------------
// Initialise
// ------------------------------------------------------------------
history.replaceState({ view: 'timeline' }, '', '');
initApp();

// Poll for new tweets and notification badge every 10 seconds.
// Auto-refresh of the feed is replaced by the "新しいツイート" bar —
// only the top-1 tweet id is fetched here to detect new arrivals.
setInterval(function() {
    pollNewTweets();
    pollNotifications();
}, 10000);
