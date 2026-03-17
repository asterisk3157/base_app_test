from flask import Flask, render_template
from config import UPLOAD_FOLDER
from models import init_db

app = Flask(__name__)

# Register blueprints
from routes import tweets_bp, users_bp, notifications_bp, bots_bp
app.register_blueprint(tweets_bp)
app.register_blueprint(users_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(bots_bp)


@app.route('/')
def index():
    return render_template('index.html')


# Initialize DB when this file is loaded (works with both `python app.py` and `flask run`)
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
