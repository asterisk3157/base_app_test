---
id: 003
title: "Gemini API bot integration"
assignee: backend-agent
status: done
priority: high
depends_on: 001
created: 2026-03-16
---

## Description

Add Gemini API integration: POST /api/generate-bot-tweet endpoint that calls Gemini API (google-generativeai package) to generate a tweet from a random bot user. Create 3-4 fictional bot accounts in init_db (e.g. TechBot, CatLover, NewsFlash). The Gemini prompt should generate short, personality-matching tweets. Store GEMINI_API_KEY in env var. Add google-generativeai to requirements.txt. Include a fallback if API key is not set (return a random pre-written tweet).

## Acceptance criteria

- [ ] Implementation complete
- [ ] No regressions introduced
- [ ] Code follows project conventions

## Result

Implemented in `app.py`. POST /api/generate-bot-tweet picks a random bot, calls Gemini gemini-2.0-flash with a personality prompt if GEMINI_API_KEY env var is set, saves and returns the tweet. Falls back to hardcoded tweets per-bot when no API key is present. google-generativeai added to requirements.txt.
