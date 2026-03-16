---
name: add-feature
description: Add a new feature to the bulletin board app. Handles DB schema changes, backend routes, and frontend UI. Use when adding functionality like usernames, deletion, likes, image uploads, or search.
argument-hint: <feature-name>
---

# Add Feature

Add **$ARGUMENTS** to the bulletin board app.

## Constraints

This app is for a **security lecture**. Follow these rules:

1. **Preserve intentional vulnerabilities** — Do NOT fix the `innerHTML` XSS in `index.html:187`. It exists for teaching purposes.
2. **Keep it simple** — Students must be able to read and understand the code.
3. **Document new vulnerabilities** — If the new feature introduces security concerns, note them in code comments.

## App architecture

See [references/architecture.md](references/architecture.md) for details.

## Steps

1. Clarify requirements for `$ARGUMENTS`
2. Check if DB schema changes are needed
3. Add/modify backend routes in `app.py`
4. Update frontend UI in `templates/index.html`
5. Test the feature manually
6. Note any security implications
