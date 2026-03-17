// ------------------------------------------------------------------
// Tweet-related state variables
// ------------------------------------------------------------------
var knownTweetIds = new Set();
var currentPage = 1;
var isLoadingMore = false;
var hasMoreTweets = true;
var lastKnownLatestId = 0;

// ------------------------------------------------------------------
// Render a single tweet card element (returns a DOM node)
// ------------------------------------------------------------------
function buildTweetCard(tweet) {
    const card = document.createElement('article');
    card.className = 'tweet-card';
    card.dataset.tweetId = tweet.id;

    const user = tweet.user;

    // Avatar (image or letter circle)
    const avatarEl = buildAvatar(user, 42);
    avatarEl.style.cursor = 'pointer';
    avatarEl.onclick = function() { showProfile(user.handle); };

    // Body
    const bodyEl = document.createElement('div');
    bodyEl.className = 'tweet-body';

    // Meta line
    const metaEl = document.createElement('div');
    metaEl.className = 'tweet-meta';

    const nameEl = document.createElement('span');
    nameEl.className = 'tweet-display-name';
    nameEl.textContent = user.display_name;
    nameEl.style.cursor = 'pointer';
    nameEl.onclick = function() { showProfile(user.handle); };

    const handleEl = document.createElement('span');
    handleEl.className = 'tweet-handle';
    handleEl.textContent = user.handle;
    handleEl.style.cursor = 'pointer';
    handleEl.onclick = function() { showProfile(user.handle); };

    const timeEl = document.createElement('span');
    timeEl.className = 'tweet-time';
    timeEl.textContent = timeAgo(tweet.created_at);
    timeEl.setAttribute('title', tweet.created_at);

    metaEl.appendChild(nameEl);
    metaEl.appendChild(handleEl);
    metaEl.appendChild(timeEl);

    // "···" more button — shown on all tweets, but delete menu only for own tweets
    var moreBtn = document.createElement('button');
    moreBtn.className = 'tweet-more-btn';
    moreBtn.innerHTML = '···';
    moreBtn.setAttribute('aria-label', 'その他のオプション');
    moreBtn.onclick = function(e) {
        e.stopPropagation();
        // Only show delete for own tweets
        if (!currentUser || tweet.user.id !== currentUser.id) return;

        var existing = document.querySelector('.tweet-context-menu');
        if (existing) existing.remove();

        var menu = document.createElement('div');
        menu.className = 'tweet-context-menu';

        var deleteItem = document.createElement('div');
        deleteItem.className = 'tweet-context-item delete';
        deleteItem.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg> 削除';
        deleteItem.onclick = function(e) {
            e.stopPropagation();
            menu.remove();
            if (confirm('このツイートを削除しますか？')) {
                fetch('/api/tweets/' + tweet.id, { method: 'DELETE' })
                    .then(function() { loadTweets(); });
            }
        };

        menu.appendChild(deleteItem);

        var rect = moreBtn.getBoundingClientRect();
        menu.style.position = 'fixed';
        menu.style.left = (rect.left - 120) + 'px';
        menu.style.top = (rect.bottom + 4) + 'px';
        document.body.appendChild(menu);

        setTimeout(function() {
            document.addEventListener('click', function close() {
                menu.remove();
                document.removeEventListener('click', close);
            }, { once: true });
        }, 10);
    };
    metaEl.appendChild(moreBtn);

    // Content
    const contentEl = document.createElement('div');
    contentEl.className = 'tweet-content';
    // Intentionally using innerHTML to make XSS easier for the lecture
    contentEl.innerHTML = tweet.content.replace(/\n/g, '<br>');
    // After setting innerHTML, wrap hashtags in clickable links
    contentEl.innerHTML = contentEl.innerHTML.replace(/#([^\s<]+)/g, '<a href="javascript:void(0)" onclick="searchHashtag(\'$1\')" style="color:var(--accent);text-decoration:none">#$1</a>');
    contentEl.style.cursor = 'pointer';
    contentEl.onclick = function(e) {
        // Don't trigger if clicking a link inside
        if (e.target.tagName === 'A') return;
        showTweetDetail(tweet.id);
    };

    // Action bar
    const actionsEl = document.createElement('div');
    actionsEl.className = 'tweet-actions';

    // Reply button (speech bubble icon)
    var replyBtn = document.createElement('button');
    replyBtn.className = 'reply-btn';
    replyBtn.setAttribute('aria-label', '返信');
    replyBtn.onclick = function() { toggleReplyBox(tweet.id); };

    var replySvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    replySvg.setAttribute('viewBox', '0 0 24 24');
    replySvg.setAttribute('width', '18');
    replySvg.setAttribute('height', '18');
    replySvg.setAttribute('aria-hidden', 'true');
    replySvg.style.fill = 'none';
    replySvg.style.stroke = 'currentColor';
    replySvg.style.strokeWidth = '2';

    var replyPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    replyPath.setAttribute('d', 'M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z');
    replySvg.appendChild(replyPath);

    var replyCountEl = document.createElement('span');
    replyCountEl.textContent = (tweet.reply_count && tweet.reply_count > 0) ? tweet.reply_count : '';

    replyBtn.appendChild(replySvg);
    replyBtn.appendChild(replyCountEl);
    actionsEl.appendChild(replyBtn);

    // Repost button
    var repostBtn = document.createElement('button');
    repostBtn.className = 'repost-btn' + (tweet.reposted ? ' reposted' : '');
    repostBtn.setAttribute('aria-label', 'リポスト');
    repostBtn.onclick = function(e) { e.stopPropagation(); showRepostMenu(tweet, repostBtn); };

    var repostSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    repostSvg.setAttribute('viewBox', '0 0 24 24');
    repostSvg.setAttribute('width', '18');
    repostSvg.setAttribute('height', '18');
    repostSvg.setAttribute('aria-hidden', 'true');
    repostSvg.style.fill = 'none';
    repostSvg.style.stroke = tweet.reposted ? '#00ba7c' : 'currentColor';
    repostSvg.style.strokeWidth = '2';
    repostSvg.style.strokeLinecap = 'round';
    repostSvg.style.strokeLinejoin = 'round';

    var repostPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    repostPath.setAttribute('d', 'M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3');
    repostSvg.appendChild(repostPath);

    var repostCountEl = document.createElement('span');
    repostCountEl.textContent = (tweet.reposts && tweet.reposts > 0) ? formatCount(tweet.reposts) : '';
    repostCountEl.style.cursor = (tweet.reposts && tweet.reposts > 0) ? 'pointer' : 'default';
    repostCountEl.onclick = function(e) {
        e.stopPropagation();
        if (tweet.reposts > 0) showUserList('リポストしたユーザー', '/api/tweets/' + tweet.id + '/reposts');
    };

    repostBtn.appendChild(repostSvg);
    repostBtn.appendChild(repostCountEl);
    actionsEl.appendChild(repostBtn);

    // Like button
    const likeBtn = document.createElement('button');
    likeBtn.className = 'like-btn' + (tweet.liked ? ' liked' : '');
    likeBtn.setAttribute('aria-label', 'Like tweet');
    likeBtn.setAttribute('aria-pressed', tweet.liked ? 'true' : 'false');
    likeBtn.onclick = function() { likeTweet(tweet.id); };

    const heartSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    heartSvg.setAttribute('viewBox', '0 0 24 24');
    heartSvg.setAttribute('width', '18');
    heartSvg.setAttribute('height', '18');
    heartSvg.setAttribute('aria-hidden', 'true');
    heartSvg.style.fill = tweet.liked ? 'var(--like-color)' : 'none';
    heartSvg.style.stroke = tweet.liked ? 'var(--like-color)' : 'currentColor';
    heartSvg.style.strokeWidth = '2';

    const heartPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    heartPath.setAttribute('d', 'M12 21.638h-.014C9.403 21.59 1.95 14.856 1.95 8.478c0-3.064 2.525-5.754 5.403-5.754 2.29 0 3.83 1.58 4.646 2.73.814-1.148 2.354-2.73 4.645-2.73 2.88 0 5.404 2.69 5.404 5.755 0 6.376-7.454 13.11-10.037 13.157H12z');
    heartSvg.appendChild(heartPath);

    const likeCountEl = document.createElement('span');
    likeCountEl.textContent = tweet.likes > 0 ? formatCount(tweet.likes) : '';
    likeCountEl.style.cursor = tweet.likes > 0 ? 'pointer' : 'default';
    likeCountEl.onclick = function(e) {
        e.stopPropagation();
        if (tweet.likes > 0) showUserList('いいねしたユーザー', '/api/tweets/' + tweet.id + '/likes');
    };

    likeBtn.appendChild(heartSvg);
    likeBtn.appendChild(likeCountEl);
    actionsEl.appendChild(likeBtn);

    // Impression count (eye icon) — display only
    var impressionBtn = document.createElement('span');
    impressionBtn.className = 'impression-count';
    impressionBtn.setAttribute('aria-label', 'インプレッション');

    var eyeSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    eyeSvg.setAttribute('viewBox', '0 0 24 24');
    eyeSvg.setAttribute('width', '18');
    eyeSvg.setAttribute('height', '18');
    eyeSvg.setAttribute('aria-hidden', 'true');
    eyeSvg.style.fill = 'none';
    eyeSvg.style.stroke = 'currentColor';
    eyeSvg.style.strokeWidth = '2';

    var eyePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    eyePath.setAttribute('d', 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z');
    eyeSvg.appendChild(eyePath);
    var eyeCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    eyeCircle.setAttribute('cx', '12');
    eyeCircle.setAttribute('cy', '12');
    eyeCircle.setAttribute('r', '3');
    eyeSvg.appendChild(eyeCircle);

    var impCount = document.createElement('span');
    impCount.textContent = (tweet.impressions && tweet.impressions > 0) ? formatCount(tweet.impressions) : '';

    impressionBtn.appendChild(eyeSvg);
    impressionBtn.appendChild(impCount);
    actionsEl.appendChild(impressionBtn);

    // Bookmark button (flag icon)
    var bookmarkBtn = document.createElement('button');
    bookmarkBtn.className = 'bookmark-btn' + (tweet.bookmarked ? ' bookmarked' : '');
    bookmarkBtn.setAttribute('aria-label', 'ブックマーク');
    var bookmarkSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    bookmarkSvg.setAttribute('viewBox', '0 0 24 24');
    bookmarkSvg.setAttribute('width', '18');
    bookmarkSvg.setAttribute('height', '18');
    bookmarkSvg.setAttribute('aria-hidden', 'true');
    bookmarkSvg.style.fill = tweet.bookmarked ? 'var(--accent)' : 'none';
    bookmarkSvg.style.stroke = tweet.bookmarked ? 'var(--accent)' : 'currentColor';
    bookmarkSvg.style.strokeWidth = '2';
    var bookmarkPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    bookmarkPath.setAttribute('d', 'M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z');
    bookmarkSvg.appendChild(bookmarkPath);
    bookmarkBtn.appendChild(bookmarkSvg);
    (function(btn, svg, tweetData) {
        btn.onclick = function(e) {
            e.stopPropagation();
            fetch('/api/tweets/' + tweetData.id + '/bookmark', { method: 'POST' })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.bookmarked) {
                        btn.classList.add('bookmarked');
                        svg.style.fill = 'var(--accent)';
                        svg.style.stroke = 'var(--accent)';
                    } else {
                        btn.classList.remove('bookmarked');
                        svg.style.fill = 'none';
                        svg.style.stroke = 'currentColor';
                    }
                });
        };
    })(bookmarkBtn, bookmarkSvg, tweet);
    actionsEl.appendChild(bookmarkBtn);

    bodyEl.appendChild(metaEl);
    bodyEl.appendChild(contentEl);

    // Tweet image display
    if (tweet.image_url) {
        var imgContainer = document.createElement('div');
        imgContainer.style.cssText = 'margin-top:8px;border-radius:16px;overflow:hidden;border:1px solid var(--border)';
        var tweetImg = document.createElement('img');
        tweetImg.src = tweet.image_url;
        tweetImg.style.cssText = 'width:100%;max-height:400px;object-fit:cover;display:block;cursor:pointer';
        tweetImg.alt = '';
        (function(url) {
            tweetImg.onclick = function(e) { e.stopPropagation(); showImageModal(url); };
        })(tweet.image_url);
        imgContainer.appendChild(tweetImg);
        bodyEl.appendChild(imgContainer);
    }

    // Quoted tweet embed — fetch and show if this is a quote retweet
    if (tweet.quote_of_id) {
        var quoteWrap = document.createElement('div');
        quoteWrap.className = 'quote-embed';
        quoteWrap.style.cursor = 'pointer';
        quoteWrap.innerHTML = '<div style="color:var(--text-secondary);font-size:0.85rem">読み込み中...</div>';
        bodyEl.appendChild(quoteWrap);

        (function(wrap, qid) {
            fetch('/api/tweets/' + qid)
                .then(function(r) { return r.json(); })
                .then(function(d) {
                    if (d.tweet) {
                        var qt = d.tweet;
                        // Intentionally using innerHTML to match XSS pattern
                        wrap.innerHTML = '<div class="quote-embed-name">' + qt.user.display_name
                            + ' <span style="color:var(--text-secondary);font-weight:400">' + qt.user.handle + '</span></div>'
                            + '<div class="quote-embed-content">' + qt.content + '</div>';
                        wrap.onclick = function() { showProfile(qt.user.handle); };
                    }
                })
                .catch(function() {
                    wrap.innerHTML = '<div style="color:var(--text-secondary);font-size:0.85rem">ツイートを読み込めませんでした</div>';
                });
        })(quoteWrap, tweet.quote_of_id);
    }

    bodyEl.appendChild(actionsEl);

    card.appendChild(avatarEl);
    card.appendChild(bodyEl);

    return card;
}

