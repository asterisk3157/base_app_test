---
id: 002
title: "Tweet and Like API endpoints"
assignee: backend-agent
status: done
priority: high
depends_on: 001
created: 2026-03-16
---

## Description

Implement API routes: GET /api/tweets (join users, include like count, ordered by created_at DESC), POST /api/tweets (create tweet with user_id, content, auto timestamp), POST /api/tweets/<id>/like (toggle like), GET /api/users (list all users). Return JSON with user info embedded in each tweet.

## Acceptance criteria

- [ ] Implementation complete
- [ ] No regressions introduced
- [ ] Code follows project conventions

## Result

Implemented in `app.py`. Routes added: GET /api/tweets (join users + like count, DESC order), POST /api/tweets (JSON body, returns created tweet), POST /api/tweets/<id>/like (toggle like for user_id=1), GET /api/users. GET /api/posts kept as backward-compat alias.
