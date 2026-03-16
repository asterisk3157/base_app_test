---
name: reset-db
description: Reset the SQLite database to a clean initial state. Use when clearing all posts, recovering from DB corruption, or preparing for a demo.
disable-model-invocation: true
allowed-tools: Bash(python *)
---

# Reset Database

Wipe all data and re-initialize the database.

## Usage

```bash
python ${CLAUDE_SKILL_DIR}/scripts/reset.py
```

Pass `--seed` to populate with sample posts for demo purposes:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/reset.py --seed
```

## What it does

1. Deletes `database.db`
2. Re-creates the schema via `init_db()`
3. Optionally inserts sample posts
4. Prints row count to confirm
