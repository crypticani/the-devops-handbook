# Lab 02: ELK Stack — Enterprise Logging with Elasticsearch, Logstash, and Kibana

## 🎯 Objective

Set up the ELK Stack (Elasticsearch, Logstash, Kibana) with Filebeat using Docker Compose. You'll ingest logs, create Logstash pipelines, search with KQL in Kibana, and build visualizations — the enterprise-standard logging stack.

---

## 📋 Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available for Docker
- Completed Lab 01 (Loki)

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Commands you ran and the important output you used for validation
- Any files, scripts, configs, manifests, or workflows you created
- A short failure note describing one thing that broke, how you diagnosed it, and how you fixed it
- Cleanup commands or confirmation that no long-running resources remain

Treat the validation section as the minimum proof that the lab worked.

---

## 📂 Lab Files

Every file this lab creates also exists as a real, CI-validated file in
[`../code/lab-02/`](../code/lab-02/) (6 files).

```bash
# Option A — type them out yourself (recommended the first time; that's the learning)
# Option B — start from the reference copies
cp -r /path/to/the-devops-handbook/08-logging/code/lab-02/. .
```

Use Option B when you're comparing against a known-good version, or when something
won't start and you need to rule out a typo. See [`../code/README.md`](../code/README.md).

---

## 🔬 Exercise 1: Launch the ELK Stack

### Step 1: Create Project

```bash
mkdir -p elk-lab/{logstash/pipeline,filebeat,app} && cd elk-lab
```

### Step 2: Logstash Pipeline

```bash
cat > logstash/pipeline/logstash.conf << 'CONFIG'
input {
  beats {
    port => 5044
  }
}

filter {
  # Try parsing JSON logs
  json {
    source => "message"
    skip_on_invalid_json => true
  }

  # Drop health check noise
  if [message] =~ /health/ {
    drop { }
  }

  # Add processed timestamp
  mutate {
    add_field => { "processed_at" => "%{@timestamp}" }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "app-logs-%{+YYYY.MM.dd}"
  }
  stdout {
    codec => rubydebug
  }
}
CONFIG
```

### Step 3: Filebeat Configuration

```bash
cat > filebeat/filebeat.yml << 'CONFIG'
filebeat.inputs:
  - type: container
    paths:
      - /var/lib/docker/containers/*/*.log
    processors:
      - add_docker_metadata:
          host: "unix:///var/run/docker.sock"

output.logstash:
  hosts: ["logstash:5044"]

logging.level: warning
CONFIG
```

### Step 4: Sample Application (Same as Lab 01)

```bash
cat > app/app.py << 'APP'
import json, time, random, logging, sys
from flask import Flask, jsonify

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "service": "elk-demo",
            "message": record.getMessage(),
        }
        if hasattr(record, '_extra'):
            log.update(record._extra)
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
def users():
    logger.info("Fetching users", extra={"_extra": {"endpoint": "/api/users"}})
    return jsonify({"users": ["alice", "bob"]})

@app.route('/api/orders', methods=['POST'])
def orders():
    oid = random.randint(1000, 9999)
    if random.random() < 0.3:
        logger.error("Order failed", extra={"_extra": {"order_id": oid, "reason": "payment_error"}})
        return jsonify({"error": "failed"}), 500
    logger.info("Order created", extra={"_extra": {"order_id": oid}})
    return jsonify({"order_id": oid}), 201

if __name__ == '__main__':
    logger.info("Starting ELK demo app")
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
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    restart: unless-stopped

  logstash:
    image: docker.elastic.co/logstash/logstash:8.12.0
    container_name: logstash
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch
    restart: unless-stopped

  kibana:
    image: docker.elastic.co/kibana/kibana:8.12.0
    container_name: kibana
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
    restart: unless-stopped

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.12.0
    container_name: filebeat
    user: root
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - logstash
    restart: unless-stopped

  elk-demo-app:
    build: ./app
    container_name: elk-demo-app
    ports:
      - "8080:8080"
    restart: unless-stopped

volumes:
  es_data:
COMPOSE
```

### Step 6: Launch

```bash
docker compose up -d --build

# Wait for Elasticsearch to be ready (takes ~30-60 seconds)
echo "Waiting for Elasticsearch..."
until curl -s http://localhost:9200/_cluster/health | grep -q '"status"'; do
  sleep 5
done
echo "Elasticsearch is ready!"
```

**✅ Checkpoint:** All 5 containers running. Elasticsearch at http://localhost:9200, Kibana at http://localhost:5601.

---

## 🔬 Exercise 2: Generate Logs and Search in Kibana

### Step 1: Generate Traffic

