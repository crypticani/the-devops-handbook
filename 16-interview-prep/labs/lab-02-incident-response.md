# Lab 02: Incident Response — Running the Process

## 🎯 Objective

Run an incident end to end: get paged, declare a severity, communicate before you know the cause, mitigate, and write the postmortem.

Lab 01 was about finding the fault. This one is about everything else: declaring a severity, communicating while you still don't know the cause, choosing mitigation over root cause, and writing a postmortem that produces action items rather than apologies.

You will be paged, with traffic still arriving, and you will produce the artefacts a real incident produces — a timeline, status updates, and a postmortem. Those artefacts are the deliverable. The bug is easy; the process is what interviews are actually probing when they ask "walk me through an incident you handled".

> 🧨 **Note on structure**: like Lab 01, this lab **is** the Break It section. The stack starts broken under live traffic and stays broken until you act. There is no happy path to work through first.

---

## 📋 Prerequisites

- Completed [Lab 01: Mock Incident Debugging](./lab-01-mock-incident-debugging.md)
- Docker and Docker Compose
- A timer. Genuinely — the clock is part of the exercise
- Modules 07 (observability), 12 (Kubernetes debugging habits), and 13 §10 (security incident response) as background

```bash
docker --version && docker compose version
```

---

## 📦 Deliverables and Evidence

- `timeline.md` — every event with a UTC timestamp, including your wrong turns
- Three or more status updates, written at the time, not reconstructed afterwards
- `postmortem.md` — completed, with action items that have owners and dates
- Your MTTA and MTTR, calculated, plus the detection gap
- A one-paragraph answer to "why did you mitigate before finding the root cause?"

---

## 📂 Lab Files

Reference copies are in [`../code/lab-02/`](../code/lab-02/).

```bash
cp -r /path/to/the-devops-handbook/16-interview-prep/code/lab-02/. .
chmod +x page.sh
```

**Do not read `api/app.py` yet.** It is in the repository because the lab contract requires it and because you will want it afterwards, but reading it first turns this into a code review instead of an incident. Diagnose from the outside, the way you will have to at 3 a.m.

---

## 🔬 Exercise 1: Before the Page — Set Up the Frame

### Step 1: The Severity Matrix

Severity is not a feeling. It is a decision with consequences: who gets woken, who gets told, how much you are allowed to break to fix it. Agree it before the incident, because during one you will not be thinking clearly.

| | Impact | Response | Comms | Example |
|---|---|---|---|---|
| **SEV1** | Complete outage, or data loss, or a security breach | Page everyone needed, immediately. Wake people up | Status page + exec notification, updates every 15 min | Nobody can log in; customer data exposed |
| **SEV2** | Major function broken or badly degraded for many users; no workaround | On-call leads, during or out of hours | Status page, updates every 30 min | Checkout failing for most users |
| **SEV3** | Minor or partial degradation, or a workaround exists | Next business hours | Internal ticket, no status page | One report format broken; slow admin page |

Two rules that matter more than the table:

- **Anyone may declare.** If the person noticing has to ask permission, the declaration is late.
- **Over-declare, then downgrade.** Downgrading a SEV1 costs you a slightly embarrassing message. Under-declaring costs you the outage.

### Step 2: The Roles

Even solo, name the roles out loud — the point is that they are different jobs, and the failure mode is one person silently trying to do all three.

| Role | Owns | Explicitly does *not* |
|------|------|----------------------|
| **Incident commander** | Decisions, severity, who does what, when to escalate | Debug. The moment the IC is head-down in logs, nobody is running the incident |
| **Operations / investigator** | Hypotheses, commands, mitigation | Talk to stakeholders |
| **Communications / scribe** | Status updates, the timeline as it happens | Change anything |

For this lab you are all three, so do them in sequence rather than in parallel: decide, then investigate, then write. Timestamp everything as you go — a timeline reconstructed from memory two hours later is missing exactly the parts that matter.

### Step 3: Start the Traffic

```bash
docker compose up -d --build
docker compose ps
```

```text
NAME              IMAGE                     STATUS          PORTS
checkout-api      lab-02-api                Up 8 seconds
incident-load     curlimages/curl:8.8.0     Up 7 seconds
incident-nginx    nginx:1.27-alpine         Up 8 seconds    0.0.0.0:8080->80/tcp
```

Customers are now arriving at ~2 requests/second and will keep arriving whatever you do. Give it a minute, then:

```bash
./page.sh
```

**Start your clock now.** Everything below is timed.

---

## 🔬 Exercise 2: The Incident

Work these in order, and write down the time at the start of each.

### Step 1: Acknowledge and Assess (target: T+2 min)

Before touching anything, answer two questions — the same two, every incident:

1. **Is it real?** An alert can fire because the monitoring broke.
2. **What is the user impact, in user terms?**

