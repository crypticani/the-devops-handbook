# Lab 01: Prometheus + Grafana — Build Your Monitoring Stack

## 🎯 Objective

Set up a complete monitoring stack from scratch using Docker Compose. You'll run Prometheus, Grafana, and Node Exporter, explore PromQL, and build your first dashboard — the exact workflow used in production environments.

---

## 📋 Prerequisites

- Docker and Docker Compose installed (`docker compose version`)
- Completed Module 05 (Docker) and Module 06 (CI/CD)
- A terminal and web browser

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Commands you ran and the important output you used for validation
- Any files, scripts, configs, manifests, or workflows you created
- A short failure note describing one thing that broke, how you diagnosed it, and how you fixed it
- Cleanup commands or confirmation that no long-running resources remain

Treat the validation section as the minimum proof that the lab worked.

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

## 🧨 Break It: Four Monitoring Failures

Exercise 5 broke a *target* on purpose. These four break the **monitoring system itself** — the failure mode nobody notices until an outage happens and no alert fires.

### Scenario 1: The Target That Vanishes Silently

**Break it:**

```bash
cd observability-lab

# Rename the node-exporter service so Prometheus can no longer resolve it
docker compose stop node-exporter
docker compose rm -f node-exporter
```

Now open Prometheus → **Status → Targets**.

**Symptom:** The `node-exporter` target shows `DOWN` with `dial tcp: lookup node-exporter: no such host`. Your `InstanceDown` alert fires — good. But now try this:

```bash
# Remove the job from the config entirely — as if someone "cleaned up" prometheus.yml
cp prometheus/prometheus.yml prometheus/prometheus.yml.bak
python3 - <<'EOF'
import pathlib
p = pathlib.Path("prometheus/prometheus.yml")
s = p.read_text()
s = s.split('  - job_name: "node-exporter"')[0]
p.write_text(s)
EOF

docker compose restart prometheus
sleep 20
```

Check Prometheus → **Alerts** again.

**Symptom:** `InstanceDown` is **green/inactive**. Everything looks healthy. The host is not being monitored at all and nothing tells you.

**Investigate:**

```bash
# The series simply doesn't exist any more:
curl -s 'http://localhost:9090/api/v1/query?query=up{job="node-exporter"}' | jq '.data.result'
# []   ← empty. `up == 0` cannot match a series that isn't there.
```

**Root cause:** `up == 0` can only fire for targets Prometheus **knows about**. Delete the scrape job, mistype a label, or lose service discovery, and the alert goes quiet rather than firing. This is the single most dangerous gap in naive alerting.

**Fix — assert that the job must exist:**

```yaml
- alert: NodeExporterJobMissing
  expr: absent(up{job="node-exporter"})
  for: 5m
  labels: {severity: critical}
  annotations:
    summary: "The node-exporter scrape job has disappeared from Prometheus"
    description: "No `up` series exists for job=node-exporter. Monitoring is blind."
```

```bash
mv prometheus/prometheus.yml.bak prometheus/prometheus.yml
docker compose up -d node-exporter && docker compose restart prometheus
```

> 💡 Pair **every** critical job with an `absent()` alert. Also add a dead-man's switch: an alert that fires *constantly* and routes to a receiver that pages you when it **stops** arriving — that's how you detect Prometheus itself being down.

---

### Scenario 2: The Alert That Never Fires

**Break it:**

```bash
# Add a rule with a for: longer than the condition ever lasts
cat >> prometheus/alert_rules.yml <<'RULES'
      - alert: BrieflyHighCPU
        expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 50
        for: 30m
        labels: {severity: warning}
        annotations:
          summary: "CPU above 50% for 30 minutes"
RULES

docker compose restart prometheus && sleep 15

# Generate a 60-second CPU spike
docker run --rm -d --name spike alpine sh -c 'for i in $(seq 1 4); do while :; do :; done & done; sleep 60'
```

Watch Prometheus → **Alerts** while it runs.

**Symptom:** `BrieflyHighCPU` goes to **PENDING**, then drops straight back to **INACTIVE** when the spike ends. It never reaches FIRING, and nobody is ever notified.

**Investigate:**

```bash
# Confirm the condition WAS true — query the expression directly
curl -sG 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)' | jq '.data.result[].value'
```

Prometheus → **Status → Rules** shows the rule's state and how long it has held.

**Root cause:** `for: 30m` requires the expression to be continuously true for 30 minutes. A 60-second spike can never satisfy it. This is often *correct* behaviour — it's what stops transient blips paging you — but here the rule can never fire for the condition it claims to detect.

**Fix:** match `for:` to the duration you actually care about, and use the multi-window burn-rate pattern when you want both fast detection and low noise:

```yaml
# Fast burn: page quickly on a severe problem
- alert: CPUCriticallyHigh
  expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90
  for: 5m
# Slow burn: ticket on sustained pressure
- alert: CPUSustainedHigh
  expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[30m])) * 100) > 70
  for: 30m
```

```bash
docker rm -f spike 2>/dev/null
```

---

### Scenario 3: The Alert Fires But Nobody Is Told

**Break it:**

```bash
# Point a route at a receiver that doesn't exist
cp alertmanager/alertmanager.yml alertmanager/alertmanager.yml.bak 2>/dev/null || true
docker compose restart alertmanager
docker compose stop node-exporter          # trigger InstanceDown again
sleep 90
```

**Symptom:** Prometheus → Alerts shows `InstanceDown` **FIRING**. Alertmanager's UI shows nothing, or shows the alert but no notification is delivered.

