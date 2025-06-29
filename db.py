# db.py
import sqlite3

def init_db():
    conn = sqlite3.connect("zig_clg.db")
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        type TEXT,
        content TEXT,
        file_name TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    

    conn.commit()
    conn.close()

def insert_message(sender, msg_type, content, file_name=""):
    conn = sqlite3.connect("zig_clg.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (sender, type, content, file_name)
        VALUES (?, ?, ?, ?)
    """, (sender, msg_type, content, file_name))
    conn.commit()
    conn.close()

def get_all_messages():
    conn = sqlite3.connect("zig_clg.db")
    c = conn.cursor()
    c.execute("SELECT sender, type, content, file_name FROM messages")
    rows = c.fetchall()
    conn.close()
    return [
        {"sender": r[0], "type": r[1], "content": r[2], "fileName": r[3]} for r in rows
    ]
