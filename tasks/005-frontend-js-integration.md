---
id: 005
title: "Frontend JS integration"
assignee: frontend-agent
status: done
priority: high
depends_on: 002, 004
created: 2026-03-16
---

## Description

Wire up all frontend JavaScript: loadTweets() fetches /api/tweets and renders timeline, postTweet() sends to /api/tweets, likeTweet(id) posts to /api/tweets/<id>/like and updates count, generateBotTweet() calls /api/generate-bot-tweet then refreshes timeline. Auto-refresh timeline every 5 seconds. Show relative timestamps (e.g. '2m ago'). Animate new tweets sliding in. Keep innerHTML for XSS vulnerability.

## Acceptance criteria

- [ ] Implementation complete
- [ ] No regressions introduced
- [ ] Code follows project conventions

## Result

All JavaScript wired up inline in `templates/index.html`.

- `loadTweets()`: fetches GET /api/tweets, diffs against `knownTweetIds` set to prepend only new cards; updates like state on existing cards without full re-render. Auto-refresh every 5 seconds via `setInterval`.
- `postTweet()`: POST /api/tweets with JSON `{content, user_id: 1}`, clears textarea, calls `loadTweets()`. Ctrl+Enter/Cmd+Enter keyboard shortcut supported.
- `likeTweet(id)`: POST /api/tweets/<id>/like, updates heart SVG fill/stroke and count in-place without reload.
- `generateBotTweet()`: POST /api/generate-bot-tweet with loading state on button, then refreshes timeline.
- `timeAgo(dateStr)`: normalises SQLite UTC timestamps (appends Z), returns "Xs ago", "Xm ago", "Xh ago", "Xd ago", or "Mon D" for older dates.
- `updateCharCounter()`: live counter, yellow warning at <=20 remaining, red + disabled at 0.
- `loadBotAccounts()`: fetches /api/users, renders bot list in right sidebar.
- XSS vulnerability preserved: `contentEl.innerHTML = tweet.content` with identifying comment.
