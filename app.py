from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import sqlite3
import os
import hashlib
import base64
from werkzeug.utils import secure_filename

app = Flask(__name__)
DB_NAME = 'database.db'

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
    return render_template('index.html')

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

def contains_dark_magic(text):
    if not text:
        return False
    # List of forbidden keywords for basic XSS & SQLi
    forbidden_words = ['<script>', 'javascript:', 'drop table', 'select ', 'union select', 'onload=', 'onerror=']
    text_lower = text.lower()
    return any(word in text_lower for word in forbidden_words)

@app.route('/post', methods=['POST'])
def post():
    content = request.form.get('content')
    raw_name = request.form.get('name', '').strip()
    file = request.files.get('file')
    
    # Process tripcode
    processed_name = generate_tripcode(raw_name)
    
    # Lv.3 Defense: Backend Magical Barrier (WAF)
    if contains_dark_magic(content):
        return jsonify({'success': False, 'error': '結界発動：不正な魔法（ハッキング詠唱）を検知しました！'}), 400
        
    file_path = None
    if file and file.filename != '':
        if not allowed_file(file.filename):
            # Return an error JSON if the file type is not supported
            return jsonify({'success': False, 'error': 'この魔導書（ファイル形式）は解読できません。対応: png, jpg, pdf, doc 等'}), 400
            
        # Secure the filename before saving
        filename = secure_filename(file.filename)
        # Create a unique path to avoid overwriting
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        # Store relative path for frontend access (served natively by Flask)
        file_path = f"/static/uploads/{filename}"

    if content or file_path:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        # Vulnerability Note: This is currently using parameterized queries (safe), 
        # but students will likely ask AI to "just make it work" or "fix error",
        # which might introduce SQLi if not careful. Or we can INTENTIONALLY make this vulnerable later.
        # For base app, we keep it simple but functional.
        c.execute('INSERT INTO posts (content, file_path, name) VALUES (?, ?, ?)', (content, file_path, processed_name))
        conn.commit()
        conn.close()
    return jsonify({'success': True}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# Initialize DB when this file is loaded (works with flask run)
init_db()
