import os
import uuid
import json
import re
from flask import request, jsonify
from routes import tweets_bp as bp
from models import get_db, get_current_user_id, _tweet_row_to_dict, allowed_file
from bot_engine import trigger_bot_reactions
from config import UPLOAD_FOLDER


def _get_poll_data(c, tweet_id, current_user_id=None):
    """Return poll data dict for a tweet, or None if the tweet has no poll."""
    c.execute('SELECT id, ends_at FROM polls WHERE tweet_id = ?', (tweet_id,))
    poll_row = c.fetchone()
    if not poll_row:
        return None
    poll_id = poll_row['id']
    c.execute('''
        SELECT po.id, po.text, po.position,
               COUNT(pv.id) AS vote_count
        FROM poll_options po
        LEFT JOIN poll_votes pv ON pv.option_id = po.id
        WHERE po.poll_id = ?
        GROUP BY po.id
        ORDER BY po.position
    ''', (poll_id,))
    options = [dict(r) for r in c.fetchall()]
    voted_option_id = None
    if current_user_id:
        c.execute('SELECT option_id FROM poll_votes WHERE poll_id = ? AND user_id = ?',
                  (poll_id, current_user_id))
        voted_row = c.fetchone()
        if voted_row:
            voted_option_id = voted_row['option_id']
    return {
        'id': poll_id,
        'ends_at': poll_row['ends_at'],
        'options': options,
        'voted_option_id': voted_option_id,
    }


def _create_mention_notifications(content, tweet_id, author_id):
    """Scan tweet content for @mentions and create notifications.
    Security note: handles are extracted with regex and looked up via parameterized
    query — no injection risk. However, any user can mention any other user, which
    could be used for notification spam (intentional for lecture demo purposes).
    """
    handles = re.findall(r'@([a-zA-Z0-9_]+)', content)
    if not handles:
        return

    conn = get_db()
    c = conn.cursor()
    for handle_name in set(handles):
        c.execute(
            'SELECT id FROM users WHERE username = ? OR handle = ?',
            (handle_name, '@' + handle_name)
        )
        user = c.fetchone()
        if user and user['id'] != author_id:
            c.execute(
                'INSERT INTO notifications (user_id, type, actor_id, tweet_id) VALUES (?, ?, ?, ?)',
                (user['id'], 'mention', author_id, tweet_id)
            )
    conn.commit()
    conn.close()


