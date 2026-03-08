from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
DB_NAME = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author TEXT DEFAULT '名無し',
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        likes INTEGER DEFAULT 0,
        delete_password TEXT,
        weather TEXT DEFAULT "",
        parent_id INTEGER
    )''')
    # Migration for older databases that may be missing newer columns
    for col, col_def in [('delete_password', 'TEXT'), ('weather', 'TEXT DEFAULT ""'), ('parent_id', 'INTEGER')]:
        try:
            c.execute(f'ALTER TABLE posts ADD COLUMN {col} {col_def}')
        except sqlite3.OperationalError:
            pass
    # Fix rows with missing defaults
    c.execute('UPDATE posts SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL')
    c.execute('UPDATE posts SET likes = 0 WHERE likes IS NULL')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/posts')
def get_posts():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, author, content, datetime(created_at, "localtime"), likes, weather, parent_id FROM posts ORDER BY id DESC')
    all_posts = [{'id': row[0], 'author': row[1], 'content': row[2], 'created_at': row[3], 'likes': row[4] or 0, 'weather': row[5] or '', 'parent_id': row[6], 'replies': []} for row in c.fetchall()]
    
    post_dict = {p['id']: p for p in all_posts}
    top_level_posts = []
    
    for p in all_posts:
        if p['parent_id'] and p['parent_id'] in post_dict:
            # all_posts is newest first, so inserting at 0 makes replies chronological
            post_dict[p['parent_id']]['replies'].insert(0, p)
        else:
            # If it has no parent, OR its parent is deleted/missing, it becomes a top-level post
            top_level_posts.append(p)
            
    conn.close()
    return {'posts': top_level_posts}

@app.route('/post', methods=['POST'])
def post():
    author = request.form.get('author', '').strip()
    if not author:
        author = '名無し'
    content = request.form.get('content')
    delete_password = request.form.get('delete_password', '')
    weather = request.form.get('weather', '')
    parent_id = request.form.get('parent_id') or None

    if content:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('INSERT INTO posts (author, content, created_at, delete_password, weather, parent_id) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)',
                  (author, content, delete_password, weather, parent_id))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE posts SET likes = coalesce(likes, 0) + 1 WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()
    return {'status': 'success'}

def verify_password(cursor, post_id, secret):
    """Verify that the provided secret matches the admin password or the post's edit password.
    Returns (True, row) if authorized, (False, row) otherwise. row is None if post not found."""
    cursor.execute('SELECT delete_password FROM posts WHERE id = ?', (post_id,))
    row = cursor.fetchone()
    if not row:
        return False, None
    db_password = row[0]
    if secret == 'admin123':
        return True, row
    if db_password and secret == db_password:
        return True, row
    return False, row

@app.route('/api/posts/<int:post_id>/edit', methods=['POST'])
def edit_post(post_id):
    secret = request.form.get('secret', '')
    new_content = request.form.get('content', '')
    new_password = request.form.get('new_password', '')

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    valid, row = verify_password(c, post_id, secret)

    if row is None:
        conn.close()
        return {'status': 'error', 'message': 'Post not found'}, 404
    if not valid:
        conn.close()
        return {'status': 'error', 'message': 'Unauthorized'}, 403

    if new_content:
        c.execute('UPDATE posts SET content = ? WHERE id = ?', (new_content, post_id))
    if new_password:
        c.execute('UPDATE posts SET delete_password = ? WHERE id = ?', (new_password, post_id))
    conn.commit()
    conn.close()
    return {'status': 'success'}

@app.route('/api/posts/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    secret = request.form.get('secret', '')

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    valid, row = verify_password(c, post_id, secret)

    if row is None:
        conn.close()
        return {'status': 'error', 'message': 'Post not found'}, 404
    if not valid:
        conn.close()
        return {'status': 'error', 'message': 'Unauthorized'}, 403

    # Reattach children to the deleted post's parent
    c.execute('SELECT parent_id FROM posts WHERE id = ?', (post_id,))
    parent_row = c.fetchone()
    if parent_row:
        c.execute('UPDATE posts SET parent_id = ? WHERE parent_id = ?', (parent_row[0], post_id))

    c.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()
    return {'status': 'success'}

if __name__ == '__main__':
    # Initialize DB before starting the server
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
