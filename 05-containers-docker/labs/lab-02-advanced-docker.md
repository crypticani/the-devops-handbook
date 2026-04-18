# Lab 02: Advanced Docker Patterns

## 🎯 Objective

Master multi-stage builds, image optimization, Docker networking internals, and production-grade container patterns.

---

## 📋 Prerequisites

- Completed Lab 01
- Docker and Docker Compose installed

---

## 🔬 Exercise 1: Multi-Stage Build

### Build a Go App (Extreme Size Reduction)

```bash
mkdir -p ~/devops-labs/module-05/multistage && cd ~/devops-labs/module-05/multistage

# Create a simple Go HTTP server
cat > main.go << 'GOAPP'
package main

import (
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "os"
    "time"
)

type Response struct {
    Message   string `json:"message"`
    Hostname  string `json:"hostname"`
    Timestamp string `json:"timestamp"`
}

func handler(w http.ResponseWriter, r *http.Request) {
    hostname, _ := os.Hostname()
    resp := Response{
        Message:   "Hello from multi-stage build!",
        Hostname:  hostname,
        Timestamp: time.Now().Format(time.RFC3339),
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(resp)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    fmt.Fprint(w, `{"status":"healthy"}`)
}

func main() {
    http.HandleFunc("/", handler)
    http.HandleFunc("/health", healthHandler)
    port := os.Getenv("PORT")
    if port == "" {
        port = "8080"
    }
    log.Printf("Server starting on port %s", port)
    log.Fatal(http.ListenAndServe(":"+port, nil))
}
GOAPP

cat > go.mod << 'GOMOD'
module multistage-demo
go 1.21
GOMOD
```

### Single-stage (large) vs Multi-stage (tiny)

```bash
# Single-stage Dockerfile (BAD — includes compiler)
cat > Dockerfile.single << 'DF'
FROM golang:1.21
WORKDIR /app
COPY . .
RUN go build -o server .
EXPOSE 8080
CMD ["./server"]
DF

# Multi-stage Dockerfile (GOOD — tiny final image)
cat > Dockerfile.multi << 'DF'
# Stage 1: Build
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod .
COPY main.go .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o server .

# Stage 2: Run (scratch = empty image!)
FROM scratch
COPY --from=builder /app/server /server
EXPOSE 8080
ENTRYPOINT ["/server"]
DF

# Build both
docker build -t demo:single -f Dockerfile.single .
docker build -t demo:multi  -f Dockerfile.multi .

# Compare sizes
docker images | grep demo
# demo   single   abc123   840MB    ← Includes entire Go SDK!
# demo   multi    def456   6.5MB   ← Just the binary!

# Test the multi-stage image
docker run -d --name demo -p 8080:8080 demo:multi
curl http://localhost:8080
docker rm -f demo

echo "Size reduction: ~99%!"
```

---

## 🔬 Exercise 2: Docker Networking Deep Dive

### Understanding Network Modes

```bash
# Default bridge network — containers get private IPs
docker run -d --name web1 nginx:1.25-alpine
docker run -d --name web2 nginx:1.25-alpine

# Get their IP addresses
docker inspect web1 --format '{{.NetworkSettings.IPAddress}}'
docker inspect web2 --format '{{.NetworkSettings.IPAddress}}'

# They can reach each other by IP but NOT by name on default bridge
docker exec web1 ping -c 2 $(docker inspect web2 --format '{{.NetworkSettings.IPAddress}}')
# Works!
docker exec web1 ping -c 2 web2 2>&1 || echo "Name resolution FAILED on default bridge"
# Fails! (Default bridge doesn't have DNS)

# Custom bridge — containers CAN resolve by name
docker network create mynet
docker rm -f web1 web2

docker run -d --name web1 --network mynet nginx:1.25-alpine
docker run -d --name web2 --network mynet nginx:1.25-alpine

# Now name resolution works!
docker exec web1 ping -c 2 web2
# Success! Docker's embedded DNS resolves "web2" to its IP

# This is EXACTLY how Docker Compose networking works

docker rm -f web1 web2
docker network rm mynet
```

### Exposing Services

