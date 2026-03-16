---
name: xss-demo
description: Generate XSS demonstration payloads for the lecture. Provides attack examples and remediation guidance. For security education only.
disable-model-invocation: true
argument-hint: [payload-type]
allowed-tools: Read
---

# XSS Demonstration

**For security education purposes only. Never use against systems without authorization.**

The app has an intentional XSS vulnerability at `templates/index.html:187` where `div.innerHTML = post.content` renders user input without sanitization.

## Usage

Provide a payload type as argument: `$ARGUMENTS`

Available types are listed in the payload catalog:

- See [assets/payloads.md](assets/payloads.md) for all payloads organized by category

## Lecture flow

1. Start with `basic` to prove XSS exists
2. Use `cookie` to show data theft risk
3. Use `phishing` to demonstrate real-world attack scenarios
4. Show the fix (see [assets/remediation.md](assets/remediation.md))

## Important notes

- `<script>` tags do NOT execute via `innerHTML` (HTML5 spec). Use event handlers instead.
- All demos should run on `localhost` only.
