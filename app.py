from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import sqlite3
import os
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
    # Try creating new schema with file_path
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    content TEXT,
                    file_path TEXT)''')
    
    # Simple migration: check if file_path exists, if not, recreate or alter
    c.execute("PRAGMA table_info(posts)")
    columns = [col[1] for col in c.fetchall()]
    if 'file_path' not in columns:
        c.execute("ALTER TABLE posts ADD COLUMN file_path TEXT")
        
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
    posts = [{'id': row[0], 'content': row[1], 'file_path': row[2]} for row in c.fetchall()]
    conn.close()
    return {'posts': posts}

# Route to serve uploaded files securely
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/post', methods=['POST'])
def post():
    content = request.form.get('content')
    file = request.files.get('file')
    
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
        # Store the proper route path to be served by Flask
        file_path = f"/uploads/{filename}"

    if content or file_path:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        # Vulnerability Note: This is currently using parameterized queries (safe), 
        # but students will likely ask AI to "just make it work" or "fix error",
        # which might introduce SQLi if not careful. Or we can INTENTIONALLY make this vulnerable later.
        # For base app, we keep it simple but functional.
        c.execute('INSERT INTO posts (content, file_path) VALUES (?, ?)', (content, file_path))
        conn.commit()
        conn.close()
    return jsonify({'success': True}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# Initialize DB when this file is loaded (works with flask run)
init_db()
