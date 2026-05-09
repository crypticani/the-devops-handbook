# Lab 01: Mock Incident Debugging

## 🎯 Objective

Practice diagnosing and resolving simulated production incidents using Docker. Each scenario replicates a common real-world failure that DevOps engineers encounter. Your goal is to identify the root cause, fix the issue, and document your process — just like you would during an on-call shift or in an interview.

---

## 📋 Prerequisites

- Docker and Docker Compose installed
- Familiarity with Linux commands, Docker, and networking
- Completed Modules 01, 02, 05, and 07

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- For each incident: the symptoms observed, commands used to diagnose, root cause, and fix
- Terminal output or screenshots showing key diagnostic steps
- A short reflection on which incident was hardest and why

---

## 🔬 Incident 1: The Crash-Looping Container

### Setup

```bash
mkdir -p incident-lab && cd incident-lab

# Create an app that crashes after 3 seconds
cat > crash_app.py << 'APP'
import time, sys, os
print("Starting application...")
print(f"Config file: {os.environ.get('CONFIG_PATH', '/etc/app/config.yml')}")
time.sleep(3)
# Simulate crash: missing required config file
config_path = os.environ.get('CONFIG_PATH', '/etc/app/config.yml')
if not os.path.exists(config_path):
    print(f"FATAL: Config file not found: {config_path}", file=sys.stderr)
    sys.exit(1)
print("Application running normally")
while True:
    time.sleep(10)
APP

cat > Dockerfile.crash << 'DOCKER'
FROM python:3.12-slim
WORKDIR /app
COPY crash_app.py .
CMD ["python3", "-u", "crash_app.py"]
DOCKER

cat > docker-compose-incident1.yml << 'COMPOSE'
services:
  webapp:
    build:
      context: .
      dockerfile: Dockerfile.crash
    restart: always
COMPOSE

docker compose -f docker-compose-incident1.yml up -d --build
```

### Your Mission

The webapp container keeps restarting. Diagnose why and fix it.

**Hints** (use only if stuck):
1. Check the container status: `docker compose -f docker-compose-incident1.yml ps`
2. Check logs: `docker compose -f docker-compose-incident1.yml logs webapp`
3. The fix involves providing what the application needs

### Expected Fix

```bash
# Create the missing config file
mkdir -p config
echo "database_host: localhost" > config/config.yml

# Update compose to mount the config
cat > docker-compose-incident1.yml << 'COMPOSE'
services:
  webapp:
    build:
      context: .
      dockerfile: Dockerfile.crash
    environment:
      - CONFIG_PATH=/etc/app/config.yml
    volumes:
      - ./config/config.yml:/etc/app/config.yml:ro
    restart: always
COMPOSE

docker compose -f docker-compose-incident1.yml up -d
# Verify: container should now stay running
docker compose -f docker-compose-incident1.yml ps
```

**✅ Checkpoint:** Container status shows "Up" with no restarts.

---

## 🔬 Incident 2: The Disk-Full Application

### Setup

```bash
# App that fills up its log directory
cat > diskfill_app.py << 'APP'
import time, os
log_dir = "/app/logs"
os.makedirs(log_dir, exist_ok=True)
counter = 0
print("Application started, writing logs...")
while True:
    with open(f"{log_dir}/app.log", "a") as f:
        f.write(f"Log entry {counter}: " + "x" * 10000 + "\n")
    counter += 1
    if counter % 100 == 0:
        size = os.path.getsize(f"{log_dir}/app.log")
        print(f"Log file size: {size / 1024 / 1024:.1f} MB")
    time.sleep(0.01)
APP

cat > Dockerfile.disk << 'DOCKER'
FROM python:3.12-slim
WORKDIR /app
COPY diskfill_app.py .
CMD ["python3", "-u", "diskfill_app.py"]
DOCKER

cat > docker-compose-incident2.yml << 'COMPOSE'
services:
  logger:
    build:
      context: .
      dockerfile: Dockerfile.disk
    deploy:
      resources:
        limits:
          memory: 128M
    tmpfs:
      - /app/logs:size=5M
COMPOSE

docker compose -f docker-compose-incident2.yml up -d --build
```

### Your Mission

The application will eventually fail when the log directory fills up. Diagnose the disk issue and implement log rotation or cleanup.

**Debugging steps to practice:**
```bash
# Check container resource usage
docker stats --no-stream

# Exec into the container to check disk usage
docker compose -f docker-compose-incident2.yml exec logger sh -c "du -sh /app/logs/*"

# Check if the container is still running
docker compose -f docker-compose-incident2.yml ps

# Check logs for errors
docker compose -f docker-compose-incident2.yml logs --tail 20 logger
```