// ------------------------------------------------------------------
// Render a reply card (visually indented, smaller than tweet-card)
// ------------------------------------------------------------------
function buildReplyCard(tweet) {
    const card = document.createElement('article');
    card.className = 'reply-card';
    card.dataset.tweetId = tweet.id;

    const user = tweet.user;

    // Avatar (smaller for replies)
    const avatarEl = buildAvatar(user, 32);
    avatarEl.style.cursor = 'pointer';
    avatarEl.onclick = function() { showProfile(user.handle); };

    // Body
    const bodyEl = document.createElement('div');
    bodyEl.className = 'tweet-body';

    // Meta line
    const metaEl = document.createElement('div');
    metaEl.className = 'tweet-meta';

    const nameEl = document.createElement('span');
    nameEl.className = 'tweet-display-name';
    nameEl.textContent = user.display_name;
    nameEl.style.cursor = 'pointer';
    nameEl.onclick = function() { showProfile(user.handle); };

    const handleEl = document.createElement('span');
    handleEl.className = 'tweet-handle';
    handleEl.textContent = user.handle;
    handleEl.style.cursor = 'pointer';
    handleEl.onclick = function() { showProfile(user.handle); };

    const timeEl = document.createElement('span');
    timeEl.className = 'tweet-time';
    timeEl.textContent = timeAgo(tweet.created_at);
    timeEl.setAttribute('title', tweet.created_at);

    metaEl.appendChild(nameEl);
    metaEl.appendChild(handleEl);
    metaEl.appendChild(timeEl);

    // Content — intentionally using innerHTML to keep XSS for the lecture
    const contentEl = document.createElement('div');
    contentEl.className = 'tweet-content';
    contentEl.innerHTML = tweet.content.replace(/\n/g, '<br>');
    // Wrap hashtags in clickable links
    contentEl.innerHTML = contentEl.innerHTML.replace(/#([^\s<]+)/g, '<a href="javascript:void(0)" onclick="searchHashtag(\'$1\')" style="color:var(--accent);text-decoration:none">#$1</a>');

    // Action bar — full set: reply, repost, like
    const actionsEl = document.createElement('div');
    actionsEl.className = 'tweet-actions';

    // Reply button
    var replyBtnR = document.createElement('button');
    replyBtnR.className = 'reply-btn';
    replyBtnR.setAttribute('aria-label', '返信');
    replyBtnR.onclick = function() { toggleReplyBox(tweet.id); };

    var replySvgR = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    replySvgR.setAttribute('viewBox', '0 0 24 24');
    replySvgR.setAttribute('width', '16');
    replySvgR.setAttribute('height', '16');
    replySvgR.setAttribute('aria-hidden', 'true');
    replySvgR.style.fill = 'none';
    replySvgR.style.stroke = 'currentColor';
    replySvgR.style.strokeWidth = '2';

    var replyPathR = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    replyPathR.setAttribute('d', 'M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z');
    replySvgR.appendChild(replyPathR);

    var replyCountElR = document.createElement('span');
    replyCountElR.textContent = (tweet.reply_count && tweet.reply_count > 0) ? tweet.reply_count : '';

    replyBtnR.appendChild(replySvgR);
    replyBtnR.appendChild(replyCountElR);
    actionsEl.appendChild(replyBtnR);

    // Repost button
    var repostBtnR = document.createElement('button');
    repostBtnR.className = 'repost-btn' + (tweet.reposted ? ' reposted' : '');
    repostBtnR.setAttribute('aria-label', 'リポスト');
    repostBtnR.onclick = function(e) { e.stopPropagation(); showRepostMenu(tweet, repostBtnR); };

    var repostSvgR = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    repostSvgR.setAttribute('viewBox', '0 0 24 24');
    repostSvgR.setAttribute('width', '16');
    repostSvgR.setAttribute('height', '16');
    repostSvgR.setAttribute('aria-hidden', 'true');
    repostSvgR.style.fill = 'none';
    repostSvgR.style.stroke = tweet.reposted ? '#00ba7c' : 'currentColor';
    repostSvgR.style.strokeWidth = '2';
    repostSvgR.style.strokeLinecap = 'round';
    repostSvgR.style.strokeLinejoin = 'round';

    var repostPathR = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    repostPathR.setAttribute('d', 'M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3');
    repostSvgR.appendChild(repostPathR);

    var repostCountElR = document.createElement('span');
    repostCountElR.textContent = (tweet.reposts && tweet.reposts > 0) ? tweet.reposts : '';

    repostBtnR.appendChild(repostSvgR);
    repostBtnR.appendChild(repostCountElR);
    actionsEl.appendChild(repostBtnR);

    // Like button
    const likeBtn = document.createElement('button');
    likeBtn.className = 'like-btn' + (tweet.liked ? ' liked' : '');
    likeBtn.setAttribute('aria-label', 'Like tweet');
    likeBtn.setAttribute('aria-pressed', tweet.liked ? 'true' : 'false');
    likeBtn.onclick = function() { likeTweet(tweet.id); };

    const heartSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    heartSvg.setAttribute('viewBox', '0 0 24 24');
    heartSvg.setAttribute('width', '16');
    heartSvg.setAttribute('height', '16');
    heartSvg.setAttribute('aria-hidden', 'true');
    heartSvg.style.fill = tweet.liked ? 'var(--like-color)' : 'none';
    heartSvg.style.stroke = tweet.liked ? 'var(--like-color)' : 'currentColor';
    heartSvg.style.strokeWidth = '2';

    const heartPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    heartPath.setAttribute('d', 'M12 21.638h-.014C9.403 21.59 1.95 14.856 1.95 8.478c0-3.064 2.525-5.754 5.403-5.754 2.29 0 3.83 1.58 4.646 2.73.814-1.148 2.354-2.73 4.645-2.73 2.88 0 5.404 2.69 5.404 5.755 0 6.376-7.454 13.11-10.037 13.157H12z');
    heartSvg.appendChild(heartPath);

    const likeCountEl = document.createElement('span');
    likeCountEl.textContent = tweet.likes > 0 ? tweet.likes : '';

    likeBtn.appendChild(heartSvg);
    likeBtn.appendChild(likeCountEl);
    actionsEl.appendChild(likeBtn);

    bodyEl.appendChild(metaEl);
    bodyEl.appendChild(contentEl);

    // Reply card image display
    if (tweet.image_url) {
        var replyImgContainer = document.createElement('div');
        replyImgContainer.style.cssText = 'margin-top:8px;border-radius:12px;overflow:hidden;border:1px solid var(--border)';
        var replyImg = document.createElement('img');
        replyImg.src = tweet.image_url;
        replyImg.style.cssText = 'width:100%;max-height:280px;object-fit:cover;display:block;cursor:pointer';
        replyImg.alt = '';
        (function(url) {
            replyImg.onclick = function(e) { e.stopPropagation(); showImageModal(url); };
        })(tweet.image_url);
        replyImgContainer.appendChild(replyImg);
        bodyEl.appendChild(replyImgContainer);
    }

    bodyEl.appendChild(actionsEl);

    card.appendChild(avatarEl);
    card.appendChild(bodyEl);

    return card;
}

// ------------------------------------------------------------------
// Load tweets with pagination / infinite scroll
// ------------------------------------------------------------------
function loadTweets(append) {
    if (isLoadingMore) return;
    if (append && !hasMoreTweets) return;

    var page = append ? currentPage + 1 : 1;
    var tweetsUrl = '/api/tweets?page=' + page + '&limit=30';
    if (currentTab === 'following') tweetsUrl += '&filter=following';

    if (append) isLoadingMore = true;

    fetch(tweetsUrl)
        .then(function(res) { return res.json(); })
        .then(function(data) {
            var feed = document.getElementById('tweet-feed');

            if (!append) {
                // Fresh load — clear and rebuild
                feed.innerHTML = '';
                knownTweetIds.clear();
                currentPage = 1;
            } else {
                currentPage = page;
            }

            // has_more may not exist on older backend — treat missing as true for page 1
            hasMoreTweets = (data.has_more !== undefined) ? data.has_more : false;

            // Separate top-level tweets and replies
            var topLevel = [];
            var repliesMap = {};  // parent_id -> [replies]

            data.tweets.forEach(function(tweet) {
                if (tweet.reply_to_id) {
                    if (!repliesMap[tweet.reply_to_id]) {
                        repliesMap[tweet.reply_to_id] = [];
                    }
                    repliesMap[tweet.reply_to_id].push(tweet);
                } else {
                    topLevel.push(tweet);
                }
            });

            // Recursive function to render replies and their sub-replies
            function renderReplies(parentId, container, depth) {
                var replies = repliesMap[parentId];
                if (!replies) return;
                replies.sort(function(a, b) { return a.id - b.id; });
                var repliesContainer = document.createElement('div');
                repliesContainer.className = 'tweet-replies';
                if (depth > 1) repliesContainer.style.marginLeft = '20px';
                replies.forEach(function(reply) {
                    if (knownTweetIds.has(reply.id)) return;
                    repliesContainer.appendChild(buildReplyCard(reply));
                    knownTweetIds.add(reply.id);
                    // Recursively render sub-replies (max depth 5)
                    if (depth < 5 && repliesMap[reply.id]) {
                        renderReplies(reply.id, repliesContainer, depth + 1);
                    }
                });
                container.appendChild(repliesContainer);
            }

            // Remove existing loading indicator before appending new content
            var existingLoader = feed.querySelector('.load-more-indicator');
            if (existingLoader) existingLoader.remove();

            // Render top-level tweets (API returns DESC — newest first)
            topLevel.forEach(function(tweet) {
                if (knownTweetIds.has(tweet.id)) return; // skip duplicates
                var card = buildTweetCard(tweet);
                feed.appendChild(card);
                knownTweetIds.add(tweet.id);

                // Attach replies recursively
                if (repliesMap[tweet.id]) {
                    card.classList.add('has-replies');
                    renderReplies(tweet.id, feed, 1);
                }
            });

            // Track the newest tweet id for the "new tweets" polling bar
            if (!append && data.tweets.length > 0) {
                lastKnownLatestId = data.tweets[0].id;
            }

            if (!append && topLevel.length === 0 && Object.keys(repliesMap).length === 0) {
                if (currentTab === 'following') {
                    feed.innerHTML = '<div class="feed-placeholder"><div style="font-size:1.2rem;font-weight:700;margin-bottom:8px;color:var(--text-primary)">フォロー中のユーザーの投稿がありません</div><div>ユーザーをフォローするとここに表示されます</div></div>';
                } else {
                    feed.innerHTML = '<div class="feed-placeholder"><div style="font-size:1.8rem;font-weight:800;margin-bottom:8px;color:var(--text-primary)">ようこそ</div><div>最初のツイートを投稿してみましょう</div></div>';
                }
            }

            // Show loading indicator at bottom if more pages remain
            if (hasMoreTweets) {
                var loader = document.createElement('div');
                loader.className = 'load-more-indicator';
                loader.style.cssText = 'padding:20px;text-align:center;color:var(--text-secondary)';
                loader.textContent = '読み込み中...';
                feed.appendChild(loader);
            }

            isLoadingMore = false;
        })
        .catch(function(err) {
            console.error('Failed to load tweets:', err);
            isLoadingMore = false;
        });
}

// ------------------------------------------------------------------
// Post a new tweet
// ------------------------------------------------------------------
function postTweet() {
    var textarea = document.getElementById('compose-input');
    var content = textarea.value.trim();
    if (!content && !composeImageFile) return;

    var submitBtn = document.getElementById('compose-submit');
    submitBtn.disabled = true;

    var fetchOptions;
    if (composeImageFile) {
        var formData = new FormData();
        formData.append('content', content);
        formData.append('image', composeImageFile);
        fetchOptions = { method: 'POST', body: formData };
    } else {
        fetchOptions = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content })
        };
    }

    fetch('/api/tweets', fetchOptions)
    .then(function(res) {
        if (res.status === 401) {
            showRegistrationModal();
            return null;
        }
        return res.json();
    })
    .then(function(data) {
        if (!data) return;
        textarea.value = '';
        clearComposeImage();
        updateCharCounter();
        loadTweets();
    })
    .catch(function(err) {
        console.error('Failed to post tweet:', err);
    })
    .finally(function() {
        submitBtn.disabled = false;
    });
}

