"""One image, two roles: an order producer and an order consumer.

    MODE=producer   publishes orders at RATE per second, some of them poison
    MODE=consumer   consumes them, does "work", and acknowledges

Every behaviour the lab needs to break is an environment variable, so you can
reproduce each failure without editing code:

    PREFETCH=0          no basic_qos — one consumer grabs the whole queue (scenario 3)
    IDEMPOTENT=0        no duplicate protection (scenario 2)
    CRASH_AFTER_WORK=1  ack is lost after the work is done — at-least-once, demonstrated
    WORK_MS=250         make the consumer slower than the producer, and watch the backlog
"""

import json
import os
import random
import sys
import time

import pika

MODE = os.environ.get("MODE", "consumer")
AMQP_URL = os.environ.get("AMQP_URL", "amqp://guest:guest@rabbitmq:5672/%2F")
QUEUE = "orders"
DLX = "orders.dlx"
DLQ = "orders.dlq"

RATE = float(os.environ.get("RATE", "5"))
POISON_RATE = float(os.environ.get("POISON_RATE", "0.05"))
WORK_MS = int(os.environ.get("WORK_MS", "50"))
PREFETCH = int(os.environ.get("PREFETCH", "5"))
IDEMPOTENT = os.environ.get("IDEMPOTENT", "1") == "1"
CRASH_AFTER_WORK = os.environ.get("CRASH_AFTER_WORK", "0") == "1"
DELIVERY_LIMIT = int(os.environ.get("DELIVERY_LIMIT", "3"))
WORKER = os.environ.get("HOSTNAME", "worker")[:12]


def log(event, **fields):
    print(json.dumps({"ts": round(time.time(), 3), "role": MODE, "worker": WORKER,
                      "event": event, **fields}), flush=True)


def connect():
    """Retry the connection — RabbitMQ takes a few seconds to accept clients."""
    for attempt in range(30):
        try:
            return pika.BlockingConnection(pika.URLParameters(AMQP_URL))
        except pika.exceptions.AMQPConnectionError:
            log("waiting_for_broker", attempt=attempt + 1)
            time.sleep(2)
    log("broker_unreachable")
    sys.exit(1)


def declare(channel):
    """Topology. This is the part that decides whether a poison message can ever die.

    A quorum queue with x-delivery-limit gives you retry-then-dead-letter for free:
    after N deliveries the broker routes the message to the DLX instead of the
    consumer. Without the limit, a message that always fails is redelivered forever.
    """
    args = {
        "x-queue-type": "quorum",
        "x-dead-letter-exchange": DLX,
    }
    if DELIVERY_LIMIT > 0:                       # set DELIVERY_LIMIT=0 for scenario 1
        args["x-delivery-limit"] = DELIVERY_LIMIT

    channel.exchange_declare(exchange=DLX, exchange_type="fanout", durable=True)
    channel.queue_declare(queue=DLQ, durable=True)
    channel.queue_bind(queue=DLQ, exchange=DLX)
    channel.queue_declare(queue=QUEUE, durable=True, arguments=args)
    return args


def produce(channel):
    log("producing", rate=RATE, poison_rate=POISON_RATE)
    n = 0
    while True:
        n += 1
        order = {
            "order_id": f"ord-{n:06d}",
            "amount_pence": random.randint(500, 25000),
            # A poison message is not malicious — it is usually a schema change, or a
            # reference to a row someone deleted. It just never succeeds.
            "poison": random.random() < POISON_RATE,
        }
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE,
            body=json.dumps(order),
            properties=pika.BasicProperties(
                delivery_mode=2,                  # persist: survive a broker restart
                content_type="application/json",
                message_id=order["order_id"],     # ⭐ the idempotency key, carried by the message
            ),
        )
        if n % 20 == 0:
            log("published", count=n)
        time.sleep(1.0 / RATE if RATE > 0 else 1.0)


def charge(order):
    """The 'work'. Poison orders always fail, whoever retries them."""
    time.sleep(WORK_MS / 1000)
    if order.get("poison"):
        raise ValueError(f"cannot process {order['order_id']}: unknown schema version")
    return True


def consume(channel):
    seen = set()                                  # ⭐ per-process, so restarts lose it — see the lab
    charged = 0

    if PREFETCH > 0:
        channel.basic_qos(prefetch_count=PREFETCH)
    else:
        log("no_prefetch_limit")                   # scenario 3: this consumer will hoard

    def handle(ch, method, props, body):
        nonlocal charged
        order = json.loads(body)
        oid = order["order_id"]

        if IDEMPOTENT and oid in seen:
            log("duplicate_skipped", order_id=oid)
            ch.basic_ack(method.delivery_tag)
            return

        try:
            charge(order)
        except ValueError as exc:
            # requeue=True so the delivery counter increments and x-delivery-limit can
            # eventually dead-letter it. requeue=False would DLQ on the first failure —
            # correct for a message you KNOW is unprocessable, wrong for a transient error.
            log("work_failed", order_id=oid, error=str(exc),
                redelivered=method.redelivered)
            ch.basic_nack(method.delivery_tag, requeue=True)
            return

        seen.add(oid)
        charged += 1
        log("CHARGED", order_id=oid, total=charged)

        if CRASH_AFTER_WORK:
            # The classic at-least-once window: the work is done, the ack never arrives.
            # The broker redelivers, and a non-idempotent consumer charges twice.
            log("ack_lost", order_id=oid)
            ch.basic_nack(method.delivery_tag, requeue=True)
            return

        ch.basic_ack(method.delivery_tag)

    channel.basic_consume(queue=QUEUE, on_message_callback=handle)
    log("consuming", prefetch=PREFETCH, idempotent=IDEMPOTENT, work_ms=WORK_MS)
    channel.start_consuming()


def main():
    conn = connect()
    channel = conn.channel()
    log("topology", **declare(channel))
    produce(channel) if MODE == "producer" else consume(channel)


if __name__ == "__main__":
    main()
