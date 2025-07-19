# server.py (final with registration API)
from http.server import SimpleHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import threading, asyncio, websockets, os, json #type: ignore
from websocket_handler import handle_ws
from db import init_db, register_user, fetchAllUsers, ban_user, unban_user, delete_user_account, get_all_public_messages, delete_message, get_online_users, insert_admin_message, login_admin, create_default_admin, get_user_by_username, set_temporary_kick, clear_temporary_kick, is_user_temporarily_kicked
import socket
from aiohttp import web #type: ignore
import aiofiles

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Get server IP address for LAN compatibility
def get_server_ip():
    try:
        # Connect to a remote server to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

SERVER_IP = get_server_ip()
print(f"Server IP: {SERVER_IP}")

class MyHTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.path = "/templates/index.html"
        elif self.path == "/register":
            self.path = "/templates/register.html"
        return super().do_GET()

    def do_POST(self):
        if self.path == "/upload":
            content_length = int(self.headers['Content-Length'])
            boundary = self.headers['Content-Type'].split("boundary=")[1].encode()
            body = self.rfile.read(content_length)

            parts = body.split(boundary)
            for part in parts:
                if b"Content-Disposition" in part and b"filename=" in part:
                    header, file_data = part.split(b"\r\n\r\n", 1)
                    file_data = file_data.rsplit(b"\r\n", 1)[0]
                    disposition = header.decode()
                    filename = disposition.split("filename=")[1].split("\r\n")[0].strip('"')
                    filepath = os.path.join(UPLOAD_DIR, filename)
                    with open(filepath, "wb") as f:
                        f.write(file_data)
                    response = json.dumps({"url": f"/uploads/{filename}"}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(response)))
                    self.end_headers()
                    self.wfile.write(response)
                    return

            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Bad Request")

        elif self.path == "/api/login":
                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                data = json.loads(body)

                from db import login_user
                result = login_user(data["username"], data["password"])

                response = json.dumps(result).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

    def translate_path(self, path):
        if path.startswith("/uploads/"):
            return os.path.join(os.getcwd(), path.lstrip("/"))
        return super().translate_path(path)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass

def start_http_server():
    os.chdir(".")
    httpd = ThreadedHTTPServer(('0.0.0.0', 8000), MyHTTPRequestHandler)
    print("HTTP server running at http://0.0.0.0:8000")
    httpd.serve_forever()

async def handle_register(request):
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        name = data.get("name")
        device_id = data.get("device_id")
        ip = request.remote

        result = register_user(username, password, name, ip, device_id)

        return web.json_response({
                "status": "success",
                "message": "User registered successfully.",
                "username": username,
                "name": name
            }, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)})
    
async def handle_options(request):
    return web.Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })

async def handle_login(request):
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")

        from db import login_user
        result = login_user(username, password)

        if result.get("status") == "success":
            return web.json_response(result, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            })
        else:
            return web.json_response(result, status=401, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def upload_file(request):
    import time
    import uuid
    
    try:
        reader = await request.multipart()
        field = await reader.next()
        
        # Get sender from form data
        if field.name == "sender":
            sender = await field.text()
            field = await reader.next()
        else:
            sender = "Unknown"
        
        if field.name != "file":
            return web.json_response({"status": "error", "message": "No file provided"}, status=400)
        
        if not field.filename:
            return web.json_response({"status": "error", "message": "No file selected"}, status=400)
        
        # Validate file type
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf', '.txt', '.docx', '.xlsx', '.pptx', '.zip', '.rar'}
        file_extension = os.path.splitext(field.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            return web.json_response({"status": "error", "message": f"File type {file_extension} not allowed"}, status=400)
        
        # Generate unique filename to avoid conflicts
        timestamp = str(int(time.time()))
        unique_id = str(uuid.uuid4())[:8]
        safe_filename = f"{timestamp}_{unique_id}_{field.filename}"
        file_path = f"./uploads/{safe_filename}"
        
        # Ensure uploads directory exists
        os.makedirs("./uploads", exist_ok=True)
        
        # Save the file
        file_size = 0
        async with aiofiles.open(file_path, 'wb') as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                file_size += len(chunk)
                # Limit file size to 10MB
                if file_size > 10 * 1024 * 1024:
                    os.remove(file_path)  # Clean up partial file
                    return web.json_response({"status": "error", "message": "File too large (max 10MB)"}, status=400)
                await f.write(chunk)
        
        # Store file info in database
        from db import insert_message
        file_url = f"http://{SERVER_IP}:8900/uploads/{safe_filename}"
        
        # Determine file type for display
        is_image = file_extension in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        file_type = "image" if is_image else "file"
        
        # Insert into database with file path (not content)
        insert_message(
            sender=sender,
            msg_type=file_type,
            content=file_url,  # Store the URL/path, not the file content
            file_name=field.filename  # Original filename for display
        )
        
        # Broadcast file info to all users via WebSocket
        from websocket_handler import connected_clients
        broadcast_message = {
            "type": file_type,
            "sender": sender,
            "filename": field.filename,
            "content": file_url,
            "fileName": field.filename,
            "timestamp": time.strftime("%H:%M", time.localtime())
        }
        
        for ws in connected_clients:
            try:
                await ws.send(json.dumps(broadcast_message))
            except Exception as e:
                print(f"Error sending file broadcast: {e}")
        
        return web.json_response({
            "status": "success",
            "filename": field.filename,
            "url": file_url,
            "type": file_type
        }, headers={
            "Access-Control-Allow-Origin": "*"
        })
        
    except Exception as e:
        print(f"File upload error: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

# Admin API endpoints
async def handle_kick_user(request):
    """Kick a user with optional temporary restriction"""
    try:
        username = request.match_info['username']
        data = await request.json() if request.content_type == 'application/json' else {}
        
        duration_minutes = data.get("duration_minutes", 0)
        reason = data.get("reason", "Kicked by admin")
        
        # If duration is specified, set temporary kick
        if duration_minutes > 0:
            set_temporary_kick(username, duration_minutes, reason)
            kick_message = f"You have been temporarily kicked for {duration_minutes} minutes. Reason: {reason}"
        else:
            kick_message = "You have been kicked by admin"
        
        # Find and disconnect the user from WebSocket
        from websocket_handler import connected_clients
        for ws, user in connected_clients.items():
            if user == username:
                await ws.close(code=1000, reason=kick_message)
                break
        
        if duration_minutes > 0:
            return web.json_response({
                "status": "success", 
                "message": f"User {username} temporarily kicked for {duration_minutes} minutes"
            }, headers={"Access-Control-Allow-Origin": "*"})
        else:
            return web.json_response({
                "status": "success", 
                "message": f"User {username} kicked"
            }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def handle_ban_user(request):
    """Ban a user permanently"""
    try:
        username = request.match_info['username']
        result = ban_user(username)
        
        # Also kick them if they're online
        from websocket_handler import connected_clients
        for ws, user in connected_clients.items():
            if user == username:
                await ws.close(code=1000, reason="You have been banned")
                break
        
        return web.json_response(result, headers={
            "Access-Control-Allow-Origin": "*"
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def handle_delete_user(request):
    """Delete user account"""
    try:
        username = request.match_info['username']
        result = delete_user_account(username)
        
        # Also kick them if they're online
        from websocket_handler import connected_clients
        for ws, user in connected_clients.items():
            if user == username:
                await ws.close(code=1000, reason="Your account has been deleted")
                break
        
        return web.json_response(result, headers={
            "Access-Control-Allow-Origin": "*"
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def handle_get_messages(request):
    """Get all public messages for admin"""
    try:
        messages = get_all_public_messages()
        return web.json_response(messages, headers={
            "Access-Control-Allow-Origin": "*"
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def handle_delete_message(request):
    """Delete a message"""
    try:
        message_id = request.match_info['message_id']
        result = delete_message(int(message_id))
        return web.json_response(result, headers={
            "Access-Control-Allow-Origin": "*"
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def handle_get_online_users(request):
    """Get currently online users"""
    try:
        online_users = get_online_users()
        return web.json_response({"online_users": online_users}, headers={
            "Access-Control-Allow-Origin": "*"
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def handle_broadcast_message(request):
    """Send admin broadcast message"""
    try:
        data = await request.json()
        message = data.get("message")
        
        if not message:
            return web.json_response({"status": "error", "message": "Message is required"}, status=400)
        
        # Insert into database
        insert_admin_message(message)
        
        # Broadcast to all connected users
        from websocket_handler import connected_clients
        import time
        
        broadcast_data = {
            "type": "admin_broadcast",
            "sender": "ADMIN",
            "content": message,
            "timestamp": time.strftime("%H:%M", time.localtime())
        }
        
        for ws in connected_clients:
            try:
                await ws.send(json.dumps(broadcast_data))
            except Exception as e:
                print(f"Error sending broadcast: {e}")
        
        return web.json_response({"status": "success", "message": "Broadcast sent"}, headers={
            "Access-Control-Allow-Origin": "*"
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

# Admin unban user API
async def handle_unban_user(request):
    """Admin unban user endpoint"""
    try:
        username = request.match_info['username']
        
        # Check if user exists
        user = get_user_by_username(username)
        if not user:
            return web.json_response({"status": "error", "message": "User not found"}, status=404)
        
        # Unban the user
        unban_user(username)
        
        return web.json_response({"status": "success", "message": f"User {username} unbanned"}, headers={
            "Access-Control-Allow-Origin": "*"
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

# Admin login API
async def handle_admin_login(request):
    """Admin login endpoint"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return web.json_response({"status": "error", "message": "Username and password required"}, status=400)
        
        result = login_admin(username, password)
        
        if result.get("status") == "success":
            return web.json_response(result, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            })
        else:
            return web.json_response(result, status=401, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def start_ws_and_api():
    app = web.Application()
    app.router.add_post('/api/register', handle_register)
    app.router.add_route("OPTIONS", "/api/register", handle_options)
    app.router.add_post('/api/login', handle_login)
    app.router.add_route("OPTIONS", "/api/login", handle_options)
    app.router.add_route("GET", "/api/users", fetchAllUsers)
    app.router.add_post("/api/upload", upload_file)
    app.router.add_static("/uploads/", path="./uploads", name="uploads")
    app.router.add_route("OPTIONS", "/uploads", handle_options)
    app.router.add_route("OPTIONS", "/api/upload", handle_options)
    
    # Admin routes
    app.router.add_post("/api/admin/kick/{username}", handle_kick_user)
    app.router.add_post("/api/admin/ban/{username}", handle_ban_user)
    app.router.add_post("/api/admin/unban/{username}", handle_unban_user)
    app.router.add_post("/api/admin/delete/{username}", handle_delete_user)
    app.router.add_get("/api/admin/messages", handle_get_messages)
    app.router.add_delete("/api/admin/messages/{message_id}", handle_delete_message)
    app.router.add_get("/api/admin/online-users", handle_get_online_users)
    app.router.add_post("/api/admin/broadcast", handle_broadcast_message)
    app.router.add_post("/api/admin/login", handle_admin_login)
    
    # CORS for admin routes
    app.router.add_route("OPTIONS", "/api/admin/kick/{username}", handle_options)
    app.router.add_route("OPTIONS", "/api/admin/ban/{username}", handle_options)
    app.router.add_route("OPTIONS", "/api/admin/unban/{username}", handle_options)
    app.router.add_route("OPTIONS", "/api/admin/delete/{username}", handle_options)
    app.router.add_route("OPTIONS", "/api/admin/messages", handle_options)
    app.router.add_route("OPTIONS", "/api/admin/messages/{message_id}", handle_options)
    app.router.add_route("OPTIONS", "/api/admin/online-users", handle_options)
    app.router.add_route("OPTIONS", "/api/admin/broadcast", handle_options)
    app.router.add_route("OPTIONS", "/api/admin/login", handle_options)

    # app.router.add_get("/api/connected-users", get_connected_users)
    # app.router.add_post("/api/login",do_POST)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8900)
    await site.start()
    print("API server running at http://0.0.0.0:8900")

    async with websockets.serve(handle_ws, "0.0.0.0", 8765):
        print("WebSocket server running at ws://0.0.0.0:8765")
        await asyncio.Future()


if __name__ == "__main__":
    init_db()
    
    # Try to create default admin account
    print("Creating default admin account...")
    result = create_default_admin()
    if result["status"] == "success":
        print("✅ Default admin created: username='admin', password='admin123'")
    else:
        print(f"ℹ️  Default admin: {result['message']}")
    
    threading.Thread(target=start_http_server, daemon=True).start()
    asyncio.run(start_ws_and_api())