// ------------------------------------------------------------------
// Like / unlike a tweet
// ------------------------------------------------------------------
function likeTweet(tweetId) {
    fetch('/api/tweets/' + tweetId + '/like', { method: 'POST' })
        .then(function(res) {
            if (res.status === 401) {
                showRegistrationModal();
                return null;
            }
            return res.json();
        })
        .then(function(data) {
            if (!data) return;
            const feed = document.getElementById('tweet-feed');
            const card = feed.querySelector('[data-tweet-id="' + tweetId + '"]');
            if (!card) return;

            const likeBtn = card.querySelector('.like-btn');
            const likeCount = likeBtn.querySelector('span');
            const svg = likeBtn.querySelector('svg');

            if (data.liked) {
                likeBtn.classList.add('liked');
                likeBtn.setAttribute('aria-pressed', 'true');
                if (svg) { svg.style.fill = 'var(--like-color)'; svg.style.stroke = 'var(--like-color)'; }
            } else {
                likeBtn.classList.remove('liked');
                likeBtn.setAttribute('aria-pressed', 'false');
                if (svg) { svg.style.fill = 'none'; svg.style.stroke = 'currentColor'; }
            }
            if (likeCount) likeCount.textContent = data.likes > 0 ? data.likes : '';
        })
        .catch(function(err) {
            console.error('Failed to like tweet:', err);
        });
}

