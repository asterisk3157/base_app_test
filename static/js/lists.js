// ------------------------------------------------------------------
// Feature 12: List management UI
// ------------------------------------------------------------------

function showLists(fromPopstate) {
    currentView = 'lists';
    window.scrollTo(0, 0);
    if (!fromPopstate) pushView('lists');

    var timeline = document.getElementById('top');
    var tabs = document.getElementById('timeline-tabs');
    if (tabs) tabs.style.display = 'none';
    var composeBox = timeline.querySelector('.compose-box');
    var feed = document.getElementById('tweet-feed');
    if (composeBox) composeBox.style.display = 'none';
    if (feed) feed.style.display = 'none';

    ['profile-view', 'notif-view', 'search-view', 'tweet-detail-view', 'bookmarks-view', 'dm-view', 'lists-view'].forEach(function(cls) {
        var el = timeline.querySelector('.' + cls);
        if (el) el.remove();
    });

    var header = timeline.querySelector('.timeline-header h1');
    if (header) header.textContent = 'リスト';

    document.querySelectorAll('.nav-item').forEach(function(btn) { btn.classList.remove('active'); });
    var listsNav = document.getElementById('lists-nav');
    if (listsNav) listsNav.classList.add('active');

    var view = document.createElement('div');
    view.className = 'lists-view';
    timeline.appendChild(view);

    // "リストを作成" button
    var createBtn = document.createElement('button');
    createBtn.className = 'create-list-btn';
    createBtn.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> リストを作成';
    createBtn.onclick = function() { showCreateListModal(function() { showLists(); }); };
    view.appendChild(createBtn);

    if (!currentUser) {
        view.innerHTML += '<div class="feed-placeholder">ログインしてリスト機能を使いましょう</div>';
        return;
    }

    // Loading indicator
    var loadingEl = document.createElement('div');
    loadingEl.className = 'feed-placeholder';
    loadingEl.textContent = '読み込み中…';
    view.appendChild(loadingEl);

    fetch('/api/lists')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            loadingEl.remove();
            var lists = data.lists || [];
            if (lists.length === 0) {
                var empty = document.createElement('div');
                empty.className = 'feed-placeholder';
                empty.innerHTML = '<div style="font-size:1.1rem;font-weight:700;color:var(--text-primary);margin-bottom:8px">リストがありません</div><div>リストを作成してタイムラインを整理しよう</div>';
                view.appendChild(empty);
                return;
            }
            lists.forEach(function(list) {
                view.appendChild(buildListItem(list));
            });
        })
        .catch(function() {
            loadingEl.textContent = '読み込みに失敗しました';
        });
}

function buildListItem(list) {
    var item = document.createElement('div');
    item.className = 'list-item';
    item.onclick = function() { showListTimeline(list); };

    var icon = document.createElement('div');
    icon.className = 'list-item-icon';
    icon.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>';

    var info = document.createElement('div');
    info.className = 'list-item-info';
    var name = document.createElement('div');
    name.className = 'list-item-name';
    name.textContent = list.name;
    var count = document.createElement('div');
    count.className = 'list-item-count';
    count.textContent = (list.member_count || 0) + '人のメンバー' + (list.description ? ' · ' + list.description : '');
    info.appendChild(name);
    info.appendChild(count);

    item.appendChild(icon);
    item.appendChild(info);

    // Arrow
    var arrow = document.createElement('span');
    arrow.style.cssText = 'color:var(--text-secondary);font-size:1.1rem;flex-shrink:0';
    arrow.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>';
    item.appendChild(arrow);

    return item;
}

function showListTimeline(list) {
    var timeline = document.getElementById('top');
    var header = timeline.querySelector('.timeline-header h1');
    if (header) header.textContent = list.name;

    var view = timeline.querySelector('.lists-view');
    if (view) view.innerHTML = '';
    else {
        view = document.createElement('div');
        view.className = 'lists-view';
        timeline.appendChild(view);
    }

    var loadingEl = document.createElement('div');
    loadingEl.className = 'feed-placeholder';
    loadingEl.textContent = '読み込み中…';
    view.appendChild(loadingEl);

    fetch('/api/lists/' + list.id + '/timeline')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            loadingEl.remove();
            var tweets = data.tweets || [];
            if (tweets.length === 0) {
                var empty = document.createElement('div');
                empty.className = 'feed-placeholder';
                empty.textContent = 'まだありません';
                view.appendChild(empty);
                return;
            }
            tweets.forEach(function(tweet) {
                view.appendChild(buildTweetCard(tweet));
            });
        })
        .catch(function() {
            loadingEl.textContent = '読み込みに失敗しました';
        });
}

// ------------------------------------------------------------------
// Create list modal
// ------------------------------------------------------------------
function showCreateListModal(onSuccess) {
    var modal = document.getElementById('create-list-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'create-list-modal';
        modal.onclick = function(e) { if (e.target === modal) modal.style.display = 'none'; };

        var card = document.createElement('div');
        card.className = 'modal-card';
        card.style.position = 'relative';
        card.style.textAlign = 'left';

        var closeBtn = document.createElement('button');
        closeBtn.style.cssText = 'position:absolute;top:12px;right:16px;background:none;color:var(--text-secondary);font-size:1.4rem;padding:4px 8px;border-radius:9999px;cursor:pointer;border:none';
        closeBtn.innerHTML = '&times;';
        closeBtn.onclick = function() { modal.style.display = 'none'; };

        var title = document.createElement('h2');
        title.className = 'modal-title';
        title.textContent = 'リストを作成';
        title.style.textAlign = 'center';

        var nameInput = document.createElement('input');
        nameInput.type = 'text';
        nameInput.className = 'modal-input';
        nameInput.id = 'list-name-input';
        nameInput.placeholder = 'リスト名';
        nameInput.maxLength = 50;

        var descInput = document.createElement('input');
        descInput.type = 'text';
        descInput.className = 'modal-input';
        descInput.id = 'list-desc-input';
        descInput.placeholder = '説明（任意）';
        descInput.maxLength = 100;

        var errorEl = document.createElement('div');
        errorEl.className = 'modal-error';
        errorEl.id = 'list-error';

        var submitBtn = document.createElement('button');
        submitBtn.className = 'modal-submit';
        submitBtn.textContent = '作成';
        submitBtn.onclick = function() {
            var name = nameInput.value.trim();
            if (!name) { errorEl.textContent = 'リスト名を入力してください'; return; }
            submitBtn.disabled = true;
            fetch('/api/lists', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, description: descInput.value.trim() })
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) {
                    errorEl.textContent = data.error;
                    submitBtn.disabled = false;
                    return;
                }
                modal.style.display = 'none';
                nameInput.value = '';
                descInput.value = '';
                if (typeof onSuccess === 'function') onSuccess();
            })
            .catch(function() {
                errorEl.textContent = '作成に失敗しました';
                submitBtn.disabled = false;
            });
        };

        card.appendChild(closeBtn);
        card.appendChild(title);
        card.appendChild(nameInput);
        card.appendChild(descInput);
        card.appendChild(errorEl);
        card.appendChild(submitBtn);
        modal.appendChild(card);
        document.body.appendChild(modal);
    }

    document.getElementById('list-error').textContent = '';
    modal.style.display = 'flex';
    document.getElementById('list-name-input').focus();
}

// ------------------------------------------------------------------
// SPA popstate support for lists view
// ------------------------------------------------------------------
(function() {
    var origPopstate = window.onpopstate;
    window.addEventListener('popstate', function(e) {
        var state = e.state;
        if (state && state.view === 'lists') {
            showLists(true);
        }
    });
})();
