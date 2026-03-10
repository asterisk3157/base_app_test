from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
import sqlite3
import random
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'table_hockey_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
DB_NAME = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Existing Posts table migrated to support Rooms and Teams
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        username TEXT, 
        content TEXT,
        timestamp TEXT,
        reply_to_id INTEGER,
        room_id TEXT,
        team_id INTEGER
    )''')
    
    # New tables
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (
        id TEXT PRIMARY KEY,
        name TEXT,
        status TEXT,
        admin_username TEXT,
        is_public BOOLEAN DEFAULT 0,
        set_number INTEGER DEFAULT 1,
        team1_score INTEGER DEFAULT 0,
        team2_score INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        room_id TEXT,
        team_id INTEGER,
        is_ready BOOLEAN DEFAULT 0
    )''')
    
    # Migrations for existing posts DB if we just added new columns
    c.execute("PRAGMA table_info(posts)")
    columns = [col[1] for col in c.fetchall()]
    if "username" not in columns:
        c.execute("ALTER TABLE posts ADD COLUMN username TEXT DEFAULT 'Anonymous'")
    if "timestamp" not in columns:
        c.execute("ALTER TABLE posts ADD COLUMN timestamp TEXT")
    if "reply_to_id" not in columns:
        c.execute("ALTER TABLE posts ADD COLUMN reply_to_id INTEGER")
    if "room_id" not in columns:
        c.execute("ALTER TABLE posts ADD COLUMN room_id TEXT")
    if "team_id" not in columns:
        c.execute("ALTER TABLE posts ADD COLUMN team_id INTEGER")
        
    c.execute("PRAGMA table_info(rooms)")
    rooms_cols = [col[1] for col in c.fetchall()]
    if "is_public" not in rooms_cols:
        c.execute("ALTER TABLE rooms ADD COLUMN is_public BOOLEAN DEFAULT 0")
    
    # Migration: add in_result column to users
    c.execute("PRAGMA table_info(users)")
    user_cols = [col[1] for col in c.fetchall()]
    if "in_result" not in user_cols:
        c.execute("ALTER TABLE users ADD COLUMN in_result BOOLEAN DEFAULT 0")
        
    conn.commit()
    conn.close()

# ---------------- HTTP ROUTES ----------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, name, status, admin_username FROM rooms WHERE status != "finished"')
    rows = c.fetchall()
    
    rooms = []
    for r in rows:
        c.execute('SELECT COUNT(*) FROM users WHERE room_id = ?', (r[0],))
        user_count = c.fetchone()[0]
        rooms.append({
            'id': r[0],
            'name': r[1],
            'status': r[2],
            'admin': r[3],
            'user_count': user_count
        })
    conn.close()
    return jsonify({'rooms': rooms})

@app.route('/api/create_room', methods=['POST'])
def create_room():
    data = request.json
    room_name = data.get('room_name')
    username = data.get('username')
    is_public = data.get('is_public', False)
    
    room_id = str(uuid.uuid4())[:8] # Short UUID
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO rooms (id, name, status, admin_username, is_public) VALUES (?, ?, 'waiting', ?, ?)", 
              (room_id, room_name, username, is_public))
    conn.commit()
    conn.close()
    
    return jsonify({'room_id': room_id, 'status': 'success'})