// ------------------------------------------------------------------
// Repost dropdown menu — リポスト or 引用リポスト
// ------------------------------------------------------------------
function showRepostMenu(tweet, anchorEl) {
    // Remove any existing menu
    var existing = document.querySelector('.repost-menu');
    if (existing) existing.remove();

    var menu = document.createElement('div');
    menu.className = 'repost-menu';

    var repostOption = document.createElement('div');
    repostOption.className = 'repost-menu-item';
    repostOption.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3"/></svg> リポスト';
    repostOption.onclick = function(e) {
        e.stopPropagation();
        menu.remove();
        toggleRepost(tweet.id);
    };

    var quoteOption = document.createElement('div');
    quoteOption.className = 'repost-menu-item';
    quoteOption.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg> 引用リポスト';
    quoteOption.onclick = function(e) {
        e.stopPropagation();
        menu.remove();
        showQuoteCompose(tweet);
    };

    menu.appendChild(repostOption);
    menu.appendChild(quoteOption);

    // Position near the button
    var rect = anchorEl.getBoundingClientRect();
    menu.style.position = 'fixed';
    menu.style.left = rect.left + 'px';
    menu.style.top = (rect.bottom + 4) + 'px';

    document.body.appendChild(menu);

    // Close when clicking outside
    setTimeout(function() {
        document.addEventListener('click', function closeMenu() {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        }, { once: true });
    }, 10);
}

