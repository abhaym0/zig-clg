# server.py (final with registration API)
from http.server import SimpleHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import threading, asyncio, websockets, os, json #type: ignore
from websocket_handler import handle_ws
from db import init_db, register_user
from aiohttp import web #type: ignore

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

        return web.json_response(result, headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)})
    
async def handle_options(request):
    return web.Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })

async def start_ws_and_api():
    app = web.Application()
    app.router.add_post('/api/register', handle_register)
    app.router.add_route("OPTIONS", "/api/register", handle_options)
    app.router.add_post("/api/login",do_POST)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("API server running at http://0.0.0.0:8080")

    async with websockets.serve(handle_ws, "0.0.0.0", 8765):
        print("WebSocket server running at ws://0.0.0.0:8765")
        await asyncio.Future()

if __name__ == "__main__":
    init_db()
    threading.Thread(target=start_http_server, daemon=True).start()
    asyncio.run(start_ws_and_api())
