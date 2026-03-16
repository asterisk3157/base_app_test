# XSS Remediation Guide

## Fix 1: Use textContent instead of innerHTML

Before (vulnerable):
```javascript
div.innerHTML = post.content;
```

After (safe):
```javascript
div.textContent = post.content;
```

**Trade-off**: No HTML formatting allowed in posts.

## Fix 2: Use DOMPurify for sanitization

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.6/purify.min.js"></script>
```

```javascript
div.innerHTML = DOMPurify.sanitize(post.content);
```

**Trade-off**: Allows safe HTML (bold, italic, etc.) while stripping dangerous elements.

## Fix 3: Server-side escaping

In `app.py`, escape content before storing or returning:

```python
from markupsafe import escape

@app.route('/api/posts')
def get_posts():
    # ... fetch posts ...
    posts = [{'id': row[0], 'content': str(escape(row[1]))} for row in c.fetchall()]
    return {'posts': posts}
```

## Fix 4: Content Security Policy header

In `app.py`:

```python
@app.after_request
def add_csp(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'"
    return response
```

## Defense in depth

Best practice is to combine multiple layers:
1. Server-side output encoding
2. Client-side sanitization (DOMPurify)
3. CSP headers
4. Input validation
