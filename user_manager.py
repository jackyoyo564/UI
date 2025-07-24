import sqlite3
import hashlib
import csv
import os

class UserManager:
    def __init__(self, db_name="users.db"):
        self.db_name = db_name
        self.plain_passwords = {}  # 記憶體儲存未加密密碼，僅限管理者存取
        self.init_db()
        self.migrate_admin_to_manager()
        self.initialize_plain_passwords()
        # self.debug_users()  # 禁用自動調試輸出

    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                display_name TEXT NOT NULL,
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", ('manager001',))
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO users (display_name, username, password, role) VALUES (?, ?, ?, ?)",
                ('Manager One', 'manager001', self.hash_password('manager001'), 'manager')
            )
            self.plain_passwords['manager001'] = 'manager001'
        conn.commit()
        conn.close()

    def migrate_admin_to_manager(self):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = 'manager' WHERE role = 'admin'")
            conn.commit()
            # 移除成功訊息
        except sqlite3.Error as e:
            print(f"資料庫遷移失敗：{str(e)}")
        finally:
            conn.close()

    def initialize_plain_passwords(self):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users")
            users = cursor.fetchall()
            for user in users:
                username = user[0]
                if username not in self.plain_passwords:
                    self.plain_passwords[username] = username
            conn.close()
            # 移除成功訊息
        except sqlite3.Error as e:
            print(f"初始化未加密密碼失敗：{str(e)}")

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def add_user(self, display_name, username, password, role):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                conn.close()
                return False
            hashed_password = self.hash_password(password)
            cursor.execute(
                "INSERT INTO users (display_name, username, password, role) VALUES (?, ?, ?, ?)",
                (display_name, username, hashed_password, role)
            )
            self.plain_passwords[username] = password
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"新增使用者失敗：{str(e)}")
            return False

    def delete_user(self, username):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if not cursor.fetchone():
                conn.close()
                return False
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            self.plain_passwords.pop(username, None)
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"刪除使用者失敗：{str(e)}")
            return False

    def update_user(self, username, new_display_name=None, new_username=None, new_password=None):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if not cursor.fetchone():
                conn.close()
                return False
            updates = []
            values = []
            if new_display_name:
                updates.append("display_name = ?")
                values.append(new_display_name)
            if new_username:
                cursor.execute("SELECT username FROM users WHERE username = ?", (new_username,))
                if cursor.fetchone():
                    conn.close()
                    return False
                updates.append("username = ?")
                values.append(new_username)
            if new_password:
                updates.append("password = ?")
                values.append(self.hash_password(new_password))
                self.plain_passwords[username] = new_password
            if not updates:
                conn.close()
                return False
            values.append(username)
            query = f"UPDATE users SET {', '.join(updates)} WHERE username = ?"
            cursor.execute(query, values)
            if new_username:
                self.plain_passwords[new_username] = self.plain_passwords.pop(username, None)
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"更新使用者失敗：{str(e)}")
            return False

    def verify_user(self, username, password):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE username = ? AND password = ?",
                           (username, self.hash_password(password)))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"驗證使用者失敗：{str(e)}")
            return None

    def get_user_details(self, username, is_manager=False):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT display_name, username, password, role FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()
            if result:
                display_name, username, hashed_password, role = result
                password = self.plain_passwords.get(username, "（無法顯示原始密碼）") if is_manager else hashed_password
                return display_name, username, password, role
            return None
        except sqlite3.Error as e:
            print(f"獲取使用者詳細資訊失敗：{str(e)}")
            return None

    def get_all_users_by_role(self):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT display_name, username FROM users WHERE role = 'manager'")
            admins = cursor.fetchall()
            cursor.execute("SELECT display_name, username FROM users WHERE role = 'operator'")
            operators = cursor.fetchall()
            cursor.execute("SELECT display_name, username FROM users WHERE role = 'technician'")
            technicians = cursor.fetchall()
            conn.close()
            return admins, operators, technicians
        except sqlite3.Error as e:
            print(f"按角色獲取使用者失敗：{str(e)}")
            return [], [], []

    def export_users_to_csv(self):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT display_name, username, role FROM users ORDER BY CASE role WHEN 'manager' THEN 1 WHEN 'operator' THEN 2 WHEN 'technician' THEN 3 ELSE 4 END")
            users = cursor.fetchall()
            conn.close()
            filename = "users_export.csv"
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Display Name', 'Username', 'Role'])
                writer.writerows(users)
            print(f"帳號已匯出至 {filename}，按身分排序")
            return filename
        except (sqlite3.Error, IOError) as e:
            print(f"匯出使用者失敗：{str(e)}")
            return None

    def debug_users(self):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT display_name, username, password, role FROM users")
            users = cursor.fetchall()
            print("=== 資料庫使用者清單 ===")
            for user in users:
                print(f"Display Name: {user[0]}, Username: {user[1]}, Password: {user[2]}, Role: {user[3]}")
            print("=== 未加密密碼清單 ===")
            for username, password in self.plain_passwords.items():
                print(f"Username: {username}, Plain Password: {password}")
            conn.close()
        except sqlite3.Error as e:
            print(f"調試使用者清單失敗：{str(e)}")