# GET /api/tweets — list all tweets with user info and like counts
# Accepts optional ?filter=following to show only tweets from followed users + self
# Accepts optional ?page=1&limit=30 for pagination (backward compatible)
@bp.route('/api/tweets')
def get_tweets():
    filter_mode = request.args.get('filter', 'all')  # 'all' or 'following'
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 30))
    offset = (page - 1) * limit

    conn = get_db()
    c = conn.cursor()

    current_user_id = get_current_user_id()

    # Collect muted and blocked user IDs to exclude from timeline
    muted_ids = set()
    blocked_ids = set()
    if current_user_id:
        c.execute('SELECT target_id FROM mutes WHERE user_id = ?', (current_user_id,))
        muted_ids = {r['target_id'] for r in c.fetchall()}
        c.execute('SELECT target_id FROM blocks WHERE user_id = ?', (current_user_id,))
        blocked_ids = {r['target_id'] for r in c.fetchall()}
    hidden_ids = muted_ids | blocked_ids

    if filter_mode == 'following' and current_user_id is not None:
        # Get IDs of users the current user follows
        c.execute('SELECT following_id FROM follows WHERE follower_id = ?', (current_user_id,))
        following_ids = {r['following_id'] for r in c.fetchall()}
        following_ids.add(current_user_id)  # include own tweets
        # Remove muted/blocked from following feed
        following_ids -= hidden_ids

        if not following_ids:
            conn.close()
            return jsonify({'tweets': [], 'page': page, 'has_more': False})

        # following_ids contains only integer PKs from the DB — safe to interpolate
        placeholders = ','.join('?' * len(following_ids))
        c.execute(f'''
            SELECT
                t.id,
                t.content,
                t.created_at,
                t.edited_at,
                t.reply_to_id,
                t.quote_of_id,
                t.impressions,
                t.image_url,
                u.id   AS user_id,
                u.display_name,
                u.handle,
                u.avatar_url,
                u.is_bot,
                COUNT(DISTINCT l.id) AS like_count,
                (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count
            FROM tweets t
            JOIN  users u ON u.id = t.user_id
            LEFT JOIN likes l ON l.tweet_id = t.id
            WHERE t.user_id IN ({placeholders})
            GROUP BY t.id
            ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?
        ''', list(following_ids) + [limit, offset])
    else:
        # Default: all tweets, excluding muted/blocked authors
        if hidden_ids:
            hide_placeholders = ','.join('?' * len(hidden_ids))
            c.execute(f'''
                SELECT
                    t.id,
                    t.content,
                    t.created_at,
                    t.edited_at,
                    t.reply_to_id,
                    t.quote_of_id,
                    t.impressions,
                    t.image_url,
                    u.id   AS user_id,
                    u.display_name,
                    u.handle,
                    u.avatar_url,
                    u.is_bot,
                    COUNT(DISTINCT l.id) AS like_count,
                    (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count
                FROM tweets t
                JOIN  users u ON u.id = t.user_id
                LEFT JOIN likes l ON l.tweet_id = t.id
                WHERE t.user_id NOT IN ({hide_placeholders})
                GROUP BY t.id
                ORDER BY t.created_at DESC
                LIMIT ? OFFSET ?
            ''', list(hidden_ids) + [limit, offset])
        else:
            c.execute('''
                SELECT
                    t.id,
                    t.content,
                    t.created_at,
                    t.edited_at,
                    t.reply_to_id,
                    t.quote_of_id,
                    t.impressions,
                    t.image_url,
                    u.id   AS user_id,
                    u.display_name,
                    u.handle,
                    u.avatar_url,
                    u.is_bot,
                    COUNT(DISTINCT l.id) AS like_count,
                    (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count
                FROM tweets t
                JOIN  users u ON u.id = t.user_id
                LEFT JOIN likes l ON l.tweet_id = t.id
                GROUP BY t.id
                ORDER BY t.created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))

    rows = c.fetchall()

    # Increment impressions for all visible tweets
    if rows:
        tweet_ids = [row['id'] for row in rows]
        imp_placeholders = ','.join('?' * len(tweet_ids))
        c.execute(f'UPDATE tweets SET impressions = impressions + 1 WHERE id IN ({imp_placeholders})', tweet_ids)
        conn.commit()

    # Fetch liked, reposted, and bookmarked tweet IDs for the current cookie user (empty sets if not logged in)
    liked_ids = set()
    reposted_ids = set()
    bookmarked_ids = set()
    if current_user_id is not None:
        c.execute('SELECT tweet_id FROM likes WHERE user_id = ?', (current_user_id,))
        liked_ids = {r['tweet_id'] for r in c.fetchall()}
        c.execute('SELECT tweet_id FROM reposts WHERE user_id = ?', (current_user_id,))
        reposted_ids = {r['tweet_id'] for r in c.fetchall()}
        c.execute('SELECT tweet_id FROM bookmarks WHERE user_id = ?', (current_user_id,))
        bookmarked_ids = {r['tweet_id'] for r in c.fetchall()}

    tweets = []
    for row in rows:
        t = _tweet_row_to_dict(row, row['id'] in liked_ids, row['id'] in reposted_ids, row['id'] in bookmarked_ids)
        t['poll'] = _get_poll_data(c, row['id'], current_user_id)
        tweets.append(t)

    conn.close()
    return jsonify({'tweets': tweets, 'page': page, 'has_more': len(rows) == limit})


# POST /api/tweets — create a new tweet
# Supports both JSON and multipart/form-data (for image uploads)
@bp.route('/api/tweets', methods=['POST'])
def create_tweet():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    # Support both JSON and multipart form data
    poll_options = []
    poll_duration_hours = None
    if request.content_type and 'multipart' in request.content_type:
        content = (request.form.get('content') or '').strip()
        reply_to_id = request.form.get('reply_to_id')
        quote_of_id = request.form.get('quote_of_id')
    else:
        data = request.get_json(force=True, silent=True) or {}
        content = (data.get('content') or '').strip()
        reply_to_id = data.get('reply_to_id')
        quote_of_id = data.get('quote_of_id')
        poll_options = data.get('poll_options') or []
        poll_duration_hours = data.get('poll_duration_hours')

    # Handle multiple image uploads (up to 4 images)
    # Accepts file fields: image, image0, image1, image2, image3
    image_urls = []
    if request.content_type and 'multipart' in request.content_type:
        for key in ['image', 'image0', 'image1', 'image2', 'image3']:
            f = request.files.get(key)
            if f and allowed_file(f.filename):
                ext = f.filename.rsplit('.', 1)[1].lower()
                filename = f'tweet_{user_id}_{uuid.uuid4().hex[:8]}.{ext}'
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                f.save(filepath)
                image_urls.append(f'/static/uploads/{filename}')
        if len(image_urls) > 4:
            image_urls = image_urls[:4]

    if not content and not image_urls:
        return jsonify({'error': 'content or image required'}), 400

    # Store as JSON array if multiple images, single string preserved for backward compat
    image_url = json.dumps(image_urls) if image_urls else ''

    conn = get_db()
    c = conn.cursor()

    # Verify user exists
    c.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'user not found'}), 404

    c.execute(
        'INSERT INTO tweets (user_id, content, reply_to_id, quote_of_id, image_url) VALUES (?, ?, ?, ?, ?)',
        (user_id, content, reply_to_id, quote_of_id, image_url)
    )
    tweet_id = c.lastrowid

    # Create poll if poll_options provided (2-4 options required)
    if poll_options and isinstance(poll_options, list) and 2 <= len(poll_options) <= 4:
        ends_at = None
        if poll_duration_hours:
            try:
                hours = float(poll_duration_hours)
                c.execute("SELECT datetime('now', ? || ' hours') AS ends_at", (str(hours),))
                ends_at = c.fetchone()['ends_at']
            except (ValueError, TypeError):
                pass
        c.execute('INSERT INTO polls (tweet_id, ends_at) VALUES (?, ?)', (tweet_id, ends_at))
        poll_id = c.lastrowid
        for i, opt_text in enumerate(poll_options):
            opt_text = str(opt_text).strip()
            if opt_text:
                c.execute('INSERT INTO poll_options (poll_id, text, position) VALUES (?, ?, ?)',
                          (poll_id, opt_text, i))

    conn.commit()

    # Fetch the full tweet row to return
    c.execute('''
        SELECT
            t.id,
            t.content,
            t.created_at,
            t.edited_at,
            t.reply_to_id,
            t.quote_of_id,
            t.image_url,
            u.id   AS user_id,
            u.display_name,
            u.handle,
            u.avatar_url,
            u.is_bot,
            0 AS like_count,
            0 AS repost_count,
            0 AS impressions
        FROM tweets t
        JOIN users u ON u.id = t.user_id
        WHERE t.id = ?
    ''', (tweet_id,))
    row = c.fetchone()

    # Build tweet dict including poll data
    tweet_dict = _tweet_row_to_dict(row, False)
    tweet_dict['poll'] = _get_poll_data(c, tweet_id, user_id)

    # Check if poster is human (not a bot) — only trigger reactions for human posts
    c.execute('SELECT is_bot FROM users WHERE id = ?', (user_id,))
    user_row = c.fetchone()
    conn.close()

    if user_row and not user_row['is_bot']:
        trigger_bot_reactions(tweet_id, content, user_id)

    # Detect @mentions in tweet content and notify mentioned users
    if content:
        _create_mention_notifications(content, tweet_id, user_id)

    return jsonify({'tweet': tweet_dict}), 201


# GET /api/tweets/<id> — fetch a single tweet by ID
@bp.route('/api/tweets/<int:tweet_id>')
def get_single_tweet(tweet_id):
    current_user_id = get_current_user_id()
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT t.id, t.content, t.created_at, t.edited_at, t.reply_to_id, t.quote_of_id, t.image_url,
               u.id AS user_id, u.display_name, u.handle, u.avatar_url, u.is_bot,
               COUNT(DISTINCT l.id) AS like_count,
               (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count,
               t.impressions
        FROM tweets t
        JOIN users u ON u.id = t.user_id
        LEFT JOIN likes l ON l.tweet_id = t.id
        WHERE t.id = ?
        GROUP BY t.id
    ''', (tweet_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'tweet not found'}), 404
    t = _tweet_row_to_dict(row, False)
    t['poll'] = _get_poll_data(c, tweet_id, current_user_id)
    conn.close()
    return jsonify({'tweet': t})


