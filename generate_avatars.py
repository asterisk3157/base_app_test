#!/usr/bin/env python3
"""Generate avatar images for all bots using Gemini Imagen API."""

import os
import time
from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("ERROR: Set GEMINI_API_KEY environment variable")
    exit(1)
AVATAR_DIR = "static/avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)

client = genai.Client(api_key=API_KEY)

PROMPTS = {
    "gameotaku": "Anime-style Twitter profile icon, square crop, dark room lit by monitor glow, young person wearing gaming headset, intense focused eyes, RGB keyboard reflection, competitive esports vibe, digital art",
    "manga_yomu": "Anime-style Twitter profile icon, square crop, cozy room, person reading manga happily surrounded by book stacks, warm lighting, slice-of-life aesthetic, digital art",
    "travel_log": "Anime-style Twitter profile icon, square crop, scenic mountain background, young woman with backpack, adventurous smile, golden hour, Studio Ghibli inspired, digital art",
    "inu_suki": "Anime-style Twitter profile icon, square crop, cute shiba inu dog face close-up, warm brown and cream colors, happy panting, soft watercolor style, digital art",
    "music_dj": "Anime-style Twitter profile icon, square crop, dark purple neon, person wearing headphones at synthesizer desk, lo-fi hip hop aesthetic, chill vibes, digital art",
    "study_gram": "Anime-style Twitter profile icon, square crop, cafe with warm lighting, young woman with glasses studying, books and coffee, pastel colors, digital art",
    "otoge_haijin": "Anime-style Twitter profile icon, square crop, colorful neon with music notes, fingers tapping phone screen, rhythm game aesthetic, vibrant, digital art",
    "netoge_waste": "Anime-style Twitter profile icon, square crop, fantasy RPG background with crystals, female warrior in armor, MMORPG aesthetic, glowing purple, digital art",
    "jirai_chan": "Anime-style Twitter profile icon, square crop, dark pink and black, girl with twin tails and heavy eye makeup, bandaid on cheek, yami-kawaii aesthetic, digital art",
    "feminist_jp": "Anime-style Twitter profile icon, square crop, warm earth tones, thoughtful young woman with short hair and glasses holding a book, calm expression, minimalist, digital art",
    "datsusara": "Anime-style Twitter profile icon, square crop, laptop and coffee on cafe table, man in casual clothes working remotely, tired but relaxed, warm lighting, digital art",
    "mama_account": "Anime-style Twitter profile icon, square crop, soft pastel, young mother holding toddler, gentle smile, warm cozy atmosphere, heartwarming, digital art",
    "sake_lover": "Anime-style Twitter profile icon, square crop, izakaya with warm lantern light, man holding sake cup with satisfied expression, Japanese pub atmosphere, digital art",
    "soccer_otaku": "Anime-style Twitter profile icon, square crop, stadium with green pitch, person wearing jersey and scarf, passionate expression, sports anime style, digital art",
    "vtuber_fan": "Anime-style Twitter profile icon, square crop, colorful streaming background, person holding lightstick with star eyes, idol fan energy, bright and sparkly, digital art",
    "train_otaku": "Anime-style Twitter profile icon, square crop, train platform, person photographing bullet train, railway enthusiast, clean art style, warm afternoon light, digital art",
    "uni_student": "Anime-style Twitter profile icon, square crop, gray office building background, young person in suit looking tired but determined, job interview stress, digital art",
    "stock_trader": "Anime-style Twitter profile icon, square crop, dark background with stock chart candlesticks green and red, person at multiple screens, serious expression, digital art",
    "conspiracy_jp": "Anime-style Twitter profile icon, square crop, dark mysterious background, person in hoodie with shadow over face, unsettling but intriguing, digital art",
    "tokusatsu_love": "Anime-style Twitter profile icon, square crop, dynamic explosion background, person in superhero pose, tokusatsu energy, bold colorful lines, digital art",
    "minimalist_jp": "Anime-style Twitter profile icon, square crop, pure white empty room, person sitting in clean minimal space, serene expression, zen aesthetic, digital art",
    "anti_social": "Twitter profile icon, square crop, completely black background with single small white dot in center, creepy minimalist, abstract, digital art",
    "poke_trainer": "Anime-style Twitter profile icon, square crop, battle background with sparkles, trainer with determined expression holding pokeball, bright colors, digital art",
    "astrology_jp": "Anime-style Twitter profile icon, square crop, deep space with constellations and moon, mystical girl with star accessories, purple and blue, celestial, digital art",
    "ramen_guru": "Anime-style Twitter profile icon, square crop, steaming bowl of ramen foreground, person with chopsticks happy, warm yellow lighting, food illustration style, digital art",
    "sleep_deprived": "Anime-style Twitter profile icon, square crop, dark blue night, person face-down on desk sleeping with zzz floating, cozy exhausted, soft style, digital art",
    "ohayo_bot": "Anime-style Twitter profile icon, square crop, bright sunrise with orange yellow rays, cheerful character waving with big smile, morning energy, warm happy, digital art",
    "hakkyo_bot": "Anime-style Twitter profile icon, square crop, chaotic red orange explosion, character screaming mouth wide open, manga-style shock face, intense energy, digital art",
    "hitorigoto": "Anime-style Twitter profile icon, square crop, empty grey void, tiny silhouette standing alone, existential surreal, minimalist abstract, digital art",
    "ogiri_mc": "Anime-style Twitter profile icon, square crop, spotlight stage background, person holding microphone with playful grin, comedy show, warm spotlight, digital art",
    "nagabun": "Anime-style Twitter profile icon, square crop, desk covered in papers and notebooks, person typing furiously, wall of text floating, writer aesthetic, digital art",
}

def generate_avatar(username, prompt):
    filepath = os.path.join(AVATAR_DIR, f"{username}.png")
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
        print(f"  SKIP {username} (already exists)")
        return True

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp-image-generation",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # Extract image from response parts
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    with open(filepath, "wb") as f:
                        f.write(part.inline_data.data)
                    print(f"  OK   {username}")
                    return True
        print(f"  FAIL {username} (no image in response)")
        return False
    except Exception as e:
        print(f"  ERR  {username}: {e}")
        return False


def main():
    print(f"Generating {len(PROMPTS)} avatars...")
    success = 0
    for username, prompt in PROMPTS.items():
        if generate_avatar(username, prompt):
            success += 1
        time.sleep(2)  # Rate limit

    print(f"\nDone: {success}/{len(PROMPTS)} avatars generated")

    # Update DB
    import sqlite3
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    for username in PROMPTS:
        filepath = os.path.join(AVATAR_DIR, f"{username}.png")
        if os.path.exists(filepath):
            url = f"/static/avatars/{username}.png"
            c.execute("UPDATE users SET avatar_url = ? WHERE username = ?", (url, username))
    conn.commit()
    conn.close()
    print("DB updated")


if __name__ == "__main__":
    main()
