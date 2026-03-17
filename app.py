from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import sqlite3
import os
import hashlib
import base64
import uuid
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)
DB_NAME = 'database.db'
# Simple CSRF Secret
CSRF_SECRET = "frieren_magical_secret_key_2026"
CSRF_TOKEN = hashlib.sha256(CSRF_SECRET.encode()).hexdigest()

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Limit upload size to 16MB
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

# Allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx'}

# Ensure upload dir exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    # Magical Reset Seal: If a file named 'PURGE_DATABASE' exists, clear everything
    purge_trigger = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'PURGE_DATABASE')
    if os.path.exists(purge_trigger):
        if os.path.exists(DB_NAME):
            os.remove(DB_NAME)
        # Also clear uploads
        if os.path.exists(UPLOAD_FOLDER):
            for f in os.listdir(UPLOAD_FOLDER):
                os.remove(os.path.join(UPLOAD_FOLDER, f))
        # Remove the trigger so it doesn't keep purging
        try:
            os.remove(purge_trigger)
        except:
            pass

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Try creating new schema with file_path and name
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    content TEXT,
                    file_path TEXT,
                    name TEXT)''')
    
    # Simple migration: check if file_path or name exists, if not, recreate or alter
    c.execute("PRAGMA table_info(posts)")
    columns = [col[1] for col in c.fetchall()]
    if 'file_path' not in columns:
        c.execute("ALTER TABLE posts ADD COLUMN file_path TEXT")
    if 'name' not in columns:
        c.execute("ALTER TABLE posts ADD COLUMN name TEXT")
        
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html', csrf_token=CSRF_TOKEN)

@app.route('/api/posts')
def get_posts():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM posts ORDER BY id DESC')
    posts = [{'id': row[0], 'content': row[1], 'file_path': row[2], 'name': row[3]} for row in c.fetchall()]
    conn.close()
    return {'posts': posts}

def generate_tripcode(name_input):
    if not name_input:
        return "名無しの魔法使い"
    
    if '#' in name_input:
        parts = name_input.split('#', 1)
        name = parts[0] if parts[0] else "名無しの魔法使い"
        password = parts[1]
        
        if password:
            # Generate a secure hash
            hasher = hashlib.sha256()
            hasher.update(password.encode('utf-8'))
            # Get a short, URL-safe base64 string
            trip_hash = base64.urlsafe_b64encode(hasher.digest()).decode('utf-8')[:10]
            return f"{name} ◆{trip_hash}"
            
    return name_input

# In-memory rate limiting: {ip: last_post_timestamp}
last_post_times = {}

def contains_dark_magic(text):
    if not text:
        return False
    # List of forbidden signatures for XSS, SQLi, and Command Injection
    forbidden_words = [
        '<script', 'javascript:', 'drop table', 'select ', 'union select', 
        'onload=', 'onerror=', 'eval(', 'alert(', 'confirm(', 
        'prompt(', 'document.cookie', 'document.domain', 
        'window.location', 'src=', 'href=', '..', '.php', '.exe', '.sh'
    ]
    text_lower = text.lower()
    return any(word in text_lower for word in forbidden_words)

@app.route('/post', methods=['POST'])
def post():
    # Verify CSRF Token
    client_token = request.form.get('csrf_token')
    if client_token != CSRF_TOKEN:
        return jsonify({'success': False, 'error': '結界拒絶：CSRFトークンが無効です。'}), 403

    # Basic Rate Limiting
    user_ip = request.remote_addr
    now = time.time()
    if user_ip in last_post_times:
        if now - last_post_times[user_ip] < 3: # 3 second cooldown
            return jsonify({'success': False, 'error': '魔力が回復していません。3秒ほどお待ちください。'}), 429
    
    content = request.form.get('content')
    raw_name = request.form.get('name', '').strip()
    file = request.files.get('file')
    
    # Process tripcode
    processed_name = generate_tripcode(raw_name)
    
    # Lv.3 Defense: Backend Magical Barrier (WAF)
    # Check content, name, AND the original filename
    if contains_dark_magic(content) or contains_dark_magic(raw_name) or (file and contains_dark_magic(file.filename)):
        return jsonify({'success': False, 'error': '結界発動：不正な魔法（ハッキング詠唱）を検知しました！'}), 400
        
    file_path = None
    if file and file.filename != '':
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'この魔導書（ファイル形式）は解読できません。対応: png, jpg, pdf, doc 等'}), 400
            
        # Secure and Randomize filename to prevent path traversal and overwrites
        original_ext = file.filename.rsplit('.', 1)[1].lower()
        random_filename = f"{uuid.uuid4().hex}.{original_ext}"
        
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], random_filename)
        file.save(save_path)
        file_path = f"/static/uploads/{random_filename}"

    if content or file_path:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('INSERT INTO posts (content, file_path, name) VALUES (?, ?, ?)', (content, file_path, processed_name))
        conn.commit()
        conn.close()
        # Update rate limit timestamp
        last_post_times[user_ip] = now
        
    return jsonify({'success': True}), 200

# Initialize DB when this file is loaded
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
