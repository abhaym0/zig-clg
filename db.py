# db.py
import sqlite3
import hashlib
from aiohttp import web #type: ignore



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
        recipient TEXT,
        is_private BOOLEAN DEFAULT 0,
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
        device_id TEXT,
        is_banned BOOLEAN DEFAULT 0
    );
    """)
    
    # Add is_banned column if it doesn't exist (for existing databases)
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add temporary kick columns if they don't exist
    try:
        c.execute("ALTER TABLE users ADD COLUMN kick_until DATETIME DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN kick_reason TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Create admin table
    c.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

def insert_message(sender, msg_type, content, file_name="", recipient=None, is_private=False):
    conn = sqlite3.connect("zig_clg.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (sender, type, content, file_name, recipient, is_private)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (sender, msg_type, content, file_name, recipient, is_private))
    conn.commit()
    conn.close()

def get_all_messages():
    """Get all public messages"""
    conn = sqlite3.connect("zig_clg.db")
    c = conn.cursor()
    c.execute("SELECT sender, type, content, file_name FROM messages WHERE is_private = 0")
    rows = c.fetchall()
    conn.close()
    return [
        {"sender": r[0], "type": r[1], "content": r[2], "fileName": r[3]} for r in rows
    ]

def get_private_messages(user1, user2):
    """Get private messages between two users"""
    conn = sqlite3.connect("zig_clg.db")
    c = conn.cursor()
    c.execute("""
        SELECT sender, type, content, file_name, timestamp 
        FROM messages 
        WHERE is_private = 1 
        AND ((sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?))
        ORDER BY timestamp ASC
    """, (user1, user2, user2, user1))
    rows = c.fetchall()
    conn.close()
    return [
        {"sender": r[0], "type": r[1], "content": r[2], "fileName": r[3], "timestamp": r[4]} for r in rows
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
        return {
            "status": "success",
            "message": "User registered successfully",
            "username": username,
            "name": name
        }
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Username already exists"}
    finally:
        conn.close()


def login_user(username, password):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, ip_address, device_id, is_banned FROM users
        WHERE username = ? AND password = ?
    """, (username, hashed_password))
    user = cursor.fetchone()
    conn.close()

    if user:
        # Check if user is banned
        if user[4] == 1:  # is_banned column
            return {
                "status": "error",
                "redirect": "banned",
                "message": "Your account has been banned. Contact admin for support."
            }
        
        # Check if user is temporarily kicked
        kick_status = is_user_temporarily_kicked(username)
        if kick_status["is_kicked"]:
            import datetime
            kick_until = datetime.datetime.fromisoformat(kick_status["kick_until"])
            remaining_time = kick_until - datetime.datetime.now()
            minutes_remaining = int(remaining_time.total_seconds() / 60)
            
            return {
                "status": "error",
                "redirect": "kicked_temp",
                "message": f"You are temporarily restricted from joining the chat. {minutes_remaining} minutes remaining. Reason: {kick_status['reason']}",
                "minutes_remaining": minutes_remaining,
                "reason": kick_status["reason"]
            }
        
        return {
            "status": "success",
            "id": user[0],
            "username": username,
            "name": user[1],
            "ip_address": user[2],
            "device_id": user[3]
        }
    else:
        return {
            "status": "error",
            "message": "Invalid username or password"
        }

def delete_Record(record_id):
    conn = sqlite3.connect("zig_clg.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

# delete_Record(42)

# Admin functions
def ban_user(username):
    """Ban a user permanently"""
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"User {username} has been banned"}

def unban_user(username):
    """Unban a user"""
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = 0 WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"User {username} has been unbanned"}

def get_user_by_username(username):
    """Get user information by username"""
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, name, ip_address, device_id, is_banned FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            "id": user[0],
            "username": user[1],
            "name": user[2],
            "ip_address": user[3],
            "device_id": user[4],
            "is_banned": user[5]
        }
    return None

def is_user_banned(username):
    """Check if user is banned"""
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def delete_user_account(username):
    """Delete user account permanently"""
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"User {username} account deleted"}

def get_all_public_messages():
    """Get all public messages for admin"""
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, sender, type, content, file_name, timestamp 
        FROM messages 
        WHERE is_private = 0 
        ORDER BY timestamp DESC
    """)
    messages = cursor.fetchall()
    conn.close()
    return [
        {
            "id": msg[0],
            "sender": msg[1],
            "type": msg[2],
            "content": msg[3],
            "file_name": msg[4],
            "timestamp": msg[5]
        }
        for msg in messages
    ]

def delete_message(message_id):
    """Delete a specific message"""
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Message deleted"}

def get_online_users():
    """Get list of currently online users (this will be updated from websocket)"""
    # This will be populated from websocket connections
    from websocket_handler import connected_clients
    return list(connected_clients.values())

def insert_admin_message(content):
    """Insert admin broadcast message"""
    insert_message(
        sender="ADMIN",
        msg_type="admin_broadcast",
        content=content,
        file_name="",
        recipient=None,
        is_private=False
    )

# Admin authentication functions
def create_admin(username, password, name=None):
    """Create a new admin (to be used via database query only)"""
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    try:
        conn = sqlite3.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO admins (username, password, name)
            VALUES (?, ?, ?)
        """, (username, hashed_password, name))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Admin created successfully"}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Admin username already exists"}
    finally:
        if conn:
            conn.close()

def login_admin(username, password):
    """Admin login function"""
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, created_at FROM admins
        WHERE username = ? AND password = ?
    """, (username, hashed_password))
    admin = cursor.fetchone()
    conn.close()
    
    if admin:
        return {
            "status": "success",
            "id": admin[0],
            "username": username,
            "name": admin[1] or "Admin",
            "created_at": admin[2]
        }
    else:
        return {
            "status": "error",
            "message": "Invalid admin credentials"
        }

# Temporary kick functions
def set_temporary_kick(username, duration_minutes, reason="No reason provided"):
    """Set a temporary kick for a user"""
    import datetime
    kick_until = datetime.datetime.now() + datetime.timedelta(minutes=duration_minutes)
    
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET kick_until = ?, kick_reason = ? WHERE username = ?
    """, (kick_until.isoformat(), reason, username))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"User {username} temporarily kicked for {duration_minutes} minutes"}

def clear_temporary_kick(username):
    """Clear temporary kick for a user"""
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET kick_until = NULL, kick_reason = NULL WHERE username = ?
    """, (username,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Temporary kick cleared for {username}"}

def is_user_temporarily_kicked(username):
    """Check if user is currently temporarily kicked"""
    import datetime
    conn = sqlite3.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("SELECT kick_until, kick_reason FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        kick_until = datetime.datetime.fromisoformat(result[0])
        if datetime.datetime.now() < kick_until:
            return {
                "is_kicked": True,
                "kick_until": result[0],
                "reason": result[1] or "No reason provided"
            }
        else:
            # Kick expired, clear it
            clear_temporary_kick(username)
    
    return {"is_kicked": False}

# Function to create default admin (call this manually if needed)
def create_default_admin():
    """Create a default admin account"""
    return create_admin("admin", "admin123", "System Admin")


# admin side code

async def fetchAllUsers(request):
    try:
        conn = sqlite3.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, name, ip_address, device_id FROM users")
        users = cursor.fetchall()
        conn.close()

        user_list = [
            {
                "id": row[0],
                "username": row[1],
                "name": row[2],
                "ip": row[3],
                "device_id": row[4]
            }
            for row in users
        ]

        return web.json_response(user_list, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)
