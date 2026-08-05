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
