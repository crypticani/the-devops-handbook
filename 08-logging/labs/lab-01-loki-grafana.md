# Lab 01: Loki + Grafana — Centralized Logging with Docker Compose

## 🎯 Objective

Set up a centralized logging stack using Grafana Loki, Promtail, and Grafana. You'll ship application logs, learn LogQL, and build log dashboards — the modern, lightweight approach used in cloud-native environments.

---

## 📋 Prerequisites

- Docker and Docker Compose installed
- Completed Module 07 (Observability)

---

## 🔬 Exercise 1: Launch the Logging Stack

### Step 1: Create the Project

```bash
mkdir -p logging-lab/{loki,promtail,app} && cd logging-lab
```

### Step 2: Loki Configuration

```bash
cat > loki/loki-config.yml << 'CONFIG'
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-10-24
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  allow_structured_metadata: true
  volume_enabled: true
CONFIG
```

### Step 3: Promtail Configuration

```bash
cat > promtail/promtail-config.yml << 'CONFIG'
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(.*)'
        target_label: 'container'
      - source_labels: ['__meta_docker_container_log_stream']
        target_label: 'stream'
CONFIG
```

### Step 4: Sample Application

```bash
cat > app/app.py << 'APP'
import json
import time
import random
import logging
import sys
from flask import Flask, request, jsonify

# Structured JSON logging to stdout
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "service": "demo-app",
            "message": record.getMessage(),
            "module": record.module,
        }
        if hasattr(record, '_extra'):
            log.update(record._extra)
        if record.exc_info and record.exc_info[0]:
            log["exception"] = self.formatException(record.exc_info)
        return json.dumps(log)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("app")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/users')
def get_users():
    logger.info("Fetching users", extra={"_extra": {"endpoint": "/api/users", "method": "GET"}})
    time.sleep(random.uniform(0.01, 0.05))
    return jsonify({"users": ["alice", "bob", "charlie"]})

@app.route('/api/orders', methods=['POST'])
def create_order():
    order_id = random.randint(1000, 9999)
    if random.random() < 0.3:
        logger.error("Order processing failed",
            extra={"_extra": {"order_id": order_id, "error": "payment_declined"}})
        return jsonify({"error": "Payment declined"}), 500
    logger.info("Order created",
        extra={"_extra": {"order_id": order_id, "status": "success"}})
    return jsonify({"order_id": order_id}), 201

@app.route('/api/error')
def error():
    logger.critical("Critical failure detected",
        extra={"_extra": {"component": "database", "error": "connection_pool_exhausted"}})
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    logger.info("Application starting", extra={"_extra": {"port": 8080}})
    app.run(host='0.0.0.0', port=8080)
APP

cat > app/requirements.txt << 'REQ'
flask==3.0.0
REQ

cat > app/Dockerfile << 'DOCKERFILE'
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
CMD ["python", "-u", "app.py"]
DOCKERFILE
```

### Step 5: Docker Compose

```bash
cat > docker-compose.yml << 'COMPOSE'
services:
  demo-app:
    build: ./app
    container_name: demo-app
    ports:
      - "8080:8080"
    labels:
      - "logging=true"
    restart: unless-stopped

  loki:
    image: grafana/loki:2.9.4
    container_name: loki
    ports:
      - "3100:3100"
    volumes:
      - ./loki/loki-config.yml:/etc/loki/loki-config.yml
      - loki_data:/loki
    command: -config.file=/etc/loki/loki-config.yml
    restart: unless-stopped

  promtail:
    image: grafana/promtail:2.9.4
    container_name: promtail
    volumes:
      - ./promtail/promtail-config.yml:/etc/promtail/promtail-config.yml
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: -config.file=/etc/promtail/promtail-config.yml
    depends_on:
      - loki
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.3.1
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

volumes:
  loki_data:
  grafana_data:
COMPOSE
```

### Step 6: Launch

```bash
docker compose up -d --build
```

**✅ Checkpoint:** All services running. http://localhost:8080/health returns OK.

---

## 🔬 Exercise 2: Generate Logs and Query with LogQL

### Step 1: Generate Traffic

```bash
for i in $(seq 1 50); do
  curl -s http://localhost:8080/api/users > /dev/null
  curl -s -X POST http://localhost:8080/api/orders > /dev/null
  curl -s http://localhost:8080/api/error > /dev/null
  sleep 0.3
done
```

### Step 2: Add Loki Data Source in Grafana

1. Go to http://localhost:3000 (admin/admin)
2. **Connections** → **Data Sources** → **Add** → **Loki**
3. URL: `http://loki:3100`
4. **Save & Test**

### Step 3: Explore Logs

1. Go to **Explore** (compass icon in sidebar)
2. Select **Loki** as data source
3. Run these LogQL queries:

```logql
# All logs from the demo app
{container="demo-app"}

# Only error logs
{container="demo-app"} |= "ERROR"

# Critical logs
{container="demo-app"} |= "CRITICAL"

# Parse JSON and filter
{container="demo-app"} | json | level = "ERROR"

# Count errors over time
count_over_time({container="demo-app"} |= "ERROR" [1m])

# Exclude health checks
{container="demo-app"} != "health"
```

**✅ Checkpoint:** You can see structured JSON logs flowing into Grafana from your application.

---

## 🔬 Exercise 3: Build a Log Dashboard

### Create a Dashboard with These Panels

**Panel 1: Log Volume Over Time (Time Series)**
- Query: `sum(count_over_time({container="demo-app"} [1m])) by (container)`

**Panel 2: Error Count Over Time (Time Series)**
- Query: `count_over_time({container="demo-app"} |= "ERROR" [1m])`

**Panel 3: Logs Panel (Logs visualization)**
- Query: `{container="demo-app"} | json`
- Visualization type: **Logs**

**Panel 4: Error Percentage (Stat)**
- Query A: `count_over_time({container="demo-app"} |= "ERROR" [5m])`
- Query B: `count_over_time({container="demo-app"} [5m])`
- Use math: A/B * 100

Save as "Application Logs Dashboard".

**✅ Checkpoint:** Dashboard shows log volume, error trends, and live log stream.

---

## 🧹 Cleanup

```bash
docker compose down -v
cd .. && rm -rf logging-lab
```

---

## ✅ Validation

- [ ] Set up Loki + Promtail + Grafana with Docker Compose
- [ ] Ship structured JSON logs from a Python application
- [ ] Query logs using LogQL (stream selectors, filters, JSON parsing)
- [ ] Build a log dashboard with volume, error counts, and live logs
- [ ] Explain the difference between ELK and Loki
- [ ] Explain why structured logging matters for production systems
- [ ] Use `count_over_time()` to aggregate log patterns

---

[← Back to Module README](../README.md) | [Next Lab: ELK Stack →](./lab-02-elk-stack.md)
