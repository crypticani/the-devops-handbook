# Lab 02: ELK Stack — Enterprise Logging with Elasticsearch, Logstash, and Kibana

## 🎯 Objective

Set up the ELK Stack (Elasticsearch, Logstash, Kibana) with Filebeat using Docker Compose. You'll ingest logs, create Logstash pipelines, search with KQL in Kibana, and build visualizations — the enterprise-standard logging stack.

---

## 📋 Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available for Docker
- Completed Lab 01 (Loki)

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

---

[← Back to Module README](../README.md) | [← Lab 01: Loki + Grafana](./lab-01-loki-grafana.md)
