# Lab 01: Prometheus + Grafana — Build Your Monitoring Stack

## 🎯 Objective

Set up a complete monitoring stack from scratch using Docker Compose. You'll run Prometheus, Grafana, and Node Exporter, explore PromQL, and build your first dashboard — the exact workflow used in production environments.

---

## 📋 Prerequisites

- Docker and Docker Compose installed (`docker compose version`)
- Completed Module 05 (Docker) and Module 06 (CI/CD)
- A terminal and web browser

---

## 🔬 Exercise 1: Launch the Monitoring Stack

### Step 1: Create the Project Structure

```bash
mkdir -p observability-lab && cd observability-lab
mkdir -p prometheus alertmanager
```

### Step 2: Prometheus Configuration

```bash
cat > prometheus/prometheus.yml << 'CONFIG'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "node-exporter"
    static_configs:
      - targets: ["node-exporter:9100"]
CONFIG
```

### Step 3: Alert Rules

```bash
cat > prometheus/alert_rules.yml << 'RULES'
groups:
  - name: node
    rules:
      - alert: InstanceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Instance {{ $labels.instance }} is down"
          description: "{{ $labels.job }} target {{ $labels.instance }} has been down for more than 1 minute."

      - alert: HighCPU
        expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU on {{ $labels.instance }}"
          description: "CPU usage is above 80% for 5 minutes."

      - alert: HighMemory
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
RULES
```

### Step 4: Alertmanager Configuration

```bash
cat > alertmanager/alertmanager.yml << 'CONFIG'
global:
  resolve_timeout: 5m

route:
  receiver: "default"
  group_by: ["alertname"]
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 1h

receivers:
  - name: "default"
    webhook_configs:
      - url: "http://localhost:5001/"
        send_resolved: true
CONFIG
```

### Step 5: Docker Compose

```bash
cat > docker-compose.yml << 'COMPOSE'
services:
  prometheus:
    image: prom/prometheus:v2.50.0
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=7d"
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

  node-exporter:
    image: prom/node-exporter:v1.7.0
    container_name: node-exporter
    ports:
      - "9100:9100"
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:v0.27.0
    container_name: alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager:/etc/alertmanager
    command:
      - "--config.file=/etc/alertmanager/alertmanager.yml"
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
COMPOSE
```

### Step 6: Launch Everything

```bash
docker compose up -d

# Verify all containers are running
docker compose ps
```

Open in your browser:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (login: admin/admin)
- **Node Exporter**: http://localhost:9100/metrics
- **Alertmanager**: http://localhost:9093

**✅ Checkpoint:** All four services should be running. Prometheus → Status → Targets should show both targets as UP.

---

## 🔬 Exercise 2: Explore PromQL

### Step 1: Open Prometheus UI

Go to http://localhost:9090 → click "Graph" tab.

### Step 2: Run These Queries (One at a Time)

```promql
# 1. Check if targets are up
up

# 2. CPU usage (idle time)
node_cpu_seconds_total{mode="idle"}

# 3. Rate of CPU usage over 5 minutes
rate(node_cpu_seconds_total{mode="idle"}[5m])

# 4. Overall CPU usage percentage
100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 5. Total memory vs available
node_memory_MemTotal_bytes
node_memory_MemAvailable_bytes

# 6. Memory usage percentage
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100

# 7. Disk usage
(node_filesystem_size_bytes{mountpoint="/"} - node_filesystem_avail_bytes{mountpoint="/"}) / node_filesystem_size_bytes{mountpoint="/"} * 100

# 8. Network traffic (bytes received per second)
rate(node_network_receive_bytes_total[5m])

# 9. Prometheus self-monitoring: how many time series?
prometheus_tsdb_head_series

# 10. How many scrapes per second?
rate(prometheus_target_interval_length_seconds_count[5m])
```

For each query, click **Execute**, then switch between **Table** and **Graph** views.

**✅ Checkpoint:** You should see real data from your machine for each query.

---

## 🔬 Exercise 3: Build a Grafana Dashboard

### Step 1: Add Prometheus Data Source

1. Go to http://localhost:3000 (login: admin/admin)
2. Navigate to **Connections** → **Data Sources** → **Add data source**
3. Select **Prometheus**
4. URL: `http://prometheus:9090`
5. Click **Save & Test** — should say "Successfully queried the Prometheus API"

