# database.py
# نفس منطق قاعدة البيانات الأصلي (SQLite) - يعمل بدون تعديل على أندرويد
# لأن sqlite3 جزء من مكتبة بايثون القياسية ومدعوم بالكامل عبر python-for-android

import sqlite3
import os


def get_db_path():
    """
    على أندرويد يجب تخزين قاعدة البيانات داخل مجلد التطبيق الخاص
    (وليس بجانب الكود كما في سطح المكتب)، لذلك نستخدم App.user_data_dir
    """
    try:
        from kivy.app import App
        app = App.get_running_app()
        if app:
            return os.path.join(app.user_data_dir, "nexus_core.db")
    except Exception:
        pass
    return "nexus_core.db"


class NexusDB:
    def __init__(self):
        self.conn = sqlite3.connect(get_db_path())
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS folders (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL,
                                parent_id INTEGER DEFAULT NULL)''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS items (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                folder_id INTEGER,
                                name TEXT NOT NULL,
                                actual_path TEXT,
                                size_info TEXT,
                                is_locked INTEGER DEFAULT 0,
                                is_app INTEGER DEFAULT 0,
                                FOREIGN KEY(folder_id) REFERENCES folders(id))''')
        self.conn.commit()

        self.cursor.execute("SELECT COUNT(*) FROM folders")
        if self.cursor.fetchone()[0] == 0:
            root_id = self.add_folder("Nexus Core System", None)
            sub_f = self.add_folder("Project_Nebula", root_id)
            self.add_item(root_id, "Project_Nebula", "Folder", "Folder", 0, 0)
            self.add_item(sub_f, "Sub_Data_01.log", "File", "45 KB", 0, 0)
            self.add_item(root_id, "Encrypted.log", "File", "1.2 MB", 1, 0)
            self.add_item(root_id, "Access.log", "File", "920 KB", 0, 0)

    def add_folder(self, name, parent_id):
        self.cursor.execute("INSERT INTO folders (name, parent_id) VALUES (?, ?)", (name, parent_id))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_folder_details(self, folder_id):
        self.cursor.execute("SELECT name, parent_id FROM folders WHERE id = ?", (folder_id,))
        return self.cursor.fetchone()

    def get_items_in_folder(self, folder_id):
        self.cursor.execute(
            "SELECT id, name, size_info, actual_path, is_locked, is_app FROM items WHERE folder_id = ?",
            (folder_id,))
        return self.cursor.fetchall()

    def add_item(self, folder_id, name, path, size, is_locked, is_app):
        self.cursor.execute(
            "INSERT INTO items (folder_id, name, actual_path, size_info, is_locked, is_app) VALUES (?, ?, ?, ?, ?, ?)",
            (folder_id, name, path, size, is_locked, is_app))
        self.conn.commit()

    def update_lock_status(self, item_id, status):
        self.cursor.execute("UPDATE items SET is_locked = ? WHERE id = ?", (status, item_id))
        self.conn.commit()

    def update_item_path(self, item_id, path):
        self.cursor.execute("UPDATE items SET actual_path = ?, is_locked = 1 WHERE id = ?", (path, item_id))
        self.conn.commit()

    def find_subfolder(self, name, parent_id):
        self.cursor.execute("SELECT id FROM folders WHERE name = ? AND parent_id = ?", (name, parent_id))
        return self.cursor.fetchone()

    def get_apps(self):
        self.cursor.execute("SELECT name, actual_path FROM items WHERE is_app = 1")
        return self.cursor.fetchall()
