---
id: 001
title: "DB schema redesign for Twitter"
assignee: backend-agent
status: done
priority: high
depends_on: []
created: 2026-03-16
---

## Description

Redesign SQLite schema: users table (id, username, display_name, handle, avatar_url, is_bot), tweets table (id, user_id FK, content, created_at), likes table (id, tweet_id FK, user_id FK). Create default human user. Drop old posts table. Keep init_db() pattern.

## Acceptance criteria

- [ ] Implementation complete
- [ ] No regressions introduced
- [ ] Code follows project conventions

## Result

Implemented in `app.py`. Created `users`, `tweets`, and `likes` tables via `init_db()`. Old `posts` table removed. Seeded 1 human user (id=1, @you) and 4 bot users (TechBot, CatLover, NewsFlash, PhiloBot). Seed is idempotent — runs only when users table is empty.
