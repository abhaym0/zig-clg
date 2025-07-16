# Admin Setup Instructions

## ✅ What's Done

### 1. **Admin Authentication System**
- ✅ Admin table created in database
- ✅ Admin login API endpoint: `/api/admin/login`
- ✅ Admin login page: `/templates/admin-login.html`
- ✅ Authentication check on admin panel
- ✅ LocalStorage for admin session management

### 2. **File Upload System (LAN Compatible)**
- ✅ Files stored in `uploads/` folder
- ✅ Database stores file URLs (not file content)
- ✅ URLs use server IP instead of localhost: `http://SERVER_IP:8900/uploads/filename`
- ✅ Auto-detects server IP for LAN compatibility

### 3. **Admin Features**
- ✅ **KICK**: Disconnects user from WebSocket (temporary)
- ✅ **BAN**: Permanently blocks user login (sets `is_banned = 1`)
- ✅ **DELETE**: Removes user account completely
- ✅ **Chat Management**: View and delete public messages
- ✅ **Online Users**: Real-time monitoring
- ✅ **Broadcast Messages**: Send announcements to all users

## 🔑 Default Admin Account

**Username**: `admin`
**Password**: `admin123`

*This account is created automatically when you first run the server.*

## 📝 Create Additional Admin Accounts

To create more admin accounts, you can use these database queries:

### SQLite Command Line:
```sql
-- Open the database
sqlite3 zig_clg.db

-- Create a new admin
INSERT INTO admins (username, password, name) 
VALUES ('newadmin', 'hashed_password_here', 'Admin Name');

-- To get the hashed password, use Python:
```

### Python Script to Hash Password:
```python
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Example:
password = "mypassword123"
hashed = hash_password(password)
print(f"Hashed password: {hashed}")
```

### Complete Example:
```sql
-- Create admin with username 'superadmin' and password 'mypassword123'
INSERT INTO admins (username, password, name) 
VALUES ('superadmin', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'Super Admin');
```

## 🌐 LAN Access

The server automatically detects your LAN IP address. Users can access:
- **Chat**: `http://YOUR_LAN_IP:8000`
- **Admin Panel**: `http://YOUR_LAN_IP:8000/templates/admin-login.html`

## 🔗 API Endpoints

### Admin Endpoints:
- `POST /api/admin/login` - Admin login
- `POST /api/admin/kick/{username}` - Kick user
- `POST /api/admin/ban/{username}` - Ban user
- `POST /api/admin/delete/{username}` - Delete user
- `GET /api/admin/messages` - Get all messages
- `DELETE /api/admin/messages/{id}` - Delete message
- `GET /api/admin/online-users` - Get online users
- `POST /api/admin/broadcast` - Send broadcast message

### File Upload:
- `POST /api/upload` - Upload file (stores in uploads/ folder)
- `GET /uploads/{filename}` - Access uploaded files

## 🚀 Ready to Go!

Your admin system is now complete with:
- ✅ Secure admin authentication
- ✅ LAN-compatible file sharing
- ✅ Full user management
- ✅ Real-time chat monitoring
- ✅ Broadcast messaging

Just run your server and access the admin panel at: 
`http://YOUR_LAN_IP:8000/templates/admin-login.html`
