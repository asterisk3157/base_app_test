# App Architecture

## Overview

A minimal Flask bulletin board ("Hitokoto Keijiban") designed for security lectures.

## Files

| File | Role |
|---|---|
| `app.py` | Flask backend — routes, DB init, SQLite operations |
| `templates/index.html` | SPA-style frontend — glassmorphism UI, Fetch API |
| `database.db` | SQLite database (auto-created on first run) |
| `requirements.txt` | Python dependencies: flask, playwright, pytest |
| `.devcontainer/` | DevContainer/Codespaces configuration |

## Database schema

```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT
);
```

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Render index.html |
| GET | `/api/posts` | Return all posts as JSON (newest first) |
| POST | `/post` | Create a new post (form data: `content`) |

## Frontend behavior

- Form submission via Fetch API (no page reload)
- Posts loaded via `/api/posts` and rendered with `innerHTML` (**intentional XSS vector**)
- Auto-refresh every 2 seconds via `setInterval`

## Adding new features

When modifying the database:
1. Add new columns or tables in `init_db()`
2. Update the relevant route handlers
3. Update the frontend JS to handle new data fields

When adding new routes:
1. Follow the existing pattern in `app.py`
2. Use parameterized queries for all SQL
3. Return JSON for API endpoints, redirect for form posts
