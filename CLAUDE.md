# Project: antigravity-lecture / base_app_test

## Overview

A Flask bulletin board app ("Hitokoto Keijiban") used as a base template for a security-focused web development lecture. Students fork `main`, then use AI tools to build dynamic websites, deploying via GitHub Codespaces.

## Architecture

- `app.py` — Flask backend, SQLite, all routes
- `templates/index.html` — SPA-style frontend, Fetch API, glassmorphism UI
- `database.db` — Auto-created SQLite (gitignored)
- `.devcontainer/` — Codespaces config (Python 3.11 + Playwright)
- `tasks/` — Local task/issue tracking for multi-agent workflows

## Git branching

- `main` — Pristine base for students to fork. **Never push directly.**
- `hi` — Personal development branch. All work happens here.
- Students create their own branches from `main`.
- Push restriction enforced by hook: only `git push origin hi` is allowed.

## Intentional vulnerabilities (DO NOT FIX)

- **XSS**: `templates/index.html:187` — `div.innerHTML = post.content` renders unsanitized input
- These exist for educational purposes in the security lecture

## Agent team

Four specialized agents are available in `.claude/agents/`:

| Agent | Role | Model |
|---|---|---|
| `orchestrator-agent` | Decomposes requests, creates tasks, coordinates agents | opus |
| `backend-agent` | Flask routes, SQLite, API endpoints | sonnet |
| `frontend-agent` | HTML/CSS/JS, responsive UI, design system | sonnet |
| `qa-agent` | Playwright testing, bug reports, verification | sonnet |

### Multi-agent workflow

1. `/orchestrate <description>` to start a full build
2. Orchestrator creates task files in `tasks/`
3. Backend → Frontend → QA in dependency order
4. Each agent updates its task file status
5. QA verifies with Playwright; fix loop if needed
6. Summary written to `tasks/SUMMARY.md`

## Development workflow

1. Edit code on `hi` branch
2. Verify with Playwright: `python .claude/skills/auto-build/scripts/verify.py`
3. Push only to `hi`: `git push origin hi`

## Commands

- Start server: `python app.py` (port 5000)
- Reset DB: `python .claude/skills/reset-db/scripts/reset.py`
- Run with seed data: `python .claude/skills/reset-db/scripts/reset.py --seed`
- Create task: `python .claude/skills/orchestrate/scripts/create_task.py --id 001 --title "..." --assignee backend-agent --description "..."`

## Tech stack

- Python 3.11, Flask, SQLite3
- Playwright (headless browser testing)
- GitHub Codespaces for deployment