// ------------------------------------------------------------------
// Quote retweet compose modal
// ------------------------------------------------------------------
function showQuoteCompose(quotedTweet) {
    var modal = document.getElementById('quote-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'quote-modal';
        modal.onclick = function(e) { if (e.target === modal) modal.style.display = 'none'; };

        var card = document.createElement('div');
        card.className = 'modal-card';
        card.style.maxWidth = '500px';

        var textarea = document.createElement('textarea');
        textarea.className = 'modal-input';
        textarea.id = 'quote-textarea';
        textarea.placeholder = 'コメントを追加...';
        textarea.maxLength = 280;
        textarea.rows = 3;
        textarea.style.resize = 'vertical';
        textarea.style.fontFamily = "'Inter', sans-serif";

        var preview = document.createElement('div');
        preview.id = 'quote-preview';
        preview.className = 'quote-embed';

        var submitBtn = document.createElement('button');
        submitBtn.className = 'modal-submit';
        submitBtn.textContent = 'ツイートする';
        submitBtn.id = 'quote-submit';

        card.appendChild(textarea);
        card.appendChild(preview);
        card.appendChild(submitBtn);
        modal.appendChild(card);
        document.body.appendChild(modal);
    }

    // Fill preview with the quoted tweet content (intentional innerHTML for XSS demo)
    var preview = document.getElementById('quote-preview');
    preview.innerHTML = '<div class="quote-embed-name">' + quotedTweet.user.display_name
        + ' <span style="color:var(--text-secondary)">' + quotedTweet.user.handle + '</span></div>'
        + '<div class="quote-embed-content">' + quotedTweet.content + '</div>';

    document.getElementById('quote-textarea').value = '';
    document.getElementById('quote-submit').onclick = function() {
        var content = document.getElementById('quote-textarea').value.trim();
        if (!content) return;
        fetch('/api/tweets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content, quote_of_id: quotedTweet.id })
        })
        .then(function(res) {
            if (res.status === 401) { showRegistrationModal(); return null; }
            return res.json();
        })
        .then(function(data) {
            if (!data) return;
            modal.style.display = 'none';
            loadTweets();
        });
    };

    modal.style.display = 'flex';
    document.getElementById('quote-textarea').focus();
}

