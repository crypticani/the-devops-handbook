# Lab 01: Loki + Grafana — Centralized Logging with Docker Compose

## 🎯 Objective

Set up a centralized logging stack using Grafana Loki, Promtail, and Grafana. You'll ship application logs, learn LogQL, and build log dashboards — the modern, lightweight approach used in cloud-native environments.

---

## 📋 Prerequisites

- Docker and Docker Compose installed
- Completed Module 07 (Observability)

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Commands you ran and the important output you used for validation
- Any files, scripts, configs, manifests, or workflows you created
- A short failure note describing one thing that broke, how you diagnosed it, and how you fixed it
- Cleanup commands or confirmation that no long-running resources remain

Treat the validation section as the minimum proof that the lab worked.

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

## 🧨 Break It: Four Ways Centralised Logging Fails

The stack works. Now find out how it stops working — and, more importantly, how it stops working **quietly**.

### Scenario 1: The Cardinality Bomb (Loki's Cardinal Sin)

**Break it:**

```bash
cd logging-lab

# Promote a high-cardinality field to a STREAM LABEL — the classic Loki mistake
cp promtail/promtail-config.yml promtail/promtail-config.yml.bak
cat > promtail/promtail-config.yml <<'CONFIG'
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
    pipeline_stages:
      - json:
          expressions:
            request_id: request_id
            user_id: user_id
      - labels:
          request_id:        # ❌ a NEW STREAM for every single request
          user_id:           # ❌ and another dimension on top
CONFIG

docker compose restart promtail
# Generate traffic for a minute
for i in $(seq 1 300); do curl -s localhost:8080/ >/dev/null; done
sleep 30
```

**Symptom:** Queries get slow, then Promtail logs start showing
`server returned HTTP status 429 Too Many Requests ... per-user streams limit exceeded`.
Logs are being **dropped**, and the only place that says so is Promtail's own output.

**Investigate:**

```bash
# ⭐ How many distinct streams have you created?
curl -s 'http://localhost:3100/loki/api/v1/labels' | jq
curl -s 'http://localhost:3100/loki/api/v1/label/request_id/values' | jq '.data | length'

# Promtail is telling you it is dropping data
docker compose logs promtail | grep -iE '429|limit|error' | tail -20

# Loki's own metrics
curl -s http://localhost:3100/metrics | grep -E 'loki_ingester_memory_streams|discarded_samples'
```

**Root cause:** Loki indexes **only stream labels**, not log content. That's what makes it cheap. Every unique label-value combination is a separate stream with its own index entry and chunk. `request_id` with 10,000 values creates 10,000 streams.

**Fix — labels are for low-cardinality dimensions only:**

```yaml
pipeline_stages:
  - json:
      expressions:
        level: level
        request_id: request_id      # extracted, but NOT promoted to a label
  - labels:
      level:                        # ✅ ~5 possible values
```

Query the high-cardinality field from the **line** instead — this is fast and free:

```logql
{container="demo-app"} | json | request_id = "abc-123"
```

| Good stream label | Bad stream label |
|-------------------|------------------|
| `container`, `namespace`, `app`, `env`, `level`, `stream` | `request_id`, `user_id`, `trace_id`, `ip`, `path` with IDs, timestamps |

```bash
mv promtail/promtail-config.yml.bak promtail/promtail-config.yml
docker compose restart promtail
```

---

### Scenario 2: Every Log Line Has the Same Timestamp

**Break it:**

```bash
# Stop shipping for a while, then let Promtail catch up in one burst
docker compose stop promtail
for i in $(seq 1 100); do curl -s localhost:8080/ >/dev/null; done
sleep 60
docker compose start promtail
sleep 20
```

Now in Grafana Explore, query `{container="demo-app"}` over the last 15 minutes.

**Symptom:** A minute's worth of activity appears compressed into a few seconds — all at the moment Promtail restarted, not when the events happened. Correlating with a metrics spike becomes impossible.

**Investigate:**

```bash
# Compare the app's own timestamp with the ingest timestamp
docker compose logs --tail 5 demo-app          # what the app wrote
curl -sG 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={container="demo-app"}' --data-urlencode 'limit=5' \
  | jq -r '.data.result[0].values[][0]'        # nanosecond ingest timestamps
```

**Root cause:** Without a `timestamp` pipeline stage, Loki stamps each entry with the time it was **received**, not the time in the log line. Any shipping delay — a restart, backpressure, a network blip — rewrites your history.

**Fix:**

```yaml
pipeline_stages:
  - json:
      expressions:
        ts: timestamp
        level: level
  - timestamp:
      source: ts
      format: RFC3339Nano       # or: Unix, UnixMs, "2006-01-02 15:04:05"
      action_on_failure: fudge  # skip | fudge — never silently use ingest time
  - labels:
      level:
```

> ⚠️ Out-of-order writes used to be rejected outright by Loki. Modern versions accept them, but entries older than the configured `reject_old_samples_max_age` are still **dropped**. A collector that catches up after a long outage can silently lose the oldest data.

---

### Scenario 3: The Stack Runs Out of Disk

**Break it:**

