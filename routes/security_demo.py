"""
Security demonstration endpoints for the security lecture.

IMPORTANT: These endpoints are INTENTIONALLY VULNERABLE.
They exist solely to demonstrate common web security vulnerabilities
in a controlled classroom environment. Do NOT deploy to production.
"""
from flask import Blueprint, request
from models import get_db

security_demo_bp = Blueprint('security_demo', __name__)


# INTENTIONALLY VULNERABLE - for security lecture demo
# GET /api/demo/xss — demonstrates stored XSS by reflecting user input without escaping.
# A real attacker could inject <script>alert(1)</script> and have it execute in
# the victim's browser. This is intentional — the vulnerability is the lesson.
@security_demo_bp.route('/api/demo/xss')
def demo_xss():
    user_input = request.args.get('input', '')
    # INTENTIONALLY VULNERABLE: user input is reflected without HTML escaping.
    # Demonstrates Reflected XSS — any script tag or event handler injected here
    # will execute in the browser.
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>XSS Demo</title></head>
<body>
  <h2>XSS Demonstration Endpoint</h2>
  <p>This page reflects the <code>?input=</code> parameter without sanitization.</p>
  <p>Your input: {user_input}</p>
  <hr>
  <p><em>INTENTIONALLY VULNERABLE - for security lecture demo</em></p>
</body>
</html>"""
    return html, 200, {'Content-Type': 'text/html'}


# INTENTIONALLY VULNERABLE - for security lecture demo
# GET /api/demo/sqli?q=<query> — demonstrates SQL injection.
# The query parameter is interpolated directly into the SQL string using Python
# string formatting instead of parameterized queries.
# Example exploit: ?q=' OR '1'='1
@security_demo_bp.route('/api/demo/sqli')
def demo_sqli():
    q = request.args.get('q', '')
    conn = get_db()
    c = conn.cursor()

    # INTENTIONALLY VULNERABLE: string concatenation used instead of parameterized query.
    # An attacker can inject arbitrary SQL, e.g.: ?q=' UNION SELECT username,password FROM users--
    # This is intentional — demonstrates why parameterized queries are critical.
    try:
        # nosec (intentional vulnerability for lecture)
        c.execute("SELECT id, display_name, handle FROM users WHERE handle LIKE '%" + q + "%'")
        rows = [dict(r) for r in c.fetchall()]
        result = {'results': rows, 'query': q}
    except Exception as e:
        result = {'error': str(e), 'query': q}
    conn.close()

    import json
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>SQL Injection Demo</title></head>
<body>
  <h2>SQL Injection Demonstration Endpoint</h2>
  <p>Query parameter <code>?q=</code> is interpolated directly into SQL without parameterization.</p>
  <pre>{json.dumps(result, ensure_ascii=False, indent=2)}</pre>
  <hr>
  <p><em>INTENTIONALLY VULNERABLE - for security lecture demo</em></p>
</body>
</html>"""
    return html, 200, {'Content-Type': 'text/html'}


# INTENTIONALLY VULNERABLE - for security lecture demo
# GET /api/demo/csrf — demonstrates a CSRF-vulnerable HTML form.
# This form submits a POST request without any CSRF token, so any page on
# any origin can silently trigger this action for logged-in users.
@security_demo_bp.route('/api/demo/csrf')
def demo_csrf():
    # INTENTIONALLY VULNERABLE: no CSRF token validation.
    # Demonstrates how a malicious third-party site can perform actions on behalf
    # of a logged-in user by embedding this form or an <img>/<fetch> targeting it.
    html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>CSRF Demo</title></head>
<body>
  <h2>CSRF Demonstration Form</h2>
  <p>This form submits to the tweet creation endpoint with <strong>no CSRF token</strong>.
     Any website could host this form and silently post a tweet on behalf of a logged-in user.</p>
  <form method="POST" action="/api/tweets" id="csrfForm">
    <label>Tweet content:
      <input type="text" name="content" value="This tweet was posted via CSRF!">
    </label>
    <button type="submit">Post Tweet (CSRF demo)</button>
  </form>
  <script>
    // To auto-submit from another origin, an attacker would use:
    // document.getElementById('csrfForm').submit();
  </script>
  <hr>
  <p><em>INTENTIONALLY VULNERABLE - for security lecture demo</em></p>
</body>
</html>"""
    return html, 200, {'Content-Type': 'text/html'}
