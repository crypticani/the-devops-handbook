#!/usr/bin/env python3
"""Simple HTTP backend for reverse proxy testing"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import datetime

class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "healthy", "timestamp": str(datetime.datetime.now())}
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/api/info':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "app": "DevOps Handbook Backend",
                "version": "1.0.0",
                "port": 8080,
                "headers_received": dict(self.headers)
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<h1>Backend Server Running</h1><p>Served from port 8080</p>")
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def log_message(self, format, *args):
        print(f"[Backend:{8080}] {args[0]}")

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 8080), AppHandler)
    print("Backend running on http://127.0.0.1:8080")
    server.serve_forever()
