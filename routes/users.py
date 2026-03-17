import os
import re
import uuid
import threading
import random
from flask import request, jsonify, make_response
from routes import users_bp as bp
from models import get_db, get_current_user_id, _tweet_row_to_dict, allowed_file
from bot_engine import _bot_follow_back
from config import UPLOAD_FOLDER


# POST /api/register — create a new human user account and set cookie
# Security note: no password, handle uniqueness enforced by DB UNIQUE constraint.
# The user_id cookie is httponly=False so JS can read it (intentional for this app).
@bp.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(force=True, silent=True) or {}
    display_name = (data.get('display_name') or '').strip()
    handle = (data.get('handle') or '').strip()

    if not display_name:
        return jsonify({'error': 'display_name is required'}), 400
    if not handle:
        return jsonify({'error': 'handle is required'}), 400

    # Handle must start with "@" and be 2-20 chars total (including @), alphanumeric + underscore after @
    if not re.match(r'^@[a-zA-Z0-9_]{1,19}$', handle):
        return jsonify({'error': 'handle must start with @ and contain only letters, numbers, or underscores (2-20 chars total)'}), 400

    # Derive a username from the handle (strip the @)
    username = handle[1:]

    conn = get_db()
    c = conn.cursor()

    # Check for duplicate handle or username
    c.execute('SELECT id FROM users WHERE handle = ? OR username = ?', (handle, username))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'handle already taken'}), 409

    c.execute(
        'INSERT INTO users (username, display_name, handle, avatar_url, is_bot) VALUES (?, ?, ?, ?, ?)',
        (username, display_name, handle, None, 0)
    )
    new_id = c.lastrowid
    conn.commit()

    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot, created_at, pinned_tweet_id FROM users WHERE id = ?', (new_id,))
    user = dict(c.fetchone())
    conn.close()

    resp = make_response(jsonify({'user': user}), 201)
    resp.set_cookie('user_id', str(new_id), max_age=30 * 24 * 60 * 60, httponly=False, samesite='Lax')
    return resp


# GET /api/me — return the current user based on cookie
@bp.route('/api/me')
def get_me():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'user': None})

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot, created_at, pinned_tweet_id FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()

    if row is None:
        return jsonify({'user': None})

    return jsonify({'user': dict(row)})