@app.route('/api/check_room/<room_id>', methods=['GET'])
def check_room(room_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, status FROM rooms WHERE id = ?', (room_id,))
    room = c.fetchone()
    conn.close()
    
    if room:
        return jsonify({'exists': True, 'status': room[1]})
    return jsonify({'exists': False}), 404

@app.route('/api/join_public', methods=['GET'])
def join_public():
    username = request.args.get('username', 'Player')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Find public rooms that are still waiting
    c.execute('SELECT id FROM rooms WHERE is_public = 1 AND status = "waiting"')
    rooms = c.fetchall()
    
    best_room = None
    most_users = -1
    
    for r in rooms:
        r_id = r[0]
        c.execute('SELECT COUNT(*) FROM users WHERE room_id = ?', (r_id,))
        count = c.fetchone()[0]
        if count < 6 and count > most_users:
            most_users = count
            best_room = r_id
    
    if not best_room:
        # Auto-create a public room
        room_id = str(uuid.uuid4())[:8]
        c.execute("INSERT INTO rooms (id, name, status, admin_username, is_public) VALUES (?, ?, 'waiting', ?, 1)",
                  (room_id, 'パブリックルーム', username))
        conn.commit()
        best_room = room_id
            
    conn.close()
    
    return jsonify({'room_id': best_room, 'status': 'success'})

@app.route('/api/reset_room/<room_id>', methods=['POST'])
def reset_room(room_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE rooms SET status = "waiting", team1_score = 0, team2_score = 0, set_number = 1 WHERE id = ?', (room_id,))
    c.execute('UPDATE users SET team_id = 0, is_ready = 0, in_result = 0 WHERE room_id = ?', (room_id,))
    # Clear team chat
    c.execute('DELETE FROM posts WHERE room_id = ? AND team_id > 0', (room_id,))
    conn.commit()
    conn.close()
    socketio.emit('room_update', fetch_room_state(room_id), to=room_id)
    return jsonify({'status': 'success'})

@app.route('/api/posts', methods=['GET'])
def get_posts():
    room_id = request.args.get('room_id')
    team_id = request.args.get('team_id')
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('PRAGMA table_info(posts)')
    columns = [col[1] for col in c.fetchall()]
    
    query = 'SELECT * FROM posts WHERE room_id = ?'
    params = [room_id]
    
    if team_id and team_id != "0" and team_id != "null":
        # Strictly show only this team's chat (no waiting room chat mixed in)
        query += ' AND team_id = ?'
        params.append(int(team_id))
    else:
        # Waiting room: only fetch global/waiting room chats (team_id is null or 0)
        query += ' AND (team_id IS NULL OR team_id = 0)'
        
    query += ' ORDER BY id ASC'
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    posts = []
    for row in rows:
        post_data = {}
        for idx, col_name in enumerate(columns):
            post_data[col_name] = row[idx]
        posts.append(post_data)

    return jsonify({'posts': posts})

@app.route('/post', methods=['POST'])
def post():
    # We will use Flask-SocketIO or AJAX for this now, but keeping endpoint for fallback
    content = request.form.get('content')
    username = request.form.get('username') or 'Anonymous'
    reply_to = request.form.get('reply_to_id')
    room_id = request.form.get('room_id')
    team_id = request.form.get('team_id')
    
    if reply_to == "": reply_to = None
    if team_id == "null" or team_id == "": team_id = 0
    if not room_id: return jsonify({'error': 'no room_id'}), 400

    timestamp = datetime.now().strftime('%Y/%m/%d/%H:%M')
    
    if content:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''
            INSERT INTO posts (username, content, timestamp, reply_to_id, room_id, team_id) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, content, timestamp, reply_to, room_id, team_id))
        conn.commit()
        conn.close()
        
        # Broadcast via socket
        socketio.emit('new_message', {'room_id': room_id, 'team_id': team_id}, to=room_id)
        
    return jsonify({'status': 'success'})

@app.route('/edit/<int:post_id>', methods=['POST'])
def edit_post(post_id):
    content = request.form.get('content')
    username = request.form.get('username')
    room_id = request.form.get('room_id')
    
    if content and username:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('UPDATE posts SET content = ? WHERE id = ? AND username = ?', (content, post_id, username))
        conn.commit()
        conn.close()
        if room_id:
            socketio.emit('new_message', {'room_id': room_id}, to=room_id)
            
    return jsonify({'status': 'success'})