```bash
for i in $(seq 1 100); do
  curl -s http://localhost:8080/api/users > /dev/null
  curl -s -X POST http://localhost:8080/api/orders > /dev/null
  sleep 0.2
done
```

### Step 2: Create Data View in Kibana

1. Go to http://localhost:5601
2. Navigate to **Management** → **Stack Management** → **Data Views**
3. Click **Create data view**
4. Name: `app-logs`, Index pattern: `app-logs-*`
5. Timestamp field: `@timestamp`
6. Click **Save**

### Step 3: Search Logs in Discover

1. Go to **Discover** (sidebar)
2. Select the `app-logs` data view
3. Try these KQL queries:

```
# All error logs
level: "ERROR"

# Errors from a specific service
level: "ERROR" AND service: "elk-demo"

# Search by message content
message: *order*

# Specific order
order_id: 4521

# Combine conditions
level: "ERROR" AND reason: "payment_error"
```

**✅ Checkpoint:** You can see structured log entries in Kibana Discover and filter them with KQL.

---

## 🔬 Exercise 3: Build Kibana Visualizations

### Step 1: Create a Dashboard

1. Go to **Dashboard** → **Create dashboard**
2. Add these visualizations:

**Viz 1: Log Count Over Time (Lens → Bar chart)**
- Drag `@timestamp` to X-axis
- Use Count for Y-axis
- Split by `level` field

**Viz 2: Error Count (Lens → Metric)**
- Filter: `level: "ERROR"`
- Metric: Count

**Viz 3: Logs by Service (Lens → Pie chart)**
- Split by `service` field

3. Save as "ELK Demo Dashboard"

**✅ Checkpoint:** Dashboard shows log volume over time, error counts, and service distribution.

---

## 🧨 Break It: Four ELK Failures You Will Meet in Production

ELK has more moving parts than Loki, and each one fails differently. These are the four you'll actually hit.

### Scenario 1: The Mapping Conflict

This is **the** most common ELK failure, and it's invisible from Kibana.

**Break it:**

```bash
cd elk-lab

# Send a document where 'status' is a NUMBER
curl -s -X POST "localhost:9200/app-logs-conflict/_doc" \
  -H 'Content-Type: application/json' \
  -d '{"@timestamp":"2026-08-04T09:00:00Z","service":"api","status":500,"message":"server error"}'
echo

# Now send one where 'status' is a STRING
curl -s -X POST "localhost:9200/app-logs-conflict/_doc" \
  -H 'Content-Type: application/json' \
  -d '{"@timestamp":"2026-08-04T09:00:01Z","service":"api","status":"failed","message":"server error"}' | jq
```

**Symptom:**

```json
{"error":{"type":"document_parsing_exception",
  "reason":"failed to parse field [status] of type [long] ..."}}
```

The document is **rejected**. In a real pipeline, Logstash logs this and moves on — Kibana shows a gap and nothing tells you why. You debug for an hour convinced the service stopped logging.

**Investigate:**

```bash
# What type did Elasticsearch infer from the FIRST document it saw?
curl -s "localhost:9200/app-logs-conflict/_mapping?pretty" | jq '.[].mappings.properties.status'
# → {"type": "long"}   — locked in, permanently, for this index

# Are documents being rejected right now?
docker compose logs logstash | grep -iE 'mapper_parsing|document_parsing|_bulk' | tail -20
curl -s "localhost:9200/_cat/indices/app-logs-*?v&h=index,docs.count,store.size"
```

**Root cause:** Elasticsearch uses **dynamic mapping** — the first document to contain a field fixes that field's type for the whole index, and mappings are **immutable**. Any later document with a different type for that field is rejected outright.

**Fix — declare your mappings with an index template, before any data arrives:**

```bash
curl -s -X PUT "localhost:9200/_index_template/app-logs" \
  -H 'Content-Type: application/json' -d '{
  "index_patterns": ["app-logs-*"],
  "template": {
    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    "mappings": {
      "dynamic": "strict",
      "properties": {
        "@timestamp":  {"type": "date"},
        "level":       {"type": "keyword"},
        "service":     {"type": "keyword"},
        "message":     {"type": "text"},
        "status":      {"type": "integer"},
        "duration_ms": {"type": "float"},
        "trace_id":    {"type": "keyword"}
      }
    }
  }
}' | jq
```

And normalise types in Logstash so a bad producer can't poison the index:

```ruby
filter {
  mutate { convert => { "status" => "integer" "duration_ms" => "float" } }
  if "_mutate_error" in [tags] {
    mutate { add_field => { "parse_problem" => "type conversion failed" } }
  }
}
```

> 💡 `"dynamic": "strict"` makes unknown fields a **loud error** instead of a silent new mapping. That's what you want in production — mapping sprawl is the other half of this problem.

