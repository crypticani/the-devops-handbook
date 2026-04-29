# Lab 02: Application Monitoring — Instrument Your Own App

## 🎯 Objective

Instrument a Python Flask application with custom Prometheus metrics. You'll implement the RED method (Rate, Errors, Duration), build a service dashboard in Grafana, and create alerting rules — the exact workflow used to monitor production microservices.

---

## 📋 Prerequisites

- Completed Lab 01 (Prometheus + Grafana stack)
- Docker and Docker Compose installed
- Basic Python knowledge (Module 04)

---

## 🔬 Exercise 1: Build an Instrumented Application

### Step 1: Create the Project Structure

```bash
mkdir -p app-monitoring-lab/app && cd app-monitoring-lab
mkdir -p prometheus
```

### Step 2: Create the Flask Application

```bash
cat > app/app.py << 'APP'
import time
import random
from flask import Flask, request, jsonify
from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    generate_latest, CONTENT_TYPE_LATEST
)

app = Flask(__name__)

# ──────────────────────────────────────────────
# METRICS DEFINITIONS (RED Method)
# ──────────────────────────────────────────────

# Rate: Total requests
REQUEST_COUNT = Counter(
    'app_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Duration: Request latency
REQUEST_DURATION = Histogram(
    'app_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Errors: Explicit error counter
ERROR_COUNT = Counter(
    'app_errors_total',
    'Total application errors',
    ['type']
)

# Business metrics
ORDERS_TOTAL = Counter(
    'app_orders_total',
    'Total orders placed',
    ['status']
)

ACTIVE_USERS = Gauge(
    'app_active_users',
    'Number of currently active users'
)

# Initialize active users
ACTIVE_USERS.set(random.randint(10, 50))

# ──────────────────────────────────────────────
# MIDDLEWARE — Auto-instrument all requests
# ──────────────────────────────────────────────

@app.before_request
def before_request():
    request._start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - request._start_time
    endpoint = request.path
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status=response.status_code
    ).inc()
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=endpoint
    ).observe(duration)
    return response

# ──────────────────────────────────────────────
# API ENDPOINTS
# ──────────────────────────────────────────────

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/api/users')
def get_users():
    # Simulate variable latency
    time.sleep(random.uniform(0.01, 0.1))
    users = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Charlie"}
    ]
    return jsonify({"users": users})

@app.route('/api/orders', methods=['POST'])
def create_order():
    time.sleep(random.uniform(0.05, 0.3))

    # Simulate occasional failures (20% chance)
    if random.random() < 0.2:
        ERROR_COUNT.labels(type="order_failed").inc()
        ORDERS_TOTAL.labels(status="failed").inc()
        return jsonify({"error": "Order processing failed"}), 500

    ORDERS_TOTAL.labels(status="success").inc()
    return jsonify({"order_id": random.randint(1000, 9999), "status": "created"}), 201

@app.route('/api/slow')
def slow_endpoint():
    """Intentionally slow — for testing latency alerts."""
    delay = random.uniform(0.5, 3.0)
    time.sleep(delay)
    return jsonify({"message": "Done", "delay": round(delay, 2)})

@app.route('/api/error')
def error_endpoint():
    """Intentionally errors — for testing error alerts."""
    ERROR_COUNT.labels(type="intentional").inc()
    return jsonify({"error": "Something went wrong"}), 500

@app.route('/metrics')
def metrics():
    # Simulate fluctuating active users
    ACTIVE_USERS.set(random.randint(10, 100))
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
APP
```

### Step 3: Create Requirements and Dockerfile

```bash
cat > app/requirements.txt << 'REQ'
flask==3.0.0
prometheus_client==0.20.0
REQ

cat > app/Dockerfile << 'DOCKERFILE'
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN useradd -r appuser
USER appuser
EXPOSE 8080
CMD ["python", "app.py"]
DOCKERFILE
```

### Step 4: Prometheus Config

```bash
cat > prometheus/prometheus.yml << 'CONFIG'
global:
  scrape_interval: 10s
  evaluation_interval: 10s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "flask-app"
    static_configs:
      - targets: ["flask-app:8080"]
    scrape_interval: 5s
CONFIG
```

### Step 5: Alert Rules for the App

```bash
cat > prometheus/alert_rules.yml << 'RULES'
groups:
  - name: flask-app
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(app_http_requests_total{status=~"5.."}[2m]))
          /
          sum(rate(app_http_requests_total[2m]))
          > 0.10
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Error rate above 10%"
          description: "Current error rate: {{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(app_http_request_duration_seconds_bucket[2m])
          ) > 1.0
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency above 1 second"

      - alert: AppDown
        expr: up{job="flask-app"} == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Flask app is down"
RULES
```

### Step 6: Docker Compose

```bash
cat > docker-compose.yml << 'COMPOSE'
services:
  flask-app:
    build: ./app
    container_name: flask-app
    ports:
      - "8080:8080"
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:v2.50.0
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus:/etc/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.3.1
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
    restart: unless-stopped
COMPOSE
```

### Step 7: Launch

```bash
docker compose up -d --build
```

Verify:
- **App**: http://localhost:8080/health → `{"status": "healthy"}`
- **App metrics**: http://localhost:8080/metrics → raw Prometheus metrics
- **Prometheus**: http://localhost:9090 → Targets → flask-app should be UP
- **Grafana**: http://localhost:3000

**✅ Checkpoint:** All services running, `/metrics` endpoint returning counter and histogram data.

---

