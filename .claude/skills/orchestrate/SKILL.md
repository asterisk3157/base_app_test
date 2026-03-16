---
name: orchestrate
description: Decompose a complex site-building request into tasks, assign to backend/frontend/QA agents, and track progress via the tasks/ directory. Use for multi-feature builds or full site creation.
argument-hint: <site-description>
allowed-tools: Read Write Edit Bash Grep Glob Agent
---

# Orchestrate Multi-Agent Build

Build request: **$ARGUMENTS**

## Step 1: Analyze & Plan

Read the current codebase state:
- `app.py` — current routes and DB schema
- `templates/index.html` — current UI
- `tasks/` — any existing tasks

Then decompose the request into discrete tasks.

## Step 2: Create task files

Use the task creation script:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/create_task.py --id 001 --title "Task title" --assignee backend-agent --priority high --description "What to do"
```

Create tasks following this order:
1. **DB/Schema tasks** → `backend-agent` (no dependencies)
2. **API/Route tasks** → `backend-agent` (may depend on schema)
3. **UI tasks** → `frontend-agent` (depends on API being ready)
4. **Integration tasks** → `frontend-agent` (depends on API + UI)
5. **QA task** → `qa-agent` (depends on everything, always last)

## Step 3: Execute

Delegate tasks to agents in dependency order. Use parallel agents for independent tasks:

- Use `backend-agent` for all backend tasks
- Use `frontend-agent` for all frontend tasks
- Use `qa-agent` for verification

When delegating, tell the agent:
1. Which task file to read (`tasks/NNN-name.md`)
2. The full context of what's needed
3. To update the task file status when done

## Step 4: Verify

After all build tasks complete:
1. Delegate to `qa-agent` to run full Playwright verification
2. If bugs found → create fix tasks → re-delegate → re-verify
3. Loop until all pass

## Step 5: Report

Check all task files in `tasks/` and write `tasks/SUMMARY.md`:

```markdown
# Build Summary

## Request
[Original request]

## Tasks
| ID | Title | Assignee | Status |
|----|-------|----------|--------|
| 001 | ... | backend-agent | done |

## Test Results
[QA summary]

## Access
http://localhost:5000
```