# PUT /api/me — update the current user's display_name
@bp.route('/api/me', methods=['PUT'])
def update_me():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    data = request.get_json(force=True, silent=True) or {}
    display_name = (data.get('display_name') or '').strip()
    bio = (data.get('bio') or '').strip()
    location = (data.get('location') or '').strip()
    birthday = (data.get('birthday') or '').strip()

    if not display_name:
        return jsonify({'error': 'display_name is required'}), 400

    conn = get_db()
    c = conn.cursor()

    # Don't allow editing bot accounts
    c.execute('SELECT is_bot FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    if not row or row['is_bot']:
        conn.close()
        return jsonify({'error': 'cannot edit this account'}), 403

    c.execute(
        'UPDATE users SET display_name = ?, bio = ?, location = ?, birthday = ? WHERE id = ?',
        (display_name, bio, location, birthday, user_id)
    )
    conn.commit()

    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot, created_at, pinned_tweet_id FROM users WHERE id = ?', (user_id,))
    user = dict(c.fetchone())
    conn.close()

    return jsonify({'user': user})


# GET /api/users — list all users
@bp.route('/api/users')
def get_users():
    conn = get_db()
    c = conn.cursor()

    current_user_id = get_current_user_id()
    following_ids = set()
    if current_user_id is not None:
        c.execute('SELECT following_id FROM follows WHERE follower_id = ?', (current_user_id,))
        following_ids = {r['following_id'] for r in c.fetchall()}

    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot, created_at, pinned_tweet_id FROM users')
    users = []
    for row in c.fetchall():
        u = dict(row)
        u['is_following'] = u['id'] in following_ids
        users.append(u)

    conn.close()
    return jsonify({'users': users})


# GET /api/users/search — search users by display_name, handle, or username
@bp.route('/api/users/search')
def search_users():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 1:
        return jsonify({'users': []})

    conn = get_db()
    c = conn.cursor()

    search_term = f'%{q}%'
    c.execute('''
        SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot
        FROM users
        WHERE display_name LIKE ? OR handle LIKE ? OR username LIKE ?
        ORDER BY display_name
        LIMIT 20
    ''', (search_term, search_term, search_term))
    users = [dict(row) for row in c.fetchall()]

    current_user_id = get_current_user_id()
    following_ids = set()
    if current_user_id is not None:
        c.execute('SELECT following_id FROM follows WHERE follower_id = ?', (current_user_id,))
        following_ids = {r['following_id'] for r in c.fetchall()}

    for u in users:
        u['is_following'] = u['id'] in following_ids

    conn.close()
    return jsonify({'users': users})


# GET /api/users/<handle>/profile — return a user's profile + their tweets
@bp.route('/api/users/<path:handle>/profile')
def get_user_profile(handle):
    # handle comes with @ prefix from frontend
    if not handle.startswith('@'):
        handle = '@' + handle

    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot, created_at, pinned_tweet_id FROM users WHERE handle = ?', (handle,))
    user = c.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'user not found'}), 404

    user_dict = dict(user)
    user_id = user['id']

    # Get tweet count (top-level tweets only, no replies)
    c.execute('SELECT COUNT(*) AS cnt FROM tweets WHERE user_id = ? AND reply_to_id IS NULL', (user_id,))
    user_dict['tweet_count'] = c.fetchone()['cnt']

    # Get like count (how many likes this user has received across all their tweets)
    c.execute('''
        SELECT COUNT(*) AS cnt FROM likes l
        JOIN tweets t ON t.id = l.tweet_id
        WHERE t.user_id = ?
    ''', (user_id,))
    user_dict['likes_received'] = c.fetchone()['cnt']

    # Get follower/following counts
    c.execute('SELECT COUNT(*) AS cnt FROM follows WHERE following_id = ?', (user_id,))
    user_dict['followers_count'] = c.fetchone()['cnt']

    c.execute('SELECT COUNT(*) AS cnt FROM follows WHERE follower_id = ?', (user_id,))
    user_dict['following_count'] = c.fetchone()['cnt']

    # Check if the current user is following this profile
    current_user_id = get_current_user_id()
    user_dict['is_following'] = False
    if current_user_id is not None:
        c.execute('SELECT id FROM follows WHERE follower_id = ? AND following_id = ?', (current_user_id, user_id))
        user_dict['is_following'] = c.fetchone() is not None

    # Get this user's tweets (including replies), with like/repost counts
    c.execute('''
        SELECT
            t.id, t.content, t.created_at, t.reply_to_id, t.quote_of_id, t.impressions, t.image_url,
            u.id AS user_id, u.display_name, u.handle, u.avatar_url, u.is_bot,
            COUNT(DISTINCT l.id) AS like_count,
            (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count
        FROM tweets t
        JOIN users u ON u.id = t.user_id
        LEFT JOIN likes l ON l.tweet_id = t.id
        WHERE t.user_id = ?
        GROUP BY t.id
        ORDER BY t.created_at DESC
    ''', (user_id,))
    rows = c.fetchall()

    # Increment impressions for all visible tweets
    if rows:
        tweet_ids = [row['id'] for row in rows]
        placeholders = ','.join('?' * len(tweet_ids))
        c.execute(f'UPDATE tweets SET impressions = impressions + 1 WHERE id IN ({placeholders})', tweet_ids)
        conn.commit()

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

    pinned_tweet_id = user_dict.get('pinned_tweet_id')
    tweets = []
    for row in rows:
        t = _tweet_row_to_dict(row, row['id'] in liked_ids, row['id'] in reposted_ids, row['id'] in bookmarked_ids)
        t['is_pinned'] = (pinned_tweet_id is not None and row['id'] == pinned_tweet_id)
        tweets.append(t)

    # Fetch tweets this user reposted
    c.execute('''
        SELECT t.id, t.content, t.created_at, t.reply_to_id, t.quote_of_id, t.image_url,
               u.id AS user_id, u.display_name, u.handle, u.avatar_url, u.is_bot,
               COUNT(DISTINCT l.id) AS like_count,
               (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count,
               t.impressions
        FROM reposts rp
        JOIN tweets t ON t.id = rp.tweet_id
        JOIN users u ON u.id = t.user_id
        LEFT JOIN likes l ON l.tweet_id = t.id
        WHERE rp.user_id = ?
        GROUP BY t.id
        ORDER BY rp.id DESC
    ''', (user_id,))
    repost_rows = c.fetchall()
    reposted_tweets = [_tweet_row_to_dict(row, row['id'] in liked_ids, True, row['id'] in bookmarked_ids) for row in repost_rows]

    # Mark reposted tweets with a 'reposted_by' field
    for rt in reposted_tweets:
        rt['reposted_by'] = user_dict['display_name']

    conn.close()

    return jsonify({'user': user_dict, 'tweets': tweets, 'reposted_tweets': reposted_tweets})


