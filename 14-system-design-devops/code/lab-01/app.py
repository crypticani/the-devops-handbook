from http.server import HTTPServer, BaseHTTPRequestHandler
import os, socket, time, random

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        elif self.path == "/slow":
            time.sleep(random.uniform(2, 5))
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Slow response complete")
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            server_id = os.environ.get("SERVER_ID", "unknown")
            hostname = socket.gethostname()
            msg = f"Hello from server {server_id} (hostname: {hostname})\n"
            self.wfile.write(msg.encode())

    def log_message(self, format, *args):
        server_id = os.environ.get("SERVER_ID", "unknown")
        print(f"[Server {server_id}] {args[0]}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server_id = os.environ.get("SERVER_ID", "unknown")
    print(f"Server {server_id} listening on port {port}")
    server.serve_forever()