```bash
curl -s -X DELETE "localhost:9200/app-logs-conflict" >/dev/null
```

---

### Scenario 2: The Grok Filter That Silently Tags Everything

**Break it:**

```bash
cp logstash/pipeline/logstash.conf logstash/pipeline/logstash.conf.bak
cat > logstash/pipeline/logstash.conf <<'CONFIG'
input { beats { port => 5044 } }
filter {
  # A grok pattern for COMBINED apache logs — applied to JSON app logs
  grok {
    match => { "message" => "%{COMBINEDAPACHELOG}" }
  }
}
output {
  elasticsearch { hosts => ["elasticsearch:9200"] index => "app-logs-%{+YYYY.MM.dd}" }
}
CONFIG
docker compose restart logstash
sleep 30
for i in $(seq 1 50); do curl -s localhost:8080/ >/dev/null; done
sleep 30
```

**Symptom:** Documents arrive, so nothing looks broken. But in Kibana every document has a `_grokparsefailure` tag and **none of the fields are parsed** — you have a `message` blob and nothing to filter or aggregate on.

**Investigate:**

```bash
# ⭐ Count the failures — this is the check nobody runs
curl -s "localhost:9200/app-logs-*/_count" \
  -H 'Content-Type: application/json' \
  -d '{"query":{"term":{"tags":"_grokparsefailure"}}}' | jq

curl -s "localhost:9200/app-logs-*/_search?size=1&pretty" \
  -H 'Content-Type: application/json' \
  -d '{"query":{"term":{"tags":"_grokparsefailure"}}}' | jq '.hits.hits[]._source'
```

**Root cause:** Logstash's `grok` filter does not fail the pipeline on a non-match. It adds a `_grokparsefailure` tag and passes the document through unparsed. Nothing alerts; your dashboards just quietly show zero for every field.

**Fix — make parse failures visible and route them somewhere you'll look:**

```ruby
filter {
  json { source => "message" skip_on_invalid_json => true }

  if "_jsonparsefailure" in [tags] or "_grokparsefailure" in [tags] {
    mutate { add_field => { "[@metadata][dest]" => "parse-failures" } }
  } else {
    mutate { add_field => { "[@metadata][dest]" => "app-logs" } }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "%{[@metadata][dest]}-%{+YYYY.MM.dd}"    # ⭐ a dead-letter index
  }
}
```

Then alert on it: if `parse-failures-*` document count is non-zero and growing, a producer changed its format.

```bash
mv logstash/pipeline/logstash.conf.bak logstash/pipeline/logstash.conf
docker compose restart logstash
```

---

### Scenario 3: Yellow Cluster, Unassigned Shards

**Break it:**

```bash
# Ask for a replica on a single-node cluster
curl -s -X PUT "localhost:9200/app-logs-replicated" \
  -H 'Content-Type: application/json' \
  -d '{"settings":{"number_of_shards":1,"number_of_replicas":2}}' | jq
sleep 5
curl -s "localhost:9200/_cluster/health?pretty" | jq '{status, unassigned_shards}'
```

**Symptom:** Cluster status is **yellow** (or red). Indexing still works, but you've lost redundancy — and on a real cluster, red means some data is completely unreadable.

**Investigate:**

```bash
curl -s "localhost:9200/_cat/shards?v&s=state" | grep -i unassigned

# ⭐ The command that actually tells you WHY
curl -s "localhost:9200/_cluster/allocation/explain?pretty" \
  | jq '{index, shard, "reason": .unassigned_info.reason, "explanation": .allocate_explanation}'
```

**Root cause colour code:**

| Status | Meaning | Urgency |
|--------|---------|---------|
| 🟢 **green** | All primaries and replicas assigned | Fine |
| 🟡 **yellow** | All primaries assigned, some replicas are not | Degraded — no redundancy. Common on single-node dev clusters, **never acceptable in prod** |
| 🔴 **red** | At least one **primary** unassigned | **Data is unavailable.** Indexing to that shard fails |

Usual causes: more replicas than nodes; disk watermark exceeded; a node left the cluster; shard allocation filtering.

**Fix:**

```bash
# Single node → no replicas
curl -s -X PUT "localhost:9200/app-logs-*/_settings" \
  -H 'Content-Type: application/json' -d '{"index":{"number_of_replicas":0}}' | jq

# Check the disk watermarks — read-only-allow-delete is the classic prod surprise
curl -s "localhost:9200/_cluster/settings?include_defaults=true&flat_settings=true" \
  | jq '{low: .defaults["cluster.routing.allocation.disk.watermark.low"],
         high: .defaults["cluster.routing.allocation.disk.watermark.high"],
         flood: .defaults["cluster.routing.allocation.disk.watermark.flood_stage"]}'
```

