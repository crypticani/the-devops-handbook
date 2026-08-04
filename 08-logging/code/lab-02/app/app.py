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