// ------------------------------------------------------------------
// Repost / un-repost a tweet
// ------------------------------------------------------------------
function toggleRepost(tweetId) {
    fetch('/api/tweets/' + tweetId + '/repost', { method: 'POST' })
        .then(function(res) {
            if (res.status === 401) { showRegistrationModal(); return null; }
            return res.json();
        })
        .then(function(data) {
            if (!data) return;
            var feed = document.getElementById('tweet-feed');
            var card = feed.querySelector('[data-tweet-id="' + tweetId + '"]');
            if (!card) return;
            var repostBtn = card.querySelector('.repost-btn');
            var repostCount = repostBtn.querySelector('span');
            var svg = repostBtn.querySelector('svg');
            if (data.reposted) {
                repostBtn.classList.add('reposted');
                if (svg) svg.style.stroke = '#00ba7c';
            } else {
                repostBtn.classList.remove('reposted');
                if (svg) svg.style.stroke = 'currentColor';
            }
            if (repostCount) repostCount.textContent = data.reposts > 0 ? data.reposts : '';
        })
        .catch(function(err) {
            console.error('Failed to repost tweet:', err);
        });
}

// ------------------------------------------------------------------
// Inline reply compose box — toggle / submit
// ------------------------------------------------------------------
function toggleReplyBox(tweetId) {
    var existingBox = document.getElementById('reply-box-' + tweetId);
    if (existingBox) {
        existingBox.remove();
        return;
    }

    // Close any other open reply boxes
    document.querySelectorAll('.inline-reply-box').forEach(function(box) { box.remove(); });

    var card = document.querySelector('[data-tweet-id="' + tweetId + '"]');
    if (!card) return;

    var replyBox = document.createElement('div');
    replyBox.className = 'inline-reply-box';
    replyBox.id = 'reply-box-' + tweetId;

    var textarea = document.createElement('textarea');
    textarea.className = 'reply-textarea';
    textarea.placeholder = '返信をツイート...';
    textarea.maxLength = 280;

    var submitBtn = document.createElement('button');
    submitBtn.className = 'reply-submit';
    submitBtn.textContent = '返信';
    submitBtn.onclick = function() { submitReply(tweetId, textarea.value); };

    // Handle Enter key (Ctrl/Cmd+Enter to submit)
    textarea.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            submitReply(tweetId, textarea.value);
        }
    });

    replyBox.appendChild(textarea);
    replyBox.appendChild(submitBtn);

    // Insert after the card — handle both top-level tweets and reply cards
    if (card.nextSibling) {
        card.parentNode.insertBefore(replyBox, card.nextSibling);
    } else {
        card.parentNode.appendChild(replyBox);
    }
    textarea.focus();
}

function submitReply(tweetId, content) {
    content = content.trim();
    if (!content) return;

    fetch('/api/tweets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: content, reply_to_id: tweetId })
    })
    .then(function(res) {
        if (res.status === 401) {
            showRegistrationModal();
            return null;
        }
        return res.json();
    })
    .then(function(data) {
        if (!data) return;
        var box = document.getElementById('reply-box-' + tweetId);
        if (box) box.remove();
        loadTweets();
    });
}

