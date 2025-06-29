# server.py (updated)
from http.server import SimpleHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import threading, asyncio, websockets, os, json
from websocket_handler import handle_ws
from db import init_db

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class MyHTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.path = "/templates/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path == "/upload":
            content_length = int(self.headers['Content-Length'])
            boundary = self.headers['Content-Type'].split("boundary=")[1].encode()
            body = self.rfile.read(content_length)

            # Extract filename and file content from multipart/form-data
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

    def translate_path(self, path):
        # Let /uploads/ serve from ./uploads folder
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

async def start_ws_server():
    async with websockets.serve(handle_ws, "0.0.0.0", 8765):
        print("WebSocket server running at ws://0.0.0.0:8765")
        await asyncio.Future()

if __name__ == "__main__":
    init_db()
    threading.Thread(target=start_http_server, daemon=True).start()
    asyncio.run(start_ws_server())
