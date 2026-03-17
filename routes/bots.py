import os
import random
import threading
from flask import request, jsonify
from routes import bots_bp as bp
from models import get_db, _tweet_row_to_dict
from bot_data import BOT_PERSONALITIES, BOT_FALLBACK_TWEETS, BOT_IMAGE_URLS, BOT_SELF_REPLIES


# POST /api/generate-bot-tweet — generate a tweet from a random bot via Gemini
@bp.route('/api/generate-bot-tweet', methods=['POST'])
def generate_bot_tweet():
    conn = get_db()
    c = conn.cursor()

    # Pick a random bot user
    c.execute('SELECT id, username, display_name, handle, avatar_url, banner_url, bio, location, birthday, is_bot, created_at FROM users WHERE is_bot = 1')
    bots = c.fetchall()
    if not bots:
        conn.close()
        return jsonify({'error': 'no bot users found'}), 500

    bot = random.choice(bots)
    bot_username = bot['username']
    personality = BOT_PERSONALITIES.get(bot_username)

    api_key = os.environ.get('GEMINI_API_KEY')

    if api_key and personality:
        # --- Live Gemini path ---
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(personality)
            content = response.text.strip()
            # Truncate to 280 chars just in case
            content = content[:280]
        except Exception:
            # Fall back gracefully rather than crashing
            content = random.choice(BOT_FALLBACK_TWEETS.get(bot_username, ['Hello world!']))
    else:
        # --- Fallback path (no API key or unknown bot) ---
        fallback_list = BOT_FALLBACK_TWEETS.get(bot_username, ['Hello world!'])
        content = random.choice(fallback_list)

    # Optionally attach an image URL for bots that have images (30% chance)
    image_url = ''
    if bot_username in BOT_IMAGE_URLS and random.random() < 0.3:
        image_url = random.choice(BOT_IMAGE_URLS[bot_username])

    # Save the tweet
    c.execute(
        'INSERT INTO tweets (user_id, content, reply_to_id, quote_of_id, image_url) VALUES (?, ?, ?, ?, ?)',
        (bot['id'], content, None, None, image_url)
    )
    tweet_id = c.lastrowid
    conn.commit()

    # Schedule a self-reply for impression farming bots
    if bot_username in BOT_SELF_REPLIES:
        def _self_reply(bot_id, parent_tweet_id, username):
            try:
                replies = BOT_SELF_REPLIES.get(username, [])
                if replies:
                    reply_content = random.choice(replies)
                    conn2 = get_db()
                    c2 = conn2.cursor()
                    c2.execute(
                        'INSERT INTO tweets (user_id, content, reply_to_id) VALUES (?, ?, ?)',
                        (bot_id, reply_content, parent_tweet_id)
                    )
                    conn2.commit()
                    conn2.close()
            except Exception:
                pass

        threading.Timer(
            random.uniform(3, 15),
            _self_reply,
            args=[bot['id'], tweet_id, bot_username]
        ).start()

    # Fetch the full tweet row to return
    c.execute('''
        SELECT
            t.id,
            t.content,
            t.created_at,
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
    conn.close()

    return jsonify({'tweet': _tweet_row_to_dict(row, False)}), 201
