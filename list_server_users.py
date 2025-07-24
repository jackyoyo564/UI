import sqlite3
import os

SERVER_DB = 'users_server.db'

def list_users():
    if not os.path.exists(SERVER_DB):
        print('找不到 users_server.db')
        return
    conn = sqlite3.connect(SERVER_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT display_name, username, password, role FROM users")
    users = cursor.fetchall()
    conn.close()
    print("=== users_server.db 帳號清單 ===")
    for display_name, username, password, role in users:
        print(f"display_name: {display_name}, username: {username}, password: {password}, role: {role}")
    print(f"共 {len(users)} 筆")

if __name__ == '__main__':
    list_users() 