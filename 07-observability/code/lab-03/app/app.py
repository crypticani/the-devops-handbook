"""One image, two services.

Run it with OTEL_SERVICE_NAME=checkout and DOWNSTREAM_URL set, and it calls the other
instance. Run it with OTEL_SERVICE_NAME=payment and no DOWNSTREAM_URL, and it is the
other instance. Two containers from one file is the smallest thing that produces a
trace with more than one service in it.
"""

import json
import logging
import os
import random
import time

import requests
from flask import Flask, jsonify
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "unnamed-service")
DOWNSTREAM_URL = os.environ.get("DOWNSTREAM_URL")  # set on checkout, absent on payment

# ──────────────────────────────────────────────
# TRACING SETUP
# ──────────────────────────────────────────────
# The resource is how a span says who emitted it. service.name is the one attribute
# every backend groups by — get it wrong and your traces are attributed to "unknown".
provider = TracerProvider(
    resource=Resource.create(
        {
            "service.name": SERVICE_NAME,
            "deployment.environment": os.environ.get("ENVIRONMENT", "lab"),
        }
    )
)

# Batch, not simple: the SDK buffers spans and exports in the background, so a slow
# collector slows down nothing. The tradeoff is that spans are DROPPED when the queue
# fills or the exporter fails — silently, by design. See Break It scenario 4.
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter())  # endpoint from OTEL_EXPORTER_OTLP_ENDPOINT
)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

app = Flask(__name__)

# These two lines are the whole reason a trace spans services:
FlaskInstrumentor().instrument_app(app)  # ⭐ READS traceparent from the incoming request
RequestsInstrumentor().instrument()      # ⭐ WRITES traceparent onto the outgoing one


# ──────────────────────────────────────────────
# LOGGING WITH TRACE CONTEXT
# ──────────────────────────────────────────────
class TraceContextFilter(logging.Filter):
    """Stamp every log line with the trace it belongs to.

    This is the cheapest correlation you will ever buy: it turns "find the logs for this
    slow request" from a timestamp-guessing exercise into an exact query.
    """

    def filter(self, record):
        ctx = trace.get_current_span().get_span_context()
        record.trace_id = format(ctx.trace_id, "032x") if ctx.is_valid else "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(
            {
                "ts": self.formatTime(record),
                "level": record.levelname,
                "service": SERVICE_NAME,
                "trace_id": record.trace_id,
                "msg": record.getMessage(),
            }
        )


handler = logging.StreamHandler()
handler.addFilter(TraceContextFilter())
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
log = logging.getLogger(SERVICE_NAME)


# ──────────────────────────────────────────────
# ENDPOINTS
# ──────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "healthy", "service": SERVICE_NAME})


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    """Entry point. Does a little work, then calls the payment service."""
    # A manual span for work worth attributing separately. Flask's instrumentation
    # already gave us a span for the request itself — this one nests inside it.
    with tracer.start_as_current_span("validate_cart") as span:
        items = random.randint(1, 5)
        # Attributes are for values you want to filter and group by. Bounded ones.
        span.set_attribute("cart.item_count", items)
        time.sleep(random.uniform(0.005, 0.02))

    if not DOWNSTREAM_URL:
        return jsonify({"error": "DOWNSTREAM_URL is not set"}), 500

    log.info("calling payment service")
    resp = requests.post(f"{DOWNSTREAM_URL}/charge", json={"items": items}, timeout=10)
    if resp.status_code != 200:
        log.error("payment failed: %s", resp.status_code)
        return jsonify({"error": "payment failed", "upstream": resp.status_code}), 502
    return jsonify({"status": "ok", "payment": resp.json()})


@app.route("/charge", methods=["POST"])
def charge():
    """Downstream service. Sometimes slow, sometimes broken — on purpose."""
    span = trace.get_current_span()

    with tracer.start_as_current_span("fraud_check") as fraud:
        # ⭐ 1 request in 8 takes two seconds. This is the span you go looking for,
        # and the reason p99 is the number that matters.
        slow = random.random() < 0.125
        fraud.set_attribute("fraud.slow_path", slow)
        time.sleep(2.0 if slow else random.uniform(0.01, 0.05))

    with tracer.start_as_current_span("db_write") as db:
        db.set_attribute("db.system", "postgresql")
        db.set_attribute("db.operation", "INSERT")
        time.sleep(random.uniform(0.01, 0.04))

    if random.random() < 0.1:
        # An exception recorded on the span is what makes a trace searchable by failure.
        # Without this the span is just "slow"; with it, it says what went wrong.
        error = RuntimeError("card processor rejected the transaction")
        span.record_exception(error)
        span.set_status(Status(StatusCode.ERROR, str(error)))
        log.error("charge failed: %s", error)
        return jsonify({"error": str(error)}), 500

    return jsonify({"charge_id": random.randint(1000, 9999), "status": "captured"})


if __name__ == "__main__":
    log.info("starting %s (downstream=%s)", SERVICE_NAME, DOWNSTREAM_URL or "none")
    app.run(host="0.0.0.0", port=8080)
