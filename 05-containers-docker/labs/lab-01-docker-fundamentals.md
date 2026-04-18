# Lab 01: Docker Fundamentals

## 🎯 Objective

Get hands-on with Docker's core operations — pull images, run containers, publish ports, manage logs, and build your first custom image. These are the commands you'll use every single day.

---

## 📋 Prerequisites

- Docker installed and running (`docker --version`)
- Your user in the `docker` group (`id | grep docker`)

---

## 🔬 Exercise 1: Running Containers

### Step 1: Your First Container

```bash
# Run hello-world (verifies Docker works)
docker run hello-world

# Run an interactive Ubuntu container
docker run -it ubuntu:22.04 bash
# You're now INSIDE a container!
cat /etc/os-release
whoami          # root (default — we'll fix this later)
ls /
exit            # Leave the container

# The container is now stopped
docker ps -a | head -5
# STATUS: Exited
```

### Step 2: Running a Web Server

```bash
# Run Nginx in the background
docker run -d --name web -p 8080:80 nginx:1.25-alpine

# Verify it's running
docker ps

# Test it
curl http://localhost:8080
# You should see the Nginx welcome page!

# View the logs
docker logs web
docker logs -f web   # Follow mode (Ctrl+C to stop)

# Get container details
docker inspect web | head -30

# Get inside the running container
docker exec -it web sh
# (Alpine uses sh, not bash)
ls /usr/share/nginx/html/
cat /etc/nginx/nginx.conf
exit
```

### Step 3: Environment Variables and Custom Content

```bash
# Stop and remove the old container
docker rm -f web

# Run with custom content using a bind mount
mkdir -p ~/devops-labs/module-05/html
echo '<h1>Hello from Docker!</h1><p>Served by Nginx in a container.</p>' \
  > ~/devops-labs/module-05/html/index.html

docker run -d \
  --name web \
  -p 8080:80 \
  -v ~/devops-labs/module-05/html:/usr/share/nginx/html:ro \
  nginx:1.25-alpine

# Test
curl http://localhost:8080
# Output: <h1>Hello from Docker!</h1>...

# Modify the file on the host — it updates immediately!
echo '<h1>Updated Content!</h1>' > ~/devops-labs/module-05/html/index.html
curl http://localhost:8080
# Output: <h1>Updated Content!</h1>
```

### Step 4: Resource Monitoring

```bash
# See resource usage (live)
docker stats --no-stream

# Limit resources
docker rm -f web
docker run -d \
  --name web \
  -p 8080:80 \
  --memory=128m \
  --cpus=0.5 \
  nginx:1.25-alpine

docker stats web --no-stream
# Memory limit shown as 128MiB

# Clean up
docker rm -f web
```

---

## 🔬 Exercise 2: Build Your First Docker Image

### Step 1: Create a Simple Application

```bash
mkdir -p ~/devops-labs/module-05/myapp
cd ~/devops-labs/module-05/myapp

# Create a Python Flask app
cat > app.py << 'APP'
from flask import Flask, jsonify
import os
import socket
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "message": "Hello from Docker!",
        "hostname": socket.gethostname(),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
APP

echo "flask==3.0.0" > requirements.txt
```

### Step 2: Write the Dockerfile

```bash
cat > Dockerfile << 'DOCKERFILE'
FROM python:3.12-slim

# Metadata
LABEL maintainer="devops-handbook"

# Set working directory
WORKDIR /app

# Install dependencies first (caching!)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Create non-root user
RUN useradd -r -s /usr/sbin/nologin appuser
USER appuser

# Set environment variables
ENV PORT=5000
ENV APP_VERSION=1.0.0

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["python", "app.py"]
DOCKERFILE

# Create .dockerignore
cat > .dockerignore << 'IGNORE'
__pycache__
*.pyc
.git
.gitignore
README.md
Dockerfile
docker-compose.yml
IGNORE
```

### Step 3: Build and Run

```bash
# Build the image
docker build -t myapp:v1.0 .

# Check the image
docker images myapp

# Run it
docker run -d --name myapp -p 5000:5000 myapp:v1.0

# Test
curl http://localhost:5000
curl http://localhost:5000/health

# Check the health status
docker inspect myapp --format='{{.State.Health.Status}}'

# View logs
docker logs myapp

# Clean up
docker rm -f myapp
```

---

## 🔬 Exercise 3: Docker Compose Multi-Container App

### Step 1: Create the Compose File

```bash
cd ~/devops-labs/module-05/myapp

cat > docker-compose.yml << 'COMPOSE'
version: "3.8"

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - APP_VERSION=2.0.0
      - REDIS_HOST=cache
    depends_on:
      - cache
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"]
      interval: 30s
      timeout: 5s
      retries: 3

  cache:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - app
    restart: unless-stopped

volumes:
  redis_data:
COMPOSE

# Create Nginx proxy config
cat > nginx.conf << 'NGINX'
upstream app {
    server app:5000;
}

server {
    listen 80;

    location / {
        proxy_pass http://app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /health {
        proxy_pass http://app/health;
        access_log off;
    }
}
NGINX
```

### Step 2: Run the Stack

```bash
# Start everything
docker compose up -d

# Check status
docker compose ps

# View all logs
docker compose logs

# Follow specific service logs
docker compose logs -f app

# Test through Nginx (port 80)
curl http://localhost
curl http://localhost/health

# Test directly (port 5000)
curl http://localhost:5000

# Check the network
docker network ls | grep myapp

# Scale the app (run 3 instances)
docker compose up -d --scale app=3
docker compose ps
```

### Step 3: Clean Up

```bash
# Stop everything and remove volumes
docker compose down -v

# Remove all build caches
docker builder prune -f
```

---

## 🧨 Break It: Docker Debugging

### Failure 1: Container Exits Immediately

```bash
# Create a broken Dockerfile
mkdir -p /tmp/broken-app && cd /tmp/broken-app
echo 'import nonexistent_module' > app.py
echo 'flask' > requirements.txt

cat > Dockerfile << 'DF'
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py"]
DF

docker build -t broken:v1 .
docker run --name broken broken:v1

# Container exits immediately!
# Debug:
docker logs broken
# ModuleNotFoundError: No module named 'nonexistent_module'

# Fix: correct the import, rebuild, rerun
docker rm broken
```

### Failure 2: Port Already In Use

```bash
# Start something on port 5000
docker run -d --name first -p 5000:80 nginx:1.25-alpine

# Try to start another on the same port
docker run -d --name second -p 5000:80 nginx:1.25-alpine 2>&1
# Error: port is already allocated

# Debug:
docker ps | grep 5000
# Shows: first is using port 5000

# Fix: use a different port or stop the first container
docker rm -f first second
```

---

## ✅ Validation

- [ ] Run and manage containers with `docker run/stop/rm/logs/exec`
- [ ] Build a custom Docker image from a Dockerfile
- [ ] Use `.dockerignore` to exclude unnecessary files
- [ ] Run a multi-container app with Docker Compose
- [ ] Explain Docker layers and why COPY order matters for caching
- [ ] Debug a container that exits immediately
- [ ] Run containers as non-root users

---

[← Back to Module README](../README.md) | [Next Lab: Advanced Docker Patterns →](./lab-02-advanced-docker.md)
