// ------------------------------------------------------------------
// Scheduled Tweet UI
// ------------------------------------------------------------------

// Holds the ISO string of the scheduled time, or null
var scheduledAt = null;

// Reference to the open schedule popup, or null
var schedulePopupEl = null;

// ------------------------------------------------------------------
// Show / toggle the schedule datetime popup
// ------------------------------------------------------------------
function showSchedulePopup(anchorBtn) {
    if (schedulePopupEl) {
        closeSchedulePopup();
        return;
    }

    var popup = document.createElement('div');
    popup.className = 'schedule-popup';
    popup.setAttribute('role', 'dialog');
    popup.setAttribute('aria-label', '送信日時を設定');

    var label = document.createElement('label');
    label.setAttribute('for', 'schedule-dt-input');
    label.textContent = '送信日時を選択';
    popup.appendChild(label);

    var input = document.createElement('input');
    input.type = 'datetime-local';
    input.id = 'schedule-dt-input';
    input.className = 'schedule-datetime-input';

    // Set minimum to now + 1 minute
    var minDate = new Date(Date.now() + 60000);
    input.min = toLocalISOString(minDate);

    // If a time is already set, pre-fill
    if (scheduledAt) {
        input.value = scheduledAt.slice(0, 16);
    }

    popup.appendChild(input);

    var actions = document.createElement('div');
    actions.className = 'schedule-popup-actions';

    var cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn-cancel';
    cancelBtn.textContent = 'キャンセル';
    cancelBtn.setAttribute('type', 'button');
    cancelBtn.onclick = function(e) {
        e.stopPropagation();
        // If there was already a scheduled time, clear it
        scheduledAt = null;
        updateScheduleUI();
        closeSchedulePopup();
    };

    var setBtn = document.createElement('button');
    setBtn.className = 'btn-set';
    setBtn.textContent = '設定';
    setBtn.setAttribute('type', 'button');
    setBtn.onclick = function(e) {
        e.stopPropagation();
        var val = input.value;
        if (!val) {
            scheduledAt = null;
        } else {
            // Convert local datetime-local value to ISO string
            scheduledAt = new Date(val).toISOString();
        }
        updateScheduleUI();
        closeSchedulePopup();
    };

    actions.appendChild(cancelBtn);
    actions.appendChild(setBtn);
    popup.appendChild(actions);

    document.body.appendChild(popup);
    schedulePopupEl = popup;

    // Position above/below the anchor
    var rect = anchorBtn.getBoundingClientRect();
    var popupHeight = 140;
    var top;
    if (rect.top > popupHeight + 8) {
        top = rect.top - popupHeight - 8;
    } else {
        top = rect.bottom + 8;
    }
    var left = Math.max(8, Math.min(rect.left - 60, window.innerWidth - 300));
    popup.style.top = top + 'px';
    popup.style.left = left + 'px';

    input.focus();

    setTimeout(function() {
        document.addEventListener('click', scheduleOutsideClick, true);
        document.addEventListener('keydown', scheduleEscHandler);
    }, 10);
}

function closeSchedulePopup() {
    if (schedulePopupEl) {
        schedulePopupEl.remove();
        schedulePopupEl = null;
    }
    document.removeEventListener('click', scheduleOutsideClick, true);
    document.removeEventListener('keydown', scheduleEscHandler);
}

function scheduleOutsideClick(e) {
    if (schedulePopupEl && !schedulePopupEl.contains(e.target)) {
        closeSchedulePopup();
    }
}

function scheduleEscHandler(e) {
    if (e.key === 'Escape') closeSchedulePopup();
}

// ------------------------------------------------------------------
// Update UI after setting / clearing a schedule
// ------------------------------------------------------------------
function updateScheduleUI() {
    var submitBtn = document.getElementById('compose-submit');
    var footer = document.querySelector('.compose-footer');

    // Remove any existing indicator
    var existing = document.getElementById('schedule-indicator');
    if (existing) existing.remove();

    if (scheduledAt) {
        // Change button text
        if (submitBtn) submitBtn.textContent = '予約する';

        // Add indicator chip
        var indicator = document.createElement('span');
        indicator.id = 'schedule-indicator';
        indicator.className = 'schedule-indicator';

        var schedBtn = document.getElementById('schedule-toggle-btn');
        indicator.innerHTML = '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> '
            + formatScheduledTime(scheduledAt);
        indicator.title = '予約をキャンセルするにはクリック';
        indicator.onclick = function() {
            scheduledAt = null;
            updateScheduleUI();
        };

        // Insert before the char counter
        var counter = document.getElementById('char-counter');
        if (counter && counter.parentNode) {
            counter.parentNode.insertBefore(indicator, counter);
        }
    } else {
        // Restore button text
        if (submitBtn) submitBtn.textContent = 'ツイートする';
    }
}

function formatScheduledTime(isoString) {
    var d = new Date(isoString);
    var mm = d.getMonth() + 1;
    var dd = d.getDate();
    var hh = String(d.getHours()).padStart(2, '0');
    var min = String(d.getMinutes()).padStart(2, '0');
    return mm + '/' + dd + ' ' + hh + ':' + min;
}

// Convert Date to datetime-local string (YYYY-MM-DDTHH:MM)
function toLocalISOString(date) {
    var year = date.getFullYear();
    var month = String(date.getMonth() + 1).padStart(2, '0');
    var day = String(date.getDate()).padStart(2, '0');
    var hours = String(date.getHours()).padStart(2, '0');
    var minutes = String(date.getMinutes()).padStart(2, '0');
    return year + '-' + month + '-' + day + 'T' + hours + ':' + minutes;
}

