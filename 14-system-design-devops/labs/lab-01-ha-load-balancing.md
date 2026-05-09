# Lab 01: High Availability and Load Balancing

## 🎯 Objective

Build a load-balanced, highly available web application using Nginx as a reverse proxy with health checks, and simulate real-world failure scenarios including server crashes and rolling deployments.

---

## 📋 Prerequisites

- Docker and Docker Compose installed
- Completed Module 02 (Networking) and Module 05 (Docker)
- Basic understanding of HTTP and reverse proxies

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Commands you ran and the important output you used for validation
- Any files, scripts, configs, manifests, or workflows you created
- A short failure note describing one thing that broke, how you diagnosed it, and how you fixed it
- Cleanup commands or confirmation that no long-running resources remain

Treat the validation section as the minimum proof that the lab worked.

---

## 🔬 Exercise 1: Build the Application Stack

### Step 1: Create the Application

```bash
mkdir -p ha-lab && cd ha-lab

# Simple Python app that identifies which server responded
cat > app.py << 'APP'
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
APP

# Dockerfile
cat > Dockerfile << 'DOCKER'
FROM python:3.12-slim
WORKDIR /app
COPY app.py .
RUN useradd -r -s /sbin/nologin appuser
USER appuser
EXPOSE 8080
CMD ["python3", "app.py"]
DOCKER
```

### Step 2: Create the Nginx Load Balancer Configuration

```bash
mkdir -p nginx

cat > nginx/nginx.conf << 'NGINX'
upstream backend {
    # Round-robin by default
    server app1:8080 max_fails=3 fail_timeout=30s;
    server app2:8080 max_fails=3 fail_timeout=30s;
    server app3:8080 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 5s;
        proxy_read_timeout 10s;
        proxy_next_upstream error timeout http_502 http_503;
    }

    location /nginx-health {
        return 200 "nginx is healthy\n";
        add_header Content-Type text/plain;
    }
}
NGINX
```

### Step 3: Create Docker Compose

```bash
cat > docker-compose.yml << 'COMPOSE'
services:
  lb:
    image: nginx:1.25-alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - app1
      - app2
      - app3
    restart: unless-stopped

  app1:
    build: .
    environment:
      - SERVER_ID=1
      - PORT=8080
    restart: unless-stopped

  app2:
    build: .
    environment:
      - SERVER_ID=2
      - PORT=8080
    restart: unless-stopped

  app3:
    build: .
    environment:
      - SERVER_ID=3
      - PORT=8080
    restart: unless-stopped
COMPOSE

# Build and start
docker compose up -d --build
```

### Step 4: Verify Load Balancing

```bash
# Send 10 requests — observe round-robin distribution
for i in $(seq 1 10); do
  curl -s http://localhost:8080
done

# You should see responses from servers 1, 2, and 3 cycling
```

**✅ Checkpoint:** All three servers respond, and traffic is distributed across them.

---

## 🔬 Exercise 2: Simulate Failures

### Step 1: Kill a Backend Server

```bash
# Stop server 2
docker compose stop app2

# Send requests — should only see servers 1 and 3
for i in $(seq 1 6); do
  curl -s http://localhost:8080
done

# Check Nginx detects the failure
docker compose logs lb | tail -10
```

### Step 2: Bring It Back

```bash
# Restart server 2
docker compose start app2

# Wait a moment, then verify it's back in rotation
sleep 5
for i in $(seq 1 9); do
  curl -s http://localhost:8080
done
```

### Step 3: Simulate Complete Backend Failure

```bash
# Stop all backends
docker compose stop app1 app2 app3

# What does the load balancer return?
curl -v http://localhost:8080

# You should see a 502 Bad Gateway — Nginx has no healthy upstream

# Restart all
docker compose start app1 app2 app3
```

**✅ Checkpoint:** Nginx automatically removes failed servers and adds them back when they recover.

---

## 🔬 Exercise 3: Simulate a Rolling Deployment

```bash
# Make a "v2" of the app (change the greeting)
sed 's/Hello from/[v2] Hello from/' app.py > app_v2.py
mv app_v2.py app.py

# Rebuild the image
docker compose build

# Rolling restart: one at a time
for svc in app1 app2 app3; do
  echo "--- Updating $svc ---"
  docker compose up -d --no-deps $svc
  sleep 5  # Wait for the new container to be healthy

  # Verify the service is responding
  for i in $(seq 1 3); do
    curl -s http://localhost:8080
  done
  echo ""
done

# Final check — all servers should show [v2]
for i in $(seq 1 9); do
  curl -s http://localhost:8080
done
```

**✅ Checkpoint:** The application is updated with zero downtime — old and new versions serve traffic during the transition.

---

## 🔬 Exercise 4: Experiment with Load Balancing Algorithms

### Least Connections

```bash
# Update nginx.conf
cat > nginx/nginx.conf << 'NGINX'
upstream backend {
    least_conn;
    server app1:8080 max_fails=3 fail_timeout=30s;
    server app2:8080 max_fails=3 fail_timeout=30s;
    server app3:8080 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /nginx-health {
        return 200 "nginx is healthy\n";
        add_header Content-Type text/plain;
    }
}
NGINX

# Reload Nginx without downtime
docker compose exec lb nginx -s reload

# Test with slow endpoint — least_conn should avoid the busy server
curl -s http://localhost:8080/slow &
curl -s http://localhost:8080/slow &
for i in $(seq 1 6); do curl -s http://localhost:8080; done
wait
```

### Weighted Round Robin

```bash
# Update nginx.conf — server 1 gets 3x traffic
cat > nginx/nginx.conf << 'NGINX'
upstream backend {
    server app1:8080 weight=3 max_fails=3 fail_timeout=30s;
    server app2:8080 weight=1 max_fails=3 fail_timeout=30s;
    server app3:8080 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /nginx-health {
        return 200 "nginx is healthy\n";
        add_header Content-Type text/plain;
    }
}
NGINX

docker compose exec lb nginx -s reload

# Send 10 requests — server 1 should handle ~60%
for i in $(seq 1 10); do curl -s http://localhost:8080; done
```

**✅ Checkpoint:** You can observe different traffic distribution patterns with each algorithm.

---

## 🧨 Break It: Failure Scenarios

Try these challenges and document what happens:

1. **Split brain**: Stop Nginx and access backend servers directly on their container IPs. What happens to traffic consistency?
2. **Thundering herd**: Start all three backends at once after a full outage. Watch Nginx logs to see how it rediscovers healthy upstreams.
3. **Config syntax error**: Introduce a typo in `nginx.conf` and run `nginx -s reload`. Does it crash the running proxy, or does Nginx keep the old config?
4. **Resource exhaustion**: Send many concurrent requests to `/slow` and observe how Nginx handles upstream timeouts.

---

## 🧹 Cleanup

```bash
docker compose down -v
cd ..
rm -rf ha-lab
```

---

## ✅ Validation

- [ ] Deploy a 3-server application behind an Nginx load balancer
- [ ] Observe round-robin traffic distribution across all backends
- [ ] Simulate a server failure and confirm Nginx stops routing to it
- [ ] Recover the failed server and confirm it returns to the pool
- [ ] Perform a rolling deployment with zero downtime
- [ ] Switch between round-robin, least_conn, and weighted algorithms
- [ ] Explain why health checks are critical for production load balancing
- [ ] Describe the difference between Layer 4 and Layer 7 load balancing

## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- Docker Compose file and Nginx configuration
- Application code with health check endpoint
- Rolling deployment script or commands
- Failure test results showing automatic failover
- Notes comparing load balancing algorithms

---

[← Back to Module README](../README.md)