// ------------------------------------------------------------------
// Tweet detail view — show a single tweet with replies
// ------------------------------------------------------------------
function showTweetDetail(tweetId, fromPopstate) {
    currentView = 'tweet-detail';
    window.scrollTo(0, 0);
    if (!fromPopstate) pushView('tweet-detail', tweetId);

    var timeline = document.getElementById('top');
    var composeBox = timeline.querySelector('.compose-box');
    var feed = document.getElementById('tweet-feed');
    var tabs = document.getElementById('timeline-tabs');
    if (composeBox) composeBox.style.display = 'none';
    if (feed) feed.style.display = 'none';
    if (tabs) tabs.style.display = 'none';

    // Remove other views
    ['profile-view', 'notif-view', 'search-view', 'tweet-detail-view', 'bookmarks-view'].forEach(function(cls) {
        var el = timeline.querySelector('.' + cls);
        if (el) el.remove();
    });

    var header = timeline.querySelector('.timeline-header h1');
    if (header) header.textContent = 'ポスト';

    // Update nav
    document.querySelectorAll('.nav-item').forEach(function(el) { el.classList.remove('active'); });

    var view = document.createElement('div');
    view.className = 'tweet-detail-view';
    view.innerHTML = '<div style="padding:40px 20px;text-align:center;color:var(--text-secondary)">読み込み中…</div>';
    timeline.appendChild(view);

    fetch('/api/tweets/' + tweetId)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.tweet) return;
            view.innerHTML = '';
            var tweet = data.tweet;

            // Render the tweet in larger format
            var card = document.createElement('div');
            card.className = 'tweet-detail-card';

            // User row
            var userRow = document.createElement('div');
            userRow.className = 'tweet-detail-user';
            var av = buildAvatar(tweet.user, 48);
            av.style.cursor = 'pointer';
            av.onclick = function() { showProfile(tweet.user.handle); };

            var userInfo = document.createElement('div');
            var nameEl = document.createElement('div');
            nameEl.className = 'tweet-display-name';
            nameEl.style.fontSize = '1rem';
            nameEl.textContent = tweet.user.display_name;
            nameEl.style.cursor = 'pointer';
            nameEl.onclick = function() { showProfile(tweet.user.handle); };
            var handleEl = document.createElement('div');
            handleEl.className = 'tweet-handle';
            handleEl.textContent = tweet.user.handle;
            userInfo.appendChild(nameEl);
            userInfo.appendChild(handleEl);

            userRow.appendChild(av);
            userRow.appendChild(userInfo);
            card.appendChild(userRow);

            // Content (larger text)
            var contentEl = document.createElement('div');
            contentEl.className = 'tweet-detail-content';
            // Intentionally using innerHTML for XSS lecture
            contentEl.innerHTML = tweet.content.replace(/\n/g, '<br>');
            card.appendChild(contentEl);

            // Timestamp (full format)
            var timeEl = document.createElement('div');
            timeEl.className = 'tweet-detail-time';
            var d = new Date(tweet.created_at.endsWith('Z') ? tweet.created_at : tweet.created_at + 'Z');
            timeEl.textContent = d.toLocaleString('ja-JP', {year:'numeric',month:'long',day:'numeric',hour:'2-digit',minute:'2-digit'});
            card.appendChild(timeEl);

            // Stats bar
            var statsBar = document.createElement('div');
            statsBar.className = 'tweet-detail-stats';
            statsBar.innerHTML = '<span><strong>' + (tweet.reposts || 0) + '</strong> リポスト</span>'
                + '<span><strong>' + (tweet.likes || 0) + '</strong> いいね</span>'
                + '<span><strong>' + (tweet.impressions || 0) + '</strong> 表示</span>';
            card.appendChild(statsBar);

            // Action bar
            var actions = document.createElement('div');
            actions.className = 'tweet-detail-actions';

            // Reply button
            var replyBtn = document.createElement('button');
            replyBtn.className = 'reply-btn';
            replyBtn.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>';
            replyBtn.onclick = function() { toggleReplyBox(tweet.id); };

            var repostBtn = document.createElement('button');
            repostBtn.className = 'repost-btn';
            repostBtn.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3"/></svg>';
            repostBtn.onclick = function() { showRepostMenu(tweet, repostBtn); };

            var likeBtn = document.createElement('button');
            likeBtn.className = 'like-btn' + (tweet.liked ? ' liked' : '');
            likeBtn.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" fill="' + (tweet.liked ? 'var(--like-color)' : 'none') + '" stroke="' + (tweet.liked ? 'var(--like-color)' : 'currentColor') + '" stroke-width="2"><path d="M12 21.638h-.014C9.403 21.59 1.95 14.856 1.95 8.478c0-3.064 2.525-5.754 5.403-5.754 2.29 0 3.83 1.58 4.646 2.73.814-1.148 2.354-2.73 4.645-2.73 2.88 0 5.404 2.69 5.404 5.755 0 6.376-7.454 13.11-10.037 13.157H12z"/></svg>';
            likeBtn.onclick = function() { likeTweet(tweet.id); };

            actions.appendChild(replyBtn);
            actions.appendChild(repostBtn);
            actions.appendChild(likeBtn);
            card.appendChild(actions);

            // Inline reply compose for detail view
            var detailReplyBox = document.createElement('div');
            detailReplyBox.style.cssText = 'display:flex;gap:10px;padding:12px 20px;border-bottom:1px solid var(--border)';

            var replyAvatar = currentUser ? buildAvatar(currentUser, 36) : buildDefaultAvatar(36);
            var replyTextarea = document.createElement('textarea');
            replyTextarea.className = 'reply-textarea';
            replyTextarea.placeholder = '返信をツイート...';
            replyTextarea.style.flex = '1';
            replyTextarea.maxLength = 280;

            var replySubmit = document.createElement('button');
            replySubmit.className = 'reply-submit';
            replySubmit.textContent = '返信';
            replySubmit.onclick = function() {
                var content = replyTextarea.value.trim();
                if (!content) return;
                fetch('/api/tweets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: content, reply_to_id: tweet.id })
                }).then(function(res) {
                    if (res.status === 401) { showRegistrationModal(); return; }
                    return res.json();
                }).then(function() {
                    // Refresh the detail view to show the new reply
                    showTweetDetail(tweetId);
                });
            };

            detailReplyBox.appendChild(replyAvatar);
            detailReplyBox.appendChild(replyTextarea);
            detailReplyBox.appendChild(replySubmit);
            card.appendChild(detailReplyBox);

            view.appendChild(card);

            // Show replies to this tweet below
            fetch('/api/tweets')
                .then(function(r) { return r.json(); })
                .then(function(allData) {
                    // Build a replies map for recursive rendering
                    var repliesMap = {};
                    allData.tweets.forEach(function(t) {
                        if (t.reply_to_id) {
                            if (!repliesMap[t.reply_to_id]) repliesMap[t.reply_to_id] = [];
                            repliesMap[t.reply_to_id].push(t);
                        }
                    });

                    var directReplies = repliesMap[tweet.id];
                    if (directReplies && directReplies.length > 0) {
                        var repliesHeader = document.createElement('div');
                        repliesHeader.style.cssText = 'padding:14px 20px;font-weight:700;border-top:1px solid var(--border);border-bottom:1px solid var(--border)';
                        repliesHeader.textContent = '返信';
                        view.appendChild(repliesHeader);

                        directReplies.sort(function(a, b) { return a.id - b.id; });
                        directReplies.forEach(function(reply) {
                            view.appendChild(buildTweetCard(reply));

                            // Also render sub-replies recursively
                            if (repliesMap[reply.id]) {
                                var subContainer = document.createElement('div');
                                subContainer.className = 'tweet-replies';
                                repliesMap[reply.id].sort(function(a, b) { return a.id - b.id; });
                                repliesMap[reply.id].forEach(function(subReply) {
                                    subContainer.appendChild(buildReplyCard(subReply));
                                });
                                view.appendChild(subContainer);
                            }
                        });
                    }
                });
        });
}

