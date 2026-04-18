<![CDATA[# Lab 03: Nginx Reverse Proxy Setup

## 🎯 Objective

Set up Nginx as a reverse proxy — the standard production pattern used in nearly every web deployment. You'll configure routing, learn about proxy headers, and simulate a real production setup.

---

## 📋 Prerequisites

- Completed Labs 01-02
- Nginx and Python3 installed
- `sudo` access

```bash
sudo apt install -y nginx python3
```

---

## 🔬 Exercise 1: Backend Application + Nginx Proxy

### Step 1: Create a Simple Backend Application

```bash
# Create a simple Python HTTP server that simulates an API
mkdir -p ~/devops-labs/module-02/nginx-lab
cd ~/devops-labs/module-02/nginx-lab

# Create the backend "app"
cat > app.py << 'APP'
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
APP

# Start the backend
python3 app.py &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Verify it works directly
curl -s http://localhost:8080/health | python3 -m json.tool
# Expected:
# {
#     "status": "healthy",
#     "timestamp": "2024-01-15 10:30:00.123456"
# }
```

### Step 2: Configure Nginx as Reverse Proxy

```bash
# Create Nginx configuration
sudo tee /etc/nginx/sites-available/devops-lab << 'NGINX'
# Reverse Proxy Configuration for DevOps Lab
# This is the standard production pattern

upstream backend {
    server 127.0.0.1:8080;
    # In production, you'd have multiple servers:
    # server 10.0.1.10:8080;
    # server 10.0.1.11:8080;
    # server 10.0.1.12:8080;
}

server {
    listen 80;
    server_name localhost;

    # Access logging (important for monitoring — Module 07)
    access_log /var/log/nginx/devops-lab-access.log;
    error_log /var/log/nginx/devops-lab-error.log;

    # Main application
    location / {
        proxy_pass http://backend;
        
        # Forward client information to the backend
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings
        proxy_connect_timeout 5s;
        proxy_read_timeout 30s;
        proxy_send_timeout 30s;
    }

    # Health check endpoint (no access logging)
    location /health {
        proxy_pass http://backend/health;
        access_log off;    # Don't log health checks (too noisy)
    }

    # Static files (served directly by Nginx — much faster)
    location /static/ {
        alias /var/www/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Security: Block access to hidden files
    location ~ /\. {
        deny all;
        return 404;
    }
}
NGINX

# Create static directory
sudo mkdir -p /var/www/static
echo "body { font-family: sans-serif; }" | sudo tee /var/www/static/style.css

# Enable the site (create symlink)
sudo ln -sf /etc/nginx/sites-available/devops-lab /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test the configuration (ALWAYS do this before reloading!)
sudo nginx -t
# Expected: nginx: configuration file /etc/nginx/nginx.conf test is successful

# Reload Nginx (graceful — no downtime)
sudo systemctl reload nginx
```

### Step 3: Test the Reverse Proxy

```bash
# Test through Nginx (port 80) instead of directly (port 8080)
echo "=== Testing Reverse Proxy ==="

# Homepage
curl -s http://localhost/
echo ""

# Health check
curl -s http://localhost/health | python3 -m json.tool

# API endpoint — notice the headers!
echo ""
echo "=== Headers received by backend ==="
curl -s http://localhost/api/info | python3 -m json.tool
# Look for:
# "X-Real-IP" — Your actual IP
# "X-Forwarded-For" — Chain of proxies
# "X-Forwarded-Proto" — http or https
# "Host" — The hostname from the request

# Static file (served by Nginx directly)
curl -I http://localhost/static/style.css
# Look for: Cache-Control: public, immutable

# 404 — handled by backend
curl -s http://localhost/nonexistent
```

---

## 🔬 Exercise 2: Understanding Proxy Headers

### Why Proxy Headers Matter

```bash
# Without proxy headers, the backend sees Nginx's IP, not the client's
# This breaks:
# - Access logging (all requests appear from 127.0.0.1)
# - Rate limiting (can't identify clients)
# - Geo-location features
# - Security (can't block bad actors)

# Test: See what headers arrive at the backend
curl -s http://localhost/api/info | python3 -m json.tool

# The backend should see:
# "X-Real-IP": "127.0.0.1" (your actual IP)
# "X-Forwarded-For": "127.0.0.1" (proxy chain)
# "Host": "localhost" (original host header)
```

---

## 🔬 Exercise 3: Simulate Production Issues

### Scenario 1: Backend is Down (502 Bad Gateway)

```bash
# Kill the backend
kill $BACKEND_PID 2>/dev/null

# Try to access through Nginx
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost
# Expected: HTTP 502 (Bad Gateway)

# Check Nginx error log
sudo tail -5 /var/log/nginx/devops-lab-error.log
# You'll see: "connect() failed (111: Connection refused)"

# This is the MOST COMMON Nginx error in production
# It means: Nginx can't reach the backend application

# Fix: Restart the backend
cd ~/devops-labs/module-02/nginx-lab
python3 app.py &
BACKEND_PID=$!
sleep 1

# Verify recovery
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost
# Expected: HTTP 200
```

### Scenario 2: Wrong Backend Port

```bash
# Edit Nginx to point to wrong port
sudo sed -i 's/server 127.0.0.1:8080/server 127.0.0.1:9999/' /etc/nginx/sites-available/devops-lab
sudo nginx -t    # Config is valid (no syntax error)
sudo systemctl reload nginx

# Test
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost
# Expected: HTTP 502

# Debug:
echo "=== Is anything listening on port 9999? ==="
ss -tlnp | grep 9999
# Nothing! That's the problem.

echo ""
echo "=== Where is our backend actually? ==="
ss -tlnp | grep 8080
# There it is! Port 8080!

# Fix: Correct the port
sudo sed -i 's/server 127.0.0.1:9999/server 127.0.0.1:8080/' /etc/nginx/sites-available/devops-lab
sudo nginx -t
sudo systemctl reload nginx

# Verify
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost
# Expected: HTTP 200
```

### Scenario 3: Config Syntax Error

```bash
# Introduce a syntax error
echo "invalid_directive;" | sudo tee -a /etc/nginx/sites-available/devops-lab

# Try to reload
sudo nginx -t
# Expected: nginx: [emerg] unknown directive "invalid_directive"
# Nginx DOES NOT reload with a bad config — this is a safety feature!

# The old config is still running:
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost
# Expected: HTTP 200 (still working!)

# Fix: Remove the bad line
sudo sed -i '/invalid_directive/d' /etc/nginx/sites-available/devops-lab
sudo nginx -t
# Expected: test is successful
sudo systemctl reload nginx
```

---

## 🧨 Break It: Complete Debugging Exercise

### The Challenge

Something is wrong with the Nginx setup. Diagnose and fix all issues:

```bash
# Set up a broken configuration
sudo tee /etc/nginx/sites-available/devops-lab-broken << 'BROKEN'
server {
    listen 8888;
    server_name localhost;

    location / {
        proxy_pass http://127.0.0.1:5555;
    }
}
BROKEN

sudo ln -sf /etc/nginx/sites-available/devops-lab-broken /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Now debug:
echo "=== Your mission: Make http://localhost:8888 return 200 ==="
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8888
# Expected: HTTP 502

# Debugging steps to follow:
# 1. Is Nginx listening on 8888? → ss -tlnp | grep 8888
# 2. What does the proxy point to? → grep proxy_pass in config
# 3. Is anything running on 5555? → ss -tlnp | grep 5555
# 4. Fix: Either start something on 5555 or change proxy_pass to 8080
```

Solution:
```bash
# The backend is on 8080, not 5555
sudo sed -i 's/5555/8080/' /etc/nginx/sites-available/devops-lab-broken
sudo nginx -t
sudo systemctl reload nginx

curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8888
# Expected: HTTP 200
```

---

## 🧹 Cleanup

```bash
# Stop the backend
kill $BACKEND_PID 2>/dev/null

# Restore original Nginx config
sudo rm -f /etc/nginx/sites-enabled/devops-lab
sudo rm -f /etc/nginx/sites-enabled/devops-lab-broken
sudo rm -f /etc/nginx/sites-available/devops-lab
sudo rm -f /etc/nginx/sites-available/devops-lab-broken
sudo ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## ✅ Final Validation

You've completed this lab when you can:

- [ ] Set up Nginx as a reverse proxy from scratch
- [ ] Explain why proxy headers (X-Real-IP, X-Forwarded-For) are necessary
- [ ] Debug a 502 Bad Gateway error systematically
- [ ] Always run `nginx -t` before reloading configuration
- [ ] Read Nginx error logs to diagnose issues
- [ ] Explain the request flow: Client → Nginx → Backend Application

---

## 💡 Key Takeaways

1. **Always `nginx -t` before reload** — this prevents bad configs from breaking production
2. **502 Bad Gateway = backend is down or unreachable** — the #1 Nginx error
3. **Proxy headers** are essential for proper logging, security, and client identification
4. **Nginx graceful reload** (`systemctl reload`) applies new config without dropping connections
5. This exact Nginx pattern is used in every production deployment you'll encounter

---

[← Previous Lab](./lab-02-tcp-ports-connectivity.md) | [Back to Module README](../README.md)
]]>
