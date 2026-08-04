# Module 07: Observability — Cheat Sheet

> PromQL pattern library, Prometheus config, and Alertmanager reference. Concepts live in the [module README](./README.md).
> Cross-module daily commands: **[QUICK-REFERENCE.md](../QUICK-REFERENCE.md)**

**Jump to:** [Metric types](#metric-types) · [PromQL basics](#promql-basics) · [Rate & counters](#rates--counters) · [Histograms](#histograms--percentiles) · [Aggregation](#aggregation) · [Pattern library](#the-promql-pattern-library) · [Recording rules](#recording-rules) · [Alert rules](#alerting-rules) · [Alertmanager](#alertmanager) · [Config](#prometheus-configuration) · [Exporters](#exporters--instrumentation) · [Grafana](#grafana) · [Troubleshooting](#troubleshooting)

---

## Metric Types

| Type | Only goes | Use for | Query with |
|------|-----------|---------|------------|
| **Counter** | Up (resets to 0 on restart) | Requests, errors, bytes sent | `rate()`, `increase()` — **never** the raw value |
| **Gauge** | Up and down | Temperature, queue depth, memory in use, replicas | Raw value, `avg_over_time()`, `delta()` |
| **Histogram** | Buckets + `_sum` + `_count` | Request duration, response size | `histogram_quantile()` on `rate(..._bucket[5m])` |
| **Summary** | Client-computed quantiles | Legacy; quantiles that can't be aggregated | Raw quantile labels |

```
# A histogram named http_request_duration_seconds exposes:
http_request_duration_seconds_bucket{le="0.1"}   # cumulative count ≤ 100ms
http_request_duration_seconds_bucket{le="0.5"}
http_request_duration_seconds_bucket{le="+Inf"}  # == _count
http_request_duration_seconds_sum                # total seconds observed
http_request_duration_seconds_count              # number of observations
```

**Naming convention**: `<namespace>_<subsystem>_<name>_<unit>[_total]`
Use base units (seconds, bytes — not ms or MB). Counters end in `_total`.

> ⚠️ **Never use a histogram's `le` quantile as a Summary substitute across instances.** Summaries compute quantiles on the client, so you **cannot** average or aggregate them meaningfully. Histograms can be aggregated — always prefer them for anything you'll graph across replicas.

---

## PromQL Basics

```promql
http_requests_total                                     # instant vector: all series
http_requests_total{job="api"}                          # label equality
http_requests_total{job="api", status="500"}            # multiple labels (AND)
http_requests_total{status!="200"}                      # not equal
http_requests_total{status=~"5.."}                      # ⭐ regex match
http_requests_total{status!~"2..|3.."}                  # regex not-match
http_requests_total{job=~"api|web"}                     # alternation

http_requests_total[5m]                                 # range vector: 5 min of samples
http_requests_total offset 1h                           # value as of 1 hour ago
http_requests_total @ 1690000000                        # at an absolute timestamp

# Comparison and arithmetic
node_memory_MemAvailable_bytes / 1024 / 1024            # → MiB
node_filesystem_avail_bytes / node_filesystem_size_bytes * 100     # → percent
up == 0                                                 # filter: only down targets
node_load1 > 4                                          # threshold filter
node_load1 > bool 4                                     # → 1 or 0 instead of filtering
```

| Operator | Note |
|----------|------|
| `+ - * / % ^` | Arithmetic; matches on identical label sets |
| `== != > < >= <=` | Filters by default; add `bool` to get 0/1 |
| `and` / `or` / `unless` | Set operations on label sets |
| `on(labels)` / `ignoring(labels)` | Control how two vectors are matched |
| `group_left` / `group_right` | Many-to-one joins (e.g. attaching `kube_pod_labels`) |

---

## Rates & Counters

```promql
rate(http_requests_total[5m])            # ⭐ per-second average over 5m. Handles resets.
irate(http_requests_total[5m])           # instantaneous: last two samples only. Spiky.
increase(http_requests_total[1h])        # total increase over 1h (= rate × seconds)

# Requests per second, by endpoint
sum by (endpoint) (rate(http_requests_total[5m]))

# ⭐ Error rate as a percentage — the single most useful query you will write
100 * sum(rate(http_requests_total{status=~"5.."}[5m]))
    / sum(rate(http_requests_total[5m]))

# Per-service error ratio
sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
  / sum by (service) (rate(http_requests_total[5m]))
```

**Range selection rules:**

| Rule | Reason |
|------|--------|
| Range must be **≥ 4× the scrape interval** | `rate()` needs at least 2 samples; 4× tolerates a missed scrape |
| Use `[5m]` with a 15s scrape as the default | Smooth enough to be readable, fast enough to be useful |
| Use `rate()` for graphs and alerts | `irate()` is only for zoomed-in, high-resolution debugging |
| `rate()` **before** `sum()`, never after | `sum(rate(x[5m]))` ✅ — `rate(sum(x)[5m])` is invalid and would hide counter resets |

---

## Histograms & Percentiles

```promql
# p95 latency across everything
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# p99 per endpoint  ⭐ note: 'le' must ALWAYS be in the by() clause
histogram_quantile(0.99,
  sum by (le, endpoint) (rate(http_request_duration_seconds_bucket[5m])))

# Average latency (cheaper, but hides outliers — don't alert on it alone)
rate(http_request_duration_seconds_sum[5m])
  / rate(http_request_duration_seconds_count[5m])

# Apdex-style: what fraction of requests are under 300ms?
sum(rate(http_request_duration_seconds_bucket{le="0.3"}[5m]))
  / sum(rate(http_request_duration_seconds_count[5m]))

# Native histograms (Prometheus 2.40+)
histogram_quantile(0.95, sum(rate(http_request_duration_seconds[5m])))
```

> ⚠️ `histogram_quantile` interpolates **within a bucket**. If your highest finite bucket is `le="1.0"` and real latency is 8s, p99 will report something near 1s and you will believe a lie. Always define buckets that span your real latency range, including a generous top bucket.

---

## Aggregation

```promql
sum(...)        avg(...)       min(...)      max(...)
count(...)      stddev(...)    stdvar(...)
topk(5, ...)    bottomk(5, ...)     quantile(0.9, ...)
count_values("version", build_info)
group by (job) (up)             # existence only, drops the value
```

```promql
sum by (job, instance) (rate(http_requests_total[5m]))       # ⭐ keep these labels
sum without (instance) (rate(http_requests_total[5m]))       # keep everything EXCEPT
topk(5, sum by (pod) (rate(container_cpu_usage_seconds_total[5m])))
count by (job) (up == 1)                                     # healthy targets per job
```

**Over-time functions** (operate on a range vector, per series):

```promql
avg_over_time(node_load1[1h])
max_over_time(node_memory_MemAvailable_bytes[24h])
min_over_time(up[10m])
quantile_over_time(0.95, node_load1[1h])
stddev_over_time(node_load1[1h])
count_over_time(up[1h])                       # how many samples — detects gaps
last_over_time(some_gauge[5m])
present_over_time(up[10m])                    # did this series exist at all?
absent(up{job="critical-api"})                # ⭐ 1 if the series is MISSING
absent_over_time(up{job="batch"}[1h])         # missing for the whole window
changes(process_start_time_seconds[1h])       # ⭐ restart count
resets(http_requests_total[1h])               # counter resets
deriv(node_filesystem_avail_bytes[1h])        # per-second slope of a gauge
predict_linear(node_filesystem_avail_bytes[6h], 4*3600)   # ⭐ value in 4 hours
delta(node_filesystem_avail_bytes[1h])        # gauge change over the window
clamp_max(x, 100)  clamp_min(x, 0)
round(x, 0.01)   ceil(x)   floor(x)   abs(x)
label_replace(up, "host", "$1", "instance", "([^:]+):.*")
```

---

## The PromQL Pattern Library

### Golden signals (RED method — request-driven services)

```promql
# Rate — requests per second
sum by (service) (rate(http_requests_total[5m]))

# Errors — failure ratio
sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
  / sum by (service) (rate(http_requests_total[5m]))

# Duration — p50 / p95 / p99
histogram_quantile(0.50, sum by (le, service) (rate(http_request_duration_seconds_bucket[5m])))
histogram_quantile(0.95, sum by (le, service) (rate(http_request_duration_seconds_bucket[5m])))
histogram_quantile(0.99, sum by (le, service) (rate(http_request_duration_seconds_bucket[5m])))
```

### USE method (resources)

```promql
# CPU utilisation per instance (%)
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory utilisation (%)
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)

# Disk utilisation (%) — exclude pseudo-filesystems
100 * (1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs"}
         / node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs"})

# Disk saturation — time spent doing I/O
rate(node_disk_io_time_seconds_total[5m])

# Network throughput
rate(node_network_receive_bytes_total{device!~"lo|veth.*"}[5m])
rate(node_network_transmit_bytes_total{device!~"lo|veth.*"}[5m])

# Network errors
rate(node_network_receive_errs_total[5m]) + rate(node_network_transmit_errs_total[5m])

# Load average vs core count
node_load1 / count by (instance) (node_cpu_seconds_total{mode="idle"})

# Disk will be full in under 4 hours  ⭐ predictive, not reactive
predict_linear(node_filesystem_avail_bytes{fstype!~"tmpfs"}[6h], 4*3600) < 0

# Inode exhaustion
100 * (1 - node_filesystem_files_free / node_filesystem_files)
```

### Kubernetes (kube-state-metrics + cAdvisor)

```promql
# Pods not ready
sum by (namespace) (kube_pod_status_ready{condition="false"})

# Pods restarting  ⭐ the earliest crash-loop signal
sum by (namespace, pod) (increase(kube_pod_container_status_restarts_total[1h])) > 3

# Container CPU usage vs its request
sum by (pod) (rate(container_cpu_usage_seconds_total{container!=""}[5m]))
  / sum by (pod) (kube_pod_container_resource_requests{resource="cpu"})

# Memory usage vs limit  ⭐ >0.9 predicts an OOMKill
sum by (pod) (container_memory_working_set_bytes{container!=""})
  / sum by (pod) (kube_pod_container_resource_limits{resource="memory"})

# CPU throttling ratio — high values mean the limit is too low
rate(container_cpu_cfs_throttled_periods_total[5m])
  / rate(container_cpu_cfs_periods_total[5m])

# Deployment replicas not matching desired
kube_deployment_status_replicas_available != kube_deployment_spec_replicas

# Nodes not ready
kube_node_status_condition{condition="Ready", status="true"} == 0

# PVC nearly full
100 * (1 - kubelet_volume_stats_available_bytes / kubelet_volume_stats_capacity_bytes) > 85

# Cluster CPU requested vs allocatable
sum(kube_pod_container_resource_requests{resource="cpu"})
  / sum(kube_node_status_allocatable{resource="cpu"})
```

### Availability & meta-monitoring

```promql
up == 0                                              # target down
absent(up{job="payments-api"})                       # ⭐ the JOB itself vanished
changes(process_start_time_seconds[1h]) > 3          # process restarting repeatedly
time() - process_start_time_seconds                  # uptime in seconds
rate(prometheus_target_scrapes_exceeded_sample_limit_total[5m]) > 0    # cardinality blowout
prometheus_tsdb_head_series                          # ⭐ total active series — watch this
topk(10, count by (__name__) ({__name__=~".+"}))     # which metric has the most series
scrape_duration_seconds > 5                          # a slow exporter
rate(prometheus_rule_evaluation_failures_total[5m]) > 0
```

### SLO / error budget

```promql
# 30-day availability
1 - (sum(increase(http_requests_total{status=~"5.."}[30d]))
     / sum(increase(http_requests_total[30d])))

# Error budget remaining, for a 99.9% target
1 - ((1 - (sum(increase(http_requests_total{status=~"5.."}[30d]))
          / sum(increase(http_requests_total[30d])))) / 0.001)

# Multi-window burn rate — page only when the budget is burning fast  ⭐
(
  sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > (14.4 * 0.001)
  and
  sum(rate(http_requests_total{status=~"5.."}[1h])) / sum(rate(http_requests_total[1h])) > (14.4 * 0.001)
)
```

| Burn rate | Budget consumed | Windows | Action |
|-----------|----------------|---------|--------|
| 14.4× | 2% in 1 hour | 5m + 1h | 🔴 Page |
| 6× | 5% in 6 hours | 30m + 6h | 🔴 Page |
| 3× | 10% in 1 day | 2h + 1d | 🟡 Ticket |
| 1× | 10% in 3 days | 6h + 3d | 🟡 Ticket |

---

## Recording Rules

Precompute expensive queries so dashboards and alerts stay fast.

```yaml
# rules/recording.yml
groups:
  - name: http_slos
    interval: 30s
    rules:
      - record: job:http_requests:rate5m
        expr: sum by (job) (rate(http_requests_total[5m]))

      - record: job:http_errors:ratio5m
        expr: |
          sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))
            / sum by (job) (rate(http_requests_total[5m]))

      - record: job:http_latency:p99_5m
        expr: |
          histogram_quantile(0.99,
            sum by (le, job) (rate(http_request_duration_seconds_bucket[5m])))
```

**Naming convention**: `level:metric:operations` — e.g. `job:http_requests:rate5m` means "aggregated to the `job` level, of `http_requests`, as a 5-minute rate."

---

## Alerting Rules

```yaml
groups:
  - name: availability
    rules:
      - alert: TargetDown
        expr: up == 0
        for: 2m
        labels: {severity: critical, team: platform}
        annotations:
          summary: "{{ $labels.job }} target {{ $labels.instance }} is down"
          description: "Scrape has failed for 2 minutes."
          runbook_url: "https://wiki/runbooks/target-down"

      - alert: HighErrorRate
        expr: job:http_errors:ratio5m > 0.05
        for: 10m
        labels: {severity: critical}
        annotations:
          summary: "{{ $labels.job }}: {{ $value | humanizePercentage }} of requests are 5xx"

      - alert: HighLatencyP99
        expr: job:http_latency:p99_5m > 1.5
        for: 10m
        labels: {severity: warning}
        annotations:
          summary: "{{ $labels.job }} p99 is {{ $value | humanizeDuration }}"

      - alert: DiskWillFillIn4Hours
        expr: |
          predict_linear(node_filesystem_avail_bytes{fstype!~"tmpfs"}[6h], 4*3600) < 0
          and node_filesystem_avail_bytes{fstype!~"tmpfs"} / node_filesystem_size_bytes < 0.30
        for: 30m
        labels: {severity: warning}
        annotations:
          summary: "{{ $labels.instance }} {{ $labels.mountpoint }} fills within 4h"

      - alert: PodCrashLooping
        expr: increase(kube_pod_container_status_restarts_total[15m]) > 3
        for: 5m
        labels: {severity: critical}
        annotations:
          summary: "{{ $labels.namespace }}/{{ $labels.pod }} restarted {{ $value }}× in 15m"
```

**Template functions in annotations:** `{{ $value }}` · `{{ $labels.x }}` · `{{ humanize $value }}` · `{{ humanizePercentage $value }}` · `{{ humanizeDuration $value }}` · `{{ printf "%.2f" $value }}` · `{{ $externalLabels.cluster }}`

**Alert design rules:**

| Rule | Why |
|------|-----|
| Alert on **symptoms** (users affected), not causes (CPU is high) | Causes produce noise; symptoms produce action |
| Every alert needs a `runbook_url` | An alert nobody knows how to action is noise |
| Every alert needs a `for:` | Prevents paging on transient spikes |
| Page only for things that are **urgent and actionable** | Everything else is a ticket or a dashboard |
| Include `severity` and routing labels | Alertmanager routes on labels |
| Use `absent()` for "the whole job disappeared" | `up == 0` can't fire if the series is gone entirely |

```bash
promtool check rules rules/*.yml          # ⭐ validate before deploying
promtool check config prometheus.yml
promtool query instant http://localhost:9090 'up == 0'
promtool test rules tests/*.yml           # unit-test your alerts
```

---

## Alertmanager

```yaml
global:
  resolve_timeout: 5m
  slack_api_url_file: /etc/alertmanager/slack_url

route:
  receiver: default
  group_by: [alertname, cluster, namespace]     # ⭐ one notification per group
  group_wait: 30s          # wait for related alerts before the first notification
  group_interval: 5m       # wait before sending updates about an existing group
  repeat_interval: 4h      # re-notify about a still-firing alert
  routes:
    - matchers: [severity="critical"]
      receiver: pagerduty
      continue: true                          # also fall through to the next match
    - matchers: [severity="critical"]
      receiver: slack-critical
    - matchers: [severity="warning"]
      receiver: slack-warnings
      group_wait: 5m
    - matchers: ['namespace=~"dev|test"']
      receiver: 'null'                        # drop non-production noise

inhibit_rules:
  # If the whole node is down, don't also page about every service on it ⭐
  - source_matchers: [alertname="NodeDown"]
    target_matchers: [severity="warning"]
    equal: [instance]

receivers:
  - name: 'null'
  - name: default
    slack_configs: [{channel: '#alerts', send_resolved: true}]
  - name: slack-critical
    slack_configs:
      - channel: '#incidents'
        title: '{{ .Status | toUpper }} {{ .CommonLabels.alertname }}'
        text: >-
          {{ range .Alerts }}{{ .Annotations.summary }}
          <{{ .Annotations.runbook_url }}|runbook>
          {{ end }}
        send_resolved: true
  - name: pagerduty
    pagerduty_configs:
      - routing_key_file: /etc/alertmanager/pd_key
        severity: '{{ .CommonLabels.severity }}'
```

```bash
amtool check-config alertmanager.yml                                    # ⭐ validate
amtool config routes test --config.file=alertmanager.yml severity=critical    # ⭐ which receiver?
amtool config routes show --config.file=alertmanager.yml
amtool alert query                                                      # currently firing
amtool alert query alertname=HighErrorRate
amtool silence add alertname=NoisyAlert --duration=2h --comment "known issue, ticket #42"
amtool silence query
amtool silence expire <silence-id>
```

---

## Prometheus Configuration

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s
  external_labels: {cluster: prod, region: us-east-1}    # added to federated/remote data

rule_files:
  - /etc/prometheus/rules/*.yml

alerting:
  alertmanagers:
    - static_configs: [{targets: ['alertmanager:9093']}]

scrape_configs:
  - job_name: prometheus
    static_configs: [{targets: ['localhost:9090']}]

  - job_name: node
    static_configs:
      - targets: ['node1:9100', 'node2:9100']
        labels: {env: production}

  - job_name: app
    metrics_path: /actuator/prometheus
    scheme: https
    scrape_interval: 30s
    static_configs: [{targets: ['app:8080']}]
    metric_relabel_configs:
      # ⭐ Drop a high-cardinality metric before it ever hits the TSDB
      - source_labels: [__name__]
        regex: 'go_gc_duration_seconds.*'
        action: drop
      # Remove a noisy label
      - regex: 'pod_template_hash'
        action: labeldrop

  - job_name: kubernetes-pods
    kubernetes_sd_configs: [{role: pod}]
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: 'true'
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        target_label: __metrics_path__
        regex: '(.+)'
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        target_label: __address__
        regex: '([^:]+)(?::\d+)?;(\d+)'
        replacement: '$1:$2'
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod

  - job_name: blackbox
    metrics_path: /probe
    params: {module: [http_2xx]}
    static_configs: [{targets: ['https://example.com', 'https://api.example.com']}]
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115
```

```bash
promtool check config prometheus.yml
curl -X POST http://localhost:9090/-/reload      # requires --web.enable-lifecycle
kill -HUP $(pidof prometheus)
```

| Useful flag | Effect |
|-------------|--------|
| `--storage.tsdb.retention.time=30d` | Retention window |
| `--storage.tsdb.retention.size=100GB` | Size cap |
| `--web.enable-lifecycle` | Enables `/-/reload` |
| `--web.enable-admin-api` | Enables deletion endpoints ⚠️ |
| `--query.max-samples` | Guard against runaway queries |

**Useful endpoints:** `/-/healthy` · `/-/ready` · `/-/reload` · `/metrics` · `/api/v1/targets` · `/api/v1/rules` · `/api/v1/status/tsdb` (⭐ cardinality report) · `/api/v1/query?query=up`

---

## Exporters & Instrumentation

| Exporter | Port | Exposes |
|----------|------|---------|
| `node_exporter` | 9100 | Host CPU, memory, disk, network, filesystem |
| `cAdvisor` | 8080 | Container resource usage |
| `kube-state-metrics` | 8080 | Kubernetes object state (not resource usage) |
| `blackbox_exporter` | 9115 | HTTP/TCP/ICMP/DNS probes, TLS expiry |
| `postgres_exporter` | 9187 | PostgreSQL |
| `mysqld_exporter` | 9104 | MySQL |
| `redis_exporter` | 9121 | Redis |
| `nginx-prometheus-exporter` | 9113 | Nginx |
| `pushgateway` | 9091 | Short-lived batch jobs |

```python
# Python instrumentation
from prometheus_client import Counter, Histogram, Gauge, start_http_server

REQUESTS = Counter("http_requests_total", "Total requests", ["method", "endpoint", "status"])
LATENCY  = Histogram("http_request_duration_seconds", "Request duration", ["endpoint"],
                     buckets=[.005,.01,.025,.05,.1,.25,.5,1,2.5,5,10])
INFLIGHT = Gauge("http_requests_inflight", "Requests currently being served")

start_http_server(8000)

@LATENCY.labels(endpoint="/api").time()
@INFLIGHT.track_inprogress()
def handle():
    REQUESTS.labels("GET", "/api", "200").inc()
```

> ⚠️ **Cardinality is the #1 way to kill a Prometheus server.** Total series = product of every label's distinct values. Never use user IDs, request IDs, email addresses, full URLs with parameters, or timestamps as label values. `/api/users/12345` must be recorded as `endpoint="/api/users/:id"`. Watch `prometheus_tsdb_head_series` and set `sample_limit` per scrape job.

---

## Grafana

```bash
# Provisioning (config as code) — put these in the container/host filesystem
/etc/grafana/provisioning/datasources/prometheus.yml
/etc/grafana/provisioning/dashboards/dashboards.yml

# API
curl -s -H "Authorization: Bearer $GRAFANA_TOKEN" http://grafana:3000/api/health
curl -s -H "Authorization: Bearer $GRAFANA_TOKEN" http://grafana:3000/api/search?type=dash-db | jq
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d @dashboard.json http://grafana:3000/api/dashboards/db
```

```yaml
# provisioning/datasources/prometheus.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    jsonData: {timeInterval: "15s"}
```

**Dashboard variables** (the `$var` templating that makes one dashboard serve everything):

```
Query:  label_values(up, job)                        → a dropdown of all jobs
Query:  label_values(up{job="$job"}, instance)       → chained on the previous variable
Query:  label_values(kube_pod_info{namespace="$ns"}, pod)
Regex:  /^prod-(.*)$/                                → strip a prefix from displayed values
Use in a panel:  sum by (pod) (rate(x{job="$job", pod=~"$pod"}[5m]))
```

**Panel tips:** set the **unit** (seconds/bytes/percent) or your axes lie · use `$__rate_interval` instead of a hardcoded `[5m]` so zooming works · legend format `{{pod}}` keeps legends readable · add thresholds matching your alert values so the dashboard and the alert agree.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Target shows `DOWN` | Prometheus can't reach it | Check network/firewall; `curl target:port/metrics` from the Prometheus host |
| `context deadline exceeded` | Exporter slower than `scrape_timeout` | Raise the timeout or fix the exporter |
| Query returns nothing | Wrong metric name or label | Use the metric explorer; `{__name__=~".*part.*"}` |
| `rate()` returns empty | Range shorter than 2 scrape intervals | Use at least 4× the scrape interval |
| Graph is spiky and unreadable | Using `irate()` | Switch to `rate()` |
| Prometheus OOMs / gets slow | Cardinality explosion | `/api/v1/status/tsdb`; drop labels with `metric_relabel_configs` |
| Alert never fires | See the alert-lifecycle flowchart in the [README](./README.md#alert-lifecycle) | Check Rules tab → Alertmanager → silences → routing |
| Alert fires constantly | Threshold too tight, or no `for:` | Add `for:`, alert on symptoms, use burn rates |
| Percentiles look impossibly low | Top histogram bucket is below real latency | Add larger buckets |
| Counter graph looks like a sawtooth | Graphing the raw counter | Wrap it in `rate()` |
| Duplicate series after a redeploy | Churning labels (`pod_template_hash`, pod name) | `labeldrop` them, aggregate away the instance |

---

<div align="center">

[← Module 07 README](./README.md) · [Resources](./resources.md) · [Labs](./labs/) · [Handbook Quick Reference](../QUICK-REFERENCE.md)

</div>
