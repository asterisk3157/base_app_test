from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
DB_NAME = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Check if we need to migrate or just create fresh
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        username TEXT, 
        content TEXT,
        timestamp TEXT,
        reply_to_id INTEGER
    )''')
    
    # Simple migration strategy
    c.execute("PRAGMA table_info(posts)")
    columns = [col[1] for col in c.fetchall()]
    
    if "username" not in columns:
        c.execute("ALTER TABLE posts ADD COLUMN username TEXT DEFAULT 'Anonymous'")
    if "timestamp" not in columns:
        c.execute("ALTER TABLE posts ADD COLUMN timestamp TEXT")
    if "reply_to_id" not in columns:
        c.execute("ALTER TABLE posts ADD COLUMN reply_to_id INTEGER")
        
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/posts')
def get_posts():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # We will ensure mapping correctly below:
    c.execute('PRAGMA table_info(posts)')
    columns = [col[1] for col in c.fetchall()]
    
    c.execute('SELECT * FROM posts ORDER BY id ASC') # Oldest to newest for chat layout
    rows = c.fetchall()
    conn.close()
    
    posts = []
    for row in rows:
        post_data = {}
        for idx, col_name in enumerate(columns):
            post_data[col_name] = row[idx]
        posts.append(post_data)

    return {'posts': posts}

@app.route('/post', methods=['POST'])
def post():
    content = request.form.get('content')
    username = request.form.get('username') or 'Anonymous'
    reply_to = request.form.get('reply_to_id')
    
    # Format: 2026/03/01/11:14
    timestamp = datetime.now().strftime('%Y/%m/%d/%H:%M')
    
    if reply_to == "":
        reply_to = None

    if content:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''
            INSERT INTO posts (username, content, timestamp, reply_to_id) 
            VALUES (?, ?, ?, ?)
        ''', (username, content, timestamp, reply_to))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:post_id>', methods=['POST'])
def edit_post(post_id):
    content = request.form.get('content')
    username = request.form.get('username')
    if content and username:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        # Verify username matches before updating
        c.execute('UPDATE posts SET content = ? WHERE id = ? AND username = ?', (content, post_id, username))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    username = request.form.get('username')
    if username:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        # Verify username matches before deleting
        c.execute('DELETE FROM posts WHERE id = ? AND username = ?', (post_id, username))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

# Initialize DB before starting the server
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
