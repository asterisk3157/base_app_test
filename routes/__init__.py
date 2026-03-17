import time
from collections import defaultdict
from functools import wraps
from flask import Blueprint, request, jsonify

tweets_bp = Blueprint('tweets', __name__)
users_bp = Blueprint('users', __name__)
notifications_bp = Blueprint('notifications', __name__)
bots_bp = Blueprint('bots', __name__)

# ---------------------------------------------------------------------------
# Simple in-memory rate limiter
# Tracks POST request timestamps per IP address.
# Limit: 30 POST requests per 60 seconds per IP.
# Security note: in-memory only — resets on server restart and is not shared
# across processes/workers. Suitable for single-process dev/lecture use.
# ---------------------------------------------------------------------------
_rate_limit_store = defaultdict(list)
RATE_LIMIT_MAX = 30       # max requests
RATE_LIMIT_WINDOW = 60    # seconds


def rate_limit(f):
    """Decorator: allow at most RATE_LIMIT_MAX POST calls per RATE_LIMIT_WINDOW seconds per IP."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'POST':
            ip = request.remote_addr or 'unknown'
            now = time.time()
            window_start = now - RATE_LIMIT_WINDOW
            # Purge timestamps outside the window
            _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if t > window_start]
            if len(_rate_limit_store[ip]) >= RATE_LIMIT_MAX:
                return jsonify({'error': 'rate limit exceeded, try again later'}), 429
            _rate_limit_store[ip].append(now)
        return f(*args, **kwargs)
    return decorated


from routes import tweets, users, notifications, bots
from routes.dm import dm_bp
from routes.lists import lists_bp
from routes.security_demo import security_demo_bp
