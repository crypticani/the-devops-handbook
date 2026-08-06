"""checkout-api — the service that has the incident.

Two behaviours, selected by the LEAK environment variable:

  LEAK=1  the current release. Every /checkout borrows a connection from the pool and
          never returns it, so once 20 requests have been served the pool is exhausted
          and every subsequent request fails.
  LEAK=0  the previous release, which returns connections properly. This is what a
          rollback gets you.

The important detail is /healthz: it does not touch the pool, so it keeps answering 200
long after users have started seeing 503s. That is not a bug in this lab — it is the most
common way a real health check lies.
"""

import json
import logging
import os
import threading
import time

from flask import Flask, jsonify

POOL_SIZE = int(os.environ.get("POOL_SIZE", "20"))
LEAK = os.environ.get("LEAK", "1") == "1"
VERSION = os.environ.get("VERSION", "unknown")

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("checkout-api")


def emit(level, msg, **fields):
    log.info(json.dumps({"level": level, "service": "checkout-api", "version": VERSION,
                         "msg": msg, **fields}))


class ConnectionPool:
    """A deliberately simple pool: a counter and a lock."""

    def __init__(self, size):
        self.size = size
        self.in_use = 0
        self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            if self.in_use >= self.size:
                return False
            self.in_use += 1
            return True

    def release(self):
        with self.lock:
            if self.in_use > 0:
                self.in_use -= 1


pool = ConnectionPool(POOL_SIZE)


@app.route("/healthz")
def healthz():
    # ⭐ No pool check. The process is alive, so this says 200 — even when every real
    # request is failing. Compare with /readyz below.
    return jsonify({"status": "ok", "version": VERSION})


@app.route("/readyz")
def readyz():
    # What the health check SHOULD have been: it fails when the service cannot serve.
    if pool.in_use >= pool.size:
        return jsonify({"status": "pool exhausted", "in_use": pool.in_use}), 503
    return jsonify({"status": "ok", "in_use": pool.in_use})


@app.route("/pool")
def pool_status():
    return jsonify({"in_use": pool.in_use, "size": pool.size, "leaking": LEAK})


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if not pool.acquire():
        emit("ERROR", "no connection available", pool_in_use=pool.in_use)
        return jsonify({"error": "service unavailable: connection pool exhausted"}), 503

    try:
        # Latency climbs as the pool fills — the symptom that arrives BEFORE the errors,
        # and the one your dashboards should catch first.
        time.sleep(0.01 + 0.02 * (pool.in_use / pool.size))
        return jsonify({"status": "ok", "version": VERSION})
    finally:
        if not LEAK:
            pool.release()


if __name__ == "__main__":
    emit("INFO", "starting", leaking=LEAK, pool_size=POOL_SIZE)
    app.run(host="0.0.0.0", port=8080, threaded=True)
