#!/usr/bin/env python3
"""Create a task file in the tasks/ directory."""

import argparse
import os
from datetime import date

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
TASKS_DIR = os.path.join(PROJECT_ROOT, "tasks")


def create_task(task_id, title, assignee, priority, description, depends_on=None):
    os.makedirs(TASKS_DIR, exist_ok=True)

    slug = title.lower().replace(" ", "-").replace("/", "-")[:40]
    filename = f"{task_id}-{slug}.md"
    filepath = os.path.join(TASKS_DIR, filename)

    deps = depends_on or []
    deps_str = ", ".join(deps) if deps else "[]"

    content = f"""---
id: {task_id}
title: "{title}"
assignee: {assignee}
status: open
priority: {priority}
depends_on: {deps_str}
created: {date.today().isoformat()}
---

## Description

{description}

## Acceptance criteria

- [ ] Implementation complete
- [ ] No regressions introduced
- [ ] Code follows project conventions

## Result

_(To be filled by {assignee} when complete)_
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[*] Created task: {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Create a task file")
    parser.add_argument("--id", required=True, help="Task ID (e.g., 001)")
    parser.add_argument("--title", required=True, help="Task title")
    parser.add_argument(
        "--assignee",
        required=True,
        choices=["backend-agent", "frontend-agent", "qa-agent"],
        help="Agent to assign",
    )
    parser.add_argument(
        "--priority",
        default="medium",
        choices=["high", "medium", "low"],
        help="Task priority",
    )
    parser.add_argument("--description", required=True, help="Task description")
    parser.add_argument(
        "--depends-on", nargs="*", default=[], help="Task IDs this depends on"
    )

    args = parser.parse_args()
    create_task(
        args.id, args.title, args.assignee, args.priority,
        args.description, args.depends_on,
    )


if __name__ == "__main__":
    main()