**Investigate — walk the chain in order:**

```bash
# 1. Is Prometheus even talking to Alertmanager?
curl -s http://localhost:9090/api/v1/alertmanagers | jq
#    activeAlertmanagers should be non-empty

# 2. Did the alert reach Alertmanager?
curl -s http://localhost:9093/api/v2/alerts | jq '.[].labels'

# 3. Is it silenced?
curl -s http://localhost:9093/api/v2/silences | jq '.[] | {id, status, matchers}'

# 4. Which receiver would these labels route to?
docker compose exec alertmanager amtool config routes test \
  --config.file=/etc/alertmanager/alertmanager.yml severity=critical

# 5. Is the receiver itself failing?
docker compose logs alertmanager | grep -iE 'error|failed|notify'
```

**Root cause:** There are five independent places an alert dies between "condition true" and "human notified": Prometheus→Alertmanager connectivity, grouping delay, silences, inhibition rules, and route/receiver configuration. Each is silent.

**Fix — test routing *before* you need it, and monitor the notifier:**

```bash
amtool config routes test --config.file=alertmanager.yml severity=critical team=platform
amtool alert add alertname=TestPage severity=critical --alertmanager.url=http://localhost:9093
```

```yaml
- alert: AlertmanagerNotificationsFailing
  expr: rate(alertmanager_notifications_failed_total[5m]) > 0
  for: 5m
  labels: {severity: critical}
```

```bash
docker compose start node-exporter
```

---

### Scenario 4: Cardinality Explosion

**Break it:**

```bash
# Simulate a bad label choice: a unique label value per request
docker run -d --name cardinality-bomb --network observability-lab_default -p 9999:9999 \
  python:3.12-slim sh -c 'pip -q install prometheus_client && python -c "
from prometheus_client import Counter, start_http_server
import time, uuid
c = Counter(\"requests_total\", \"reqs\", [\"request_id\"])   # ❌ unbounded label
start_http_server(9999)
while True:
    c.labels(request_id=str(uuid.uuid4())).inc()
    time.sleep(0.01)
"'

# Point Prometheus at it
cat >> prometheus/prometheus.yml <<'CFG'

  - job_name: "cardinality-bomb"
    scrape_interval: 5s
    static_configs:
      - targets: ["cardinality-bomb:9999"]
CFG
docker compose restart prometheus
sleep 120
```

**Symptom:** Prometheus memory climbs steadily. Queries slow down. Eventually the container is OOMKilled.

**Investigate:**

```bash
# ⭐ Total active series — the number to watch
curl -s 'http://localhost:9090/api/v1/query?query=prometheus_tsdb_head_series' | jq -r '.data.result[0].value[1]'

# ⭐ The built-in cardinality report — which metric and which LABEL is to blame
curl -s http://localhost:9090/api/v1/status/tsdb | jq '{
  topSeriesCountByMetricName: .data.seriesCountByMetricName[:5],
  topLabelValueCountByLabelName: .data.labelValueCountByLabelName[:5]
}'

docker stats --no-stream prometheus
```

**Root cause:** Every unique combination of label values creates a **separate time series**, each with its own memory and index cost. A `request_id` label with 100k distinct values creates 100k series from a single metric. Other classic offenders: user IDs, email addresses, full URLs with query strings, timestamps, and Kubernetes `pod_template_hash` across frequent redeploys.

**Fix — bound the label values, and enforce a limit at the scrape:**

```yaml
scrape_configs:
  - job_name: "app"
    sample_limit: 10000            # ⭐ refuse a scrape that returns more than this
    label_limit: 30
    static_configs: [{targets: ["app:8080"]}]
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: 'requests_total'
        action: drop               # or labeldrop the offending label:
      - regex: 'request_id|user_id|pod_template_hash'
        action: labeldrop
```

In the application, normalise before you label: `/api/users/12345` must be recorded as `endpoint="/api/users/:id"`.

```yaml
# Alert on your own cardinality growth
- alert: PrometheusCardinalityGrowing
  expr: prometheus_tsdb_head_series > 500000
  for: 30m
  labels: {severity: warning}
```

```bash
docker rm -f cardinality-bomb
python3 - <<'EOF'
import pathlib
p = pathlib.Path("prometheus/prometheus.yml")
p.write_text(p.read_text().split('  - job_name: "cardinality-bomb"')[0])
EOF
docker compose restart prometheus
```

---

### What You Should Now Be Able to Say

| Failure | How you detect it |
|---------|-------------------|
| A monitored target silently disappears | `absent(up{job="..."})` on every critical job |
| Prometheus itself is down | Dead-man's-switch alert + external uptime check |
| An alert can never fire | Review `for:` against the real event duration; check Status → Rules |
| An alert fires but nobody is paged | `amtool config routes test`; alert on `alertmanager_notifications_failed_total` |
| Prometheus is about to OOM | Watch `prometheus_tsdb_head_series`; `/api/v1/status/tsdb` names the culprit |

> ⭐ **The meta-lesson**: monitoring is a system like any other, and it fails silently by default. "No alerts fired" and "nothing is wrong" are not the same statement. Every one of these five rows is a check on your monitoring, not on your application.

**Write this up** in `failure-notes.md`: symptom, the exact command that revealed it, root cause, fix.

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


## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- Docker Compose file for the monitoring stack
- Prometheus configuration (prometheus.yml) and alert rules
- Screenshot or JSON export of your Grafana dashboard
- PromQL queries you wrote with explanations

---

[← Back to Module README](../README.md) | [Next Lab: Application Monitoring →](./lab-02-application-monitoring.md)
