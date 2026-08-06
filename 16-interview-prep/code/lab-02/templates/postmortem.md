# Postmortem: [one-line description of user impact]

Fill this in within 48 hours, while you still remember. Replace every bracket. If a section is
genuinely not applicable, say why rather than deleting it.

| | |
|---|---|
| **Date** | YYYY-MM-DD |
| **Severity** | SEV1 / SEV2 / SEV3 |
| **Duration of impact** | [first user affected → last user affected] |
| **Detection** | [alert / customer report / someone noticed] — and how long after impact began |
| **Author** | [you] |
| **Status** | Draft / Reviewed / Actions tracked |

## Impact

What users experienced, in numbers. Requests failed, orders lost, minutes of degradation, how
many customers. "The API was down" is not impact; "checkout failed for ~70% of requests for
23 minutes, roughly 400 attempted orders" is.

## Timeline

All times UTC. Include the things that went *wrong* during the response — a wrong hypothesis
followed for eight minutes is one of the most useful lines in a postmortem.

| Time | Event |
|------|-------|
| 14:38 | v1.4.0 deployed |
| 14:41 | Error rate crosses 5% — impact begins |
| 14:52 | Alert fires; on-call paged (⭐ note the 11-minute detection gap) |
| 14:55 | First status update posted, SEV2 declared |
| 15:01 | Checked the wrong service first — three minutes lost |
| 15:06 | Rollback to v1.3.9 started |
| 15:09 | Error rate back to baseline — impact ends |
| 15:20 | Status RESOLVED |

## Root cause

The technical mechanism, stated so that someone who was not there can follow it. Distinguish
clearly between:

- **Trigger** — what started it (the 14:38 deploy)
- **Root cause** — why that was capable of breaking things (connections borrowed and never returned; the pool had no timeout)
- **Why it was not caught earlier** — the tests, review, and monitoring that could have caught it and did not

## Contributing factors

Everything that made this worse or slower than it needed to be. Detection gap, missing runbook,
a health check that reported healthy while the service failed, an alert threshold too loose, no
staged rollout.

## What went well

Write this section honestly — it is not padding. Fast rollback, good logs, a clear owner.
Knowing which of your practices are working is how you decide what to invest in next.

## Action items

Every item needs an owner and a date, and each one must be something that would have prevented
or shortened *this* incident. "Be more careful" is not an action item.

| Action | Type | Owner | Due |
|--------|------|-------|-----|
| Readiness probe checks pool availability, not process liveness | Prevent | [name] | YYYY-MM-DD |
| Connection acquisition gets a timeout, and exhaustion increments a metric | Prevent | [name] | YYYY-MM-DD |
| Alert on p95 latency as well as error rate — latency moved 11 minutes before errors | Detect | [name] | YYYY-MM-DD |
| Write `docs/runbook.md#checkouterroratehigh` | Respond | [name] | YYYY-MM-DD |
| Canary the next three releases before full rollout | Prevent | [name] | YYYY-MM-DD |

## Lessons

Two or three sentences on what you would tell another team. This is the part that gets read.

---

**Blameless means the analysis stops at the system, not the person.** "Someone deployed a
regression" is never the root cause — the question is what allowed a regression to reach every
user at once with no automated detection for eleven minutes.