**✅ Checkpoint:** You identified that the log file grows unbounded and the tmpfs fills up.

---

## 🔬 Incident 3: The Broken Reverse Proxy

### Setup

```bash
cat > backend.py << 'APP'
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        elif self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"items":["a","b","c"]}')
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, fmt, *args): pass

HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
APP

# Intentionally broken Nginx config (wrong upstream port)
mkdir -p nginx-broken
cat > nginx-broken/default.conf << 'NGINX'
upstream api {
    server backend:9999;
}
server {
    listen 80;
    location /api/ {
        proxy_pass http://api;
        proxy_connect_timeout 3s;
        proxy_read_timeout 5s;
    }
    location / {
        return 200 "Frontend OK\n";
        add_header Content-Type text/plain;
    }
}
NGINX

cat > docker-compose-incident3.yml << 'COMPOSE'
services:
  proxy:
    image: nginx:1.25-alpine
    ports:
      - "8888:80"
    volumes:
      - ./nginx-broken/default.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - backend
  backend:
    build:
      context: .
      dockerfile: Dockerfile.crash
    command: ["python3", "-u", "backend.py"]
COMPOSE

docker compose -f docker-compose-incident3.yml up -d --build
```

### Your Mission

The frontend (http://localhost:8888/) works, but the API (http://localhost:8888/api/health) returns 502 Bad Gateway. Diagnose and fix.

**Debugging steps:**
```bash
# Test the endpoints
curl http://localhost:8888/
curl -v http://localhost:8888/api/health

# Check Nginx error logs
docker compose -f docker-compose-incident3.yml logs proxy

# Check if the backend is actually running and on what port
docker compose -f docker-compose-incident3.yml exec backend ss -tlnp
```

**✅ Checkpoint:** After fixing the upstream port in the Nginx config, `/api/health` returns `{"status":"ok"}`.

---

## 🔬 Incident 4: The DNS Resolution Failure

### Setup

```bash
cat > dns_app.py << 'APP'
import urllib.request, time, sys
while True:
    try:
        resp = urllib.request.urlopen("http://datastore:6379/ping", timeout=3)
        print(f"Connected: {resp.read().decode()}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
    time.sleep(5)
APP

cat > docker-compose-incident4.yml << 'COMPOSE'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.crash
    command: ["python3", "-u", "dns_app.py"]
    networks:
      - frontend
  datastore:
    image: redis:7-alpine
    networks:
      - backend
networks:
  frontend:
  backend:
COMPOSE

docker compose -f docker-compose-incident4.yml up -d --build
```

### Your Mission

The app cannot connect to the datastore. The error mentions name resolution. Diagnose the network isolation issue and fix it.

**Debugging steps:**
```bash
# Check app logs
docker compose -f docker-compose-incident4.yml logs app

# Inspect networks
docker network ls
docker compose -f docker-compose-incident4.yml exec app cat /etc/resolv.conf

# Can the app resolve the datastore hostname?
docker compose -f docker-compose-incident4.yml exec app nslookup datastore || echo "nslookup not available, try ping"
docker compose -f docker-compose-incident4.yml exec app ping -c 1 datastore || echo "Cannot resolve"
```

**✅ Checkpoint:** After putting both services on the same network (or a shared network), the app connects successfully.

---

## 🧹 Cleanup

```bash
docker compose -f docker-compose-incident1.yml down -v 2>/dev/null
docker compose -f docker-compose-incident2.yml down -v 2>/dev/null
docker compose -f docker-compose-incident3.yml down -v 2>/dev/null
docker compose -f docker-compose-incident4.yml down -v 2>/dev/null
cd ..
rm -rf incident-lab
```

---

## ✅ Validation

- [ ] Diagnose and fix the crash-looping container (missing config file)
- [ ] Identify disk space exhaustion from unbounded log growth
- [ ] Debug a 502 Bad Gateway caused by wrong upstream port
- [ ] Resolve a DNS failure caused by Docker network isolation
- [ ] For each incident: document symptoms, diagnostic commands, root cause, and fix
- [ ] Explain how you would prevent each issue in a production environment

## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- Incident report for each scenario with diagnosis steps
- Docker Compose files and fix diffs showing what changed
- Terminal output from key diagnostic commands
- Reflection notes on which incident was most realistic

---

[← Back to Module README](../README.md)
