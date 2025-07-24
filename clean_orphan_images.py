import os
import sqlite3

ROBOT_DB = 'robots.db'
IMAGES_DIR = 'robot_images'

# 取得資料庫所有圖片路徑
conn = sqlite3.connect(ROBOT_DB)
cursor = conn.cursor()
cursor.execute("SELECT image_path FROM robot_images")
db_paths = set([os.path.basename(row[0]) for row in cursor.fetchall()])
conn.close()

# 列出資料夾所有檔案
all_files = set(os.listdir(IMAGES_DIR))

# 找出孤兒檔案
orphan_files = all_files - db_paths

# 刪除孤兒檔案
for fname in orphan_files:
    fpath = os.path.join(IMAGES_DIR, fname)
    try:
        os.remove(fpath)
        print(f"已刪除孤兒圖片: {fpath}")
    except Exception as e:
        print(f"刪除失敗: {fpath}，錯誤: {e}")

print("清理完成！") 