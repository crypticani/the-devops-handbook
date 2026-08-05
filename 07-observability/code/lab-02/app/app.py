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
