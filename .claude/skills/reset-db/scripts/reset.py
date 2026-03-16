#!/usr/bin/env python3
"""Reset the SQLite database to a clean state."""

import os
import sys
import sqlite3

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "database.db")

SAMPLE_POSTS = [
    "Hello, this is a test post!",
    "Flask is great for building small web apps.",
    "Security matters - always sanitize user input.",
]

def reset(seed=False):
    # Remove existing DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"[*] Deleted {DB_PATH}")
    else:
        print("[*] No existing database found.")

    # Re-create
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS posts "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT)"
    )

    if seed:
        for post in SAMPLE_POSTS:
            c.execute("INSERT INTO posts (content) VALUES (?)", (post,))
        print(f"[*] Seeded {len(SAMPLE_POSTS)} sample posts.")

    conn.commit()
    c.execute("SELECT count(*) FROM posts")
    count = c.fetchone()[0]
    conn.close()
    print(f"[*] Database reset complete. Posts: {count}")

if __name__ == "__main__":
    seed = "--seed" in sys.argv
    reset(seed)