```bash
# What does a customer actually get?
curl -s -o /dev/null -w 'status=%{http_code} time=%{time_total}s\n' localhost:8080/checkout

# Run it in a loop — one sample during an incident is an anecdote
for i in $(seq 1 10); do
  curl -s -o /dev/null -w '%{http_code} ' -m 6 localhost:8080/checkout
done; echo
```

```text
503 503 503 503 503 503 503 503 503 503
```

That is real, and it is most requests. Note it.

### Step 2: Declare (target: T+3 min)

Pick a severity from the matrix and write it down with a timestamp and a one-line justification. Checkout failing for most users with no workaround is a **SEV2** — or SEV1 if checkout *is* the business. Either is defensible; not deciding is not.

### Step 3: Communicate Before You Understand (target: T+5 min)

This is the step everyone skips, and it is the one that separates people who have run incidents from people who have only debugged. Write update #1 now, from `templates/status-update.md`, while you still know nothing:

```text
[SEV2] Checkout — INVESTIGATING                                   HH:MM UTC

Impact:   Most checkout requests are failing. Browsing and login look
          unaffected.
Status:   Confirmed from outside the system. Cause not yet known.
Next:     Update by HH:MM (+15 min).
Lead:     @you (incident commander)
```

> ⭐ "Cause not yet known" is a complete and professional status. Waiting until you have a cause before communicating is how a 20-minute incident becomes an hour of people asking each other what is happening.

### Step 4: Investigate — Narrow, Don't Wander (target: T+5 to T+15)

Work outside-in, and write each hypothesis down *before* you test it, along with what result would kill it. That habit is what stops the 20-minute rabbit hole.

```bash
# Proxy or backend? The nginx log answers this in one line
docker compose logs --tail=20 nginx
```

```text
2026-08-06T14:52:03+00:00 503 upstream=503 rt=0.003 urt=0.003 GET /checkout
```

`upstream=503` — nginx is faithfully relaying a backend failure. The proxy is fine.

```bash
# What is the backend saying about itself?
docker compose logs --tail=20 api
```

```text
{"level": "ERROR", "service": "checkout-api", "version": "v1.4.0", "msg": "no connection available", "pool_in_use": 20}
```

```bash
# Is it resource exhaustion? (It is not — but rule it out, it is the usual suspect)
docker stats --no-stream

# And now the thing that should unsettle you:
curl -s localhost:8080/healthz; echo
curl -s localhost:8080/readyz; echo
curl -s localhost:8080/pool; echo
```

```text
{"status":"ok","version":"v1.4.0"}
{"in_use":20,"status":"pool exhausted"}
{"in_use":20,"leaking":true,"size":20}
```

⭐ **`/healthz` says the service is healthy while every customer request fails.** Your orchestrator believes this service is fine. Nothing will restart it, no load balancer will take it out of rotation. Write that down — it is the single most valuable finding of the incident and it belongs in the postmortem's contributing factors, not just in your head.

### Step 5: Mitigate — Two Choices, Pick One and Justify It (target: T+15)

You now know the mechanism (connections are being taken and not given back) but not the code defect. **Do not go looking for the defect yet.** Stop the impact first.

| Option | Command | What it buys | What it costs |
|--------|---------|--------------|---------------|
| **Restart** | `docker compose restart api` | Recovery in seconds | It recurs in ~10 seconds under this traffic. You will be restarting forever, and you have destroyed the evidence in the process |
| **Roll back** | `LEAK=0 VERSION=v1.3.9 docker compose up -d --force-recreate api` | Recovery, and it *stays* recovered | You need to have kept the previous version deployable. That is a decision you make months earlier |

Try the restart first, deliberately, and watch it come back:

```bash
docker compose restart api
sleep 2
for i in $(seq 1 10); do curl -s -o /dev/null -w '%{http_code} ' localhost:8080/checkout; done; echo
sleep 12
for i in $(seq 1 10); do curl -s -o /dev/null -w '%{http_code} ' localhost:8080/checkout; done; echo
```

```text
200 200 200 200 200 200 200 200 200 200
503 503 503 503 503 503 503 503 503 503
```

Recovered, then failed again. **A mitigation that recurs is not a mitigation** — it is a way to spend your night. Now roll back properly:

```bash
LEAK=0 VERSION=v1.3.9 docker compose up -d --force-recreate api
sleep 15
for i in $(seq 1 20); do curl -s -o /dev/null -w '%{http_code} ' localhost:8080/checkout; done; echo
curl -s localhost:8080/pool; echo
```

```text
200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200 200
{"in_use":0,"leaking":false,"size":20}
```

Impact has ended. Record the time — this timestamp is the end of impact, and it is what MTTR is measured to, not the moment you finished understanding the bug.

### Step 6: Confirm, Then Communicate Again (T+18)

