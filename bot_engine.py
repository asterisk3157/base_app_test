import os
import random
import threading
from models import get_db
from bot_data import BOT_FALLBACK_REPLIES, BOT_PERSONALITIES


def _fallback_reply(bot_username, tweet_content):
    """Return a random fallback reply string for the given bot."""
    replies = BOT_FALLBACK_REPLIES.get(bot_username, ["いいね！"])
    return random.choice(replies)


def _bot_like(bot_user_id, tweet_id):
    """Bot likes a tweet (called from a background thread)."""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            'INSERT OR IGNORE INTO likes (tweet_id, user_id) VALUES (?, ?)',
            (tweet_id, bot_user_id)
        )
        # Create a notification for the tweet owner
        c.execute('SELECT user_id FROM tweets WHERE id = ?', (tweet_id,))
        tweet_row = c.fetchone()
        if tweet_row and tweet_row['user_id'] != bot_user_id:
            c.execute(
                'INSERT INTO notifications (user_id, type, actor_id, tweet_id) VALUES (?, ?, ?, ?)',
                (tweet_row['user_id'], 'like', bot_user_id, tweet_id)
            )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _bot_reply(bot_user_id, bot_username, tweet_id, tweet_content):
    """Bot replies to a tweet using Gemini or fallback (called from a background thread)."""
    try:
        api_key = os.environ.get('GEMINI_API_KEY')
        personality = BOT_PERSONALITIES.get(bot_username)

        if api_key and personality:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.0-flash')
                prompt = (
                    f"{personality}\n\n"
                    f"以下のツイートへのリプライとして、短い返信を1つ書いてください（100文字以内）:\n"
                    f"「{tweet_content}」"
                )
                response = model.generate_content(prompt)
                content = response.text.strip()[:280]
            except Exception:
                content = _fallback_reply(bot_username, tweet_content)
        else:
            content = _fallback_reply(bot_username, tweet_content)

        conn = get_db()
        c = conn.cursor()
        c.execute(
            'INSERT INTO tweets (user_id, content, reply_to_id) VALUES (?, ?, ?)',
            (bot_user_id, content, tweet_id)
        )
        # Create a notification for the tweet owner
        c.execute('SELECT user_id FROM tweets WHERE id = ?', (tweet_id,))
        tweet_row = c.fetchone()
        if tweet_row and tweet_row['user_id'] != bot_user_id:
            c.execute(
                'INSERT INTO notifications (user_id, type, actor_id, tweet_id) VALUES (?, ?, ?, ?)',
                (tweet_row['user_id'], 'reply', bot_user_id, tweet_id)
            )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _bot_follow_back(bot_id, user_id, should_follow):
    """Bot follows back or unfollows a user with low probability."""
    try:
        # 30% chance to follow back, 20% chance to unfollow back
        prob = 0.30 if should_follow else 0.20
        if random.random() > prob:
            return

        conn = get_db()
        c = conn.cursor()
        if should_follow:
            c.execute('INSERT OR IGNORE INTO follows (follower_id, following_id) VALUES (?, ?)', (bot_id, user_id))
        else:
            c.execute('DELETE FROM follows WHERE follower_id = ? AND following_id = ?', (bot_id, user_id))
        conn.commit()
        conn.close()
    except Exception:
        pass


def trigger_bot_reactions(tweet_id, tweet_content, poster_user_id):
    """Schedule bot reactions with FF-aware probability."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, username, display_name FROM users WHERE is_bot = 1')
    bots = [dict(row) for row in c.fetchall()]

    # Get who the poster follows
    c.execute('SELECT following_id FROM follows WHERE follower_id = ?', (poster_user_id,))
    poster_following = {r['following_id'] for r in c.fetchall()}
    conn.close()

    for bot in bots:
        is_followed = bot['id'] in poster_following

        # FF users get normal rates, non-FF get very low rates
        if is_followed:
            like_prob = {'techbot': 0.7, 'catlover99': 0.6, 'newsflash': 0.8, 'philobot': 0.5}.get(bot['username'], 0.6)
            reply_prob = {'techbot': 0.15, 'catlover99': 0.10, 'newsflash': 0.10, 'philobot': 0.05}.get(bot['username'], 0.10)
        else:
            # Non-FF: very low probability
            like_prob = 0.05
            reply_prob = 0.01

        like_delay = random.uniform(15, 120)
        reply_delay = random.uniform(30, 180)

        if random.random() < like_prob:
            threading.Timer(like_delay, _bot_like, args=[bot['id'], tweet_id]).start()

        if random.random() < reply_prob:
            threading.Timer(reply_delay, _bot_reply, args=[bot['id'], bot['username'], tweet_id, tweet_content]).start()


def seed_bot_interactions(conn, c):
    """Re-export seed_bot_interactions for backward compatibility."""
    from models import seed_bot_interactions as _seed
    _seed(conn, c)