# POST /api/users/<id>/follow — toggle follow/unfollow for the current cookie user
@bp.route('/api/users/<int:target_user_id>/follow', methods=['POST'])
def toggle_follow(target_user_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401
    if user_id == target_user_id:
        return jsonify({'error': 'cannot follow yourself'}), 400

    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT id FROM follows WHERE follower_id = ? AND following_id = ?', (user_id, target_user_id))
    existing = c.fetchone()

    if not existing:
        # User just followed someone
        c.execute('INSERT INTO follows (follower_id, following_id) VALUES (?, ?)', (user_id, target_user_id))
        following = True

        # Create follow notification for the target user
        c.execute(
            'INSERT INTO notifications (user_id, type, actor_id, tweet_id) VALUES (?, ?, ?, ?)',
            (target_user_id, 'follow', user_id, None)
        )

        # Auto follow-back: if target is a bot, maybe follow back after delay
        c.execute('SELECT is_bot FROM users WHERE id = ?', (target_user_id,))
        target_row = c.fetchone()
        if target_row and target_row['is_bot']:
            threading.Timer(
                random.uniform(5, 60),
                _bot_follow_back,
                args=[target_user_id, user_id, True]
            ).start()
    else:
        # User just unfollowed someone
        c.execute('DELETE FROM follows WHERE follower_id = ? AND following_id = ?', (user_id, target_user_id))
        following = False

        # Maybe unfollow back
        c.execute('SELECT is_bot FROM users WHERE id = ?', (target_user_id,))
        target_row = c.fetchone()
        if target_row and target_row['is_bot']:
            threading.Timer(
                random.uniform(10, 120),
                _bot_follow_back,
                args=[target_user_id, user_id, False]
            ).start()

    conn.commit()

    # Return updated counts for the target user
    c.execute('SELECT COUNT(*) AS cnt FROM follows WHERE following_id = ?', (target_user_id,))
    followers_count = c.fetchone()['cnt']
    c.execute('SELECT COUNT(*) AS cnt FROM follows WHERE follower_id = ?', (target_user_id,))
    following_count = c.fetchone()['cnt']

    conn.close()
    return jsonify({'following': following, 'followers_count': followers_count, 'following_count': following_count})


# GET /api/users/<id>/followers — list users who follow this user
@bp.route('/api/users/<int:user_id>/followers')
def get_followers(user_id):
    conn = get_db()
    c = conn.cursor()

    current_user_id = get_current_user_id()

    c.execute('''
        SELECT u.id, u.display_name, u.handle, u.avatar_url, u.bio, u.location, u.birthday
        FROM follows f
        JOIN users u ON u.id = f.follower_id
        WHERE f.following_id = ?
        ORDER BY f.created_at DESC
    ''', (user_id,))
    users = [dict(row) for row in c.fetchall()]

    # Check which of these users the current user follows
    following_ids = set()
    if current_user_id is not None:
        c.execute('SELECT following_id FROM follows WHERE follower_id = ?', (current_user_id,))
        following_ids = {r['following_id'] for r in c.fetchall()}

    for u in users:
        u['is_following'] = u['id'] in following_ids

    conn.close()
    return jsonify({'users': users})


# GET /api/users/<id>/following — list users this user follows
@bp.route('/api/users/<int:user_id>/following')
def get_following(user_id):
    conn = get_db()
    c = conn.cursor()

    current_user_id = get_current_user_id()

    c.execute('''
        SELECT u.id, u.display_name, u.handle, u.avatar_url, u.bio, u.location, u.birthday
        FROM follows f
        JOIN users u ON u.id = f.following_id
        WHERE f.follower_id = ?
        ORDER BY f.created_at DESC
    ''', (user_id,))
    users = [dict(row) for row in c.fetchall()]

    following_ids = set()
    if current_user_id is not None:
        c.execute('SELECT following_id FROM follows WHERE follower_id = ?', (current_user_id,))
        following_ids = {r['following_id'] for r in c.fetchall()}

    for u in users:
        u['is_following'] = u['id'] in following_ids

    conn.close()
    return jsonify({'users': users})


# POST /api/users/<id>/mute — toggle mute for the current user on a target user
@bp.route('/api/users/<int:target_id>/mute', methods=['POST'])
def toggle_mute(target_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401
    if user_id == target_id:
        return jsonify({'error': 'cannot mute yourself'}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM mutes WHERE user_id = ? AND target_id = ?', (user_id, target_id))
    existing = c.fetchone()
    if existing:
        c.execute('DELETE FROM mutes WHERE user_id = ? AND target_id = ?', (user_id, target_id))
        muted = False
    else:
        c.execute('INSERT INTO mutes (user_id, target_id) VALUES (?, ?)', (user_id, target_id))
        muted = True
    conn.commit()
    conn.close()
    return jsonify({'muted': muted})


# POST /api/users/<id>/block — toggle block for the current user on a target user
# Blocking also removes follows in both directions.
@bp.route('/api/users/<int:target_id>/block', methods=['POST'])
def toggle_block(target_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401
    if user_id == target_id:
        return jsonify({'error': 'cannot block yourself'}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM blocks WHERE user_id = ? AND target_id = ?', (user_id, target_id))
    existing = c.fetchone()
    if existing:
        c.execute('DELETE FROM blocks WHERE user_id = ? AND target_id = ?', (user_id, target_id))
        blocked = False
    else:
        c.execute('INSERT INTO blocks (user_id, target_id) VALUES (?, ?)', (user_id, target_id))
        blocked = True
        # Remove follows both ways when blocking
        c.execute('DELETE FROM follows WHERE (follower_id = ? AND following_id = ?) OR (follower_id = ? AND following_id = ?)',
                  (user_id, target_id, target_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({'blocked': blocked})


# POST /api/me/avatar — upload a new avatar image for the current user
@bp.route('/api/me/avatar', methods=['POST'])
def upload_avatar():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'no file provided'}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'invalid file type'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f'avatar_{user_id}_{uuid.uuid4().hex[:8]}.{ext}'
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    avatar_url = f'/static/uploads/{filename}'

    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET avatar_url = ? WHERE id = ?', (avatar_url, user_id))
    conn.commit()
    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot, created_at, pinned_tweet_id FROM users WHERE id = ?', (user_id,))
    user = dict(c.fetchone())
    conn.close()

    return jsonify({'user': user, 'avatar_url': avatar_url})


# POST /api/me/banner — upload a new banner image for the current user
@bp.route('/api/me/banner', methods=['POST'])
def upload_banner():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'no file provided'}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'invalid file type'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f'banner_{user_id}_{uuid.uuid4().hex[:8]}.{ext}'
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    banner_url = f'/static/uploads/{filename}'

    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET banner_url = ? WHERE id = ?', (banner_url, user_id))
    conn.commit()
    conn.close()

    return jsonify({'banner_url': banner_url})