Do not declare resolved on one green sample. Watch for a few minutes at real traffic — the previous failure took ten seconds to reappear, and something slower would take longer.

```bash
docker compose logs --tail=30 nginx | grep -c ' 200 '
docker compose logs --tail=30 nginx | grep -c ' 503 '
```

Then post update #2 (`MONITORING`) and, once you are satisfied, a final `RESOLVED`. The RESOLVED update must state that a postmortem is coming — otherwise everyone assumes the work is finished, and the action items never get written.

### Step 7: Now Find the Defect

With impact over and the clock stopped, read `api/app.py`. The `finally:` block only releases the connection when `LEAK` is false — every request on the current release permanently consumes one of twenty connections.

Note carefully what you are now doing: root-causing *after* recovery, without time pressure, with the failing version still available to inspect. This ordering is the entire point of the exercise, and "restore service first, diagnose second" is the answer interviewers are listening for.

---

## 🔬 Exercise 3: The Postmortem

### Step 1: Compute Your Numbers

| Metric | Definition | Yours |
|--------|-----------|-------|
| **Detection gap** | Impact began → alert fired | The page said the alert had a `for: 2m` window. In this lab, impact began when you started the stack |
| **MTTA** | Alert fired → acknowledged | |
| **MTTR** | Alert fired → impact ended | |
| **Time to root cause** | Alert fired → defect understood | ⭐ Deliberately *after* MTTR |

If your time-to-root-cause is longer than your MTTR, you did this correctly.

### Step 2: Write It

Fill in `templates/postmortem.md` completely. Two sections carry most of the value:

- **Contributing factors** — the health check that reported healthy while failing, the absent runbook the alert linked to, no latency alert (latency climbed before the errors did), no canary so the release hit every user at once.
- **Action items** — each one must have prevented or shortened *this* incident, with an owner and a date. Aim for one detect, one prevent, one respond.

### Step 3: The Blameless Test

Read your own draft and check:

- Does any sentence identify a person as the cause? Rewrite it to name the system gap that let a normal human action cause an outage.
- Is "be more careful" or "add more testing" anywhere? Neither is an action item. What specific test, on what trigger?
- Would someone from another team learn something? If not, the Lessons section is padding.

### Summary

| Failure in the response | How you'd notice | How you prevent it |
|-------------------------|------------------|--------------------|
| No severity declared | Nobody knows whether to wake anyone; nobody owns it | Declare within 3 minutes; anyone may declare; over-declare then downgrade |
| Silence until the cause is known | Stakeholders interrupt the investigation to ask for updates | First update within 5 minutes, saying explicitly what you do not know |
| Root-causing while users are down | Long MTTR, and a mitigation you never applied | Mitigate first, keep the evidence, diagnose after |
| Restart as the mitigation | Recovery, then recurrence, then a night of restarts | Prefer rollback; require the previous version to stay deployable |
| Health check that lies | Orchestrator sees healthy, users see 503 | Readiness must exercise what serving requires |
| Postmortem with no owners or dates | The same incident happens again next quarter | Every action item has a name and a date, tracked like any other work |

⭐ **The theme of this lab**: the technical fault was one missing line, and it accounted for almost none of the outage duration. Everything else — detection lag, the eleven minutes before anyone knew, the lying health check, the restart that bought ten seconds — was process. That ratio holds in real incidents, which is why the process is what gets interviewed.

**Write this up** in `failure-notes.md` alongside your postmortem.

---

## 🧹 Cleanup

```bash
docker compose down -v
docker image rm lab-02-api 2>/dev/null || true
```

Keep `timeline.md`, your status updates, and `postmortem.md` — a completed postmortem is one of the strongest artefacts you can put in a portfolio, because almost nobody has one.

---

## ✅ Validation

- [ ] Name the three severity levels and what each one triggers in response and comms
- [ ] Explain the incident commander role and why the IC should not be debugging
- [ ] Post a first status update within five minutes, stating impact without a known cause
- [ ] Determine from outside the system that the failure is real and quantify user impact
- [ ] Use the nginx log to tell a proxy fault from a backend fault in one line
- [ ] Explain why `/healthz` returning 200 during the outage is the most important finding
- [ ] Justify your choice of mitigation, and explain why a restart that recurs is not one
- [ ] Compute detection gap, MTTA, MTTR, and time-to-root-cause, and explain why the last is longest
- [ ] Produce a postmortem whose action items all have owners and dates, and none of which is "be more careful"

---

## 📝 What to Commit

- `timeline.md` with UTC timestamps, including at least one wrong hypothesis
- All status updates, in the order you posted them
- `postmortem.md`, complete
- Your metrics table, with the numbers worked out
- `failure-notes.md` covering the response failures in the summary table

---

[← Previous Lab: Mock Incident Debugging](./lab-01-mock-incident-debugging.md) | [Back to Module README](../README.md) | [Handbook Home](../../README.md)
