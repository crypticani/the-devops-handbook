# Module 08: Logging

> *"Metrics tell you WHAT is broken. Logs tell you WHY." — DevOps Wisdom*

---

## 🎯 Why This Module Matters

Metrics (Module 07) tell you a service has a 5% error rate. Logs tell you **exactly which requests failed and why** — a stack trace, a malformed payload, a database timeout. Without centralized logging, debugging production issues means SSH-ing into individual servers and grep-ing through files — it doesn't scale.

**In real-world DevOps work**, you will:
- Set up centralized logging so all services ship logs to one place
- Use the ELK Stack (Elasticsearch, Logstash, Kibana) for enterprise logging
- Use Loki + Grafana as a lightweight alternative
- Write structured logs that are easy to search and filter
- Correlate logs with metrics to debug production incidents
- Set up log-based alerts for critical errors
- Manage log retention, rotation, and storage costs

---

## 📚 Table of Contents

1. [Why Centralized Logging](#1-why-centralized-logging)
2. [Structured vs Unstructured Logs](#2-structured-vs-unstructured-logs)
3. [Log Levels](#3-log-levels)
4. [The ELK Stack](#4-the-elk-stack)
5. [Loki — Lightweight Alternative](#5-loki--lightweight-alternative)
6. [Log Collection Patterns](#6-log-collection-patterns)
7. [Searching and Analyzing Logs](#7-searching-and-analyzing-logs)
8. [Log-Based Alerting](#8-log-based-alerting)
9. [Common Mistakes and Anti-Patterns](#9-common-mistakes-and-anti-patterns)
10. [Debugging Mindset](#10-debugging-mindset)
11. [Interview Insights](#11-interview-insights)

---

## 1. Why Centralized Logging

### The Problem

```
Without centralized logging:

  Server 1: ssh → tail -f /var/log/app.log
  Server 2: ssh → tail -f /var/log/app.log
  Server 3: ssh → tail -f /var/log/app.log
  ...
  Server 50: 🤯

  "Which server had the error?"
  "The log rotated and the evidence is gone."
  "The container restarted and logs are lost."
```

### The Solution

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Server 1 │  │ Server 2 │  │ Server 3 │
│   logs   │  │   logs   │  │   logs   │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │
     └─────────────┼─────────────┘
                   │
                   ▼
          ┌─────────────────┐
          │  LOG AGGREGATOR │  ← All logs in ONE place
          │  (ELK / Loki)   │
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │  SEARCH & QUERY │  ← Kibana / Grafana
          │  Dashboards     │
          │  Alerts         │
          └─────────────────┘
```

**Benefits:**
- **One place** to search all logs across all services
- **Persistence** — logs survive container restarts and server failures
- **Correlation** — find all logs for a specific request ID across services
- **Alerting** — trigger alerts on error patterns (not just metrics)
- **Compliance** — audit trails, retention policies

---

## 2. Structured vs Unstructured Logs

### Unstructured (Bad for Searching)

```
[2024-01-15 14:23:01] ERROR - Failed to process order #4521 for user john@email.com: connection timeout after 30s
```

### Structured JSON (Good for Searching)

```json
{
  "timestamp": "2024-01-15T14:23:01.234Z",
  "level": "ERROR",
  "service": "order-service",
  "message": "Failed to process order",
  "order_id": 4521,
  "user": "john@email.com",
  "error": "connection timeout",
  "timeout_seconds": 30,
  "trace_id": "abc-123-def-456"
}
```

| Aspect | Unstructured | Structured (JSON) |
|--------|-------------|-------------------|
| **Human readable** | ✅ Easy to read | ❌ Verbose |
| **Machine parseable** | ❌ Regex needed | ✅ Native parsing |
| **Searchable** | ❌ Full-text only | ✅ Filter by any field |
| **Dashboards** | ❌ Hard to aggregate | ✅ Count errors by service |
| **Correlation** | ❌ Manual | ✅ Filter by trace_id |

> 💡 **Rule:** Always use structured logging in production. JSON is the standard.

### Python Structured Logging Example

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "order-service",
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Add extra fields
        for key, value in record.__dict__.items():
            if key.startswith("_") and not key.startswith("__"):
                log_entry[key[1:]] = value
        return json.dumps(log_entry)

# Setup
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("app")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Usage
logger.info("Order created", extra={"_order_id": 4521, "_user": "john@email.com"})
logger.error("Payment failed", extra={"_order_id": 4521, "_error": "card_declined"})
```

---

## 3. Log Levels

```
┌──────────┬────────────────────────────────────────────────────┐
│  LEVEL   │  WHEN TO USE                                      │
├──────────┼────────────────────────────────────────────────────┤
│ DEBUG    │ Detailed diagnostic info. OFF in production.       │
│          │ "Processing item 45 of 100"                        │
├──────────┼────────────────────────────────────────────────────┤
│ INFO     │ Normal operations. Key business events.            │
│          │ "Order #4521 created", "User logged in"            │
├──────────┼────────────────────────────────────────────────────┤
│ WARNING  │ Something unexpected but not broken.               │
│          │ "Retry attempt 2/3", "Cache miss, falling back"    │
├──────────┼────────────────────────────────────────────────────┤
│ ERROR    │ Something failed. Needs attention.                 │
│          │ "Payment failed", "Database connection lost"       │
├──────────┼────────────────────────────────────────────────────┤
│ CRITICAL │ System is unusable. Wake someone up.               │
│          │ "All DB connections exhausted", "Disk full"         │
└──────────┴────────────────────────────────────────────────────┘
```

**Production rules:**
- Default level: **INFO** (captures business events + errors)
- Enable **DEBUG** temporarily for troubleshooting specific issues
- Every **ERROR** should be actionable — if nothing to do, it's a WARNING
- **CRITICAL** should trigger an alert (not just a log)

---

## 4. The ELK Stack

### Architecture

```
          ELK = Elasticsearch + Logstash + Kibana

┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   LOGSTASH   │     │ELASTICSEARCH│     │     KIBANA       │
│              │     │             │     │                  │
│  • Collect   │────▶│  • Store    │◀────│  • Search        │
│  • Parse     │     │  • Index    │     │  • Visualize     │
│  • Transform │     │  • Search   │     │  • Dashboard     │
│  • Ship      │     │             │     │  • Alert         │
└──────┬───────┘     └─────────────┘     └─────────────────┘
       │
       │ collects from
       ▼
┌──────────────────────────────────┐
│  LOG SOURCES                     │
│  • Application logs (stdout)     │
│  • System logs (/var/log/*)      │
│  • Docker container logs         │
│  • Filebeat agents on servers    │
└──────────────────────────────────┘
```

### Component Roles

| Component | Role | Analogy |
|-----------|------|---------|
| **Beats (Filebeat)** | Lightweight log shippers installed on servers | Mail carrier |
| **Logstash** | Ingest, parse, transform, and route logs | Post office (sorting center) |
| **Elasticsearch** | Store and index logs for fast search | Library (indexed catalog) |
| **Kibana** | Search, visualize, and create dashboards | Library computer terminal |

### Filebeat Configuration

```yaml
# filebeat.yml — installed on each server
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/app/*.log
    json.keys_under_root: true     # Parse JSON logs
    json.add_error_key: true

  - type: container
    paths:
      - /var/lib/docker/containers/*/*.log

output.logstash:
  hosts: ["logstash:5044"]
```

### Logstash Pipeline

```ruby
# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  # Parse JSON logs
  if [message] =~ /^\{/ {
    json {
      source => "message"
    }
  }

  # Parse timestamps
  date {
    match => ["timestamp", "ISO8601"]
    target => "@timestamp"
  }

  # Add geoip for access logs
  if [client_ip] {
    geoip {
      source => "client_ip"
    }
  }

  # Drop health check noise
  if [path] == "/health" {
    drop { }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "app-logs-%{+YYYY.MM.dd}"    # Daily index rotation
  }
}
```

---

## 5. Loki — Lightweight Alternative

### Why Loki?

```
ELK:   Full-text indexing → powerful but expensive (RAM, disk, CPU)
Loki:  Label-based indexing → lightweight, cheaper, pairs with Grafana

ELK is like indexing every word in every book in the library.
Loki is like indexing only the book titles and authors — then reading the book when needed.
```

| Aspect | ELK Stack | Loki + Grafana |
|--------|-----------|----------------|
| **Indexing** | Full-text (every word) | Labels only (metadata) |
| **Resource usage** | Heavy (needs lots of RAM) | Lightweight |
| **Query language** | KQL / Lucene | LogQL (similar to PromQL) |
| **Best for** | Enterprise, complex analysis | Cloud-native, Kubernetes |
| **Visualization** | Kibana | Grafana (same as metrics!) |
| **Cost** | Higher | Lower |
| **Setup** | Complex | Simple |

### Loki Architecture

```
┌──────────┐     ┌───────────┐     ┌──────────┐
│ Promtail  │────▶│   LOKI    │◀────│ GRAFANA  │
│ (shipper) │     │ (storage) │     │ (query)  │
└──────────┘     └───────────┘     └──────────┘
```

### LogQL — Querying Loki

```logql
# Stream selector (required) — like Prometheus labels
{job="flask-app"}
{service="order-service", level="ERROR"}

# Filter expressions
{job="flask-app"} |= "error"              # Contains "error"
{job="flask-app"} != "health"              # Does NOT contain "health"
{job="flask-app"} |~ "timeout|connection"  # Regex match

# JSON parsing
{job="flask-app"} | json | status >= 500

# Count errors per minute
count_over_time({job="flask-app", level="ERROR"}[1m])

# Top error messages
topk(5, sum by (message) (count_over_time({level="ERROR"}[1h])))

# Error rate as percentage
sum(rate({level="ERROR"}[5m])) / sum(rate({level=~".+"}[5m])) * 100
```

---

## 6. Log Collection Patterns

### Pattern 1: Sidecar (Kubernetes)

```
┌──────────────────────────┐
│         POD              │
│  ┌──────┐  ┌──────────┐ │
│  │ App  │  │ Promtail  │ │
│  │      │──│ (sidecar) │ │
│  │ logs │  │ ships logs│ │
│  └──────┘  └──────────┘ │
└──────────────────────────┘
```

### Pattern 2: DaemonSet (Kubernetes)

```
Node 1                    Node 2
┌──────────────────┐     ┌──────────────────┐
│ Pod A  Pod B     │     │ Pod C  Pod D     │
│   │      │       │     │   │      │       │
│   └──────┘       │     │   └──────┘       │
│       │          │     │       │          │
│  ┌────▼────┐     │     │  ┌────▼────┐     │
│  │Promtail │     │     │  │Promtail │     │
│  │DaemonSet│     │     │  │DaemonSet│     │
│  └─────────┘     │     │  └─────────┘     │
└──────────────────┘     └──────────────────┘
```

### Pattern 3: Direct stdout (Docker / Compose)

```
Application → stdout/stderr → Docker log driver → Loki/ELK
```

> 💡 **12-Factor App Rule:** Applications should log to **stdout**, never to files. Let the platform handle log collection.

---

## 7. Searching and Analyzing Logs

### Kibana Query Language (KQL)

```
# Simple field search
level: "ERROR"

# Multiple conditions
level: "ERROR" AND service: "order-service"

# Wildcard
message: *timeout*

# Range
response_time: > 1000

# Exclude
NOT path: "/health"

# Combine
level: "ERROR" AND service: "order-service" AND NOT message: *health*
```

### Effective Log Search Strategy

```
Production incident? Follow this order:

1. TIME WINDOW — When did it start?
   Filter: last 30 minutes (or around the alert time)

2. ERROR LEVEL — What's failing?
   Filter: level = ERROR or CRITICAL

3. SERVICE — Which service?
   Filter: service = "order-service"

4. CORRELATION — Trace the request
   Filter: trace_id = "abc-123" (from the error log)
   → See the full journey of the failed request

5. PATTERN — Is it one error or many?
   Visualize: error count over time → spike or constant?

6. ROOT CAUSE — What changed?
   Compare: logs before and after the incident started
```

---

## 8. Log-Based Alerting

### When to Alert on Logs vs Metrics

```
USE METRICS ALERTS for:
  ✅ Error rate above threshold
  ✅ Latency above threshold
  ✅ Resource usage (CPU, memory)

USE LOG ALERTS for:
  ✅ Specific error messages ("database connection pool exhausted")
  ✅ Security events ("unauthorized access attempt")
  ✅ Business events ("payment processor returned fraud_detected")
  ✅ Patterns that don't have metrics
```

### Loki Alert Rules

```yaml
# loki-alert-rules.yml
groups:
  - name: log-alerts
    rules:
      - alert: HighErrorLogRate
        expr: |
          sum(rate({level="ERROR"}[5m])) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "More than 10 error logs per second"

      - alert: DatabaseConnectionError
        expr: |
          count_over_time({level="ERROR"} |= "connection pool exhausted" [5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool exhausted"
```

---

## 9. Common Mistakes and Anti-Patterns

### ❌ Logging Sensitive Data

```python
# BAD: PII in logs (violates GDPR, security risk)
logger.info(f"User logged in: email={email}, password={password}, ssn={ssn}")

# GOOD: Redact sensitive fields
logger.info("User logged in", extra={"_user_id": user.id, "_email": mask(email)})
```

### ❌ Logging Too Much

```
BAD:  500GB/day of DEBUG logs → expensive storage, slow searches, noise
GOOD: INFO level in production, DEBUG only when troubleshooting
RULE: Every log line should serve a purpose. If nobody reads it, remove it.
```

### ❌ No Correlation IDs

```python
# BAD: Can't trace a request across services
logger.error("Payment failed")

# GOOD: trace_id links logs across all services
logger.error("Payment failed", extra={"_trace_id": request_id, "_order_id": order.id})
```

### ❌ Unstructured Logs in Production

```
# BAD: Good luck parsing this with regex
print(f"ERROR: order {order_id} failed because {reason} at {time}")

# GOOD: JSON, parsed automatically by ELK/Loki
logger.error("Order failed", extra={"_order_id": order_id, "_reason": reason})
```

---

## 10. Debugging Mindset

### Logs + Metrics = Full Picture

```
Alert fires: "High error rate on order-service"
│
├─ 1. METRICS (Grafana) — WHAT is happening?
│     └─ Error rate spiked from 0.1% to 12% at 14:15
│
├─ 2. LOGS (Kibana/Grafana) — WHY is it happening?
│     ├─ Filter: service=order-service, level=ERROR, time=14:15-now
│     ├─ Pattern: "Connection refused to payment-service:8080"
│     └─ Root cause: payment-service is down
│
├─ 3. CORRELATE — Trace a single request
│     ├─ Find a trace_id from the error log
│     ├─ Search all services for that trace_id
│     └─ See the full request path: API → order → payment (FAILED)
│
└─ 4. FIX
      ├─ Restart payment-service (immediate fix)
      └─ Add circuit breaker + retry logic (long-term fix)
```

---

## 11. Interview Insights

**Q: What's the ELK Stack and when would you use it?**
> ELK is Elasticsearch (search/storage), Logstash (ingest/transform), and Kibana (visualization). Use it for centralized logging in production — it lets you search and analyze logs from all services in one place. Filebeat ships logs from servers to Logstash, which parses and sends them to Elasticsearch for indexing. Kibana provides the UI for searching and dashboarding.

**Q: How does Loki differ from Elasticsearch?**
> Elasticsearch indexes the full text of every log line — powerful but expensive in resources. Loki indexes only labels (metadata like service name, level) and stores the log content as compressed chunks. This makes Loki much cheaper to run but less flexible for ad-hoc full-text searches. Loki is ideal for cloud-native environments, especially alongside Prometheus and Grafana.

**Q: What is structured logging and why does it matter?**
> Structured logging means logs are in a parseable format (usually JSON) with consistent fields. This enables machine parsing, filtering by any field, aggregation, and dashboarding. Unstructured text logs require regex parsing which is fragile and slow. In production with thousands of log lines per second, structured logs are essential for debugging.

**Q: How do you handle log volume in production?**
> Set appropriate log levels (INFO in prod, DEBUG only when needed). Drop noisy logs (health checks) in the pipeline. Use sampling for high-traffic services. Set retention policies (keep 7-30 days depending on compliance). Use index lifecycle management in Elasticsearch. Monitor log storage costs.

**Q: How do you correlate logs across microservices?**
> Use a correlation/trace ID. When a request enters the system, generate a unique ID and pass it through every service via HTTP headers. Each service includes this ID in every log line. To debug a failed request, search for its trace ID to see the full journey across all services.

---

## ➡️ What's Next?

With observability (metrics) and logging in place, you can now see and debug your systems. Next, you'll learn cloud fundamentals before automating infrastructure.

**[Module 09: Cloud Fundamentals →](../09-cloud-fundamentals/)**

---

<div align="center">

**Module 08 Complete** ✅

[← Back to Observability](../07-observability/) | [Next: Cloud Fundamentals →](../09-cloud-fundamentals/)

</div>
