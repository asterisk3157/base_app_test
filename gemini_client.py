"""
Gemini API wrapper for bot tweet/reply generation.
Falls back gracefully when API key is not set or calls fail.
"""
import json
import urllib.request
import urllib.error
from config import GEMINI_API_KEY, GEMINI_MODEL

_API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'


def is_available():
    """Return True if Gemini API key is configured."""
    return bool(GEMINI_API_KEY)


def generate(prompt, max_tokens=256):
    """
    Call Gemini API with the given prompt. Returns generated text or None on failure.
    Uses urllib (stdlib only) — no external dependencies required.
    """
    if not GEMINI_API_KEY:
        return None

    url = f'{_API_URL}?key={GEMINI_API_KEY}'
    payload = json.dumps({
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'maxOutputTokens': max_tokens, 'temperature': 0.9}
    }).encode('utf-8')

    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            text = data['candidates'][0]['content']['parts'][0]['text']
            return text.strip()
    except Exception:
        return None


def _build_persona_context(bot_persona, profile_info=None):
    """Build a rich persona context string from persona JSON + DB profile."""
    persona = bot_persona or {}
    parts = []

    # Display name and handle from DB profile
    if profile_info:
        parts.append(f"表示名: {profile_info.get('display_name', '')}")
        parts.append(f"ハンドル: {profile_info.get('handle', '')}")
        bio = profile_info.get('bio', '')
        if bio:
            parts.append(f"自己紹介: {bio}")
        location = profile_info.get('location', '')
        if location:
            parts.append(f"場所: {location}")

    # Persona traits
    personality = persona.get('personality', '')
    if personality:
        parts.append(f"キャラ設定: {personality}")

    reply_style = persona.get('reply_style', '')
    if reply_style:
        parts.append(f"口調スタイル: {reply_style}")

    topics = persona.get('topics', [])
    if topics:
        parts.append(f"興味: {', '.join(topics)}")

    # Example tweets from reply_templates as tone reference
    templates = persona.get('reply_templates', [])
    if templates:
        examples = templates[:3]
        parts.append(f"過去の発言例: {' / '.join(examples)}")

    return '\n'.join(parts)


def generate_reply(bot_persona, tweet_content, profile_info=None):
    """Generate a reply to a tweet using the bot's persona + profile context."""
    context = _build_persona_context(bot_persona, profile_info)

    prompt = (
        f"あなたは以下のSNSユーザーです。このキャラクターになりきってください。\n\n"
        f"{context}\n\n"
        f"---\n"
        f"以下のツイートに対して、このキャラの口調で自然な返信を1つだけ書いてください。\n"
        f"ルール:\n"
        f"- 100文字以内\n"
        f"- 引用符や「」で囲まない\n"
        f"- 説明や前置きなし、返信文のみ出力\n"
        f"- キャラの口調・性格を忠実に反映\n\n"
        f"ツイート: {tweet_content}"
    )
    result = generate(prompt, max_tokens=128)
    if result:
        result = result.strip('"\'「」『』').split('\n')[0]
        return result[:280]
    return None


def generate_original_tweet(bot_persona, profile_info=None, recent_tweets=None):
    """Generate an original tweet for a bot based on persona + profile + recent posts."""
    context = _build_persona_context(bot_persona, profile_info)

    # Add recent tweets as style reference
    recent_section = ''
    if recent_tweets:
        recent_lines = [f"- {t[:60]}" for t in recent_tweets[:5]]
        recent_section = f"\n最近の投稿:\n" + '\n'.join(recent_lines)

    prompt = (
        f"あなたは以下のSNSユーザーです。このキャラクターになりきってください。\n\n"
        f"{context}{recent_section}\n\n"
        f"---\n"
        f"このキャラとして、日常的なツイートを1つだけ書いてください。\n"
        f"ルール:\n"
        f"- 140文字以内\n"
        f"- 自然な日本語のつぶやき（独り言、感想、日常報告など）\n"
        f"- 引用符や「」で囲まない\n"
        f"- 説明や前置きなし、ツイート文のみ出力\n"
        f"- キャラの口調・性格・興味を忠実に反映\n"
        f"- 過去の投稿と被らない新しい内容\n"
    )
    result = generate(prompt, max_tokens=200)
    if result:
        result = result.strip('"\'「」『』').split('\n')[0]
        return result[:280]
    return None