```bash
# Watch what the log volume is actually doing to disk
docker system df -v | grep -A3 "Local Volumes"
docker compose exec loki du -sh /loki 2>/dev/null || docker compose exec loki df -h /loki

# Now flood it
for i in $(seq 1 5000); do curl -s localhost:8080/ >/dev/null & done; wait
sleep 30
docker compose exec loki df -h /loki
```

**Symptom:** On a real host this ends as `no space left on device`. Loki stops accepting writes, Promtail buffers then drops, and — the part that hurts — **Docker's own JSON log files on the host grow without bound at the same time**, because container logs are written to disk *before* Promtail ever reads them.

**Investigate:**

```bash
# ⭐ The container log files themselves — often the real culprit
sudo du -sh /var/lib/docker/containers/*/*-json.log 2>/dev/null | sort -h | tail -5

# Which stream is the noisiest?
curl -sG 'http://localhost:3100/loki/api/v1/query' \
  --data-urlencode 'query=topk(5, sum by (container) (count_over_time({container=~".+"}[5m])))' | jq '.data.result'
```

**Root cause:** Two independent unbounded stores — Docker's per-container JSON log files, and Loki's chunk storage. Neither has a limit by default.

**Fix — cap both:**

```yaml
# compose.yaml — for EVERY service
services:
  demo-app:
    logging:
      driver: json-file
      options: {max-size: "10m", max-file: "3"}    # ⭐ 30 MB ceiling per container
```

```yaml
# loki-config.yml — retention
limits_config:
  retention_period: 168h            # 7 days
  ingestion_rate_mb: 8
  ingestion_burst_size_mb: 16
  max_streams_per_user: 5000        # ⭐ backstop against Scenario 1
compiler:
  working_directory: /loki/compactor
compactor:
  retention_enabled: true
  delete_request_store: filesystem
```

Then drop the noise you never read, at the collector — usually the single biggest saving:

```yaml
pipeline_stages:
  - drop:
      expression: '.*(GET /health|GET /metrics|kube-probe).*'
```

---

### Scenario 4: A Query That Kills the Server

**Break it:**

```bash
# No stream selector narrowing, huge time range, regex over every line
time curl -sG 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={container=~".+"} |~ ".*"' \
  --data-urlencode 'start='$(date -d '7 days ago' +%s)000000000 \
  --data-urlencode 'end='$(date +%s)000000000 \
  --data-urlencode 'limit=5000' | head -c 300
```

**Symptom:** The query hangs, then returns `maximum of series (500) reached for a single query` or times out. Loki's memory spikes. In Grafana this appears as a dashboard panel that spins forever and takes the rest of the dashboard down with it.

**Investigate:**

```bash
docker compose logs loki | grep -iE 'query|limit|timeout' | tail -20
docker stats --no-stream loki
```

**Root cause:** LogQL executes left to right. `{container=~".+"}` selects **every stream**, then `|~ ".*"` decompresses and regex-scans every line in all of them. Loki has no content index to help — narrowing must come from the stream selector.

**Fix — narrow before you filter, and filter cheaply first:**

```logql
# ❌ scans everything
{container=~".+"} |~ "timeout"

# ✅ narrow the streams, then use a cheap line filter before any parsing
{container="demo-app", level="error"} |= "timeout" | json | status >= 500
```

| Cost | Operation | Rule |
|------|-----------|------|
| Cheapest | `{label="value"}` stream selector | Always be as specific as possible |
| Cheap | `\|=` `!=` line filter (substring) | Put these **before** parsers |
| Moderate | `\|~` `!~` regex line filter | Anchor the regex; avoid `.*` |
| Expensive | `\| json` `\| logfmt` parser | Only after filtering |
| Most expensive | label filters on parsed fields | Last in the chain |

Set server-side guardrails so one bad dashboard panel can't take the stack down:

```yaml
limits_config:
  max_query_length: 721h
  max_query_parallelism: 32
  max_entries_limit_per_query: 5000
  max_query_series: 500
query_range:
  parallelise_shardable_queries: true
```

---

### Summary

| Failure | Detection | Prevention |
|---------|-----------|------------|
| Cardinality explosion | `loki_ingester_memory_streams`, Promtail 429s | Only low-cardinality stream labels |
| Wrong timestamps | Logs cluster at ingest time | `timestamp:` pipeline stage |
| Disk exhaustion | `df`, container JSON log sizes | `max-size`/`max-file` **and** Loki retention |
| Query kills the server | Slow panels, Loki OOM | Narrow selectors first; server-side query limits |

> ⭐ **The recurring theme**: logging systems fail by **dropping data silently**. Promtail logs its own 429s, Loki logs its own rejections — but nothing in Grafana tells you a gap exists. Monitor your logging pipeline with metrics (Module 07), and alert on `promtail_dropped_entries_total` and `loki_discarded_samples_total`.

**Write this up** in `failure-notes.md`.

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


## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- Docker Compose file for the Loki + Grafana stack
- LogQL queries you wrote with sample output
- Screenshot or JSON export of your log dashboard
- Notes on log label design decisions

---

[← Back to Module README](../README.md) | [Next Lab: ELK Stack →](./lab-02-elk-stack.md)
