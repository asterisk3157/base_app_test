import os
import random
import time
import threading
from models import get_db
from bot_data import BOT_FALLBACK_REPLIES, BOT_PERSONALITIES, BOT_PERSONAS
import gemini_client

# Maximum depth of bot conversation chains:
# human tweet (depth 0) -> bot1 reply (depth 1) -> bot2 reply (depth 2) -> bot3 reply (depth 3)
BOT_CHAIN_MAX_DEPTH = 3
# Probability a different bot continues the chain after a bot reply
BOT_CHAIN_PROBABILITY = 0.20


def _get_persona_topics(bot_username):
    """Return the topic list for a bot from the JSON personas (or empty list)."""
    persona = BOT_PERSONAS.get(bot_username, {})
    return persona.get('topics', [])


def _get_persona_reply_templates(bot_username):
    """Return reply_templates from JSON persona, falling back to BOT_FALLBACK_REPLIES."""
    persona = BOT_PERSONAS.get(bot_username, {})
    templates = persona.get('reply_templates', [])
    if templates:
        return templates
    return BOT_FALLBACK_REPLIES.get(bot_username, ['いいね！'])


def _topics_match(bot_username, tweet_content):
    """Return True if any of the bot's topics appear in the tweet content (case-insensitive)."""
    topics = _get_persona_topics(bot_username)
    if not topics:
        return False
    tweet_lower = tweet_content.lower()
    return any(topic.lower() in tweet_lower for topic in topics)


def _fallback_reply(bot_username, tweet_content):
    """Return a random fallback reply string for the given bot."""
    templates = _get_persona_reply_templates(bot_username)
    return random.choice(templates)


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


def _bot_reply(bot_user_id, bot_username, tweet_id, tweet_content, chain_depth=1):
    """Bot replies to a tweet using Gemini or fallback (called from a background thread).
    chain_depth: how deep in the conversation chain this reply is (1 = first bot reply).
    After posting, may trigger a chained reply from a *different* bot at depth+1.
    """
    try:
        # Try Gemini first (with DB profile context), fallback to template
        persona = BOT_PERSONAS.get(bot_username, {})
        profile_info = None
        try:
            conn2 = get_db()
            c2 = conn2.cursor()
            c2.execute('SELECT display_name, handle, bio, location FROM users WHERE username = ?', (bot_username,))
            row = c2.fetchone()
            if row:
                profile_info = dict(row)
            conn2.close()
        except Exception:
            pass
        content = gemini_client.generate_reply(persona, tweet_content, profile_info)
        if not content:
            content = _fallback_reply(bot_username, tweet_content)

        conn = get_db()
        c = conn.cursor()
        c.execute(
            'INSERT INTO tweets (user_id, content, reply_to_id) VALUES (?, ?, ?)',
            (bot_user_id, content, tweet_id)
        )
        new_tweet_id = c.lastrowid

        # Create a notification for the tweet owner
        c.execute('SELECT user_id FROM tweets WHERE id = ?', (tweet_id,))
        tweet_row = c.fetchone()
        if tweet_row and tweet_row['user_id'] != bot_user_id:
            c.execute(
                'INSERT INTO notifications (user_id, type, actor_id, tweet_id) VALUES (?, ?, ?, ?)',
                (tweet_row['user_id'], 'reply', bot_user_id, tweet_id)
            )
        conn.commit()

        # Fetch all bots for potential chain reply
        c.execute('SELECT id, username FROM users WHERE is_bot = 1')
        all_bots = [dict(r) for r in c.fetchall()]
        conn.close()

        # --- Bot Conversation Chain ---
        # After a bot posts a reply, there is a BOT_CHAIN_PROBABILITY chance
        # that a DIFFERENT bot will reply to that reply, up to BOT_CHAIN_MAX_DEPTH.
        if chain_depth < BOT_CHAIN_MAX_DEPTH and random.random() < BOT_CHAIN_PROBABILITY:
            # Pick a different bot for the chain
            other_bots = [b for b in all_bots if b['id'] != bot_user_id]
            if other_bots:
                chain_bot = random.choice(other_bots)
                chain_templates = _get_persona_reply_templates(chain_bot['username'])
                chain_content = random.choice(chain_templates)
                chain_delay = random.uniform(30, 120)
                # Use a pre-built content string to avoid Gemini call overhead in chain replies
                threading.Timer(
                    chain_delay,
                    _bot_chain_reply,
                    args=[chain_bot['id'], chain_bot['username'],
                          new_tweet_id, chain_content, chain_depth + 1]
                ).start()

    except Exception:
        pass


def _bot_chain_reply(bot_user_id, bot_username, parent_tweet_id, content, chain_depth):
    """Insert a chained bot-to-bot reply and optionally continue the chain."""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            'INSERT INTO tweets (user_id, content, reply_to_id) VALUES (?, ?, ?)',
            (bot_user_id, content, parent_tweet_id)
        )
        new_tweet_id = c.lastrowid

        # Notification for the parent tweet's author
        c.execute('SELECT user_id FROM tweets WHERE id = ?', (parent_tweet_id,))
        parent_row = c.fetchone()
        if parent_row and parent_row['user_id'] != bot_user_id:
            c.execute(
                'INSERT INTO notifications (user_id, type, actor_id, tweet_id) VALUES (?, ?, ?, ?)',
                (parent_row['user_id'], 'reply', bot_user_id, parent_tweet_id)
            )
        conn.commit()

        # Potentially continue the chain
        if chain_depth < BOT_CHAIN_MAX_DEPTH and random.random() < BOT_CHAIN_PROBABILITY:
            c.execute('SELECT id, username FROM users WHERE is_bot = 1')
            all_bots = [dict(r) for r in c.fetchall()]
            conn.close()
            other_bots = [b for b in all_bots if b['id'] != bot_user_id]
            if other_bots:
                chain_bot = random.choice(other_bots)
                chain_templates = _get_persona_reply_templates(chain_bot['username'])
                next_content = random.choice(chain_templates)
                chain_delay = random.uniform(30, 120)
                threading.Timer(
                    chain_delay,
                    _bot_chain_reply,
                    args=[chain_bot['id'], chain_bot['username'],
                          new_tweet_id, next_content, chain_depth + 1]
                ).start()
        else:
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