> ⚠️ At **95% disk** Elasticsearch sets every index to `read_only_allow_delete` and **all indexing stops**. Freeing disk does not automatically clear the flag — you must reset it:
> ```bash
> curl -X PUT "localhost:9200/_all/_settings" -H 'Content-Type: application/json' \
>   -d '{"index.blocks.read_only_allow_delete": null}'
> ```

```bash
curl -s -X DELETE "localhost:9200/app-logs-replicated" >/dev/null
```

---

### Scenario 4: Indices That Never Expire

**Break it:**

```bash
# Look at what you're accumulating
curl -s "localhost:9200/_cat/indices?v&s=store.size:desc&h=index,docs.count,store.size,creation.date.string"
curl -s "localhost:9200/_cat/allocation?v"
```

**Symptom:** On a real cluster, daily indices accumulate forever. Each index carries shard overhead, each shard consumes heap for its segment metadata, and heap pressure eventually causes long GC pauses, then node instability, then a red cluster. Nothing warns you until it's a production incident.

**Investigate:**

```bash
# ⭐ Heap usage — the number that predicts trouble
curl -s "localhost:9200/_cat/nodes?v&h=name,heap.percent,ram.percent,disk.used_percent,load_1m"

# Total shard count — keep under ~20 shards per GB of heap
curl -s "localhost:9200/_cat/shards" | wc -l

# Which indices have no lifecycle policy?
curl -s "localhost:9200/app-logs-*/_ilm/explain?pretty" | jq '.indices | to_entries[] | select(.value.managed == false) | .key'
```

**Root cause:** No Index Lifecycle Management policy, and a shard-per-day-per-index strategy that scales linearly with time rather than with data volume.

**Fix — ILM with rollover, then age-based tiering and deletion:**

```bash
curl -s -X PUT "localhost:9200/_ilm/policy/app-logs-policy" \
  -H 'Content-Type: application/json' -d '{
  "policy": {"phases": {
    "hot":    {"actions": {"rollover": {"max_primary_shard_size": "30gb", "max_age": "1d"}}},
    "warm":   {"min_age": "7d",  "actions": {"forcemerge": {"max_num_segments": 1},
                                             "shrink": {"number_of_shards": 1}}},
    "delete": {"min_age": "30d", "actions": {"delete": {}}}
  }}
}' | jq

# Attach it to the template so every new index is managed
curl -s -X PUT "localhost:9200/_index_template/app-logs" \
  -H 'Content-Type: application/json' -d '{
  "index_patterns": ["app-logs-*"],
  "template": {"settings": {
    "index.lifecycle.name": "app-logs-policy",
    "index.lifecycle.rollover_alias": "app-logs"
  }}
}' | jq
```

Rollover by **size**, not just by date — a fixed daily index gives you 100 MB indices on quiet days and 500 GB ones during an incident.

---

### ELK vs Loki — What This Exercise Taught You

| | Elasticsearch/ELK | Loki |
|---|-------------------|------|
| **Indexes** | Every field, by default | Only stream labels |
| **Fails when** | Field types conflict; heap/shard pressure | Too many stream labels |
| **Cost driver** | Indexed field count and shard count | Stream cardinality and total bytes |
| **Query strength** | Rich full-text search, aggregations | Cheap grep over narrowed streams |
| **Operational burden** | High — mappings, shards, ILM, heap | Lower — but unforgiving about labels |
| **Silent failure** | Rejected documents, `_grokparsefailure` | Dropped entries, 429s |

> ⭐ **The shared lesson across both labs**: logging pipelines fail by **discarding data quietly**. Elasticsearch rejects a document and returns 400 to Logstash, which logs it and continues. Kibana shows a gap. Nothing pages anyone. **Monitor the pipeline itself** — rejected-document counts, `_grokparsefailure` counts, Filebeat's `libbeat.output.events.dropped`, and cluster health — with the tooling from Module 07.

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
docker compose down -v
cd .. && rm -rf elk-lab
```

---

## ✅ Validation

- [ ] Set up ELK Stack (Elasticsearch + Logstash + Kibana + Filebeat) with Docker Compose
- [ ] Ingest application logs through the Filebeat → Logstash → Elasticsearch pipeline
- [ ] Create a Kibana data view and search logs with KQL
- [ ] Build a Kibana dashboard with log volume, error counts, and breakdowns
- [ ] Explain the role of each ELK component
- [ ] Compare ELK vs Loki — when to use each


## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- Docker Compose file for the ELK stack
- Logstash pipeline configuration
- Kibana visualization screenshots or saved objects
- Search queries and filter examples with results

---

[← Back to Module README](../README.md) | [← Lab 01: Loki + Grafana](./lab-01-loki-grafana.md)