// ------------------------------------------------------------------
// Bookmarks view
// ------------------------------------------------------------------
function showBookmarks(fromPopstate) {
    currentView = 'bookmarks';
    window.scrollTo(0, 0);
    if (!fromPopstate) pushView('bookmarks');

    var timeline = document.getElementById('top');
    var composeBox = timeline.querySelector('.compose-box');
    var feed = document.getElementById('tweet-feed');
    var tabs = document.getElementById('timeline-tabs');
    if (composeBox) composeBox.style.display = 'none';
    if (feed) feed.style.display = 'none';
    if (tabs) tabs.style.display = 'none';
    ['profile-view', 'notif-view', 'search-view', 'tweet-detail-view', 'bookmarks-view'].forEach(function(cls) {
        var el = timeline.querySelector('.' + cls);
        if (el) el.remove();
    });

    var header = timeline.querySelector('.timeline-header h1');
    if (header) header.textContent = 'ブックマーク';

    document.querySelectorAll('.nav-item').forEach(function(b) { b.classList.remove('active'); });
    var bookmarkNav = document.getElementById('bookmark-nav');
    if (bookmarkNav) bookmarkNav.classList.add('active');

    var view = document.createElement('div');
    view.className = 'bookmarks-view';
    view.innerHTML = '<div style="padding:40px 20px;text-align:center;color:var(--text-secondary)">読み込み中…</div>';
    timeline.appendChild(view);

    fetch('/api/bookmarks')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            view.innerHTML = '';
            if (!data.tweets || data.tweets.length === 0) {
                view.innerHTML = '<div class="feed-placeholder"><div style="font-size:1.2rem;font-weight:700;margin-bottom:8px;color:var(--text-primary)">ブックマークはまだありません</div><div>ツイートをブックマークすると、ここに表示されます</div></div>';
                return;
            }
            data.tweets.forEach(function(tweet) {
                view.appendChild(buildTweetCard(tweet));
            });
        })
        .catch(function(err) {
            console.error('Failed to load bookmarks:', err);
            view.innerHTML = '<div class="feed-placeholder">読み込みに失敗しました</div>';
        });
}

// ------------------------------------------------------------------
// Show a modal listing users who liked or reposted a tweet
// ------------------------------------------------------------------
function showUserList(title, apiUrl) {
    document.getElementById('users-list-title').textContent = title;
    var content = document.getElementById('users-list-content');
    content.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-secondary)">読み込み中…</div>';
    document.getElementById('users-list-modal').style.display = 'flex';

    fetch(apiUrl)
        .then(function(res) { return res.json(); })
        .then(function(data) {
            content.innerHTML = '';
            var users = data.users || [];
            if (users.length === 0) {
                content.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-secondary)">まだいません</div>';
                return;
            }
            users.forEach(function(user) {
                var item = document.createElement('div');
                item.className = 'user-list-item';
                item.style.cursor = 'pointer';
                item.onclick = function() {
                    document.getElementById('users-list-modal').style.display = 'none';
                    showProfile(user.handle || ('@' + user.username));
                };

                var av = buildAvatar(user, 40);

                var info = document.createElement('div');
                info.className = 'user-list-info';
                var name = document.createElement('div');
                name.className = 'user-list-name';
                name.textContent = user.display_name;
                var handle = document.createElement('div');
                handle.className = 'user-list-handle';
                handle.textContent = user.handle;
                info.appendChild(name);
                info.appendChild(handle);

                item.appendChild(av);
                item.appendChild(info);
                content.appendChild(item);
            });
        });
}

// ------------------------------------------------------------------
// Show follower / following list for a user profile
// ------------------------------------------------------------------
function showFollowList(userId, userName, type) {
    var title = type === 'followers'
        ? userName + 'のフォロワー'
        : userName + 'がフォロー中';
    var apiUrl = '/api/users/' + userId + '/' + type;

    document.getElementById('users-list-title').textContent = title;
    var content = document.getElementById('users-list-content');
    content.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-secondary)">読み込み中…</div>';
    document.getElementById('users-list-modal').style.display = 'flex';

    fetch(apiUrl)
        .then(function(res) { return res.json(); })
        .then(function(data) {
            content.innerHTML = '';
            var users = data.users || [];
            if (users.length === 0) {
                content.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-secondary)">まだいません</div>';
                return;
            }
            users.forEach(function(u) {
                var item = document.createElement('div');
                item.className = 'user-list-item';

                var av = buildAvatar(u, 40);
                av.style.cursor = 'pointer';
                av.onclick = function() {
                    document.getElementById('users-list-modal').style.display = 'none';
                    showProfile(u.handle);
                };

                var info = document.createElement('div');
                info.className = 'user-list-info';
                info.style.cursor = 'pointer';
                info.onclick = function() {
                    document.getElementById('users-list-modal').style.display = 'none';
                    showProfile(u.handle);
                };

                var name = document.createElement('div');
                name.className = 'user-list-name';
                name.textContent = u.display_name;
                var handle = document.createElement('div');
                handle.className = 'user-list-handle';
                handle.textContent = u.handle;
                info.appendChild(name);
                info.appendChild(handle);
                if (u.bio) {
                    var bio = document.createElement('div');
                    bio.style.fontSize = '0.8rem';
                    bio.style.color = 'var(--text-secondary)';
                    bio.style.marginTop = '2px';
                    bio.textContent = u.bio.substring(0, 60) + (u.bio.length > 60 ? '...' : '');
                    info.appendChild(bio);
                }

                // Follow button (skip for self)
                var followBtn = document.createElement('button');
                followBtn.className = 'follow-btn';
                followBtn.style.marginLeft = 'auto';
                if (currentUser && u.id === currentUser.id) {
                    followBtn = null;
                } else if (u.is_following) {
                    followBtn.textContent = 'フォロー中';
                    followBtn.style.background = 'transparent';
                    followBtn.style.color = 'var(--text-primary)';
                    followBtn.style.border = '1px solid var(--text-secondary)';
                } else {
                    followBtn.textContent = 'フォローする';
                }

                if (followBtn) {
                    (function(btn, uid) {
                        btn.onclick = function(e) {
                            e.stopPropagation();
                            fetch('/api/users/' + uid + '/follow', { method: 'POST' })
                                .then(function(r) { return r.json(); })
                                .then(function(d) {
                                    if (d.following) {
                                        btn.textContent = 'フォロー中';
                                        btn.style.background = 'transparent';
                                        btn.style.color = 'var(--text-primary)';
                                        btn.style.border = '1px solid var(--text-secondary)';
                                    } else {
                                        btn.textContent = 'フォローする';
                                        btn.style.background = 'var(--text-primary)';
                                        btn.style.color = 'var(--bg-main)';
                                        btn.style.border = 'none';
                                    }
                                });
                        };
                    })(followBtn, u.id);
                }

                item.appendChild(av);
                item.appendChild(info);
                if (followBtn) item.appendChild(followBtn);
                content.appendChild(item);
            });
        });
}
