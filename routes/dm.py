import threading
import time
import random
from flask import Blueprint, request, jsonify
from models import get_db, get_current_user_id
from routes import rate_limit
import gemini_client

# In-memory typing indicators: {conv_id: {user_id: expiry_timestamp}}
_typing_state = {}

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


# POST /api/dm/conversations/new — find or create a conversation with a user
@dm_bp.route('/api/dm/conversations/new', methods=['POST'])
def new_conversation():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'auth required'}), 401

    data = request.get_json(force=True, silent=True) or {}
    to_user_id = data.get('to_user_id')
    if not to_user_id:
        return jsonify({'error': 'to_user_id required'}), 400

    conn = get_db()
    c = conn.cursor()

    u1, u2 = min(user_id, to_user_id), max(user_id, to_user_id)
    c.execute('SELECT id FROM dm_conversations WHERE user1_id = ? AND user2_id = ?', (u1, u2))
    conv = c.fetchone()
    if conv:
        conv_id = conv['id']
    else:
        c.execute('INSERT INTO dm_conversations (user1_id, user2_id) VALUES (?, ?)', (u1, u2))
        conv_id = c.lastrowid
        conn.commit()

    conn.close()
    return jsonify({'conversation_id': conv_id})


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
@rate_limit
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

    # Check if the recipient is a bot — if so, schedule a Gemini reply
    c.execute('SELECT id, username, display_name, handle, bio, is_bot FROM users WHERE id = ?', (to_user_id,))
    recipient = c.fetchone()
    is_bot = recipient and recipient['is_bot']

    # Get recent DM history for context (last 10 messages in this conversation)
    recent_messages = []
    if is_bot:
        c.execute('''
            SELECT m.sender_id, m.content FROM dm_messages m
            WHERE m.conversation_id = ?
            ORDER BY m.id DESC LIMIT 10
        ''', (conv_id,))
        recent_messages = [dict(r) for r in c.fetchall()][::-1]  # chronological order

    conn.commit()
    conn.close()

    if is_bot:
        # Set typing indicator immediately, then reply after delay
        _set_typing(conv_id, recipient['id'], duration=15)
        threading.Timer(
            random.uniform(2, 5),
            _bot_dm_reply,
            args=[conv_id, recipient, user_id, content, recent_messages]
        ).start()

    return jsonify({'message_id': msg_id, 'conversation_id': conv_id}), 201


def _set_typing(conv_id, user_id, duration=10):
    """Mark a user as typing in a conversation for `duration` seconds."""
    if conv_id not in _typing_state:
        _typing_state[conv_id] = {}
    _typing_state[conv_id][user_id] = time.time() + duration


def _clear_typing(conv_id, user_id):
    """Clear typing indicator for a user."""
    if conv_id in _typing_state:
        _typing_state[conv_id].pop(user_id, None)


def _bot_dm_reply(conv_id, bot_row, human_user_id, human_message, recent_messages):
    """Generate a Gemini-powered DM reply from a bot."""
    try:
        from bot_data import BOT_PERSONAS
        persona = BOT_PERSONAS.get(bot_row['username'], {})

        profile_info = {
            'display_name': bot_row['display_name'],
            'handle': bot_row['handle'],
            'bio': bot_row['bio'] or '',
        }

        # Build conversation history for context
        history_lines = []
        for msg in recent_messages[-8:]:
            sender = 'あなた' if msg['sender_id'] == bot_row['id'] else '相手'
            history_lines.append(f"{sender}: {msg['content']}")
        history_text = '\n'.join(history_lines) if history_lines else ''

        context = gemini_client._build_persona_context(persona, profile_info)

        prompt = (
            f"あなたは以下のSNSユーザーです。このキャラクターになりきってDMの返信をしてください。\n\n"
            f"{context}\n\n"
        )
        if history_text:
            prompt += f"---\nこれまでの会話:\n{history_text}\n\n"
        prompt += (
            f"---\n"
            f"相手からのメッセージ: {human_message}\n\n"
            f"ルール:\n"
            f"- 150文字以内\n"
            f"- キャラの口調で自然に返信\n"
            f"- 引用符不要、返信文のみ出力\n"
            f"- フレンドリーに会話を続ける\n"
        )

        reply_content = gemini_client.generate(prompt, max_tokens=200)
        if not reply_content:
            # Fallback
            fallbacks = ['なるほど！', 'そうなんだ〜', 'わかる！', 'いいね！', 'へぇ〜']
            reply_content = random.choice(fallbacks)
        else:
            reply_content = reply_content.strip('"\'「」『』').split('\n')[0][:280]

        conn = get_db()
        c = conn.cursor()
        c.execute('INSERT INTO dm_messages (conversation_id, sender_id, content) VALUES (?, ?, ?)',
                  (conv_id, bot_row['id'], reply_content))
        c.execute('UPDATE dm_conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (conv_id,))
        conn.commit()
        conn.close()
        _clear_typing(conv_id, bot_row['id'])
    except Exception:
        _clear_typing(conv_id, bot_row['id'])


# GET /api/dm/conversations/<id>/typing — check who is typing
@dm_bp.route('/api/dm/conversations/<int:conv_id>/typing')
def get_typing(conv_id):
    now = time.time()
    typing_users = []
    conv_state = _typing_state.get(conv_id, {})
    for uid, expiry in list(conv_state.items()):
        if expiry > now:
            typing_users.append(uid)
        else:
            del conv_state[uid]
    return jsonify({'typing': typing_users})


# POST /api/dm/conversations/<id>/typing — signal that the current user is typing
@dm_bp.route('/api/dm/conversations/<int:conv_id>/typing', methods=['POST'])
def set_typing(conv_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'auth required'}), 401
    _set_typing(conv_id, user_id, duration=5)
    return jsonify({'ok': True})


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
