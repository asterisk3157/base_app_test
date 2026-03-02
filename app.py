from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
DB_NAME = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, likes INTEGER DEFAULT 0)''')
    try:
        c.execute('''ALTER TABLE posts ADD COLUMN author TEXT DEFAULT '名無し' ''')
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        c.execute('''ALTER TABLE posts ADD COLUMN created_at TIMESTAMP''')
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        c.execute('''ALTER TABLE posts ADD COLUMN likes INTEGER DEFAULT 0''')
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        c.execute('''ALTER TABLE posts ADD COLUMN delete_password TEXT''')
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        c.execute('''ALTER TABLE posts ADD COLUMN weather TEXT DEFAULT ""''')
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        c.execute('''ALTER TABLE posts ADD COLUMN parent_id INTEGER''')
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # Fix existing rows that may not have generated defaults correctly
    c.execute('''UPDATE posts SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL''')
    c.execute('''UPDATE posts SET likes = 0 WHERE likes IS NULL''')
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
    parent_id = request.form.get('parent_id')
    if parent_id == '':
        parent_id = None
        
    if content:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        # Vulnerability Note: This is currently using parameterized queries (safe), 
        # but students will likely ask AI to "just make it work" or "fix error",
        # which might introduce SQLi if not careful. Or we can INTENTIONALLY make this vulnerable later.
        # For base app, we keep it simple but functional.
        # Fixed: explicitly insert the CURRENT_TIMESTAMP for timezone correctness in SQLite.
        c.execute('INSERT INTO posts (author, content, created_at, delete_password, weather, parent_id) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)', (author, content, delete_password, weather, parent_id))
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

@app.route('/api/posts/<int:post_id>/edit', methods=['POST'])
def edit_post(post_id):
    secret = request.form.get('secret', '')
    new_content = request.form.get('content', '')
    new_password = request.form.get('new_password', '')
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT delete_password FROM posts WHERE id = ?', (post_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return {'status': 'error', 'message': 'Post not found'}, 404
        
    db_password = row[0]
    
    # Securely check password: 
    # If the database password is empty/None, ONLY admin can edit/delete it.
    # Otherwise, it must match either admin or the specific post password.
    if secret == 'admin123':
        valid_edit = True
    elif db_password and secret == db_password:
        valid_edit = True
    else:
        valid_edit = False
    
    if not valid_edit:
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
    # Check if the provided secret matches admin password or the custom post delete_password
    secret = request.form.get('secret', '')
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT delete_password FROM posts WHERE id = ?', (post_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return {'status': 'error', 'message': 'Post not found'}, 404
        
    db_password = row[0]
    
    # Securely check password: 
    # If the database password is empty/None, ONLY admin can edit/delete it.
    # Otherwise, it must match either admin or the specific post password.
    if secret == 'admin123':
        valid_delete = True
    elif db_password and secret == db_password:
        valid_delete = True
    else:
        valid_delete = False
    
    if not valid_delete:
        conn.close()
        return {'status': 'error', 'message': 'Unauthorized'}, 403

    # Find the parent of the post being deleted
    c.execute('SELECT parent_id FROM posts WHERE id = ?', (post_id,))
    parent_row = c.fetchone()
    if parent_row:
        parent_id_val = parent_row[0]
        # Reattach all children of this post to its parent (grandparent of the children)
        # This prevents other replies from being deleted when the user only wants to delete one.
        c.execute('UPDATE posts SET parent_id = ? WHERE parent_id = ?', (parent_id_val, post_id))

    c.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()
    return {'status': 'success'}

if __name__ == '__main__':
    # Initialize DB before starting the server
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
