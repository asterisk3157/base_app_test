---
name: auto-build
description: Fully autonomous site builder. Takes a description of a dynamic website, builds it with Flask, and verifies it works using Playwright. Use when building or iterating on the web app end-to-end.
argument-hint: <site-description>
allowed-tools: Bash Read Edit Write Glob Grep Agent
---

# Auto Build

Build a dynamic website autonomously and verify it with Playwright.

## Goal

Given the description: **$ARGUMENTS**

Build a fully functional Flask web app, then verify every feature works using headless browser testing.

## Workflow

### Phase 1: Plan

1. Analyze the request and break it into features
2. Design the DB schema if needed
3. Outline the routes and UI components

### Phase 2: Build

1. Modify `app.py` — add routes, DB tables, logic
2. Modify `templates/index.html` — or create new templates as needed
3. Add static assets if required (`static/` directory)
4. Update `requirements.txt` if new packages are needed

### Phase 3: Verify with Playwright

Run the verification script to start the server and test:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/verify.py
```

If tests fail:
1. Read the error output
2. Fix the issue in the code
3. Re-run verification
4. Repeat until all checks pass

See [references/playwright-patterns.md](references/playwright-patterns.md) for common test patterns.

### Phase 4: Report

Summarize:
- What was built
- What was tested
- Any known limitations
- How to access the site (http://localhost:5000)

## Rules

- Keep the app as a single `app.py` + templates structure (no blueprints unless necessary)
- Use SQLite via `sqlite3` (no ORM unless requested)
- All UI should be responsive and modern
- The server runs on port 5000
- In Codespaces, the port is auto-forwarded
