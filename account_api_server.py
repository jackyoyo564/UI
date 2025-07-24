from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
import hashlib

app = Flask(__name__)
DB_PATH = 'users_server.db'
ROBOT_DB = 'robots.db'
UPLOAD_FOLDER = 'robot_images'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        # 預設管理員帳號（密碼也用 SHA256 雜湊）
        cursor.execute("INSERT INTO users (display_name, username, password, role) VALUES (?, ?, ?, ?)",
                       ("管理員", "admin", hash_password("admin"), "manager"))
        conn.commit()
        conn.close()

def init_robot_db():
    if not os.path.exists(ROBOT_DB):
        conn = sqlite3.connect(ROBOT_DB)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS robots (
                robot_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                add_date TEXT NOT NULL,
                repair_count INTEGER DEFAULT 0,
                task_completion_rate REAL DEFAULT 0.0,
                damage_status TEXT DEFAULT '無損壞',
                battery_level INTEGER DEFAULT 100,
                image_path TEXT
            )
        ''')
        # 新增多圖表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS robot_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id TEXT NOT NULL,
                image_path TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT display_name, username, role FROM users WHERE username = ? AND password = ?", 
                   (username, hash_password(password)))
    user = cursor.fetchone()
    conn.close()
    if user:
        return jsonify({"success": True, "display_name": user[0], "username": user[1], "role": user[2]})
    else:
        return jsonify({"success": False, "msg": "帳號或密碼錯誤"})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    display_name = data.get('display_name')
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (display_name, username, password, role) VALUES (?, ?, ?, ?)",
                       (display_name, username, hash_password(password), role))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"success": False, "msg": "帳號已存在"})

@app.route('/api/users', methods=['GET'])
def get_users():
    # 管理員查詢所有帳號
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT display_name, username, role FROM users")
    users = cursor.fetchall()
    conn.close()
    return jsonify({"users": [{"display_name": u[0], "username": u[1], "role": u[2]} for u in users]})

@app.route('/api/delete_user', methods=['POST'])
def delete_user():
    data = request.json
    username = data.get('username')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"success": False, "msg": "帳號不存在"})
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/update_user', methods=['POST'])
def update_user():
    data = request.json
    username = data.get('username')
    new_display_name = data.get('new_display_name')
    new_username = data.get('new_username')
    new_password = data.get('new_password')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"success": False, "msg": "帳號不存在"})
    updates = []
    values = []
    if new_display_name:
        updates.append("display_name = ?")
        values.append(new_display_name)
    if new_username:
        cursor.execute("SELECT id FROM users WHERE username = ?", (new_username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "msg": "新帳號已存在"})
        updates.append("username = ?")
        values.append(new_username)
    if new_password:
        import hashlib
        updates.append("password = ?")
        values.append(hashlib.sha256(new_password.encode()).hexdigest())
    if not updates:
        conn.close()
        return jsonify({"success": False, "msg": "沒有更新內容"})
    values.append(username)
    query = f"UPDATE users SET {', '.join(updates)} WHERE username = ?"
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/robots', methods=['GET'])
def get_robots():
    conn = sqlite3.connect(ROBOT_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT robot_id, name, add_date, repair_count, task_completion_rate, damage_status, battery_level, image_path FROM robots")
    robots = cursor.fetchall()
    conn.close()
    return jsonify({"robots": [
        {"robot_id": r[0], "name": r[1], "add_date": r[2], "repair_count": r[3], "task_completion_rate": r[4], "damage_status": r[5], "battery_level": r[6], "image_path": r[7]} for r in robots
    ]})

@app.route('/api/add_robot', methods=['POST'])
def add_robot():
    data = request.json
    robot_id = data.get('robot_id')
    name = data.get('name')
    add_date = data.get('add_date')
    conn = sqlite3.connect(ROBOT_DB)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO robots (robot_id, name, add_date) VALUES (?, ?, ?)", (robot_id, name, add_date))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"success": False, "msg": "機器人ID已存在"})

@app.route('/api/update_robot', methods=['POST'])
def update_robot():
    data = request.json
    robot_id = data.get('robot_id')
    updates = []
    values = []
    for field in ["name", "repair_count", "task_completion_rate", "damage_status", "battery_level", "image_path"]:
        if field in data:
            updates.append(f"{field} = ?")
            values.append(data[field])
    if not updates:
        return jsonify({"success": False, "msg": "沒有更新內容"})
    values.append(robot_id)
    conn = sqlite3.connect(ROBOT_DB)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE robots SET {', '.join(updates)} WHERE robot_id = ?", values)
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/delete_robot', methods=['POST'])
def delete_robot():
    data = request.json
    robot_id = data.get('robot_id')
    conn = sqlite3.connect(ROBOT_DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM robots WHERE robot_id = ?", (robot_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/robot/<robot_id>', methods=['GET'])
def get_robot(robot_id):
    conn = sqlite3.connect(ROBOT_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT robot_id, name, add_date, repair_count, task_completion_rate, damage_status, battery_level, image_path FROM robots WHERE robot_id = ?", (robot_id,))
    r = cursor.fetchone()
    conn.close()
    if r:
        return jsonify({"success": True, "robot": {
            "robot_id": r[0], "name": r[1], "add_date": r[2], "repair_count": r[3], "task_completion_rate": r[4], "damage_status": r[5], "battery_level": r[6], "image_path": r[7]
        }})
    else:
        return jsonify({"success": False, "msg": "找不到該機器人"})

@app.route('/api/upload_robot_image', methods=['POST'])
def upload_robot_image():
    if 'file' not in request.files or 'robot_id' not in request.form:
        return jsonify({"success": False, "msg": "缺少檔案或 robot_id"})
    file = request.files['file']
    robot_id = request.form['robot_id']
    if file.filename == '':
        return jsonify({"success": False, "msg": "未選擇檔案"})
    ext = os.path.splitext(file.filename)[1]
    import uuid
    filename = f"{robot_id}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)
    # 新增到 robot_images
    conn = sqlite3.connect(ROBOT_DB)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO robot_images (robot_id, image_path) VALUES (?, ?)", (robot_id, f"/robot_images/{filename}"))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "image_path": f"/robot_images/{filename}"})

@app.route('/api/robot_images/<robot_id>', methods=['GET'])
def get_robot_images(robot_id):
    conn = sqlite3.connect(ROBOT_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT id, image_path FROM robot_images WHERE robot_id = ?", (robot_id,))
    images = cursor.fetchall()
    conn.close()
    return jsonify({"images": [{"id": img[0], "image_path": img[1]} for img in images]})

@app.route('/api/delete_robot_images', methods=['POST'])
def delete_robot_images():
    data = request.json
    ids = data.get('ids', [])
    if not ids:
        return jsonify({"success": False, "msg": "未指定要刪除的圖片"})
    conn = sqlite3.connect(ROBOT_DB)
    cursor = conn.cursor()
    cursor.execute(f"SELECT image_path FROM robot_images WHERE id IN ({','.join(['?']*len(ids))})", ids)
    paths = [row[0] for row in cursor.fetchall()]
    cursor.execute(f"DELETE FROM robot_images WHERE id IN ({','.join(['?']*len(ids))})", ids)
    conn.commit()
    conn.close()
    # 刪除檔案
    deleted = []
    not_found = []
    for path in paths:
        rel_path = path.lstrip('/\\')
        full_path = os.path.join(app.root_path, rel_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                deleted.append(full_path)
            except Exception as e:
                not_found.append(f"{full_path} (error: {str(e)})")
        else:
            not_found.append(full_path)
    return jsonify({"success": True, "deleted": deleted, "not_found": not_found})

@app.route('/robot_images/<filename>')
def get_robot_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    init_db()
    init_robot_db()
    app.run(host='0.0.0.0', port=5000, debug=True) 