// ------------------------------------------------------------------
// Override postTweet to handle scheduled tweets
// The original postTweet is wrapped below after the file is loaded.
// ------------------------------------------------------------------
var _originalPostTweet = null;

function initScheduleModule() {
    // Wrap the original postTweet defined in tweets.js
    if (typeof postTweet === 'function' && !_originalPostTweet) {
        _originalPostTweet = postTweet;
        postTweet = function() {
            if (scheduledAt) {
                postScheduledTweet();
            } else {
                _originalPostTweet();
            }
        };
    }
}

function postScheduledTweet() {
    var textarea = document.getElementById('compose-input');
    var content = textarea.value.trim();
    if (!content) return;

    var submitBtn = document.getElementById('compose-submit');
    if (submitBtn) submitBtn.disabled = true;

    fetch('/api/tweets/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: content, scheduled_at: scheduledAt })
    })
    .then(function(res) {
        if (res.status === 401) { showRegistrationModal(); return null; }
        if (res.status === 404) {
            // Backend doesn't support scheduling yet — show toast
            showCopyToast('予約機能は未実装です');
            return null;
        }
        return res.json();
    })
    .then(function(data) {
        if (!data) return;
        textarea.value = '';
        scheduledAt = null;
        updateScheduleUI();
        if (typeof updateCharCounter === 'function') updateCharCounter();
        if (typeof clearDraft === 'function') clearDraft();
        if (typeof autoResizeTextarea === 'function') autoResizeTextarea(textarea);
        showCopyToast('ツイートを予約しました');
    })
    .catch(function(err) {
        console.error('Failed to schedule tweet:', err);
        showCopyToast('予約に失敗しました');
    })
    .finally(function() {
        if (submitBtn) submitBtn.disabled = false;
    });
}

// ------------------------------------------------------------------
// Show scheduled tweets view
// ------------------------------------------------------------------
function showScheduledTweets() {
    var timeline = document.getElementById('top');

    // Remove existing auxiliary views
    ['profile-view', 'notif-view', 'search-view', 'tweet-detail-view', 'bookmarks-view', 'dm-view', 'lists-view', 'scheduled-view'].forEach(function(cls) {
        var el = timeline.querySelector('.' + cls);
        if (el) el.remove();
    });

    // Hide compose box and feed
    var composeBox = timeline.querySelector('.compose-box');
    var feed = document.getElementById('tweet-feed');
    var tabs = document.getElementById('timeline-tabs');
    if (composeBox) composeBox.style.display = 'none';
    if (feed) feed.style.display = 'none';
    if (tabs) tabs.style.display = 'none';

    // Update header
    var header = timeline.querySelector('.timeline-header h1');
    if (header) header.textContent = '予約ツイート';

    // Update nav
    document.querySelectorAll('.nav-item').forEach(function(btn) {
        btn.classList.remove('active');
    });

    var view = document.createElement('div');
    view.className = 'scheduled-view';

    var loadingEl = document.createElement('div');
    loadingEl.className = 'feed-placeholder';
    loadingEl.textContent = '読み込み中…';
    view.appendChild(loadingEl);
    timeline.appendChild(view);

    fetch('/api/tweets/scheduled')
        .then(function(res) {
            if (res.status === 404) return { tweets: [] };
            return res.json();
        })
        .then(function(data) {
            view.innerHTML = '';
            var tweets = data.tweets || data.scheduled || [];
            if (tweets.length === 0) {
                var empty = document.createElement('div');
                empty.className = 'feed-placeholder';
                empty.innerHTML = '<div style="font-size:1.1rem;font-weight:700;color:var(--text-primary);margin-bottom:8px">予約ツイートはありません</div><div>ツイート作成時に時計アイコンで日時を指定してください。</div>';
                view.appendChild(empty);
                return;
            }
            tweets.forEach(function(tweet) {
                var item = document.createElement('div');
                item.className = 'scheduled-tweet-item';

                var info = document.createElement('div');
                info.className = 'scheduled-tweet-info';

                var timeEl = document.createElement('div');
                timeEl.className = 'scheduled-tweet-time';
                timeEl.innerHTML = '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> '
                    + (tweet.scheduled_at ? formatScheduledTime(tweet.scheduled_at) : '');

                var contentEl = document.createElement('div');
                contentEl.className = 'scheduled-tweet-content';
                contentEl.textContent = tweet.content;

                info.appendChild(timeEl);
                info.appendChild(contentEl);

                var cancelBtn = document.createElement('button');
                cancelBtn.className = 'scheduled-cancel-btn';
                cancelBtn.textContent = 'キャンセル';
                (function(id, el) {
                    cancelBtn.onclick = function() {
                        if (!confirm('この予約ツイートをキャンセルしますか？')) return;
                        fetch('/api/tweets/scheduled/' + id, { method: 'DELETE' })
                            .then(function() { el.remove(); })
                            .catch(function() { showCopyToast('キャンセルに失敗しました'); });
                    };
                })(tweet.id, item);

                item.appendChild(info);
                item.appendChild(cancelBtn);
                view.appendChild(item);
            });
        })
        .catch(function() {
            view.innerHTML = '<div class="feed-placeholder">読み込みに失敗しました</div>';
        });

    if (typeof pushView === 'function') pushView('scheduled');
}

// Initialize after DOM is ready (called at bottom of index.html after all scripts load)
document.addEventListener('DOMContentLoaded', function() {
    initScheduleModule();
});
// Also try immediately in case DOMContentLoaded already fired
initScheduleModule();
