from flask import Blueprint, request, jsonify
from models import get_db, get_current_user_id, _tweet_row_to_dict

lists_bp = Blueprint('lists', __name__)


# GET /api/lists — get all lists owned by the current user
@lists_bp.route('/api/lists')
def get_lists():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'lists': []})

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT l.id, l.name, l.description, l.created_at,
               COUNT(lm.id) AS member_count
        FROM lists l
        LEFT JOIN list_members lm ON lm.list_id = l.id
        WHERE l.user_id = ?
        GROUP BY l.id
        ORDER BY l.created_at DESC
    ''', (user_id,))
    lists = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'lists': lists})


# POST /api/lists — create a new list
@lists_bp.route('/api/lists', methods=['POST'])
def create_list():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()

    if not name:
        return jsonify({'error': 'name is required'}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute(
        'INSERT INTO lists (user_id, name, description) VALUES (?, ?, ?)',
        (user_id, name, description)
    )
    list_id = c.lastrowid
    conn.commit()
    c.execute('SELECT id, name, description, created_at FROM lists WHERE id = ?', (list_id,))
    row = dict(c.fetchone())
    row['member_count'] = 0
    conn.close()
    return jsonify({'list': row}), 201


# DELETE /api/lists/<id> — delete a list owned by the current user
@lists_bp.route('/api/lists/<int:list_id>', methods=['DELETE'])
def delete_list(list_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id FROM lists WHERE id = ?', (list_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'list not found'}), 404
    if row['user_id'] != user_id:
        conn.close()
        return jsonify({'error': 'forbidden'}), 403

    c.execute('DELETE FROM list_members WHERE list_id = ?', (list_id,))
    c.execute('DELETE FROM lists WHERE id = ?', (list_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# POST /api/lists/<id>/members — add a user to a list
@lists_bp.route('/api/lists/<int:list_id>/members', methods=['POST'])
def add_list_member(list_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    data = request.get_json(force=True, silent=True) or {}
    target_user_id = data.get('user_id')
    if not target_user_id:
        return jsonify({'error': 'user_id is required'}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id FROM lists WHERE id = ?', (list_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'list not found'}), 404
    if row['user_id'] != user_id:
        conn.close()
        return jsonify({'error': 'forbidden'}), 403

    # Verify target user exists
    c.execute('SELECT id FROM users WHERE id = ?', (target_user_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'user not found'}), 404

    c.execute('INSERT OR IGNORE INTO list_members (list_id, user_id) VALUES (?, ?)',
              (list_id, target_user_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True}), 201


# DELETE /api/lists/<id>/members/<user_id> — remove a user from a list
@lists_bp.route('/api/lists/<int:list_id>/members/<int:target_user_id>', methods=['DELETE'])
def remove_list_member(list_id, target_user_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id FROM lists WHERE id = ?', (list_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'list not found'}), 404
    if row['user_id'] != user_id:
        conn.close()
        return jsonify({'error': 'forbidden'}), 403

    c.execute('DELETE FROM list_members WHERE list_id = ? AND user_id = ?',
              (list_id, target_user_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# GET /api/lists/<id>/timeline — get paginated tweets from list members
@lists_bp.route('/api/lists/<int:list_id>/timeline')
def get_list_timeline(list_id):
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 30))
    offset = (page - 1) * limit

    conn = get_db()
    c = conn.cursor()

    # Verify list exists and belongs to current user
    c.execute('SELECT user_id FROM lists WHERE id = ?', (list_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'list not found'}), 404
    if row['user_id'] != user_id:
        conn.close()
        return jsonify({'error': 'forbidden'}), 403

    # Get list member IDs
    c.execute('SELECT user_id FROM list_members WHERE list_id = ?', (list_id,))
    member_ids = [r['user_id'] for r in c.fetchall()]

    if not member_ids:
        conn.close()
        return jsonify({'tweets': [], 'page': page, 'has_more': False})

    # Fetch tweets from list members
    # member_ids contains only integer PKs from the DB — safe to interpolate
    placeholders = ','.join('?' * len(member_ids))
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
            (SELECT COUNT(*) FROM reposts r WHERE r.tweet_id = t.id) + (SELECT COUNT(*) FROM tweets qt WHERE qt.quote_of_id = t.id) AS repost_count,
            (SELECT COUNT(*) FROM tweets r WHERE r.reply_to_id = t.id) AS reply_count
        FROM tweets t
        JOIN users u ON u.id = t.user_id
        LEFT JOIN likes l ON l.tweet_id = t.id
        WHERE t.user_id IN ({placeholders})
        GROUP BY t.id
        ORDER BY t.created_at DESC
        LIMIT ? OFFSET ?
    ''', member_ids + [limit, offset])
    rows = c.fetchall()

    # Fetch liked, reposted, bookmarked IDs for the current user
    liked_ids = set()
    reposted_ids = set()
    bookmarked_ids = set()
    c.execute('SELECT tweet_id FROM likes WHERE user_id = ?', (user_id,))
    liked_ids = {r['tweet_id'] for r in c.fetchall()}
    c.execute('SELECT tweet_id FROM reposts WHERE user_id = ?', (user_id,))
    reposted_ids = {r['tweet_id'] for r in c.fetchall()}
    c.execute('SELECT tweet_id FROM bookmarks WHERE user_id = ?', (user_id,))
    bookmarked_ids = {r['tweet_id'] for r in c.fetchall()}

    tweets = [
        _tweet_row_to_dict(row, row['id'] in liked_ids, row['id'] in reposted_ids, row['id'] in bookmarked_ids)
        for row in rows
    ]
    conn.close()
    return jsonify({'tweets': tweets, 'page': page, 'has_more': len(rows) == limit})
