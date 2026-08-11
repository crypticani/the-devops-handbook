# Lab 04: Kafka — Partitions, Consumer Groups, and Offsets

## 🎯 Objective

Operate a partitioned log the way Kafka actually behaves: read lag per partition, prove that partition count rather than replica count is your parallelism ceiling, and cause the offset failures that lose or repeat work while every dashboard stays green.

Lab 02 was a queue: a message is delivered, acknowledged, and gone. This is a log — records stay for the retention window and each consumer group tracks its own offset. That single difference relocates every failure. Nothing here goes missing because a message was lost; things go wrong because an *offset* moved when the work had not been done, or because the partition that holds your traffic has exactly one consumer allowed to read it.

---

## 📋 Prerequisites

- Read [§7 Async Communication and Message Queues](../README.md#7-async-communication-and-message-queues), especially the queue-versus-log table
- Completed [Lab 02: Message Queues and Async Failure](./lab-02-message-queues.md) — this lab assumes you have already seen at-least-once produce duplicates
- Docker and Docker Compose, ~2 GB free
- Python basics (Module 04) — you'll read a consumer loop, not write one

```bash
docker --version && docker compose version
```

---

## 📦 Deliverables and Evidence

- A `watch-lag.sh` capture showing lag per partition, and the key → partition mapping that produced it
- Proof that three consumers each own one partition, and that the fourth and fifth own nothing
- A hot-partition capture: lag climbing on one partition while the others sit at zero
- A rebalance storm: the rebalance count over a fixed window, and the same offsets processed repeatedly
- The commit-before-work numbers: records produced, records processed, and the lag that read zero anyway
- A replay: total lag back to zero after reprocessing the whole log from offset 0
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-04/`](../code/lab-04/).

```bash
cp -r /path/to/the-devops-handbook/14-system-design-devops/code/lab-04/. .
chmod +x watch-lag.sh
```

One image runs as both producer and consumer (`MODE`), a single broker runs in KRaft mode with no ZooKeeper, and every failure in this lab is an environment variable — no scenario needs a code edit.

---

## 🔬 Exercise 1: The Log, the Key, and the Partition

### Step 1: The Number You Cannot Take Back

Read `declare()` in `app.py` before starting anything. One argument decides how much parallelism this system can ever have:

```python
topic = NewTopic(TOPIC, num_partitions=PARTITIONS, replication_factor=1)
```

A consumer group can have at most one consumer per partition. Three partitions means three useful consumers, whatever your `replicas:` field says. You can raise the count later — Scenario 1 does — but you can never lower it, and raising it re-maps keys to partitions, which is not free.

### Step 2: Start It and Watch

```bash
docker compose up -d --build
docker compose ps
```

The broker takes about 30 seconds to report healthy; the producer and consumer wait on it with `condition: service_healthy`. In a second terminal, and leave it running for the whole lab:

```bash
./watch-lag.sh
```

```text
TIME       PARTITION   CURRENT       END     LAG  OWNER
17:23:33           0       120       126       6  7fba6c385c19-c15c191b-2336-4b2
17:23:33           1       180       188       8  7fba6c385c19-c15c191b-2336-4b2
17:23:33           2       241       245       4  7fba6c385c19-c15c191b-2336-4b2
17:23:33       TOTAL       541       559      18  members=1
```

This is the Kafka equivalent of Lab 02's four numbers, except the interesting part is that there is **one row per partition**:

| Column | Question | What "bad" looks like |
|--------|----------|----------------------|
| `CURRENT` | How far has the group committed? | `-` means this group has never committed here at all |
| `END` | How far has the producer written? | Climbing while `CURRENT` does not is the whole failure mode |
| `LAG` | `END - CURRENT` — how many records is nobody past yet? | ⭐ Growing on **one** partition is a different bug from growing on all |
| `OWNER` | Which consumer holds this partition? | `-` means nobody is reading it |
| `members=` | How many consumers are in the group? | More members than partitions means some of them are idle |

> ⭐ **Total lag is the number people alert on and the number that hides things.** A hot partition, an evicted consumer, and a newly added unread partition all keep the total looking survivable. Read the spread, not just the sum.

### Step 3: The Key Decides the Partition

The producer keys each order by customer. Check what that bought you:

```bash
docker compose logs consumer | grep CHARGED | python3 -c "import sys,json,collections
r=[json.loads(l.split('| ',1)[1]) for l in sys.stdin]
by=collections.defaultdict(set)
for x in r: by[x['customer']].add(x['partition'])
print('customers:', len(by), '| any on >1 partition:', [k for k,v in by.items() if len(v)>1])
print('records per partition:', collections.Counter(x['partition'] for x in r))"
```

```text
customers: 50 | any on >1 partition: []
records per partition: Counter({2: 186, 1: 148, 0: 71})
```

Two findings in four lines. **Every customer's records live on exactly one partition** — that is the ordering guarantee, and it is the only one Kafka offers: per partition, never global. If you need a customer's events processed in order, key by customer and accept that one consumer handles all of that customer's work.

And **the partitions are not evenly loaded** — 71, 148, 186 from the same hash. Fifty keys over three partitions is not one third each; you need considerably more distinct keys than partitions before the hash looks fair, which is the mild version of Scenario 2.

---

## 🔬 Exercise 2: One Consumer per Partition

```bash
docker compose up -d --scale consumer=3
docker compose logs consumer | grep -E 'assigned|revoked' | tail -8
```

```text
{"event": "assigned", "worker": "fea2ac02ffbc", "partitions": [0, 1, 2]}
{"event": "revoked",  "worker": "fea2ac02ffbc", "partitions": [0, 1, 2]}
{"event": "assigned", "worker": "fea2ac02ffbc", "partitions": [2]}
{"event": "assigned", "worker": "38af09a519d0", "partitions": [1]}
{"event": "assigned", "worker": "86ba44ee61fe", "partitions": [0]}
```

Read the middle line. When the second consumer joined, the first one had **everything revoked** before the new assignment was handed out — a stop-the-world rebalance, which is the default `range` strategy doing exactly what it is documented to do. Every join, every leave, and every deploy pauses the whole group. That is tolerable at 200 ms and an outage at 30 seconds, and Scenario 3 is what turns it into the latter.

```bash
docker exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --describe --group orders --members
```

```text
GROUP    CONSUMER-ID                                        HOST          CLIENT-ID       #PARTITIONS
orders   86ba44ee61fe-428b8442-2fc1-4bf3-9327-7f9d7ebdd455  /172.18.0.5   86ba44ee61fe    1
orders   38af09a519d0-b0dda8f2-3c73-4218-baf9-a642f1f7dcdc  /172.18.0.6   38af09a519d0    1
orders   fea2ac02ffbc-077d038a-1527-4fc3-8d9b-207c9c41ff61  /172.18.0.3   fea2ac02ffbc    1
```

Three consumers, one partition each, and the capacity model is the same arithmetic as Lab 02 with one extra term: arrival rate against `consumers × (1000 / WORK_MS)`, **capped at `partitions × (1000 / WORK_MS)`**. At `WORK_MS=40` that ceiling is 75 records/second for this topic and no amount of scaling moves it.

---

## 🔬 Exercise 3: Replay — The Thing a Queue Cannot Do

A consumer bug shipped on Friday and processed two days of orders wrongly. In Lab 02 those messages were acknowledged and deleted, so the answer was "restore from somewhere else". Here the records are still in the log and the offset is just a number you own.

```bash
docker compose stop consumer

# You cannot rewind a group that is running — wait for it to report Empty
until docker exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 --describe --group orders --state \
        2>/dev/null | grep -q Empty; do sleep 3; done

docker exec kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group orders --topic orders --reset-offsets --to-earliest --execute
```

```text
GROUP    TOPIC    PARTITION  NEW-OFFSET
orders   orders   0          0
orders   orders   1          0
orders   orders   2          0
```

```bash
docker compose up -d consumer
./watch-lag.sh      # LAG jumps to the whole log, then drains as it reprocesses
```

Attempting the reset with the group still live fails with `Assignments can only be reset if the group 'orders' is inactive`. That is a feature: rewinding offsets under a running consumer would race the commits it is still making. Replay is a maintenance operation with a stop, a reset, and a start — script it and test the script, because you will be doing it during an incident.

> ⭐ `--to-earliest` is the blunt instrument. `--to-datetime 2026-08-11T09:00:00.000`, `--shift-by -500`, and `--to-offset N` exist for the same reason, and `--dry-run` in place of `--execute` prints what would change. **Replay only helps if the consumer is idempotent** — reprocessing 400 orders means charging 400 cards again unless the pattern from Lab 02 is in place. Retention is the other half: `retention.ms` decides how far back "earliest" actually is, and the default is seven days.

---

## 🧨 Break It: Four Kafka Failures

Each scenario restores state before the next one. `docker compose down` discards the log, which is what makes the arithmetic in each scenario clean.

### Scenario 1: More Consumers Than Partitions

**Break it.** Scale past the partition count — three partitions, five consumers:

```bash
docker compose up -d --scale consumer=5
sleep 20
docker compose logs consumer | grep assigned | tail -3
```

**Symptom.** Two consumers are running, healthy, and hold nothing:

```text
{"event": "assigned", "worker": "fea2ac02ffbc", "partitions": null}
```

```bash
docker exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --describe --group orders --members
```

```text
orders   86ba44ee61fe-428b...   /172.18.0.5   86ba44ee61fe   1
orders   2992e441ff9d-c8c3...   /172.18.0.8   2992e441ff9d   1
orders   38af09a519d0-b0dd...   /172.18.0.6   38af09a519d0   1
orders   f97781634d8c-b064...   /172.18.0.7   f97781634d8c   0      ← idle
orders   fea2ac02ffbc-077d...   /172.18.0.3   fea2ac02ffbc   0      ← idle
```

**Root cause.** A partition is assigned to exactly one consumer in a group, so the partition count is a hard ceiling on useful consumers. Every replica past it costs memory, a connection, and a rebalance on each deploy while contributing nothing. This is the failure that makes an HPA look broken: pods scale on CPU, the two new pods get no partitions, per-pod CPU falls, and the autoscaler happily adds more.

**Fix.** Add partitions — and then deal with the two things that come with it:

```bash
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 \
  --alter --topic orders --partitions 6
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 \
  --describe --topic orders | head -1
```

```text
Topic: orders   PartitionCount: 6   ReplicationFactor: 1   Configs:
```

**Catch one: nobody notices immediately.** Clients cache topic metadata (`topic.metadata.refresh.interval.ms`, five minutes by default). The producer keeps writing to three partitions until it refreshes, and — worse — the consumer group is not assigned the new partitions either, so records land where **no lag is reported at all**:

```text
17:53:53           0       245       245       0  9e20d4f350e2-1a189b1f-b92e-442
17:53:53           1       347       356       9  9e20d4f350e2-1a189b1f-b92e-442
17:53:53           2       405       407       2  9e20d4f350e2-1a189b1f-b92e-442
17:53:53       TOTAL       997      1008      11  members=1
```

Partitions 3, 4, and 5 are absent from that table and accumulating records. Restart both to close the gap:

```bash
docker compose restart producer consumer
./watch-lag.sh          # six rows now, and the backlog on 3-5 becomes visible
```

**Catch two: keys move.** The partition for a key is `hash(key) % partitions`, so changing the divisor re-maps roughly half of them:

```bash
docker compose logs consumer | grep CHARGED | python3 -c "import sys,json,collections
r=[json.loads(l.split('| ',1)[1]) for l in sys.stdin]
by=collections.defaultdict(set)
for x in r: by[x['customer']].add(x['partition'])
moved=sorted((k,sorted(v)) for k,v in by.items() if len(v)>1)
print('keys split across partitions:', len(moved), 'of', len(by)); print(moved[:4])"
```

```text
keys split across partitions: 27 of 50
[('cust-0000', [0, 3]), ('cust-0003', [0, 3]), ('cust-0005', [1, 4]), ('cust-0007', [1, 4])]
```

Twenty-seven customers now have records on two partitions, being consumed by two different consumers, in no defined order relative to each other. **Per-key ordering does not survive a partition count change.** If ordering matters, the migration is a new topic and a controlled cutover, not `--alter`. Which is why the partition count is a capacity decision you make once, with room to spare.

```bash
docker compose down                              # back to 3 partitions on the next up
```

### Scenario 2: The Hot Key

**Break it.** Key every order the same way — one tenant that dwarfs the others, or a `null`-to-`"unknown"` default, or a `customer_id` field that was empty in a batch import:

```bash
KEYS=1 WORK_MS=200 docker compose up -d --scale consumer=3
```

**Symptom.** Wait a minute, then read the spread:

```text
TIME       PARTITION   CURRENT       END     LAG  OWNER
17:31:23           2         -         0       -  dc2321f1a015-f74b5fd9-33b6-4f1
17:31:23           1         -         0       -  a3d9e0aaf7b0-8ba7b15f-a17b-48f
17:31:23           0       220       552     332  162c1c6bc63d-cfa78002-733e-4cf
17:31:23       TOTAL       220       552     332  members=3

17:32:06           0       430       988     558  162c1c6bc63d-cfa78002-733e-4cf
17:32:06       TOTAL       430       988     558  members=3
```

One partition holds everything and its lag has gone from 332 to 558 in 43 seconds. The other two consumers own partitions that will never receive a record. Confirm who is actually working:

```bash
docker compose logs consumer | grep CHARGED | python3 -c "import sys,json,collections
print(collections.Counter(json.loads(l.split('| ',1)[1])['worker'] for l in sys.stdin))"
```

```text
Counter({'162c1c6bc63d': 676})
```

**Root cause.** Parallelism in Kafka is bounded by *key distribution*, not by partition count. One key means one partition means one consumer, and scaling out is precisely useless — the same shape as Lab 02's unbounded prefetch, arrived at from the opposite direction. The tell is the spread: total lag alone looks like a capacity problem and invites the wrong fix.

**Fix.** Restore a distributed key:

```bash
docker compose down
WORK_MS=200 docker compose up -d --scale consumer=3          # KEYS back to 50
```

> ⭐ When the traffic really is one key — one enormous tenant — you have three options and they are all trade-offs: a **composite key** (`customer:order_id`) which parallelises and gives up per-customer ordering; a **dedicated topic** for that tenant, which isolates it and doubles your operational surface; or accepting the ceiling and making the per-record work faster. Choose deliberately, and write down which ordering guarantee you just gave up.

### Scenario 3: The Rebalance Storm

**Break it.** Make a batch take longer than the group allows between polls. `max.poll.interval.ms` is the progress deadline, and `BATCH × WORK_MS` here is 16 seconds against an 8-second budget:

```bash
docker compose down
MAX_POLL_MS=8000 BATCH=20 WORK_MS=800 docker compose up -d --scale consumer=2
```

**Symptom.** Two minutes later, the group has committed nothing at all:

```text
TIME       PARTITION   CURRENT       END     LAG  OWNER
17:38:44           0         -       252       -  1c9c4b273dbb-af0e13fa-af2a-442
17:38:44           1         -       435       -  1c9c4b273dbb-af0e13fa-af2a-442
17:38:44           2         -       541       -  1c9c4b273dbb-af0e13fa-af2a-442
17:38:44       TOTAL         0      1228       0  members=1
```

⭐ **Total lag reads 0 and 1,228 records are unprocessed.** `CURRENT` is `-` on every partition: not one commit has ever succeeded, so the arithmetic has nothing to subtract. A dashboard built on total lag shows a flat green line through this entire outage.

**Investigate.**

```bash
docker compose logs consumer | grep assigned | python3 -c "import sys,json
ts=sorted(json.loads(l.split('| ',1)[1])['ts'] for l in sys.stdin)
print('rebalances:', len(ts), 'over', round(ts[-1]-ts[0]), 'seconds')"

docker compose logs consumer | grep CHARGED | python3 -c "import sys,json,collections
r=[json.loads(l.split('| ',1)[1]) for l in sys.stdin]
print('charges', len(r), '| unique (partition,offset)', len({(x['partition'],x['offset']) for x in r}))
print(collections.Counter(f\"p{x['partition']}:{x['offset']}\" for x in r).most_common(3))"
```

```text
rebalances: 15 over 170 seconds
charges 261 unique (partition,offset) 20
[('p2:0', 14), ('p2:1', 14), ('p2:2', 14)]
```

**261 charges for 20 records.** Every offset processed fourteen times, and offset 0 is still not committed. The group state confirms the churn:

```bash
docker exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --describe --group orders --state
```

```text
GROUP    COORDINATOR (ID)   ASSIGNMENT-STRATEGY   STATE      #MEMBERS
orders   kafka:9092  (1)    range                 Stable     1
```

Run it repeatedly and you'll catch `PreparingRebalance` and a `#MEMBERS` that flips between 1 and 2 — a group that never settles long enough to finish a batch.

**Root cause.** The consumer is evicted for exceeding the poll deadline, its uncommitted batch is reassigned, the new owner starts the same batch from the same offset, and hits the same deadline. Each eviction triggers a stop-the-world rebalance under the default `range` strategy, so the whole group restarts its work. Progress is zero and CPU is at 100%: a livelock, driven entirely by a timeout mismatch.

**Fix.** Make the batch fit the deadline — reduce the batch, or raise the deadline, ideally both:

```bash
docker compose down
BATCH=2 WORK_MS=800 docker compose up -d --scale consumer=2      # 1.6s per batch, 300s budget
```

> ⭐ Three configuration facts worth memorising. **`session.timeout.ms` and `max.poll.interval.ms` are different timers** — the first asks "is the process alive?" (heartbeats, background thread), the second asks "is it making progress?", and only the second is affected by slow work. **`max.poll.interval.ms` must be ≥ `session.timeout.ms`**; librdkafka refuses to construct a consumer otherwise, which is a nicer failure than the Java client's. And **`partition.assignment.strategy=cooperative-sticky`** turns the stop-the-world rebalance into an incremental one, so only the moving partitions pause — the single highest-value setting change on this list.

### Scenario 4: The Offset That Moved Before the Work Was Done

**Break it.** Commit the batch up front — the shape you get from auto-commit with a slow handler, or from anyone who committed early "to avoid duplicates":

```bash
docker compose down
COMMIT_BEFORE_WORK=1 CRASH_AFTER=25 BATCH=20 docker compose up -d
sleep 30
docker compose stop producer      # freeze the log so the arithmetic is clean
docker exec kafka /opt/kafka/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic orders
```

```text
orders:0:71
orders:1:148
orders:2:186
```

405 records produced, and the consumer crashes every 25 records — a crash loop, an OOM kill, a rolling deploy. Wait for the backlog to clear:

```bash
until [ "$(docker exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 --describe --group orders 2>/dev/null \
    | awk '$3 ~ /^[0-9]+$/ {s+=($6=="-"?0:$6)} END {print s+0}')" = "0" ]; do sleep 5; done
```

**Symptom.** Everything is caught up, and a third of the orders were never processed:

```text
TIME       PARTITION   CURRENT       END     LAG  OWNER
17:48:03           0        71        71       0  bbb7f9d121e3-48a5f138-a0a2-460
17:48:03           1       148       148       0  bbb7f9d121e3-48a5f138-a0a2-460
17:48:03           2       186       186       0  bbb7f9d121e3-48a5f138-a0a2-460
17:48:03       TOTAL       405       405       0  members=1
```

```bash
docker compose logs consumer | grep CHARGED | grep -o 'ord-[0-9]*' | sort -u | wc -l
```

```text
256
```

**405 produced, 256 charged, lag zero.** 149 orders — 37% — are permanently unprocessed, and there is no error, no DLQ, and no metric anywhere that says so. The customer was told their order was placed.

**Investigate.**

```bash
docker compose logs consumer | grep -E 'committed_ahead|crashing' | tail -4
```

```text
{"event": "committed_ahead", "count": 20, "offset": 339}
{"event": "committed_ahead", "count": 20, "offset": 359}
{"event": "crashing", "processed": 25}
```

Each life committed offset 359 and then died after five of those twenty records. On restart the group resumed from 359 — the fifteen it had committed but not processed were skipped, per crash, forever.

**Root cause.** The offset is a claim about *work completed*, and committing before the work makes it a lie. That is at-most-once delivery, and its failure mode is silent loss rather than duplication. Lag cannot detect it, because lag only ever measured the offset.

**Fix.** Commit after the work — at-least-once, the same trade Lab 02 made — and then handle the duplicates:

```bash
docker compose down
docker compose up -d          # COMMIT_BEFORE_WORK back to 0
```

The duplicate window is now the batch, not the record: a crash mid-batch replays everything since the last commit, so at `BATCH=10` up to nine records repeat. Idempotency is what makes that safe, keyed on `order_id` in a shared store — the eight-line pattern in §7.

> ⭐ **The three guarantees, in one place.** *At-most-once*: commit first, lose work silently, and never notice. *At-least-once*: commit last, duplicate on crash, and require an idempotent consumer — the correct default for almost everything. *Exactly-once*: Kafka transactions (`isolation.level=read_committed`, a transactional producer, offsets committed inside the transaction), which work only where the side effect is also Kafka. A charge on a card is not, so for that path "exactly-once" means at-least-once plus idempotency, every time.

### Summary

| Failure | How you detect it | How you prevent it |
|---------|------------------|--------------------|
| Consumers > partitions | Members with `#PARTITIONS 0`; scaling changes throughput not at all | Size the partition count for future throughput; alert when members exceed partitions |
| Hot key | Lag climbing on one partition while the others sit at 0 | A key with real cardinality; composite key or dedicated topic for a whale |
| Rebalance storm | Repeated assignments; the same offsets processed over and over; `CURRENT` stuck at `-` | `BATCH × WORK_MS` well inside `max.poll.interval.ms`; `cooperative-sticky` |
| Commit before work | Records produced ≫ records processed, with lag at 0 | Commit after the work, and make the consumer idempotent |

⭐ **The theme of this lab**: in a queue the message is the unit of truth, and in a log the *offset* is — so every failure here is a lie told by a number. Lag reads zero when nothing was ever committed, reads healthy when one partition is drowning, and reads caught-up when a third of the work was skipped. Which is why the alerts are about the shape of the lag, not its sum.

| Alert | Threshold | Why |
|-------|-----------|-----|
| Max lag across partitions growing | Trending up for 10 min | Catches the hot partition and the evicted consumer that total lag hides |
| Age of oldest unprocessed record | Beyond your SLO for that work | The SLO-relevant number; `--describe` gives you records, timestamps give you time |
| Rebalance rate | More than a few per hour outside deploys | A group that rebalances constantly is doing no work and duplicating what it does |
| Group members | `!=` expected count, or `> partitions` | Catches both the deploy that started nothing and the autoscaler adding idle pods |
| Committed offsets not advancing | No movement for N minutes with `END` climbing | The only signal that survives Scenario 3, where lag itself reads 0 |

**Write this up** in `failure-notes.md`.

---

## 🔀 Queue or Log?

You have now operated both. This is the comparison to give in an interview, and it is all first-hand:

| | RabbitMQ (Lab 02) | Kafka (this lab) |
|---|---|---|
| After processing | Acknowledged and deleted | Retained for the retention window; only an offset moves |
| Health metric | Queue depth, unacked, consumer count | ⭐ Lag **per partition** — the sum hides too much |
| Parallelism limit | Consumer count, tunable with prefetch | Partition count, fixed at creation and painful to change |
| Ordering | Best-effort; per-message routing | Guaranteed per partition, so per key — never global |
| Failed message | Retry counter, then a dead letter queue | No DLQ concept; you build one, or you block the partition |
| Recovering from a consumer bug | Replay from the DLQ, if it was captured | Reset offsets and reprocess the log |
| Silent failure mode | Zero consumers with a growing depth | Committed offsets that outran the work |
| Reach for it when | Work distribution: emails, charges, thumbnails | Several consumers of the same stream; replay; event sourcing |

The honest one-liner: **a queue is a work list, a log is a shared history**. Choosing a log because it is "more scalable" and then using it as a work list gets you a fixed parallelism ceiling and no dead letter queue, which is the trade you should be able to name before you make it.

---

## 🧹 Cleanup

```bash
docker compose down -v
docker image rm lab-04-producer lab-04-consumer 2>/dev/null || true
docker image rm apache/kafka:3.9.0 2>/dev/null || true
```

---

## ✅ Validation

- [ ] Explain what a log gives you that a queue does not, and what it costs
- [ ] Read a per-partition lag table and say what the spread rules in or out
- [ ] State the parallelism ceiling for a consumer group, and why replicas past it are waste
- [ ] Explain what the key does, and what ordering guarantee you actually get
- [ ] Explain why changing the partition count breaks per-key ordering
- [ ] Distinguish `session.timeout.ms` from `max.poll.interval.ms`, and say which slow work breaks
- [ ] Explain a rebalance storm, why total lag reads 0 during one, and the two fixes
- [ ] Explain at-most-once versus at-least-once in terms of where the commit happens
- [ ] Replay a topic from a given point, including why the group must be stopped first
- [ ] State the five alerts with thresholds, and justify each

---

## 📝 What to Commit

- `docker-compose.yml`, `app/app.py`, `watch-lag.sh`
- Lag captures for: the healthy baseline, the hot partition, and the rebalance storm
- The members table showing two consumers with zero partitions
- Your rebalance count, and the charges-versus-unique-offsets numbers
- Produced, processed, and lag figures from Scenario 4
- The offset reset output and the lag returning to zero after replay
- The five alert rules, with thresholds and justification
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: Platform Engineering — A Golden Path](./lab-03-golden-path.md) | [Back to Module README](../README.md) | [Module 15: Projects →](../../15-projects/)