## 🔬 Exercise 2: Generate Traffic and Explore Metrics

### Step 1: Generate Traffic

```bash
# Hit the app repeatedly in a loop
for i in $(seq 1 100); do
  curl -s http://localhost:8080/api/users > /dev/null
  curl -s -X POST http://localhost:8080/api/orders > /dev/null
  curl -s http://localhost:8080/api/slow > /dev/null
  sleep 0.2
done &

echo "Traffic generator running in background (PID: $!)"
```

### Step 2: Query in Prometheus UI

Go to http://localhost:9090 and run these queries:

```promql
# Total requests (raw counter)
app_http_requests_total

# Request rate per second
rate(app_http_requests_total[2m])

# Request rate grouped by endpoint
sum by (endpoint) (rate(app_http_requests_total[2m]))

# Error rate percentage
sum(rate(app_http_requests_total{status=~"5.."}[2m]))
/
sum(rate(app_http_requests_total[2m]))
* 100

# P95 latency
histogram_quantile(0.95, rate(app_http_request_duration_seconds_bucket[2m]))

# P95 latency per endpoint
histogram_quantile(0.95, sum by (endpoint, le) (rate(app_http_request_duration_seconds_bucket[2m])))

# Order success vs failure rate
rate(app_orders_total[2m])

# Active users (gauge)
app_active_users
```

**✅ Checkpoint:** You can see request rates, error rates, and latency data from your custom metrics.

---

## 🔬 Exercise 3: Build a Service Dashboard in Grafana

### Step 1: Add Data Source

1. Grafana → **Connections** → **Data Sources** → **Add** → **Prometheus**
2. URL: `http://prometheus:9090`
3. **Save & Test**

### Step 2: Create Dashboard with These Panels

**Row 1 — Overview (Stat panels)**

| Panel | Query | Type | Unit |
|-------|-------|------|------|
| Request Rate | `sum(rate(app_http_requests_total[2m]))` | Stat | req/s |
| Error Rate | `sum(rate(app_http_requests_total{status=~"5.."}[2m])) / sum(rate(app_http_requests_total[2m])) * 100` | Stat | % |
| P95 Latency | `histogram_quantile(0.95, rate(app_http_request_duration_seconds_bucket[2m]))` | Stat | seconds |
| Active Users | `app_active_users` | Stat | none |

**Row 2 — Traffic & Errors (Time series)**

| Panel | Query |
|-------|-------|
| Requests by Endpoint | `sum by (endpoint) (rate(app_http_requests_total[2m]))` |
| Errors by Status | `sum by (status) (rate(app_http_requests_total{status=~"[45].."}[2m]))` |

**Row 3 — Latency (Time series)**

| Panel | Query |
|-------|-------|
| Latency Percentiles | P50: `histogram_quantile(0.5, ...)`, P95: `histogram_quantile(0.95, ...)`, P99: `histogram_quantile(0.99, ...)` |
| Orders (success/fail) | `sum by (status) (rate(app_orders_total[2m]))` |

Save the dashboard as "Flask App — RED Metrics".

**✅ Checkpoint:** Dashboard shows live RED metrics from your application.

---

## 🔬 Exercise 4: Trigger Alerts

### Step 1: Generate Error Traffic

```bash
# Hit the error endpoint repeatedly to spike the error rate
for i in $(seq 1 200); do
  curl -s http://localhost:8080/api/error > /dev/null
  sleep 0.1
done
```

### Step 2: Watch the Alert

1. Go to Prometheus → **Alerts**
2. `HighErrorRate` should go from Inactive → **Pending** → **Firing**
3. Wait for the `for: 1m` duration to pass

### Step 3: Generate Slow Traffic

```bash
# Hit the slow endpoint to trigger latency alert
for i in $(seq 1 50); do
  curl -s http://localhost:8080/api/slow > /dev/null &
done
wait
```

Check Prometheus → Alerts for `HighLatency`.

### Step 4: Let it Recover

Stop sending error/slow traffic. Within a few minutes, alerts should resolve.

**✅ Checkpoint:** You triggered HighErrorRate and HighLatency alerts, watched them fire, and saw them resolve.

---

## 🧨 Break It: Debug Scenarios

### Scenario 1: App Goes Down

```bash
docker compose stop flask-app
# Check Prometheus → Targets (flask-app = DOWN)
# Check Alerts → AppDown should fire
docker compose start flask-app
```

### Scenario 2: Metrics Disappear

```bash
# What happens if /metrics endpoint breaks?
# The target stays UP but metrics go stale
# This is different from the app being down!
```

### Scenario 3: Wrong Scrape Target

Edit `prometheus.yml` to point to a wrong port, reload, and observe the target status change.

---

## 🧹 Cleanup

```bash
docker compose down -v
cd .. && rm -rf app-monitoring-lab
```

---

## ✅ Validation

- [ ] Build a Flask app with custom Prometheus metrics (counters, histograms, gauges)
- [ ] Implement request middleware that auto-instruments all endpoints
- [ ] Generate traffic and query custom metrics in PromQL
- [ ] Build a Grafana dashboard with RED metrics (Rate, Errors, Duration)
- [ ] Configure and trigger alert rules (HighErrorRate, HighLatency)
- [ ] Explain why you use `rate()` on counters but not on gauges
- [ ] Describe what high-cardinality labels are and why they're dangerous
- [ ] Debug a "target down" scenario using Prometheus

---

[← Back to Module README](../README.md) | [← Lab 01: Prometheus + Grafana](./lab-01-prometheus-grafana.md)
