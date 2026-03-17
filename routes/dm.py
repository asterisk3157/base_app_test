from flask import Blueprint, request, jsonify
from models import get_db, get_current_user_id

dm_bp = Blueprint('dm', __name__)


# GET /api/dm/conversations — list all conversations for the current user
@dm_bp.route('/api/dm/conversations')
def get_conversations():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'conversations': []})

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT dc.id, dc.user1_id, dc.user2_id, dc.updated_at,
               CASE WHEN dc.user1_id = ? THEN u2.id ELSE u1.id END AS other_id,
               CASE WHEN dc.user1_id = ? THEN u2.display_name ELSE u1.display_name END AS other_name,
               CASE WHEN dc.user1_id = ? THEN u2.handle ELSE u1.handle END AS other_handle,
               CASE WHEN dc.user1_id = ? THEN u2.avatar_url ELSE u1.avatar_url END AS other_avatar,
               (SELECT content FROM dm_messages WHERE conversation_id = dc.id ORDER BY id DESC LIMIT 1) AS last_message,
               (SELECT COUNT(*) FROM dm_messages WHERE conversation_id = dc.id AND sender_id != ? AND read = 0) AS unread_count
        FROM dm_conversations dc
        JOIN users u1 ON u1.id = dc.user1_id
        JOIN users u2 ON u2.id = dc.user2_id
        WHERE dc.user1_id = ? OR dc.user2_id = ?
        ORDER BY dc.updated_at DESC
    ''', (user_id, user_id, user_id, user_id, user_id, user_id, user_id))
    convos = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'conversations': convos})


# GET /api/dm/conversations/<id>/messages — get messages in a conversation
@dm_bp.route('/api/dm/conversations/<int:conv_id>/messages')
def get_messages(conv_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'auth required'}), 401

    conn = get_db()
    c = conn.cursor()
    # Verify user is part of conversation
    c.execute('SELECT user1_id, user2_id FROM dm_conversations WHERE id = ?', (conv_id,))
    conv = c.fetchone()
    if not conv or (conv['user1_id'] != user_id and conv['user2_id'] != user_id):
        conn.close()
        return jsonify({'error': 'not found'}), 404

    # Mark messages as read
    c.execute('UPDATE dm_messages SET read = 1 WHERE conversation_id = ? AND sender_id != ? AND read = 0',
              (conv_id, user_id))
    conn.commit()

    c.execute('''
        SELECT m.id, m.sender_id, m.content, m.read, m.created_at,
               u.display_name, u.handle, u.avatar_url
        FROM dm_messages m
        JOIN users u ON u.id = m.sender_id
        WHERE m.conversation_id = ?
        ORDER BY m.created_at ASC
    ''', (conv_id,))
    messages = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'messages': messages})


# POST /api/dm/send — send a DM
@dm_bp.route('/api/dm/send', methods=['POST'])
def send_dm():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'auth required'}), 401

    data = request.get_json(force=True, silent=True) or {}
    to_user_id = data.get('to_user_id')
    content = (data.get('content') or '').strip()
    if not to_user_id or not content:
        return jsonify({'error': 'to_user_id and content required'}), 400

    conn = get_db()
    c = conn.cursor()

    # Find or create conversation (store with smaller id as user1_id for uniqueness)
    u1, u2 = min(user_id, to_user_id), max(user_id, to_user_id)
    c.execute('SELECT id FROM dm_conversations WHERE user1_id = ? AND user2_id = ?', (u1, u2))
    conv = c.fetchone()
    if conv:
        conv_id = conv['id']
    else:
        c.execute('INSERT INTO dm_conversations (user1_id, user2_id) VALUES (?, ?)', (u1, u2))
        conv_id = c.lastrowid

    c.execute('INSERT INTO dm_messages (conversation_id, sender_id, content) VALUES (?, ?, ?)',
              (conv_id, user_id, content))
    msg_id = c.lastrowid
    c.execute('UPDATE dm_conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (conv_id,))
    conn.commit()
    conn.close()
    return jsonify({'message_id': msg_id, 'conversation_id': conv_id}), 201


# GET /api/dm/unread — count of unread DMs for the current user
@dm_bp.route('/api/dm/unread')
def dm_unread():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'count': 0})
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT COUNT(*) AS cnt FROM dm_messages m
        JOIN dm_conversations dc ON dc.id = m.conversation_id
        WHERE (dc.user1_id = ? OR dc.user2_id = ?) AND m.sender_id != ? AND m.read = 0
    ''', (user_id, user_id, user_id))
    count = c.fetchone()['cnt']
    conn.close()
    return jsonify({'count': count})