### Step 2: Create a New Dashboard

1. Click **+** → **New Dashboard** → **Add visualization**
2. Select the Prometheus data source

### Step 3: Add Panels (Build Each One)

**Panel 1: CPU Usage (Gauge)**
- Query: `100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
- Visualization: **Gauge**
- Title: "CPU Usage %"
- Set thresholds: Green < 60, Yellow < 80, Red ≥ 80
- Unit: Percent (0-100)

**Panel 2: Memory Usage (Gauge)**
- Query: `(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100`
- Visualization: **Gauge**
- Title: "Memory Usage %"
- Set thresholds: Green < 70, Yellow < 85, Red ≥ 85

**Panel 3: CPU Over Time (Time Series)**
- Query: `100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
- Visualization: **Time series**
- Title: "CPU Usage Over Time"

**Panel 4: Network I/O (Time Series)**
- Query A: `rate(node_network_receive_bytes_total{device!="lo"}[5m])`  — Legend: "Received"
- Query B: `rate(node_network_transmit_bytes_total{device!="lo"}[5m])` — Legend: "Transmitted"
- Title: "Network Traffic"
- Unit: bytes/sec (data rate)

**Panel 5: Disk Usage (Bar Gauge)**
- Query: `(node_filesystem_size_bytes{mountpoint="/"} - node_filesystem_avail_bytes{mountpoint="/"}) / node_filesystem_size_bytes{mountpoint="/"} * 100`
- Visualization: **Bar gauge**
- Title: "Disk Usage %"

### Step 4: Save the Dashboard

1. Click the save icon (top right)
2. Name: "Node Overview"
3. Click **Save**

**✅ Checkpoint:** You should have a 5-panel dashboard showing live system metrics with color-coded thresholds.

---

## 🔬 Exercise 4: Import a Community Dashboard

### Step 1: Import Node Exporter Full Dashboard

1. In Grafana, click **+** → **Import dashboard**
2. Enter dashboard ID: **1860**
3. Click **Load**
4. Select the Prometheus data source
5. Click **Import**

### Step 2: Explore the Dashboard

This is a production-grade dashboard with dozens of panels. Study it:
- How are panels organized into rows?
- What PromQL queries do they use? (Click a panel → Edit to see)
- What template variables are at the top?

**✅ Checkpoint:** The imported dashboard should show live data. Click through the panels and understand the PromQL behind each one.

---

## 🔬 Exercise 5: Check Alert Rules

### Step 1: Verify Alerts in Prometheus

1. Go to http://localhost:9090 → **Alerts**
2. You should see your alert rules: InstanceDown, HighCPU, HighMemory
3. They should all be in **green** (inactive) state

### Step 2: Trigger an Alert (Simulate Failure)

```bash
# Stop node-exporter to trigger InstanceDown alert
docker compose stop node-exporter

# Wait 1-2 minutes, then check Prometheus → Alerts
# InstanceDown should go PENDING → FIRING
```

### Step 3: Check Alertmanager

1. Go to http://localhost:9093
2. You should see the firing alert

### Step 4: Resolve the Alert

```bash
# Restart node-exporter
docker compose start node-exporter

# Wait 1-2 minutes — alert should resolve
```

**✅ Checkpoint:** You triggered an alert, saw it fire in Alertmanager, and resolved it.

---

## 🧹 Cleanup

```bash
docker compose down -v
cd .. && rm -rf observability-lab
```

---

## ✅ Validation

- [ ] Launch Prometheus, Grafana, Node Exporter, and Alertmanager with Docker Compose
- [ ] Verify all targets are UP in Prometheus
- [ ] Run PromQL queries for CPU, memory, disk, and network metrics
- [ ] Build a custom Grafana dashboard with 5 panels (gauges + time series)
- [ ] Import a community dashboard (ID: 1860) and study its queries
- [ ] Trigger and resolve an alert by stopping/starting a service
- [ ] Explain the difference between a counter and a gauge
- [ ] Write a PromQL query for memory usage percentage from memory

---

[← Back to Module README](../README.md) | [Next Lab: Application Monitoring →](./lab-02-application-monitoring.md)
