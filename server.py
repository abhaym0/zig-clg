from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from http.server import HTTPServer
import threading
import asyncio
import websockets
from websocket_handler import handle_ws
import os

# Serve HTML files
class MyHTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.path = "/templates/index.html"
        return super().do_GET()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass

def start_http_server():
    os.chdir(".")  # Set working directory
    httpd = ThreadedHTTPServer(('0.0.0.0', 8000), MyHTTPRequestHandler)
    print("HTTP server running at http://0.0.0.0:8000")
    httpd.serve_forever()

async def start_ws_server():
    async with websockets.serve(handle_ws, "0.0.0.0", 8765):
        print("WebSocket server running at ws://0.0.0.0:8765")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    threading.Thread(target=start_http_server, daemon=True).start()
    asyncio.run(start_ws_server())
