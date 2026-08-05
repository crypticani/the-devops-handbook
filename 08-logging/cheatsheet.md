# Module 08: Logging — Cheat Sheet

> LogQL, Lucene/KQL, and Elasticsearch query reference. Concepts live in the [module README](./README.md).
> Cross-module daily commands: **[QUICK-REFERENCE.md](../QUICK-REFERENCE.md)**

**Jump to:** [Log levels](#log-levels) · [Structured logging](#structured-logging) · [LogQL](#logql-loki)  · [Lucene & KQL](#lucene--kql-kibana) · [Elasticsearch API](#elasticsearch-api) · [Shippers](#shippers--collectors) · [Local analysis](#local-log-analysis) · [Retention](#retention--cost) · [Troubleshooting](#troubleshooting)

---

## Log Levels

| Level | Use for | Page someone? |
|-------|---------|---------------|
| `TRACE` | Function entry/exit, full payloads | Never — off in production |
| `DEBUG` | Variable state, decision branches | Never — off in production by default |
| `INFO` | Normal lifecycle events: started, connected, request served | No |
| `WARN` | Recovered problems, retries, deprecations, approaching limits | Review in aggregate |
| `ERROR` | An operation failed; a user was affected | Alert on rate, not on individual lines |
| `FATAL` / `CRITICAL` | The process cannot continue and is exiting | Yes |

> 💡 **The test for WARN vs ERROR**: if nobody would ever act on it, it's INFO. If a human must eventually do something, it's WARN. If a request or job actually failed, it's ERROR. Teams that log everything at ERROR end up alerting on nothing.

---

## Structured Logging

```json
{
  "timestamp": "2026-08-04T09:12:44.512Z",
  "level": "error",
  "service": "payments-api",
  "env": "production",
  "version": "1.4.2",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "request_id": "req_01H8X...",
  "user_id": "u_8891",
  "method": "POST",
  "path": "/v1/charges",
  "status": 502,
  "duration_ms": 4310,
  "error": "upstream timeout",
  "upstream": "stripe-gateway"
}
```

| Rule | Why |
|------|-----|
| One JSON object per line (**JSONL**) | Every collector can parse it; multi-line JSON cannot be split reliably |
| **ISO-8601 UTC** timestamps with milliseconds | Sortable, unambiguous across regions |
| Always include `service`, `env`, `version` | Otherwise you can't tell which deploy broke |
| Always include `trace_id` | ⭐ The join key between logs, traces, and metrics |
| Log to **stdout/stderr**, never to a file | The platform (Docker/K8s/systemd) owns collection and rotation |
| Never log secrets, tokens, passwords, card numbers, or full PII | Logs are replicated, indexed, and widely readable |
| Keep field names and types stable | A field that's sometimes a string and sometimes a number breaks Elasticsearch mappings |

```python
# Python — structlog
import structlog
log = structlog.get_logger()
log.info("charge_created", user_id=uid, amount_cents=1999, trace_id=tid)
log.error("upstream_failed", upstream="stripe", status=502, duration_ms=4310)
```

```javascript
// Node — pino
const logger = require('pino')({ level: process.env.LOG_LEVEL || 'info' });
logger.error({ upstream: 'stripe', status: 502, trace_id: tid }, 'upstream_failed');
```

```go
// Go — log/slog (stdlib)
slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))
slog.Error("upstream failed", "upstream", "stripe", "status", 502, "trace_id", tid)
```

---

## LogQL (Loki)

LogQL is "PromQL for logs". Every query starts with a **stream selector** in `{}`.

### Stream selectors (indexed labels — keep these low-cardinality)

```logql
{app="payments-api"}
{app="payments-api", env="production"}
{app=~"payments.*"}                      # regex match
{app!="healthcheck"}
{namespace="prod", container="api"}
```

### Line filters (fast — applied before parsing)

```logql
{app="api"} |= "error"                   # contains
{app="api"} != "healthcheck"             # does not contain
{app="api"} |~ "timeout|refused"         # regex match
{app="api"} !~ "GET /(health|metrics)"   # regex not-match
{app="api"} |= "error" != "expected"     # chained — order matters for speed
```

### Parsers

```logql
{app="api"} | json                                    # parse JSON into labels
{app="api"} | json status="status", dur="duration_ms" # extract specific fields
{app="api"} | logfmt                                  # key=value format
{app="api"} | pattern `<ip> - - <_> "<method> <uri> <_>" <status> <size>`
{app="api"} | regexp `(?P<method>\w+) (?P<path>\S+) (?P<status>\d+)`
{app="api"} | unpack                                  # unwrap promtail-packed labels
```

### Label filters (applied after parsing)

```logql
{app="api"} | json | status >= 500
{app="api"} | json | duration_ms > 1000
{app="api"} | json | level="error" and service="payments"
{app="api"} | json | status =~ "5.."
{app="api"} | json | __error__ = ""                   # ⭐ drop lines that failed to parse
```

### Formatting

```logql
{app="api"} | json | line_format "{{.level}} {{.path}} {{.status}} {{.duration_ms}}ms"
{app="api"} | json | label_format endpoint=`{{ regexReplaceAll "/[0-9]+" .path "/:id" }}`
{app="api"} | json | drop trace_id, span_id
{app="api"} | json | keep level, status, path
```

### Metric queries — turn logs into graphs and alerts

```logql
# Log volume per second
rate({app="api"}[5m])
sum by (level) (rate({app="api"} | json [5m]))

# Error lines per second
sum(rate({app="api"} |= "error" [5m]))

# ⭐ Error ratio from logs
sum(rate({app="api"} | json | status >= 500 [5m]))
  / sum(rate({app="api"} | json [5m]))

# Count over a window
count_over_time({app="api"} |= "OOMKilled" [1h])

# Aggregate a numeric field with unwrap
quantile_over_time(0.95, {app="api"} | json | unwrap duration_ms [5m]) by (endpoint)
avg_over_time({app="api"} | json | unwrap duration_ms [5m])
sum_over_time({app="api"} | json | unwrap bytes_sent [1h])
max_over_time({app="api"} | json | unwrap duration_ms [5m]) by (endpoint)

# Top offenders
topk(10, sum by (path) (count_over_time({app="api"} | json | status >= 500 [1h])))

# Rate of change — spot a sudden error surge
sum(rate({app="api"} |= "ERROR" [5m])) > 10
```

### Alerting on logs

```yaml
groups:
  - name: log-alerts
    rules:
      - alert: ErrorLogSpike
        expr: sum(rate({app="payments-api"} | json | level="error" [5m])) > 5
        for: 5m
        labels: {severity: warning}
        annotations:
          summary: "payments-api is logging {{ $value | printf \"%.1f\" }} errors/sec"

      - alert: OOMKillDetected
        expr: sum(count_over_time({namespace="prod"} |= "OOMKilled" [10m])) > 0
        labels: {severity: critical}
```

```bash
# logcli — query Loki from the terminal
export LOKI_ADDR=http://localhost:3100
logcli query '{app="api"} |= "error"' --limit=100 --since=1h
logcli query '{app="api"}' --tail                      # ⭐ live tail
logcli query 'sum(rate({app="api"}[5m]))' --since=6h
logcli labels                                          # available label names
logcli labels app                                      # values for a label
logcli series '{namespace="prod"}'
```

> ⚠️ **Loki indexes only labels, not log content.** That's why it's cheap — and why putting `request_id` or `user_id` in a *stream label* destroys it. High-cardinality values belong in the log **line** (queried with `|=` and `| json`), never in `{}`.

---

## Lucene & KQL (Kibana)

**KQL** is the modern default in Kibana's search bar. **Lucene** is still used in saved queries and some APIs.

| Goal | KQL | Lucene |
|------|-----|--------|
| Field equals | `status:500` | `status:500` |
| Free text | `"connection refused"` | `"connection refused"` |
| AND / OR / NOT | `status:500 and service:api` | `status:500 AND service:api` |
| Negation | `not status:200` | `NOT status:200` |
| Wildcard | `path:/api/*` | `path:\/api\/*` |
| Range | `duration_ms > 1000` | `duration_ms:[1000 TO *]` |
| Between | `status >= 400 and status < 500` | `status:[400 TO 499]` |
| Field exists | `error:*` | `_exists_:error` |
| Multiple values | `status:(500 or 502 or 503)` | `status:(500 OR 502 OR 503)` |
| Nested field | `kubernetes.pod.name:api-*` | same |
| Escaping | wrap in quotes | escape `+ - && \|\| ! ( ) { } [ ] ^ " ~ * ? : \ /` |

```
# Practical Kibana searches
level:error and kubernetes.namespace:production
status >= 500 and not path:/health
service:payments-api and duration_ms > 3000
message:"connection refused" and not kubernetes.labels.app:test
trace_id:"4bf92f3577b34da6a3ce929d0e0e4736"        # ⭐ pull one request's full story
error:* and @timestamp >= "2026-08-04T09:00:00Z"
```

---

## Elasticsearch API

```bash
ES=http://localhost:9200

# ─── Health and capacity ───
curl -s "$ES/_cluster/health?pretty"
curl -s "$ES/_cat/health?v"
curl -s "$ES/_cat/indices?v&s=store.size:desc"        # ⭐ biggest indices first
curl -s "$ES/_cat/nodes?v&h=name,heap.percent,disk.used_percent,load_1m"
curl -s "$ES/_cat/shards?v&s=state"                   # find UNASSIGNED shards
curl -s "$ES/_cluster/allocation/explain?pretty"      # ⭐ WHY is a shard unassigned
curl -s "$ES/_cat/pending_tasks?v"

# ─── Index management ───
curl -s "$ES/logs-2026.08.04/_mapping?pretty"
curl -s "$ES/logs-2026.08.04/_count?pretty"
curl -X DELETE "$ES/logs-2026.07.*"                   # ⚠️ deletes data
curl -X POST "$ES/logs-2026.08.04/_forcemerge?max_num_segments=1"
curl -X PUT "$ES/logs-*/_settings" -H 'Content-Type: application/json' \
  -d '{"index.number_of_replicas": 1}'
```

### Search

```bash
curl -s "$ES/logs-*/_search?pretty" -H 'Content-Type: application/json' -d '{
  "size": 20,
  "sort": [{"@timestamp": "desc"}],
  "query": {
    "bool": {
      "must":   [{"match": {"message": "timeout"}}],
      "filter": [
        {"term":  {"service.keyword": "payments-api"}},
        {"range": {"status": {"gte": 500}}},
        {"range": {"@timestamp": {"gte": "now-1h"}}}
      ],
      "must_not": [{"term": {"path.keyword": "/health"}}]
    }
  }
}'
```

### Aggregations

```bash
# Top 10 error paths in the last hour
curl -s "$ES/logs-*/_search?pretty" -H 'Content-Type: application/json' -d '{
  "size": 0,
  "query": {"bool": {"filter": [
    {"range": {"status": {"gte": 500}}},
    {"range": {"@timestamp": {"gte": "now-1h"}}}
  ]}},
  "aggs": {
    "by_path": {
      "terms": {"field": "path.keyword", "size": 10, "order": {"_count": "desc"}},
      "aggs": {"p95_latency": {"percentiles": {"field": "duration_ms", "percents": [95]}}}
    }
  }
}'

# Error count over time (date histogram)
curl -s "$ES/logs-*/_search?pretty" -H 'Content-Type: application/json' -d '{
  "size": 0,
  "query": {"term": {"level.keyword": "error"}},
  "aggs": {"over_time": {"date_histogram": {"field": "@timestamp", "fixed_interval": "5m"}}}
}'
```

| Query type | Use |
|------------|-----|
| `term` | Exact match on a keyword field ⭐ use `.keyword` sub-field |
| `match` | Full-text, analysed |
| `match_phrase` | Exact phrase |
| `range` | Numeric or date ranges |
| `wildcard` / `prefix` | Pattern matching (slow — avoid leading wildcards) |
| `exists` | Field is present |
| `bool` | Combine: `must` (scored AND), `filter` (⭐ unscored AND — **cached and faster**), `should` (OR), `must_not` |

### Index Lifecycle Management

```bash
curl -X PUT "$ES/_ilm/policy/logs-policy" -H 'Content-Type: application/json' -d '{
  "policy": {"phases": {
    "hot":    {"actions": {"rollover": {"max_size": "50gb", "max_age": "1d"}}},
    "warm":   {"min_age": "7d",  "actions": {"forcemerge": {"max_num_segments": 1},
                                             "shrink": {"number_of_shards": 1}}},
    "cold":   {"min_age": "30d", "actions": {"freeze": {}}},
    "delete": {"min_age": "90d", "actions": {"delete": {}}}
  }}
}'
```

---

## Shippers & Collectors

| Tool | Best for | Notes |
|------|----------|-------|
| **Promtail** | Loki | Lightweight, Kubernetes-native, label-driven |
| **Filebeat** | Elasticsearch | Low footprint, huge module library |
| **Fluent Bit** | Anything | ⭐ Tiny (C), the usual Kubernetes DaemonSet choice |
| **Fluentd** | Anything | Heavier (Ruby), more plugins |
| **Logstash** | Elasticsearch | Powerful transforms, memory-hungry |
| **Vector** | Anything | ⭐ Fast (Rust), excellent transform language |
| **OpenTelemetry Collector** | Vendor-neutral | Logs + metrics + traces in one agent |

```yaml
# promtail-config.yml — Kubernetes pod discovery
scrape_configs:
  - job_name: kubernetes-pods
    kubernetes_sd_configs: [{role: pod}]
    pipeline_stages:
      - cri: {}                          # parse the container runtime wrapper
      - json:
          expressions: {level: level, msg: message, trace_id: trace_id}
      - labels:
          level:                         # ⭐ ONLY low-cardinality fields become labels
      - timestamp: {source: time, format: RFC3339Nano}
      - output: {source: msg}
    relabel_configs:
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
      - source_labels: [__meta_kubernetes_pod_container_name]
        target_label: container
      - source_labels: [__meta_kubernetes_pod_uid, __meta_kubernetes_pod_container_name]
        target_label: __path__
        separator: /
        replacement: /var/log/pods/*$1/*.log
```

```conf
# fluent-bit.conf
[SERVICE]
    Flush        5
    Log_Level    info
    Parsers_File parsers.conf

[INPUT]
    Name              tail
    Path              /var/log/containers/*.log
    Parser            cri
    Tag               kube.*
    Mem_Buf_Limit     50MB
    Skip_Long_Lines   On
    Refresh_Interval  10

[FILTER]
    Name                kubernetes
    Match               kube.*
    Merge_Log           On
    Keep_Log            Off
    K8S-Logging.Exclude On          # honour a pod annotation to opt out

[OUTPUT]
    Name   es
    Match  *
    Host   elasticsearch
    Port   9200
    Index  logs
    Retry_Limit 5
```

**Collection patterns:**

| Pattern | How | Use when |
|---------|-----|----------|
| **Node agent (DaemonSet)** | One collector per node reads all container logs | ⭐ The default for Kubernetes — one agent, no app changes |
| **Sidecar** | A collector container in each pod | The app insists on writing to a file inside the pod |
| **Direct push** | The app ships logs itself | Rare — couples the app to your logging vendor |

---

## Local Log Analysis

Before you reach for a stack, these get you a long way:

```bash
tail -f /var/log/nginx/access.log
tail -F app.log | grep --line-buffered -i error       # -F survives rotation
journalctl -u myapp -f -p err
docker logs -f --tail 100 container
kubectl logs -f deploy/api --all-containers --since=10m

# Top client IPs
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head

# Status code distribution
awk '{print $9}' access.log | sort | uniq -c | sort -rn

# Slowest requests (if $request_time is the last field)
awk '{print $NF, $7}' access.log | sort -rn | head -20

# Requests per minute
awk '{print substr($4, 2, 17)}' access.log | uniq -c

# Errors in a time window
sed -n '/09:00:00/,/09:15:00/p' app.log | grep -i error

# JSON logs
jq -r 'select(.level=="error") | "\(.timestamp) \(.service) \(.message)"' app.jsonl
jq -r 'select(.duration_ms > 1000) | .path' app.jsonl | sort | uniq -c | sort -rn
jq -s 'group_by(.level) | map({level: .[0].level, count: length})' app.jsonl
jq -r 'select(.trace_id=="4bf92f35...")' app.jsonl     # ⭐ one request's whole story

# Count errors per hour
grep ERROR app.log | awk '{print substr($1,1,13)}' | uniq -c

# Multi-line stack traces
grep -A 20 "Exception" app.log
awk '/^[0-9]{4}-/{p=/ERROR/} p' app.log                # print an entry and its continuation lines

# Compressed archives — no need to decompress
zgrep -i "timeout" /var/log/app.log.*.gz
zcat app.log.1.gz | jq -r 'select(.status >= 500)'
```

### logrotate

```bash
sudo logrotate -d /etc/logrotate.d/myapp        # ⭐ dry run — shows what WOULD happen
sudo logrotate -f /etc/logrotate.d/myapp        # force a rotation now
cat /var/lib/logrotate/status                   # when did each file last rotate
```

```
/var/log/myapp/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 appuser appuser
    sharedscripts
    postrotate
        systemctl reload myapp >/dev/null 2>&1 || true
    endscript
}
```

---

## Retention & Cost

| Lever | Effect |
|-------|--------|
| **Sample high-volume INFO** | Keep 1 in N for chatty success paths; keep 100% of WARN/ERROR |
| **Drop health-check and metrics-scrape lines at the collector** | Often 50%+ of total volume for free |
| **Tier retention** | 7d hot searchable · 30d warm · 90d+ cold object storage |
| **Cap indexed fields** | In Elasticsearch, mapped fields cost storage and memory; in Loki, labels do |
| **Compress and force-merge** older indices | Big storage win, minor query cost |
| **Set per-tenant/per-namespace ingest limits** | Stops one noisy service consuming the whole budget |

```yaml
# Drop noise before it costs you — Fluent Bit
[FILTER]
    Name    grep
    Match   kube.*
    Exclude log  (GET /health|GET /metrics|kube-probe)
```

```logql
# Find what's costing you the most in Loki
topk(10, sum by (app) (rate({namespace="prod"}[5m])))
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No logs appear at all | Collector isn't running, or path mismatch | Check the DaemonSet/agent; verify `__path__` and file permissions |
| Logs stop after a rotation | Agent held the old inode | Use `tail -F` semantics; check the agent's rotation handling |
| Timestamps are wrong / all "now" | Ingest time used instead of the log's own timestamp | Configure the timestamp parser and format |
| Multi-line stack traces split into many entries | No multiline rule | Add a multiline parser keyed on the timestamp pattern |
| Elasticsearch rejects documents | Field-type conflict (`status` string vs number) | Fix at the source; add an index template with explicit mappings |
| `Loki: maximum active stream limit exceeded` | Too many label combinations | Remove high-cardinality labels |
| Loki queries time out | Query span too wide, or too few labels | Narrow the time range; add stream selectors before line filters |
| Kibana shows no data | Wrong index pattern or time range | Check the index pattern and the time picker (very common) |
| Disk fills on the nodes | Container logs not rotated | Set `max-size`/`max-file` in Docker, or `containerLogMaxSize` in kubelet |
| Costs exploding | DEBUG left on in production, or health checks logged | Set `LOG_LEVEL=info`; drop probe traffic at the collector |
| Can't correlate logs with a trace | No `trace_id` in the logs | Propagate and log the trace ID — this is the highest-value single change |

---

<div align="center">

[← Module 08 README](./README.md) · [Resources](./resources.md) · [Labs](./labs/) · [Handbook Quick Reference](../QUICK-REFERENCE.md)

</div>
