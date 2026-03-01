from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
DB_NAME = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Check if we need to migrate or just create fresh
    c.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, content TEXT)''')
    
    # Simple migration strategy: if the table exists but doesn't have username, alter it
    c.execute("PRAGMA table_info(posts)")
    columns = [col[1] for col in c.fetchall()]
    if "username" not in columns:
        c.execute("ALTER TABLE posts ADD COLUMN username TEXT DEFAULT 'Anonymous'")
        
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
    # Row depends on table schema mapping. Assuming: id, username, content
    # If the default id, content was used, content might be index 1 instead of 2.
    # It's safer to fetch based on description or just rely on index 1 as username and 2 as content.
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
    if content:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('INSERT INTO posts (username, content) VALUES (?, ?)', (username, content))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

# Initialize DB before starting the server
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