def _bots_follow_new_user(new_user_id):
    """After a new human registers, 3-5 random bots follow them (called in background)."""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE is_bot = 1')
        all_bots = [r['id'] for r in c.fetchall()]
        conn.close()

        if not all_bots:
            return

        follow_count = min(random.randint(3, 5), len(all_bots))
        chosen_bots = random.sample(all_bots, follow_count)

        for bot_id in chosen_bots:
            delay = random.uniform(5, 60)
            threading.Timer(delay, _do_bot_follow, args=[bot_id, new_user_id]).start()

    except Exception:
        pass


def _do_bot_follow(bot_id, user_id):
    """Insert a follow row for bot -> user."""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            'INSERT OR IGNORE INTO follows (follower_id, following_id) VALUES (?, ?)',
            (bot_id, user_id)
        )
        # Notify the new user that a bot followed them
        c.execute(
            'INSERT INTO notifications (user_id, type, actor_id, tweet_id) VALUES (?, ?, ?, ?)',
            (user_id, 'follow', bot_id, None)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def trigger_bot_reactions(tweet_id, tweet_content, poster_user_id):
    """Schedule bot reactions with FF-aware and topic-aware probability."""
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
        topic_match = _topics_match(bot['username'], tweet_content)

        if is_followed:
            # Followed bots: base like rate, boosted/reduced by topic match
            if topic_match:
                like_prob = 0.80  # high — topic matches bot's interests
            else:
                like_prob = 0.20  # low — not their thing
            reply_prob = {'techbot': 0.15, 'catlover99': 0.10, 'newsflash': 0.10,
                          'philobot': 0.05}.get(bot['username'], 0.10)
        else:
            # Non-followed bots: topic match still raises the bar slightly
            if topic_match:
                like_prob = 0.20  # some interest even without follow
            else:
                like_prob = 0.05  # very unlikely to notice
            reply_prob = 0.01

        like_delay = random.uniform(15, 120)
        reply_delay = random.uniform(30, 180)

        if random.random() < like_prob:
            threading.Timer(like_delay, _bot_like, args=[bot['id'], tweet_id]).start()

        if random.random() < reply_prob:
            # chain_depth starts at 1 (first bot reply to a human tweet)
            threading.Timer(reply_delay, _bot_reply,
                            args=[bot['id'], bot['username'], tweet_id, tweet_content, 1]).start()


# ---------------------------------------------------------------------------
# B: Bot spontaneous tweets (Gemini-generated)
# Only bots that have at least 1 human follower are eligible.
# Each bot has its own cooldown tracked in _bot_last_tweet.
# ---------------------------------------------------------------------------
_bot_last_tweet = {}  # bot_user_id -> last tweet timestamp
_BOT_TWEET_COOLDOWN = 120  # 2 min cooldown per bot
_BOT_TWEET_PROBABILITY = 0.05  # 5% chance per bot per check


def maybe_generate_bot_tweet():
    """Check ALL bots — each has 5% chance to tweet if cooldown (2min) has passed.
    Called from get_tweets() on each page load.
    """
    if not gemini_client.is_available():
        return

    def _do_generate():
        try:
            conn = get_db()
            c = conn.cursor()

            # Get all bots
            c.execute('SELECT id, username, display_name, handle, bio, location FROM users WHERE is_bot = 1')
            all_bots = [dict(r) for r in c.fetchall()]

            if not all_bots:
                conn.close()
                return

            now = time.time()

            for bot in all_bots:
                # Check cooldown
                if now - _bot_last_tweet.get(bot['id'], 0) < _BOT_TWEET_COOLDOWN:
                    continue

                # 5% chance
                if random.random() > _BOT_TWEET_PROBABILITY:
                    continue

                _bot_last_tweet[bot['id']] = now

                # Get persona
                persona = BOT_PERSONAS.get(bot['username'], {})
                profile_info = {
                    'display_name': bot['display_name'],
                    'handle': bot['handle'],
                    'bio': bot.get('bio', ''),
                    'location': bot.get('location', ''),
                }

                # Get recent tweets as style reference
                c.execute(
                    'SELECT content FROM tweets WHERE user_id = ? AND reply_to_id IS NULL ORDER BY id DESC LIMIT 5',
                    (bot['id'],)
                )
                recent_tweets = [r['content'] for r in c.fetchall()]

                content = gemini_client.generate_original_tweet(persona, profile_info, recent_tweets)
                if not content:
                    continue

                c.execute(
                    'INSERT INTO tweets (user_id, content) VALUES (?, ?)',
                    (bot['id'], content)
                )
                conn.commit()
                break  # 1 bot per page load to avoid API burst

            conn.close()
        except Exception:
            pass

    threading.Thread(target=_do_generate, daemon=True).start()


def trigger_new_user_bot_follows(new_user_id):
    """Called when a new human user registers. Schedules 3-5 bot follows."""
    threading.Thread(target=_bots_follow_new_user, args=[new_user_id], daemon=True).start()


def seed_bot_interactions(conn, c):
    """Re-export seed_bot_interactions for backward compatibility."""
    from models import seed_bot_interactions as _seed
    _seed(conn, c)
