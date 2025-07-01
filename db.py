# db.py
import sqlite3
import hashlib

db_url = "zig_clg.db"

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

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        ip_address TEXT,
        device_id TEXT
    );
    """)

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


def register_user(username, password, name=None, ip_address=None, device_id=None):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    try:
        conn = sqlite3.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, password, name, ip_address, device_id)
            VALUES (?, ?, ?, ?, ?)
        """, (username, hashed_password, name, ip_address, device_id))
        conn.commit()
        return {"status": "success", "message": "User registered"}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Username already exists"}
    finally:
        conn.close()


def login_user(username, password):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, ip_address, device_id FROM users
        WHERE username = ? AND password = ?
    """, (username, hashed_password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return {
            "status": "success",
            "id": user[0],
            "name": user[1],
            "ip_address": user[2],
            "device_id": user[3]
        }
    else:
        return {
            "status": "error",
            "message": "Invalid username or password"
        }