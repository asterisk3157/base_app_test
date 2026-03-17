from flask import request, jsonify
from routes import notifications_bp as bp
from models import get_db, get_current_user_id


# GET /api/notifications — get notifications for current user
@bp.route('/api/notifications')
def get_notifications():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'notifications': []})

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT n.id, n.type, n.tweet_id, n.read, n.created_at,
               u.id AS actor_id, u.display_name AS actor_name, u.handle AS actor_handle, u.avatar_url AS actor_avatar
        FROM notifications n
        JOIN users u ON u.id = n.actor_id
        WHERE n.user_id = ?
        ORDER BY n.created_at DESC
        LIMIT 50
    ''', (user_id,))
    notifications = [dict(row) for row in c.fetchall()]

    # Count unread
    c.execute('SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = ? AND read = 0', (user_id,))
    unread_count = c.fetchone()['cnt']

    conn.close()
    return jsonify({'notifications': notifications, 'unread_count': unread_count})


# POST /api/notifications/read — mark all notifications as read
@bp.route('/api/notifications/read', methods=['POST'])
def mark_notifications_read():
    user_id = get_current_user_id()
    if user_id is None:
        return jsonify({'error': 'authentication required'}), 401

    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE notifications SET read = 1 WHERE user_id = ? AND read = 0', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})
