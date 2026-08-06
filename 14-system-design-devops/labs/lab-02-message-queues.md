# Lab 02: Message Queues and Async Failure

## 🎯 Objective

Operate a queue the way you will have to on call: watch a backlog form, drain it by scaling consumers, and deal with the message that can never succeed.

You'll run a producer and consumers against RabbitMQ, then break the four things that actually break in production — an unbounded retry, a non-idempotent consumer, an unbounded prefetch, and consumers that quietly stopped. Every one of them leaves the application healthy and the work undone.

---

## 📋 Prerequisites

- Read [§7 Async Communication and Message Queues](../README.md#7-async-communication-and-message-queues)
- Completed [Lab 01: High Availability and Load Balancing](./lab-01-ha-load-balancing.md)
- Docker and Docker Compose, ~1 GB free
- Python basics (Module 04) — you'll read a consumer, not write one from scratch

```bash
docker --version && docker compose version
```

---

## 📦 Deliverables and Evidence

- The four numbers (depth, unacked, consumers, DLQ) captured while a backlog forms and drains
- Proof that scaling consumers drained the queue, with the timestamps
- A poison message in the DLQ, and the delivery count that put it there
- A duplicate charge you caused on purpose, and the same run with idempotency on
- The four alert rules you'd write, with thresholds and a sentence of justification each
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-02/`](../code/lab-02/).

```bash
cp -r /path/to/the-devops-handbook/14-system-design-devops/code/lab-02/. .
chmod +x watch-queue.sh
```

One image runs as both producer and consumer (`MODE`), and every failure in this lab is an environment variable — no scenario needs a code edit.

---

## 🔬 Exercise 1: Backlog and Drain

### Step 1: The Topology You're Declaring

Read `app.py`'s `declare()` before you start it. Three lines decide whether this system can lose work:

```python
args = {
    "x-queue-type": "quorum",              # replicated, and supports a delivery limit
    "x-dead-letter-exchange": DLX,         # ⭐ where a message goes when it's given up on
    "x-delivery-limit": DELIVERY_LIMIT,    # ⭐ how many attempts before that happens
}
```

Without the last two, a message that always fails is redelivered forever. That is scenario 1, and it is the most common queue outage there is.

### Step 2: Start It and Watch

```bash
docker compose up -d --build
docker compose ps
```

In a second terminal, and leave it running for the whole lab:

```bash
./watch-queue.sh
```

```text
TIME           ORDERS    UNACKED  CONSUMERS        DLQ
14:20:03            0          0          1          0
14:20:05            2          1          1          0
14:20:07            1          1          1          0
```

Four numbers, and each answers a different question:

| Column | Question | What "bad" looks like |
|--------|----------|----------------------|
| `ORDERS` | How much work is waiting? | Growing steadily — consumers are losing the race |
| `UNACKED` | How much is in flight? | High with few consumers = handlers are **stuck**, not slow |
| `CONSUMERS` | Is anyone listening? | ⭐ `0` with messages waiting is a silent outage |
| `DLQ` | What has been given up on? | Anything above zero is work nobody is doing |

### Step 3: Create a Backlog

At `RATE=5` and `WORK_MS=50` one consumer keeps up comfortably. Make the work slower than the arrival rate:

```bash
WORK_MS=400 docker compose up -d consumer      # 2.5/s capacity against 5/s arriving
```

```text
TIME           ORDERS    UNACKED  CONSUMERS        DLQ
14:22:10           14          5          1          0
14:22:20           38          5          1          0
14:22:30           63          5          1          0
```

Note what is *not* happening: nothing is failing. No error, no alert, no unhealthy container. The only signal is that a number is going up — which is why "queue depth growing over N minutes" is the alert, and why a queue with no monitoring is a silent backlog.

> ⭐ **The Kafka translation**: RabbitMQ gives you depth; Kafka gives you *consumer lag* (produced offset minus committed offset). They answer the same question. In both, the number that maps to your SLO is the **age of the oldest unprocessed message** — a depth of 10 that is four hours old is far worse than a depth of 10,000 that is five seconds old.

### Step 4: Drain It

```bash
docker compose up -d --scale consumer=4
./watch-queue.sh    # already running — watch CONSUMERS jump, then ORDERS fall
```

```text
TIME           ORDERS    UNACKED  CONSUMERS        DLQ
14:23:02           71         20          4          0
14:23:12           44         20          4          0
14:23:22           11         20          4          0
14:23:32            0          6          4          0
```

Four consumers at 2.5/s each is 10/s against 5/s arriving, so the backlog drains at ~5/s. That arithmetic — arrival rate, per-consumer capacity, consumer count — is the whole capacity model for a queue, and it is what you should be able to do in your head when someone asks "how long until we catch up?"

```bash
# Back to one consumer for the rest of the lab
docker compose up -d --scale consumer=1
```

---

## 🔬 Exercise 2: The Message That Can Never Succeed

5% of published orders carry `poison: true` and always raise. Watch one make its way out:

```bash
docker compose logs consumer | grep -E 'work_failed|CHARGED' | tail -8
```

```text
{"event": "work_failed", "order_id": "ord-000041", "error": "cannot process ord-000041: unknown schema version", "redelivered": false}
{"event": "work_failed", "order_id": "ord-000041", "error": "...", "redelivered": true}
{"event": "work_failed", "order_id": "ord-000041", "error": "...", "redelivered": true}
```

Three attempts, then the broker stops offering it and routes it to the dead letter queue — `DLQ` in your watcher goes to 1. Inspect it:

```bash
docker exec mq rabbitmqctl list_queues name messages | grep dlq
# Read one without consuming it (get with requeue, for a human looking):
docker exec mq rabbitmqadmin --username=guest --password=guest \
  get queue=orders.dlq count=1 ackmode=reject_requeue_true
```

The DLQ is doing exactly its job: one order is parked, and the other 95% of traffic flowed past it uninterrupted. That isolation is the entire point.

> ⚠️ **A DLQ nobody looks at is a folder of lost orders.** It needs an alert on depth above zero, an owner, and a documented decision for each entry: fix and replay, or discard with a reason. "We have a DLQ" is only half a design.

**Replaying** is the other half — after fixing the bug, shovel the messages back:

```bash
# The management UI (localhost:15672 → Queues → orders.dlq → Move messages) does this
# with a shovel. In production it's a script you have tested, not a UI you improvise in.
docker exec mq rabbitmq-plugins enable rabbitmq_shovel rabbitmq_shovel_management
```

---

## 🧨 Break It: Four Async Failures

Each scenario restores state before the next one.

### Scenario 1: Retry Without a Limit

**Break it.** Remove the delivery cap, which is exactly what you get by declaring an ordinary queue and forgetting the argument:

```bash
docker compose down
DELIVERY_LIMIT=0 docker compose up -d --build
```

**Symptom.** Watch for two minutes.

```text
TIME           ORDERS    UNACKED  CONSUMERS        DLQ
14:31:04           12          5          1          0
14:31:34           29          5          1          0
14:32:04           47          5          1          0
```

`DLQ` stays at 0 forever, and the depth climbs. Nothing errors at the container level, the consumer is busy, and CPU is being spent. Look at what it is busy *with*:

```bash
docker compose logs consumer --tail=30 | grep work_failed | \
  python3 -c "import sys,json,collections
c=collections.Counter(json.loads(l)['order_id'] for l in sys.stdin)
print(c.most_common(3))"
```

```text
[('ord-000041', 214), ('ord-000063', 187), ('ord-000078', 155)]
```

**Root cause.** One message, retried two hundred times, and it will be retried until the broker is restarted. Each poison message permanently consumes a slice of your consumer capacity, so throughput degrades with every one that arrives — a slow strangle rather than an outage, which is why it survives so long undetected.

**Fix.**

```bash
docker compose down
docker compose up -d --build        # DELIVERY_LIMIT back to 3
```

> ⭐ The same failure without a quorum queue: with a classic queue and `requeue=True` in a bare `except`, you have written an infinite loop with a network hop in it. Either cap deliveries at the broker (`x-delivery-limit`) or count attempts in a header yourself and `reject` past the limit. Deciding "how many times, then what?" is not optional.

### Scenario 2: At-Least-Once Meets a Non-Idempotent Consumer

**Break it.** Lose the acknowledgement after the work is done — a crash, an OOM kill, a network blip at the wrong instant — and turn off duplicate protection:

```bash
docker compose down
IDEMPOTENT=0 CRASH_AFTER_WORK=1 POISON_RATE=0 docker compose up -d --build
```

**Symptom.** Let it run for 30 seconds.

```bash
docker compose logs consumer | grep -c CHARGED                      # total charges
docker compose logs consumer | grep CHARGED | \
  grep -o 'ord-[0-9]*' | sort -u | wc -l                            # unique orders
```

```text
147
32
```

**147 charges for 32 orders.** Every order charged four and a half times on average. No error, no alert, no failed message — the queue looks perfect, and the customer's card does not.

**Investigate.**

```bash
docker compose logs consumer | grep 'ord-000005' | head -4
```

```text
{"event": "CHARGED", "order_id": "ord-000005", "total": 5}
{"event": "ack_lost", "order_id": "ord-000005"}
{"event": "CHARGED", "order_id": "ord-000005", "total": 9}
{"event": "ack_lost", "order_id": "ord-000005"}
```

**Root cause.** The broker's contract is at-least-once: it keeps a message until acknowledged, so anything that interrupts the window between "work done" and "ack sent" produces a redelivery. Exactly-once delivery does not exist across a network; exactly-once *effect* is something the consumer implements.

**Fix.** Turn idempotency back on and watch the same run behave:

```bash
docker compose down
CRASH_AFTER_WORK=1 POISON_RATE=0 IDEMPOTENT=1 docker compose up -d --build
sleep 30
docker compose logs consumer | grep -c CHARGED
docker compose logs consumer | grep -c duplicate_skipped     # ⭐ the protection working
```

Now read the caveat in the code: `seen` is an in-memory set, so a consumer **restart** loses it and duplicates return. In production the claim goes in a shared store with a TTL — the eight-line pattern in §7 — and the key comes from the message (`message_id` here), never from the receiving process.

```bash
docker compose down && docker compose up -d --build     # restore defaults
```

### Scenario 3: Unbounded Prefetch

**Break it.** Remove the prefetch limit — the default in most client libraries, and invisible until you scale:

```bash
docker compose down
PREFETCH=0 WORK_MS=400 docker compose up -d --build
sleep 20
docker compose up -d --scale consumer=4
```

**Symptom.** Adding consumers does nothing.

```text
TIME           ORDERS    UNACKED  CONSUMERS        DLQ
14:41:10           58         58          1          0
14:41:30           74         74          4          0      ← 4 consumers now
14:41:50           89         89          4          0      ← depth still climbing
```

Look at `UNACKED`: it equals the whole queue. One consumer has claimed every message, so three of your four sit idle while the backlog grows. The obvious remedy — scale out — has no effect, which sends people looking at the wrong layer entirely.

**Investigate.**

```bash
docker exec mq rabbitmqctl list_consumers          # prefetch_count column: 0 = unlimited
docker compose logs consumer | grep no_prefetch_limit
docker compose logs consumer | grep -c CHARGED     # only one worker's hostname appears
docker compose logs consumer | grep CHARGED | python3 -c "import sys,json,collections
print(collections.Counter(json.loads(l)['worker'] for l in sys.stdin))"
```

```text
Counter({'a1b2c3d4e5f6': 51})
```

One worker did all of it.

**Root cause.** Without `basic_qos(prefetch_count=N)` the broker pushes as fast as the connection allows, so the first consumer to connect buffers the queue into its own memory. Two consequences: work cannot be redistributed, and if that consumer dies, every buffered message is redelivered at once. Kafka's equivalent is partition count — you cannot have more useful consumers in a group than partitions, however many pods you start.

**Fix.**

```bash
docker compose down
WORK_MS=400 docker compose up -d --build --scale consumer=4   # PREFETCH back to 5
```

Now `UNACKED` sits near `4 × 5 = 20`, the workers share the load, and the queue drains. Prefetch is a throughput-versus-fairness dial: too low and consumers idle between fetches, too high and you have rebuilt this bug.

```bash
docker compose down && docker compose up -d --build
```

### Scenario 4: Zero Consumers, Everything Green

**Break it.** The most common real version of this is a deployment that stopped starting workers — a renamed queue, a crash loop in a sidecar, a scaled-to-zero replica set. Simulate it exactly:

```bash
docker compose stop consumer
```

**Symptom.**

```text
TIME           ORDERS    UNACKED  CONSUMERS        DLQ
14:50:02           31          0          0          0
14:50:32           181         0          0          0
14:51:02          331          0          0          0
```

The producer is healthy. The broker is healthy. Every HTTP request that enqueued an order returned 200 and the user was told their order was placed. Nothing is failing, and nothing is being done.

**Investigate.**

```bash
docker exec mq rabbitmqctl list_queues name messages consumers
docker exec mq rabbitmqctl list_consumers      # empty output — the whole finding
```

`UNACKED=0` alongside a climbing depth is the fingerprint: with stuck consumers you would see unacked messages held; with *no* consumers, nothing is in flight at all.

**Root cause.** Nothing in the request path depends on the consumer, which is exactly what the queue was for — and it means consumer liveness is a property only the *queue* can tell you about. Monitor the queue, or you monitor nothing.

**Fix.**

```bash
docker compose up -d consumer
# depth falls; the accepted-but-unprocessed orders are still there, which is the good news
```

### Summary

| Failure | How you detect it | How you prevent it |
|---------|------------------|--------------------|
| Retry without a limit | Depth climbing while DLQ stays 0; the same `order_id` failing hundreds of times | `x-delivery-limit` + a DLX, or count attempts yourself and reject |
| Non-idempotent consumer | Charges far exceed unique orders; no errors anywhere | Idempotency key from the message, claimed in a shared store before the work |
| Unbounded prefetch | `UNACKED` ≈ whole queue; scaling out changes nothing | `basic_qos(prefetch_count=N)`; in Kafka, enough partitions |
| Zero consumers | Depth climbing with `UNACKED=0` and no consumers listed | Alert on consumer count zero with messages waiting |

⭐ **The theme of this lab**: a queue converts a loud failure into a quiet one. Payment being down stops showing up as checkout errors and starts showing up as a number going up — which is an improvement only if someone is watching the number. The four alerts below are not optional extras; they are the other half of the decision to go asynchronous.

| Alert | Threshold | Why |
|-------|-----------|-----|
| Depth growing | Trending up for 10 min | Consumers are losing the race; everything downstream is now late |
| Age of oldest message | Beyond your SLO for that work | The SLO-relevant number — depth alone can mislead in both directions |
| DLQ depth | `> 0` | Every entry is work nobody is doing, and it will not fix itself |
| Consumers | `== 0` while messages waiting | Catches the deploy that quietly stopped starting workers |

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
docker compose down -v
docker image rm lab-02-producer lab-02-consumer 2>/dev/null || true
docker image rm rabbitmq:3.13-management 2>/dev/null || true
```

---

## ✅ Validation

- [ ] Explain what a queue decouples and what it costs you
- [ ] Read the four numbers and say what each one rules in or out
- [ ] Compute drain time from arrival rate, per-consumer capacity, and consumer count
- [ ] Explain why a poison message without a delivery limit degrades throughput permanently
- [ ] Explain at-least-once, and where the duplicate window actually is
- [ ] Write an idempotent consumer, and say why the key comes from the message
- [ ] Explain unbounded prefetch, and its Kafka equivalent
- [ ] Distinguish stuck consumers from absent consumers using `UNACKED`
- [ ] State the four alerts with thresholds, and justify each

---

## 📝 What to Commit

- `docker-compose.yml`, `app/app.py`, `watch-queue.sh`
- Watcher output for: backlog forming, draining after scale-out, and scenario 4
- The DLQ message and the delivery count that put it there
- Your duplicate-charge counts, before and after idempotency
- The four alert rules, with thresholds and justification
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: High Availability and Load Balancing](./lab-01-ha-load-balancing.md) | [Back to Module README](../README.md) | [Next Lab: Platform Engineering — A Golden Path →](./lab-03-golden-path.md)
