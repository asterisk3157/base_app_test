---
name: security-audit
description: Audit the app for security vulnerabilities. Detects XSS, SQL injection, CSRF, misconfigurations. Use when reviewing code security or preparing lecture materials.
allowed-tools: Read Grep Glob
---

# Security Audit

Perform a comprehensive security review of this lecture demo app.

**Important**: This app contains **intentional vulnerabilities** for educational purposes. The audit should identify them and explain their pedagogical value.

## Audit checklist

Scan for each category using the reference guide:

- See [references/checklist.md](references/checklist.md) for the full checklist

## Report format

For each finding, use this structure:

```
### [Severity: HIGH/MEDIUM/LOW] Vulnerability Name
- **Location**: file:line_number
- **Description**: What the issue is
- **Impact**: What an attacker could do
- **Fix**: How to remediate
- **Teaching point**: What students should learn from this
```

## Known intentional vulnerabilities

1. **XSS** in `templates/index.html` — `innerHTML` used without sanitization
2. **No CSRF protection** — POST endpoints lack token validation
3. **Debug mode** — `debug=True` exposes Werkzeug debugger
