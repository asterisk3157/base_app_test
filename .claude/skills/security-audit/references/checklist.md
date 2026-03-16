# Security Audit Checklist

## 1. Cross-Site Scripting (XSS)

- [ ] Search for `innerHTML` usage in all templates and JS
- [ ] Check if user input is rendered without escaping
- [ ] Look for `| safe` filter or `Markup()` in Jinja templates
- [ ] Verify Content-Security-Policy headers are set

## 2. SQL Injection

- [ ] Search for string concatenation/f-strings in SQL queries
- [ ] Verify all queries use parameterized placeholders (`?`)
- [ ] Check for raw `execute()` calls with user-controlled input

## 3. Cross-Site Request Forgery (CSRF)

- [ ] Check if POST/PUT/DELETE endpoints validate CSRF tokens
- [ ] Verify Flask-WTF or equivalent CSRF protection is installed
- [ ] Check if SameSite cookie attribute is set

## 4. Authentication & Session

- [ ] Check if `SECRET_KEY` is configured
- [ ] Verify session cookies have `HttpOnly` and `Secure` flags
- [ ] Look for hardcoded credentials

## 5. Server Configuration

- [ ] Check if `debug=True` is used in production
- [ ] Verify error handling doesn't leak stack traces
- [ ] Check for missing security headers (X-Content-Type-Options, X-Frame-Options, etc.)

## 6. Input Validation

- [ ] Check if file uploads are validated (type, size)
- [ ] Verify input length limits are enforced
- [ ] Look for path traversal in file operations

## 7. Dependencies

- [ ] Check `requirements.txt` for known vulnerable packages
- [ ] Verify packages are pinned to specific versions