@app.route('/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    username = request.form.get('username')
    room_id = request.form.get('room_id')
    
    if username:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('DELETE FROM posts WHERE id = ? AND username = ?', (post_id, username))
        conn.commit()
        conn.close()
    if room_id:
            socketio.emit('new_message', {'room_id': room_id}, to=room_id)
            
    return jsonify({'status': 'success'})

def check_and_auto_reset_room(room_id, c):
    c.execute('SELECT status FROM rooms WHERE id = ?', (room_id,))
    room_status = c.fetchone()
    if room_status and room_status[0] == 'finished':
        c.execute('SELECT COUNT(*) FROM users WHERE room_id = ? AND in_result = 1', (room_id,))
        still_in_result = c.fetchone()[0]
        if still_in_result == 0:
            c.execute('UPDATE rooms SET status = "waiting", team1_score = 0, team2_score = 0, set_number = 1 WHERE id = ?', (room_id,))
            c.execute('UPDATE users SET team_id = 0, is_ready = 0 WHERE room_id = ?', (room_id,))
            c.execute('DELETE FROM posts WHERE room_id = ? AND team_id > 0', (room_id,))

def handle_user_departure(username, room_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE username = ? AND room_id = ?', (username, room_id))
    
    c.execute('SELECT COUNT(*) FROM users WHERE room_id = ?', (room_id,))
    remaining = c.fetchone()[0]
    
    if remaining == 0:
        # Auto-delete room when all players left
        c.execute('UPDATE rooms SET status = "finished" WHERE id = ?', (room_id,))
        c.execute('DELETE FROM posts WHERE room_id = ?', (room_id,))
        conn.commit()
        conn.close()
        socketio.emit('room_disbanded', {'room_id': room_id}, to=room_id)
        return
        
    # Check admin transfer
    c.execute('SELECT status, admin_username FROM rooms WHERE id = ?', (room_id,))
    room_data = c.fetchone()
    if room_data:
        room_status, admin_username = room_data
        if username == admin_username:
            # Pick a new admin
            c.execute('SELECT username FROM users WHERE room_id = ? ORDER BY id ASC LIMIT 1', (room_id,))
            new_admin = c.fetchone()
            if new_admin:
                c.execute('UPDATE rooms SET admin_username = ? WHERE id = ?', (new_admin[0], room_id))
                
        # Auto-loss check during playing
        if room_status == 'playing':
            c.execute('SELECT COUNT(*) FROM users WHERE room_id = ? AND team_id = 1', (room_id,))
            t1_count = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM users WHERE room_id = ? AND team_id = 2', (room_id,))
            t2_count = c.fetchone()[0]
            
            if t1_count == 0 and t2_count > 0:
                c.execute('UPDATE rooms SET team1_score = 0, team2_score = 3, status = "finished" WHERE id = ?', (room_id,))
                c.execute('UPDATE users SET in_result = 1 WHERE room_id = ?', (room_id,))
                conn.commit()
                socketio.emit('goal_event', {'team_scored': 2, 'team1_score': 0, 'team2_score': 3, 'game_over': True, 'winner': 2, 'disconnect_win': True}, to=room_id)
            elif t2_count == 0 and t1_count > 0:
                c.execute('UPDATE rooms SET team1_score = 3, team2_score = 0, status = "finished" WHERE id = ?', (room_id,))
                c.execute('UPDATE users SET in_result = 1 WHERE room_id = ?', (room_id,))
                conn.commit()
                socketio.emit('goal_event', {'team_scored': 1, 'team1_score': 3, 'team2_score': 0, 'game_over': True, 'winner': 1, 'disconnect_win': True}, to=room_id)
                
    check_and_auto_reset_room(room_id, c)
    conn.commit()
    conn.close()
    
    socketio.emit('player_disconnected', {'username': username}, to=room_id)
    socketio.emit('room_update', fetch_room_state(room_id), to=room_id)

# ---------------- SOCKET.IO HANDLERS ----------------

sid_to_user = {}

@socketio.on('join_room')
def handle_join_room(data):
    username = data['username']
    room_id = data['room_id']
    
    join_room(room_id)
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Upsert user into room
    c.execute('SELECT id FROM users WHERE username = ? AND room_id = ?', (username, room_id))
    if not c.fetchone():
        c.execute('INSERT INTO users (username, room_id, team_id) VALUES (?, ?, 0)', (username, room_id))
    
    conn.commit()
    conn.close()
    
    sid_to_user[request.sid] = {'username': username, 'room_id': room_id}
    
    emit('room_update', fetch_room_state(room_id), to=room_id)

@socketio.on('disconnect')
def handle_disconnect():
    user_info = sid_to_user.get(request.sid)
    if user_info:
        username = user_info['username']
        room_id = user_info['room_id']
        handle_user_departure(username, room_id)
        # Cleanup mapping
        del sid_to_user[request.sid]

@socketio.on('leave_room')
def handle_leave_room(data):
    username = data.get('username')
    room_id = data.get('room_id')
    if room_id and username:
        leave_room(room_id)
        handle_user_departure(username, room_id)

@socketio.on('disband_room')
def handle_disband_room(data):
    room_id = data.get('room_id')
    username = data.get('username')
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Verify sender is admin
    c.execute('SELECT admin_username FROM rooms WHERE id = ?', (room_id,))
    res = c.fetchone()
    if res and res[0] == username:
        c.execute('UPDATE rooms SET status = "finished" WHERE id = ?', (room_id,))
        conn.commit()
        emit('room_disbanded', {'room_id': room_id}, to=room_id)
    conn.close()

@socketio.on('start_game')
def handle_start_game(data):
    room_id = data['room_id']
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Initial state is loading for users to click Ready
    c.execute('UPDATE rooms SET status = "playing", team1_score = 0, team2_score = 0, set_number = 1 WHERE id = ?', (room_id,))
    
    # Assign teams randomly
    c.execute('SELECT username FROM users WHERE room_id = ?', (room_id,))
    users = [u[0] for u in c.fetchall()]
    random.shuffle(users)
    
    mid = len(users) // 2
    team1 = users[:mid]
    team2 = users[mid:]
    # If odd, team2 gets the extra due to slice math, which is fine
    
    for u in team1:
        c.execute('UPDATE users SET team_id = 1, is_ready = 0 WHERE username = ? AND room_id = ?', (u, room_id))
    for u in team2:
        c.execute('UPDATE users SET team_id = 2, is_ready = 0 WHERE username = ? AND room_id = ?', (u, room_id))
        
        
    # Note: Waiting room chat is now preserved until room is disbanded
    
    conn.commit()
    conn.close()
    
    emit('room_update', fetch_room_state(room_id), to=room_id)

@socketio.on('player_ready')
def handle_ready(data):
    username = data['username']
    room_id = data['room_id']
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE users SET is_ready = 1 WHERE username = ? AND room_id = ?', (username, room_id))
    conn.commit()
    
    # Check if all users are ready
    c.execute('SELECT COUNT(*) FROM users WHERE room_id = ? AND is_ready = 0', (room_id,))
    not_ready_count = c.fetchone()[0]
    conn.close()
    
    emit('room_update', fetch_room_state(room_id), to=room_id)
    
    if not_ready_count == 0:
        emit('all_ready', {'room_id': room_id, 'countdown': 3}, to=room_id)


# Physics Syncing
@socketio.on('player_move')
def handle_player_move(data):
    # Relays racket positions to all other clients in the room
    # payload: {room_id, username, team_id, x, z}
    emit('player_moved', data, to=data['room_id'], include_self=False)

@socketio.on('puck_sync')
def handle_puck_sync(data):
    # The 'host' client (e.g. admin) calculates physics and syncs puck state
    # payload: {room_id, x, z, vx, vz}
    emit('puck_synced', data, to=data['room_id'], include_self=False)

@socketio.on('kickoff_direction')
def handle_kickoff_direction(data):
    # Relay kickoff direction from admin to all clients
    emit('kickoff_synced', data, to=data['room_id'], include_self=False)

@socketio.on('goal_scored')
def handle_goal(data):
    room_id = data['room_id']
    team_scoring = data['team_scored'] # 1 or 2
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Fetch current score
    c.execute('SELECT team1_score, team2_score, set_number FROM rooms WHERE id = ?', (room_id,))
    r = c.fetchone()
    if not r: 
        conn.close()
        return
        
    t1, t2, set_num = r
    
    if team_scoring == 1:
        t1 += 1
    else:
        t2 += 1
        
    c.execute('UPDATE rooms SET team1_score = ?, team2_score = ? WHERE id = ?', (t1, t2, room_id))
    
    # Unready everyone for next set
    c.execute('UPDATE users SET is_ready = 0 WHERE room_id = ?', (room_id,))
    
    # Game Over Check (First to 3)
    game_over = False
    winner = None
    if t1 >= 3:
        game_over = True
        winner = 1
        c.execute('UPDATE rooms SET status = "finished" WHERE id = ?', (room_id,))
    elif t2 >= 3:
        game_over = True
        winner = 2
        c.execute('UPDATE rooms SET status = "finished" WHERE id = ?', (room_id,))
    
    if game_over:
        c.execute('UPDATE users SET in_result = 1 WHERE room_id = ?', (room_id,))
        
    conn.commit()
    conn.close()
    
    emit('goal_event', {
        'team_scored': team_scoring,
        'team1_score': t1,
        'team2_score': t2,
        'game_over': game_over,
        'winner': winner
    }, to=room_id)
    
    emit('room_update', fetch_room_state(room_id), to=room_id)

@socketio.on('player_back_to_waiting')
def handle_player_back(data):
    username = data.get('username')
    room_id = data.get('room_id')
    if username and room_id:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('UPDATE users SET in_result = 0 WHERE username = ? AND room_id = ?', (username, room_id))
        check_and_auto_reset_room(room_id, c)
        conn.commit()
        conn.close()
        emit('room_update', fetch_room_state(room_id), to=room_id)

def fetch_room_state(room_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('SELECT id, name, status, admin_username, team1_score, team2_score, set_number, is_public FROM rooms WHERE id = ?', (room_id,))
    r = c.fetchone()
    if not r:
        conn.close()
        return {}
        
    room = {
        'id': r[0],
        'name': r[1],
        'status': r[2],
        'admin': r[3],
        'team1_score': r[4],
        'team2_score': r[5],
        'set_number': r[6],
        'is_public': bool(r[7])
    }
    
    c.execute('SELECT username, team_id, is_ready, COALESCE(in_result, 0) FROM users WHERE room_id = ?', (room_id,))
    users = []
    for u in c.fetchall():
        users.append({
            'username': u[0],
            'team_id': u[1],
            'is_ready': bool(u[2]),
            'in_result': bool(u[3])
        })
        
    conn.close()
    return {'room': room, 'users': users}


init_db()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=8080)
