"""One image, two roles: an order producer and a consumer in a consumer group.

    MODE=producer   creates the topic with PARTITIONS partitions and publishes orders
                    keyed by customer — the key is what decides the partition
    MODE=consumer   joins consumer group GROUP, processes a batch, commits the offsets

Unlike a queue, nothing here is "delivered and deleted": the log keeps every record and
each group tracks its own offset, so every failure below is an offset problem, not a
message problem. All of them are environment variables — no scenario needs a code edit:

    KEYS=1                every order gets the same key — one hot partition (scenario 2)
    WORK_MS=800           a batch takes longer than MAX_POLL_MS allows (scenario 3)
    COMMIT_BEFORE_WORK=1  commit the batch before processing it — at-most-once (scenario 4)
    CRASH_AFTER=25        exit after N processed records, to make the crash land on cue
"""

import json
import os
import random
import sys
import time

from confluent_kafka import Consumer, KafkaError, Producer
from confluent_kafka.admin import AdminClient, NewTopic

MODE = os.environ.get("MODE", "consumer")
BROKER = os.environ.get("BROKER", "kafka:9092")
TOPIC = os.environ.get("TOPIC", "orders")
GROUP = os.environ.get("GROUP", "orders")

PARTITIONS = int(os.environ.get("PARTITIONS", "3"))
RATE = float(os.environ.get("RATE", "10"))
KEYS = int(os.environ.get("KEYS", "50"))          # distinct customers — set to 1 for skew
WORK_MS = int(os.environ.get("WORK_MS", "40"))
BATCH = int(os.environ.get("BATCH", "10"))
MAX_POLL_MS = int(os.environ.get("MAX_POLL_MS", "300000"))
COMMIT_BEFORE_WORK = os.environ.get("COMMIT_BEFORE_WORK", "0") == "1"
CRASH_AFTER = int(os.environ.get("CRASH_AFTER", "0"))
WORKER = os.environ.get("HOSTNAME", "worker")[:12]


def log(event, **fields):
    print(json.dumps({"ts": round(time.time(), 3), "role": MODE, "worker": WORKER,
                      "event": event, **fields}), flush=True)


def wait_for_broker():
    """The broker takes a few seconds to accept clients, and longer to elect a controller."""
    admin = AdminClient({"bootstrap.servers": BROKER})
    for attempt in range(30):
        if admin.list_topics(timeout=5).brokers:
            return admin
        log("waiting_for_broker", attempt=attempt + 1)
        time.sleep(2)
    log("broker_unreachable")
    sys.exit(1)


def declare(admin):
    """Partition count is the decision this lab is about.

    It is the parallelism ceiling for the group: N partitions means at most N useful
    consumers, whatever your replica count says. You can raise it later but never lower
    it, and raising it re-maps key -> partition, so per-key ordering does not survive
    the change. Pick it for the throughput you expect to need, not the one you have.
    """
    if TOPIC in admin.list_topics(timeout=10).topics:
        return
    topic = NewTopic(TOPIC, num_partitions=PARTITIONS, replication_factor=1)
    for name, future in admin.create_topics([topic]).items():
        try:
            future.result()
            log("topic_created", topic=name, partitions=PARTITIONS)
        except Exception as exc:                   # already created by another replica
            log("topic_exists", topic=name, detail=str(exc))


def produce():
    producer = Producer({"bootstrap.servers": BROKER, "enable.idempotence": True})
    log("producing", rate=RATE, keys=KEYS, partitions=PARTITIONS)
    n = 0

    def delivered(err, msg):
        if err:
            log("delivery_failed", error=str(err))
        elif msg.offset() % 50 == 0:
            log("delivered", key=msg.key().decode(), partition=msg.partition(),
                offset=msg.offset())

    while True:
        n += 1
        # ⭐ The key, not round-robin, is what pins related records to one partition —
        # which is the only ordering guarantee Kafka offers, and the source of hot
        # partitions when the key is badly chosen.
        key = f"cust-{random.randrange(KEYS):04d}"
        order = {"order_id": f"ord-{n:06d}", "customer": key,
                 "amount_pence": random.randint(500, 25000)}
        producer.produce(TOPIC, key=key, value=json.dumps(order), on_delivery=delivered)
        producer.poll(0)
        if n % 100 == 0:
            log("published", count=n)
        time.sleep(1.0 / RATE if RATE > 0 else 1.0)


def charge(order):
    time.sleep(WORK_MS / 1000)
    return order["amount_pence"]


def consume():
    consumer = Consumer({
        "bootstrap.servers": BROKER,
        "group.id": GROUP,
        "client.id": WORKER,                  # ⭐ so a partition's owner names a container
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,          # ⭐ we commit, so we decide the guarantee
        # Two different liveness timers, and confusing them is why rebalances surprise
        # people. session.timeout.ms asks "is the process alive?" (heartbeats, sent on a
        # background thread). max.poll.interval.ms asks "is it making progress?" — exceed
        # it and the group evicts a consumer that is perfectly healthy, just slow.
        "max.poll.interval.ms": MAX_POLL_MS,
        "session.timeout.ms": min(10000, MAX_POLL_MS),   # must be <= max.poll.interval.ms
        # Left at the default eager strategy on purpose: every rebalance stops the whole
        # group. "cooperative-sticky" is the fix, and scenario 3 is why you want it.
    })

    def on_assign(_consumer, partitions):
        # An empty assignment is the finding in scenario 1: a healthy consumer with
        # nothing to do, because the partitions ran out before the replicas did.
        log("assigned", partitions=[p.partition for p in partitions] or None)

    def on_revoke(_consumer, partitions):
        log("revoked", partitions=[p.partition for p in partitions])

    consumer.subscribe([TOPIC], on_assign=on_assign, on_revoke=on_revoke)
    log("consuming", group=GROUP, batch=BATCH, work_ms=WORK_MS,
        max_poll_ms=MAX_POLL_MS, commit_before_work=COMMIT_BEFORE_WORK)

    processed = 0
    while True:
        msgs = consumer.consume(num_messages=BATCH, timeout=1.0)
        if not msgs:
            continue

        batch = []
        for msg in msgs:
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    log("consume_error", error=str(msg.error()))
                continue
            batch.append(msg)
        if not batch:
            continue

        if COMMIT_BEFORE_WORK:
            # At-most-once. The offset now says this batch is done; anything that stops
            # us before the work finishes loses those records silently — and lag reads 0,
            # because lag only ever measured the offset, never the work.
            consumer.commit(message=batch[-1], asynchronous=False)
            log("committed_ahead", count=len(batch), offset=batch[-1].offset())

        for msg in batch:
            order = json.loads(msg.value())
            charge(order)
            processed += 1
            log("CHARGED", order_id=order["order_id"], customer=order["customer"],
                partition=msg.partition(), offset=msg.offset(), total=processed)

            if CRASH_AFTER and processed >= CRASH_AFTER:
                log("crashing", processed=processed)
                sys.exit(1)                   # restart: unless-stopped brings us back

        if not COMMIT_BEFORE_WORK:
            # At-least-once. A crash before this line replays the whole batch, so the
            # duplicate window is the batch, not the message — Lab 02's idempotency
            # requirement, one batch wide.
            consumer.commit(message=batch[-1], asynchronous=False)


def main():
    admin = wait_for_broker()
    declare(admin)
    produce() if MODE == "producer" else consume()


if __name__ == "__main__":
    main()
