# Module 05: Containers & Docker

> *"Containers are not just a tool — they're a fundamental shift in how software is packaged, deployed, and run."*

---

## 🎯 Why This Module Matters

Docker is the **most transformative tool in modern DevOps**. It solves the "works on my machine" problem by packaging applications with their entire runtime environment. Every CI/CD pipeline, every Kubernetes cluster, every microservice architecture — all built on containers.

**In real-world DevOps work**, you will:
- Containerize applications for consistent deployment
- Build multi-stage Docker images for production
- Manage multi-container applications with Docker Compose
- Debug container networking and storage issues
- Optimize images for size and security
- Push images to registries and manage versioning

---

## 📚 Table of Contents

1. [What Are Containers?](#1-what-are-containers)
2. [Docker Architecture](#2-docker-architecture)
3. [Docker Images](#3-docker-images)
4. [Docker Containers](#4-docker-containers)
5. [Dockerfile — Building Custom Images](#5-dockerfile--building-custom-images)
6. [Multi-Stage Builds](#6-multi-stage-builds)
7. [Docker Networking](#7-docker-networking)
8. [Docker Volumes and Storage](#8-docker-volumes-and-storage)
9. [Docker Compose](#9-docker-compose)
10. [Docker Registry](#10-docker-registry)
11. [Image Optimization](#11-image-optimization)
12. [Common Mistakes and Anti-Patterns](#12-common-mistakes-and-anti-patterns)
13. [Debugging Mindset](#13-debugging-mindset)
14. [Security Considerations](#14-security-considerations)
15. [Interview Insights](#15-interview-insights)

---

## 1. What Are Containers?

### Containers vs Virtual Machines

```
Virtual Machines:                    Containers:
┌─────┐ ┌─────┐ ┌─────┐            ┌─────┐ ┌─────┐ ┌─────┐
│App A│ │App B│ │App C│            │App A│ │App B│ │App C│
├─────┤ ├─────┤ ├─────┤            ├─────┤ ├─────┤ ├─────┤
│Libs │ │Libs │ │Libs │            │Libs │ │Libs │ │Libs │
├─────┤ ├─────┤ ├─────┤            └──┬──┘ └──┬──┘ └──┬──┘
│Guest│ │Guest│ │Guest│               │       │       │
│ OS  │ │ OS  │ │ OS  │            ┌──┴───────┴───────┴──┐
├─────┴─┴─────┴─┴─────┤            │   Container Runtime  │
│     Hypervisor       │            │      (Docker)         │
├──────────────────────┤            ├──────────────────────┤
│      Host OS         │            │      Host OS         │
├──────────────────────┤            ├──────────────────────┤
│     Hardware         │            │     Hardware         │
└──────────────────────┘            └──────────────────────┘

VMs: Full OS per app (GB each)      Containers: Shared kernel (MB each)
Boot: Minutes                       Start: Seconds
Heavy: CPU + RAM overhead           Light: Near-native performance
```

| Feature | Virtual Machine | Container |
|---------|----------------|-----------|
| **Size** | Gigabytes | Megabytes |
| **Start time** | Minutes | Seconds |
| **Isolation** | Full OS-level | Process-level |
| **Performance** | ~95% native | ~99% native |
| **Density** | 10-20 per host | 100+ per host |
| **Use case** | Different OS requirements | Same OS, different apps |

---

## 2. Docker Architecture

```
┌─────────────────────────────────────────────┐
│                Docker Client                 │
│            (docker CLI commands)             │
└────────────────┬────────────────────────────┘
                 │  REST API
┌────────────────▼────────────────────────────┐
│              Docker Daemon (dockerd)         │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Images   │  │Containers│  │ Networks  │  │
│  └──────────┘  └──────────┘  └──────────┘  │
│  ┌──────────┐  ┌──────────┐                 │
│  │ Volumes   │  │  Build   │                 │
│  └──────────┘  └──────────┘                 │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│           Container Runtime (containerd)     │
│                                              │
│  Uses Linux kernel features:                 │
│  • Namespaces (isolation)                    │
│  • cgroups (resource limits)                 │
│  • Union filesystems (layered images)        │
└──────────────────────────────────────────────┘
```

---

## 3. Docker Images

An image is a **read-only template** containing everything needed to run an application.

```bash
# Pull an image from Docker Hub
docker pull nginx:1.25
docker pull python:3.12-slim
docker pull ubuntu:22.04

# List local images
docker images
# REPOSITORY   TAG        IMAGE ID       SIZE
# nginx        1.25       abc123         187MB
# python       3.12-slim  def456         130MB

# Image naming convention:
# registry/repository:tag
# docker.io/library/nginx:1.25
# ghcr.io/myorg/myapp:v2.1.0

# Inspect image details
docker inspect nginx:1.25

# View image layers
docker history nginx:1.25

# Remove an image
docker rmi nginx:1.25

# Remove all unused images
docker image prune -a
```

---

## 4. Docker Containers

A container is a **running instance** of an image.

```bash
# Run a container
docker run nginx:1.25
# This runs in the foreground (Ctrl+C to stop)

# Run in background (detached)
docker run -d --name webserver nginx:1.25

# Run with port mapping
docker run -d -p 8080:80 --name webserver nginx:1.25
# -p HOST_PORT:CONTAINER_PORT
# Access at: http://localhost:8080

# Run with environment variables
docker run -d \
  --name myapp \
  -p 8080:8080 \
  -e DATABASE_URL="postgres://db:5432/myapp" \
  -e LOG_LEVEL="info" \
  myapp:latest

# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Stop a container
docker stop webserver

# Start a stopped container
docker start webserver

# Restart a container
docker restart webserver

# Remove a container
docker rm webserver           # Must be stopped
docker rm -f webserver        # Force remove (even if running)

# Execute a command inside a running container
docker exec -it webserver bash
# -i = interactive
# -t = allocate a TTY
# Now you're INSIDE the container!

# View container logs
docker logs webserver
docker logs -f webserver      # Follow (real-time)
docker logs --tail 50 webserver  # Last 50 lines
docker logs --since 1h webserver # Last hour

# View resource usage
docker stats
# Shows: CPU%, Memory, Network I/O, Disk I/O

# Copy files to/from container
docker cp localfile.txt webserver:/usr/share/nginx/html/
docker cp webserver:/etc/nginx/nginx.conf ./
```

---

## 5. Dockerfile — Building Custom Images

### Basic Dockerfile

```dockerfile
# Dockerfile for a Python web application

# Base image — always use specific tags in production!
FROM python:3.12-slim

# Metadata
LABEL maintainer="devops@example.com"
LABEL version="1.0"

# Set working directory
WORKDIR /app

# Copy dependency file first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user (SECURITY!)
RUN useradd -r -s /usr/sbin/nologin appuser
USER appuser

# Expose port (documentation — doesn't actually publish)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["python", "app.py"]
```

### Build and Run

```bash
# Build an image
docker build -t myapp:v1.0 .
# -t = tag (name:version)
# . = build context (current directory)

# Build with build arguments
docker build --build-arg ENV=production -t myapp:v1.0 .

# Run the built image
docker run -d -p 8080:8080 --name myapp myapp:v1.0
```

### Dockerfile Best Practices

```dockerfile
# ✅ GOOD: Specific base image tag
FROM python:3.12-slim

# ❌ BAD: Latest tag (non-reproducible)
# FROM python:latest

# ✅ GOOD: Copy dependency file first (layer caching)
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# ❌ BAD: Copy everything at once (no cache benefit)
# COPY . .
# RUN pip install -r requirements.txt

# ✅ GOOD: Combine RUN commands (fewer layers)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# ❌ BAD: Separate RUN for each command
# RUN apt-get update
# RUN apt-get install -y curl

# ✅ GOOD: Run as non-root user
USER appuser

# ❌ BAD: Run as root (default)
```

---

## 6. Multi-Stage Builds

Multi-stage builds produce **smaller, more secure** production images.

```dockerfile
# Stage 1: Build
FROM node:20 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Production (only the built artifacts)
FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# Result: Build stage has Node.js, npm, source code (~1GB)
#         Production image has only Nginx + static files (~25MB)
```

---

## 7. Docker Networking

```bash
# List networks
docker network ls
# NETWORK ID   NAME     DRIVER    SCOPE
# abc123       bridge   bridge    local    ← Default
# def456       host     host      local
# ghi789       none     null      local

# Create a custom network (containers can resolve each other by name)
docker network create myapp-network

# Run containers on the same network
docker run -d --name db --network myapp-network postgres:15
docker run -d --name app --network myapp-network -e DB_HOST=db myapp:latest

# The 'app' container can now reach 'db' by hostname!
# This is how Docker Compose works under the hood

# Inspect a network
docker network inspect myapp-network

# Connect a running container to a network
docker network connect myapp-network existing-container
```

---

## 8. Docker Volumes and Storage

```bash
# Named volume (managed by Docker — preferred)
docker volume create mydata
docker run -d -v mydata:/var/lib/postgresql/data postgres:15

# Bind mount (map host directory into container)
docker run -d \
  -v /host/path/nginx.conf:/etc/nginx/nginx.conf:ro \
  -v /host/path/html:/usr/share/nginx/html \
  nginx:1.25

# :ro = read-only (container can't modify the host file)

# List volumes
docker volume ls

# Inspect a volume
docker volume inspect mydata

# Remove unused volumes
docker volume prune
```

---

## 9. Docker Compose

Docker Compose manages **multi-container applications** with a single YAML file.

### docker-compose.yml Example

```yaml
# docker-compose.yml
version: "3.8"

services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgres://user:pass@db:5432/myapp
      - REDIS_URL=redis://cache:6379
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_started
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  db:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d myapp"]
      interval: 10s
      timeout: 5s
      retries: 5

  cache:
    image: redis:7-alpine
    restart: unless-stopped

  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - app

volumes:
  pgdata:
```

### Compose Commands

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f
docker compose logs -f app    # Just one service

# Check status
docker compose ps

# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v

# Rebuild images
docker compose build
docker compose up -d --build

# Scale a service
docker compose up -d --scale app=3

# Execute command in a service
docker compose exec app bash
docker compose exec db psql -U user -d myapp
```

---

## 10. Docker Registry

```bash
# Docker Hub (default)
docker login
docker tag myapp:v1.0 username/myapp:v1.0
docker push username/myapp:v1.0

# GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u username --password-stdin
docker tag myapp:v1.0 ghcr.io/username/myapp:v1.0
docker push ghcr.io/username/myapp:v1.0

# Pull from a registry
docker pull ghcr.io/username/myapp:v1.0
```

---

## 11. Image Optimization

| Technique | Before | After |
|-----------|--------|-------|
| Use Alpine base | `python:3.12` (1GB) | `python:3.12-alpine` (50MB) |
| Multi-stage build | Full build env (1GB+) | Runtime only (50-100MB) |
| `--no-cache-dir` in pip | Cached packages | No cache bloat |
| `.dockerignore` | Copies everything | Only needed files |
| Combine RUN commands | Multiple layers | Single layer |

### Essential .dockerignore

```
.git
.gitignore
node_modules
__pycache__
*.pyc
.env
docker-compose*.yml
Dockerfile
README.md
.vscode
.idea
```

---

## 12. Common Mistakes and Anti-Patterns

### ❌ Running as Root

```dockerfile
# BAD: Container runs as root (default)
FROM python:3.12-slim
COPY . /app
CMD ["python", "/app/main.py"]

# GOOD: Create and use a non-root user
FROM python:3.12-slim
RUN useradd -r appuser
COPY --chown=appuser . /app
USER appuser
CMD ["python", "/app/main.py"]
```

### ❌ Using `latest` Tag

```bash
# BAD: Non-reproducible
docker pull nginx:latest

# GOOD: Pinned version
docker pull nginx:1.25.3
```

### ❌ Storing Secrets in Images

```dockerfile
# BAD: Secret baked into the image
ENV DB_PASSWORD=mysecret123

# GOOD: Pass secrets at runtime
# docker run -e DB_PASSWORD=mysecret123 myapp
# Or use Docker secrets / external secret managers
```

---

## 13. Debugging Mindset

### Container Debugging Framework

```bash
# Container won't start?
docker logs container-name           # Check logs first!
docker inspect container-name        # Check config, health, state

# Need to get inside a running container?
docker exec -it container-name bash
docker exec -it container-name sh    # If bash isn't available (Alpine)

# Container exited immediately?
docker run -it myimage bash          # Override CMD, get a shell
docker logs $(docker ps -aq -l)      # Logs from last exited container

# Network issues?
docker exec -it container-name ping other-container
docker network inspect bridge

# Check resource usage
docker stats container-name
```

---

## 14. Security Considerations

> 🔐 Container security is critical — a compromised container can affect the host.

- **Run as non-root** — always use `USER` in Dockerfile
- **Use minimal base images** — Alpine or distroless
- **Scan images for vulnerabilities** — `docker scout` or Trivy
- **Don't store secrets in images** — use runtime environment or secret managers
- **Use read-only filesystems** — `docker run --read-only`
- **Set resource limits** — prevent container from consuming all host resources
- **Keep images updated** — rebuild with latest base images regularly

---

## 15. Interview Insights

**Q: What's the difference between a Docker image and a container?**
> An image is a read-only template (like a class in OOP). A container is a running instance of that image (like an object). You can run multiple containers from the same image.

**Q: Explain Docker layers and caching.**
> Each instruction in a Dockerfile creates a layer. Layers are cached — if a layer hasn't changed, Docker reuses it. That's why you copy `requirements.txt` before the rest of the code: dependency installation is cached until requirements change.

**Q: How do containers communicate?**
> Containers on the same Docker network can reach each other by container name (DNS resolution). Docker Compose automatically creates a shared network. For external access, you publish ports with `-p HOST:CONTAINER`.

**Q: What is a multi-stage build?**
> A Dockerfile with multiple FROM statements. Build-time dependencies (compilers, test tools) stay in the build stage. Only the final artifact is copied to the production stage, resulting in much smaller images.

**Q: How do you debug a container that keeps restarting?**
> 1. `docker logs container-name` — read the logs. 2. `docker inspect container-name` — check the exit code and state. 3. `docker run -it image bash` — override the CMD and get a shell to investigate. 4. Check health check configuration if using HEALTHCHECK.

---

## ➡️ What's Next?

With Docker mastered, you can now build CI/CD pipelines that build, test, and deploy containers automatically.

**[Module 06: CI/CD →](../06-ci-cd/)**

---

<div align="center">

**Module 05 Complete** ✅

[← Back to Scripting](../04-scripting/) | [Next: CI/CD →](../06-ci-cd/)

</div>