# DELETE /api/tweets/<id> — delete a tweet owned by the current cookie user
# Only the tweet owner can delete. Cascades to likes, reposts, notifications,
# and replies (including their likes).
@bp.route('/api/tweets/<int:tweet_id>', methods=['DELETE'])
def delete_tweet(tweet_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    conn = get_db()
    c = conn.cursor()

    # Verify the tweet belongs to the user
    c.execute('SELECT user_id FROM tweets WHERE id = ?', (tweet_id,))
    tweet = c.fetchone()
    if not tweet:
        conn.close()
        return jsonify({'error': 'tweet not found'}), 404
    if tweet['user_id'] != user_id:
        conn.close()
        return jsonify({'error': 'not your tweet'}), 403

    # Delete related data first
    c.execute('DELETE FROM likes WHERE tweet_id = ?', (tweet_id,))
    c.execute('DELETE FROM reposts WHERE tweet_id = ?', (tweet_id,))
    c.execute('DELETE FROM notifications WHERE tweet_id = ?', (tweet_id,))
    # Delete replies to this tweet (and their likes)
    c.execute('DELETE FROM likes WHERE tweet_id IN (SELECT id FROM tweets WHERE reply_to_id = ?)', (tweet_id,))
    c.execute('DELETE FROM tweets WHERE reply_to_id = ?', (tweet_id,))
    # Delete the tweet itself
    c.execute('DELETE FROM tweets WHERE id = ?', (tweet_id,))

    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# POST /api/tweets/<id>/like — toggle like for the current cookie user
@bp.route('/api/tweets/<int:tweet_id>/like', methods=['POST'])
def toggle_like(tweet_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    conn = get_db()
    c = conn.cursor()

    # Check if already liked
    c.execute(
        'SELECT id FROM likes WHERE tweet_id = ? AND user_id = ?',
        (tweet_id, user_id)
    )
    existing = c.fetchone()

    if existing:
        # Unlike
        c.execute(
            'DELETE FROM likes WHERE tweet_id = ? AND user_id = ?',
            (tweet_id, user_id)
        )
        liked = False
    else:
        # Like
        c.execute(
            'INSERT INTO likes (tweet_id, user_id) VALUES (?, ?)',
            (tweet_id, user_id)
        )
        liked = True

    conn.commit()

    # Return updated like count
    c.execute('SELECT COUNT(*) AS cnt FROM likes WHERE tweet_id = ?', (tweet_id,))
    like_count = c.fetchone()['cnt']
    conn.close()

    return jsonify({'liked': liked, 'likes': like_count})


# POST /api/tweets/<id>/repost — toggle repost for the current cookie user
@bp.route('/api/tweets/<int:tweet_id>/repost', methods=['POST'])
def toggle_repost(tweet_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM reposts WHERE tweet_id = ? AND user_id = ?', (tweet_id, user_id))
    existing = c.fetchone()

    if existing:
        c.execute('DELETE FROM reposts WHERE tweet_id = ? AND user_id = ?', (tweet_id, user_id))
        reposted = False
    else:
        c.execute('INSERT INTO reposts (tweet_id, user_id) VALUES (?, ?)', (tweet_id, user_id))
        reposted = True

    conn.commit()
    c.execute('SELECT COUNT(*) AS cnt FROM reposts WHERE tweet_id = ?', (tweet_id,))
    repost_count = c.fetchone()['cnt']
    conn.close()

    return jsonify({'reposted': reposted, 'reposts': repost_count})


# POST /api/tweets/<id>/bookmark — toggle bookmark for the current cookie user
@bp.route('/api/tweets/<int:tweet_id>/bookmark', methods=['POST'])
def toggle_bookmark(tweet_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM bookmarks WHERE user_id = ? AND tweet_id = ?', (user_id, tweet_id))
    if c.fetchone():
        c.execute('DELETE FROM bookmarks WHERE user_id = ? AND tweet_id = ?', (user_id, tweet_id))
        bookmarked = False
    else:
        c.execute('INSERT INTO bookmarks (user_id, tweet_id) VALUES (?, ?)', (user_id, tweet_id))
        bookmarked = True
    conn.commit()
    conn.close()
    return jsonify({'bookmarked': bookmarked})


# GET /api/bookmarks — get bookmarked tweets for the current user
@bp.route('/api/bookmarks')
def get_bookmarks():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'tweets': []})
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT t.id, t.content, t.created_at, t.edited_at, t.reply_to_id, t.quote_of_id, t.image_url,
               u.id AS user_id, u.display_name, u.handle, u.avatar_url, u.is_bot,
               COUNT(DISTINCT l.id) AS like_count,
               (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count,
               t.impressions
        FROM bookmarks b
        JOIN tweets t ON t.id = b.tweet_id
        JOIN users u ON u.id = t.user_id
        LEFT JOIN likes l ON l.tweet_id = t.id
        WHERE b.user_id = ?
        GROUP BY t.id
        ORDER BY b.created_at DESC
    ''', (user_id,))
    rows = c.fetchall()
    liked_ids = set()
    reposted_ids = set()
    c.execute('SELECT tweet_id FROM likes WHERE user_id = ?', (user_id,))
    liked_ids = {r['tweet_id'] for r in c.fetchall()}
    c.execute('SELECT tweet_id FROM reposts WHERE user_id = ?', (user_id,))
    reposted_ids = {r['tweet_id'] for r in c.fetchall()}
    conn.close()
    # All rows here are bookmarked by definition
    tweets = [_tweet_row_to_dict(row, row['id'] in liked_ids, row['id'] in reposted_ids, True) for row in rows]
    return jsonify({'tweets': tweets})


# GET /api/tweets/search — search tweets by content (supports hashtag queries)
@bp.route('/api/tweets/search')
def search_tweets():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'tweets': []})

    conn = get_db()
    c = conn.cursor()
    search_term = f'%{q}%'
    c.execute('''
        SELECT t.id, t.content, t.created_at, t.edited_at, t.reply_to_id, t.quote_of_id, t.image_url,
               u.id AS user_id, u.display_name, u.handle, u.avatar_url, u.is_bot,
               COUNT(DISTINCT l.id) AS like_count,
               (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count,
               t.impressions
        FROM tweets t
        JOIN users u ON u.id = t.user_id
        LEFT JOIN likes l ON l.tweet_id = t.id
        WHERE t.content LIKE ?
        GROUP BY t.id
        ORDER BY t.created_at DESC
        LIMIT 50
    ''', (search_term,))
    rows = c.fetchall()
    current_user_id = get_current_user_id()
    liked_ids = set()
    reposted_ids = set()
    bookmarked_ids = set()
    if current_user_id:
        c.execute('SELECT tweet_id FROM likes WHERE user_id = ?', (current_user_id,))
        liked_ids = {r['tweet_id'] for r in c.fetchall()}
        c.execute('SELECT tweet_id FROM reposts WHERE user_id = ?', (current_user_id,))
        reposted_ids = {r['tweet_id'] for r in c.fetchall()}
        c.execute('SELECT tweet_id FROM bookmarks WHERE user_id = ?', (current_user_id,))
        bookmarked_ids = {r['tweet_id'] for r in c.fetchall()}
    conn.close()
    tweets = [_tweet_row_to_dict(row, row['id'] in liked_ids, row['id'] in reposted_ids, row['id'] in bookmarked_ids) for row in rows]
    return jsonify({'tweets': tweets})


# GET /api/tweets/<id>/likes — list users who liked a tweet
@bp.route('/api/tweets/<int:tweet_id>/likes')
def get_tweet_likes(tweet_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT u.id, u.display_name, u.handle, u.avatar_url
        FROM likes l
        JOIN users u ON u.id = l.user_id
        WHERE l.tweet_id = ?
        ORDER BY l.id DESC
    ''', (tweet_id,))
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'users': users})


# GET /api/tweets/<id>/reposts — list users who reposted a tweet
@bp.route('/api/tweets/<int:tweet_id>/reposts')
def get_tweet_reposts(tweet_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT u.id, u.display_name, u.handle, u.avatar_url
        FROM reposts r
        JOIN users u ON u.id = r.user_id
        WHERE r.tweet_id = ?
        ORDER BY r.id DESC
    ''', (tweet_id,))
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'users': users})


# POST /api/tweets/<id>/pin — pin or unpin a tweet on the current user's profile
# Pinning a different tweet replaces the existing pin. Pinning the already-pinned
# tweet unpins it. Only the tweet owner can pin their own tweets.
@bp.route('/api/tweets/<int:tweet_id>/pin', methods=['POST'])
def pin_tweet(tweet_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    conn = get_db()
    c = conn.cursor()

    # Verify tweet belongs to the requesting user
    c.execute('SELECT user_id FROM tweets WHERE id = ?', (tweet_id,))
    tweet = c.fetchone()
    if not tweet:
        conn.close()
        return jsonify({'error': 'tweet not found'}), 404
    if tweet['user_id'] != user_id:
        conn.close()
        return jsonify({'error': 'not your tweet'}), 403

    # Check current pin status
    c.execute('SELECT pinned_tweet_id FROM users WHERE id = ?', (user_id,))
    current = c.fetchone()

    if current and current['pinned_tweet_id'] == tweet_id:
        # Already pinned — unpin
        c.execute('UPDATE users SET pinned_tweet_id = NULL WHERE id = ?', (user_id,))
        pinned = False
    else:
        # Pin this tweet (replaces any existing pin)
        c.execute('UPDATE users SET pinned_tweet_id = ? WHERE id = ?', (tweet_id, user_id))
        pinned = True

    conn.commit()
    conn.close()
    return jsonify({'pinned': pinned})


# PUT /api/tweets/<id>/edit — edit the content of a tweet owned by the current user
@bp.route('/api/tweets/<int:tweet_id>/edit', methods=['PUT'])
def edit_tweet(tweet_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'auth required'}), 401

    data = request.get_json(force=True, silent=True) or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'error': 'content required'}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id FROM tweets WHERE id = ?', (tweet_id,))
    tweet = c.fetchone()
    if not tweet or tweet['user_id'] != user_id:
        conn.close()
        return jsonify({'error': 'forbidden'}), 403

    c.execute('UPDATE tweets SET content = ?, edited_at = CURRENT_TIMESTAMP WHERE id = ?', (content, tweet_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# POST /api/polls/<id>/vote — cast or change a vote on a poll
@bp.route('/api/polls/<int:poll_id>/vote', methods=['POST'])
def vote_poll(poll_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'auth required'}), 401

    data = request.get_json(force=True, silent=True) or {}
    option_id = data.get('option_id')
    if not option_id:
        return jsonify({'error': 'option_id required'}), 400

    conn = get_db()
    c = conn.cursor()

    # Verify poll exists and option belongs to it
    c.execute('SELECT id, ends_at FROM polls WHERE id = ?', (poll_id,))
    poll = c.fetchone()
    if not poll:
        conn.close()
        return jsonify({'error': 'poll not found'}), 404

    # Check poll has not ended
    if poll['ends_at']:
        c.execute("SELECT ? > ?", (poll['ends_at'], 'now'))
        # Simple approach: compare via SQL
        c.execute("SELECT CURRENT_TIMESTAMP > ? AS expired", (poll['ends_at'],))
        if c.fetchone()['expired']:
            conn.close()
            return jsonify({'error': 'poll has ended'}), 400

    c.execute('SELECT id FROM poll_options WHERE id = ? AND poll_id = ?', (option_id, poll_id))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'invalid option'}), 400

    # Insert or replace vote (user can change their vote)
    c.execute('INSERT OR REPLACE INTO poll_votes (poll_id, option_id, user_id) VALUES (?, ?, ?)',
              (poll_id, option_id, user_id))
    conn.commit()

    # Return updated vote counts per option
    c.execute('''
        SELECT po.id, po.text, po.position,
               COUNT(pv.id) AS vote_count
        FROM poll_options po
        LEFT JOIN poll_votes pv ON pv.option_id = po.id
        WHERE po.poll_id = ?
        GROUP BY po.id
        ORDER BY po.position
    ''', (poll_id,))
    options = [dict(r) for r in c.fetchall()]

    # Find what this user voted for
    c.execute('SELECT option_id FROM poll_votes WHERE poll_id = ? AND user_id = ?', (poll_id, user_id))
    voted_row = c.fetchone()
    voted_option_id = voted_row['option_id'] if voted_row else None

    conn.close()
    return jsonify({'options': options, 'voted_option_id': voted_option_id})


# ---------------------------------------------------------------------------
# Backward-compat alias: old /api/posts endpoint
# ---------------------------------------------------------------------------
@bp.route('/api/posts')
def get_posts_compat():
    """Alias for /api/tweets kept for backward compatibility."""
    return get_tweets()