```bash
# Host networking (container shares host's network stack)
docker run -d --name hostnet --network host nginx:1.25-alpine
# Nginx is now on the HOST's port 80 — no port mapping needed!
curl http://localhost
docker rm -f hostnet

# None networking (complete isolation)
docker run -d --name isolated --network none alpine sleep 3600
docker exec isolated ping -c 1 8.8.8.8 2>&1 || echo "No network access (expected)"
docker rm -f isolated
```

---

## 🔬 Exercise 3: Docker Volumes and Data Persistence

```bash
# Problem: Container data is lost when container is removed
docker run -d --name db postgres:15-alpine \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=mydb

# The database files are inside the container
# If we rm -f db, all data is GONE

docker rm -f db

# Solution: Named volumes persist data
docker volume create pgdata

docker run -d --name db \
  -v pgdata:/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=mydb \
  postgres:15-alpine

sleep 5

# Create some data
docker exec db psql -U postgres -d mydb -c "CREATE TABLE users (id SERIAL, name TEXT);"
docker exec db psql -U postgres -d mydb -c "INSERT INTO users (name) VALUES ('DevOps');"
docker exec db psql -U postgres -d mydb -c "SELECT * FROM users;"

# Remove the container
docker rm -f db

# Start a NEW container with the SAME volume
docker run -d --name db2 \
  -v pgdata:/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD=test \
  postgres:15-alpine

sleep 5

# Data is still there!
docker exec db2 psql -U postgres -d mydb -c "SELECT * FROM users;"
# Output:  id | name
#          1  | DevOps

# Clean up
docker rm -f db2
docker volume rm pgdata
```

---

## 🔬 Exercise 4: Image Security Scanning

```bash
# Scan an image with Docker Scout (built-in)
docker scout cves nginx:1.25 2>/dev/null || echo "Docker Scout not available"

# Alternative: Trivy (popular open-source scanner)
# Install Trivy
sudo apt-get install -y wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install -y trivy

# Scan an image
trivy image nginx:1.25
trivy image python:3.12-slim

# Key insight: Smaller base images = fewer vulnerabilities
trivy image python:3.12-slim --severity HIGH,CRITICAL
trivy image python:3.12-alpine --severity HIGH,CRITICAL
# Alpine typically has fewer CVEs
```

---

## 🧨 Break It: Production Debugging

### Challenge: Application Can't Connect to Database

```bash
# Start database without a custom network
docker run -d --name db -e POSTGRES_PASSWORD=test postgres:15-alpine

# Start app trying to connect to "db" by name
docker run -d --name app \
  -e DATABASE_HOST=db \
  alpine sh -c 'while true; do ping -c 1 db 2>&1; sleep 5; done'

# Check app logs
docker logs app
# "ping: bad address 'db'" — name resolution fails!

# Debug:
# 1. Are they on the same network?
docker inspect app --format='{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}'
docker inspect db --format='{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}'
# They're both on "bridge" but default bridge doesn't have DNS!

# Fix: Create a custom network
docker network create appnet
docker rm -f app db

docker run -d --name db --network appnet -e POSTGRES_PASSWORD=test postgres:15-alpine
docker run -d --name app --network appnet \
  alpine sh -c 'while true; do ping -c 1 db; sleep 5; done'

docker logs app
# "64 bytes from db (172.19.0.2): seq=0 ttl=64" — works!

docker rm -f app db
docker network rm appnet
```

---

## ✅ Validation

- [ ] Build a multi-stage image and compare sizes
- [ ] Explain why custom networks have DNS and the default bridge doesn't
- [ ] Use named volumes to persist data across container restarts
- [ ] Scan an image for security vulnerabilities
- [ ] Debug a "container can't connect" networking issue
- [ ] Explain the difference between bind mounts and named volumes

---

## 💡 Key Takeaways

1. **Multi-stage builds** can reduce image sizes by 90-99%
2. **Always use custom networks** — never rely on the default bridge for multi-container apps
3. **Named volumes** for data persistence; **bind mounts** for development
4. **Scan images regularly** — vulnerabilities in base images affect you
5. **Smaller images** = faster pulls, less attack surface, fewer CVEs

---

[← Previous Lab](./lab-01-docker-fundamentals.md) | [Back to Module README](../README.md)
