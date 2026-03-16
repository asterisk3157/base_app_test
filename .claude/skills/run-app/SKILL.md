---
name: run-app
description: Start, stop, or restart the Flask bulletin board app. Use when launching the dev server, checking if the app is running, or troubleshooting startup issues.
disable-model-invocation: true
allowed-tools: Bash(python *) Bash(kill *) Bash(netstat *) Bash(taskkill *)
---

# Run App

Manage the Flask development server lifecycle.

## Start

Run the startup script:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/start.py
```

## Stop

Find and kill the process on port 5000:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/stop.py
```

## Restart

Stop then start:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/stop.py && python ${CLAUDE_SKILL_DIR}/scripts/start.py
```

## Troubleshooting

- **Port in use**: Run the stop script first
- **ModuleNotFoundError**: Run `pip install -r requirements.txt`
- **DB errors**: Use `/reset-db`
