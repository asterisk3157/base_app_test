import os
import secrets
from flask import Flask, render_template
from config import UPLOAD_FOLDER
from models import init_db

app = Flask(__name__)
# SECRET_KEY is required for signed session cookies (used for CSRF token storage).
# In production this should be a fixed secret loaded from an environment variable.
# For this dev/lecture environment we generate a random key per process (sessions
# will reset on server restart, which is acceptable here).
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Register blueprints
from routes import tweets_bp, users_bp, notifications_bp, bots_bp, dm_bp
from routes.lists import lists_bp
from routes.security_demo import security_demo_bp
app.register_blueprint(tweets_bp)
app.register_blueprint(users_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(bots_bp)
app.register_blueprint(dm_bp)
app.register_blueprint(lists_bp)
app.register_blueprint(security_demo_bp)


@app.route('/')
def index():
    return render_template('index.html')


# Initialize DB when this file is loaded (works with both `python app.py` and `flask run`)
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
