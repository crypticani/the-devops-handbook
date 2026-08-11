# Lab 03: Platform Engineering — Building a Golden Path

## 🎯 Objective

Build the paved road: one command that takes a team from "we need a service" to a repository with probes, limits, a pipeline, alerts, and a named owner already in place — then enforce those defaults so they survive contact with real teams.

This is the smallest honest version of an internal platform. You'll measure what it buys, then break it in the four ways platforms fail: drift, cage, missing ownership, and unmeasured adoption.

> 🧨 **Note on structure**: the Break It section here breaks the *platform*, not an application. That is deliberate — a platform is production infrastructure for engineers, and its failure modes are organisational as much as technical.

---

## 📋 Prerequisites

- Read [§11 Platform Engineering](../README.md#11-platform-engineering--building-the-paved-road)
- Completed [Lab 02: Message Queues and Async Failure](./lab-02-message-queues.md)
- Bash, `envsubst` (from `gettext`), and Modules 06, 07, 12 for the defaults being encoded

```bash
command -v envsubst || sudo apt-get install -y gettext-base
```

---

## 📦 Deliverables and Evidence

- A generated service, and the policy gate passing on it
- Your measured **lead time**: seconds from command to a compliant service, versus your honest estimate of doing it by hand
- The policy gate failing on a hand-edited manifest, with the output
- A drift report after the template moves, listing which services are behind
- Your platform's three metrics, with the numbers you actually measured
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-03/`](../code/lab-03/).

```bash
cp -r /path/to/the-devops-handbook/14-system-design-devops/code/lab-03/. .
chmod +x new-service.sh platform-check.sh
```

```text
new-service.sh        the golden path — envsubst over templates, deliberately boring
platform-check.sh     the policy gate — verifies every promise the platform makes
PLATFORM-VERSION      the template version, stamped into every generated service
templates/            what a new service starts with
```

Generated services land in `services/`, which is your output, not part of the platform.

---

## 🔬 Exercise 1: The Paved Road

### Step 1: Read What Is Being Encoded

Open `templates/deployment.yml.tmpl` before running anything. Every default in it is a decision someone would otherwise have to make correctly, alone, under time pressure:

| Default | Why it's the default |
|---------|---------------------|
| Both probes, with `/readyz` checking dependencies | Liveness restarts, readiness removes from rotation. Getting this backwards restart-loops a busy service (Module 12) |
| Requests **and** limits | No requests means the scheduler is guessing; no limits means one bug takes the node |
| `runAsNonRoot`, dropped capabilities | Blast radius, for free |
| Image tagged `REPLACED_BY_CI`, never `:latest` | What you tested is what you ship (Module 06) |
| `/metrics` with RED signals | Dashboards and alerts need no per-service negotiation (Module 07) |
| A catalogue entry with an owner and tier | ⭐ Without this an incident has no human attached to it |

That table is the platform. The generator is fifty lines of `envsubst` — the value is in what the templates say, not in the tooling.

### Step 2: Walk the Path, and Time It

```bash
time ./new-service.sh payments-api payments-team 1
```

```text
✅ payments-api created at services/payments-api (template 1.2.0)
   owner: payments-team · tier: 1

   next:  ./platform-check.sh services/payments-api

real    0m0.089s
```

```bash
find services/payments-api -type f | sort
```

```text
services/payments-api/.github/workflows/ci.yml
services/payments-api/README.md
services/payments-api/app/Dockerfile
services/payments-api/app/app.py
services/payments-api/k8s/deployment.yml
services/payments-api/monitoring/alerts.yml
services/payments-api/service.yaml
```

Now write down your honest estimate of how long it takes a team to produce that by hand — correctly, with both probes right, limits set, a scan in the pipeline, four alerts, and a catalogue entry. Half a day is a generous answer, and it is a half day *per service* that also produces a subtly different result each time. **That gap is the entire business case**, and "lead time for a new service" is the metric that expresses it.

### Step 3: The Gate

```bash
./platform-check.sh
```

```text
══ payments-api
    ✅ has an owner
    ✅ has a tier
    ✅ liveness probe
    ✅ readiness probe
    ✅ resource requests
    ✅ resource limits
    ✅ runs as non-root
    ✅ no privilege escalation
    ✅ image is not :latest
    ✅ has alert rules
    ✅ exposes /metrics
    ✅ exposes /readyz
    ✅ has a pipeline
    ✅ on platform version 1.2.0

────────────────────────────────────────
checked: 1 service(s)
on current template (1.2.0): 1/1
✅ every service meets the platform contract
```

The generated pipeline runs this same script (`templates/ci.yml.tmpl`, the `policy` job). Generating good defaults is the easy half; **verifying they are still there** is the half that survives contact with real teams.

### Step 4: Add a Second Service and Look at Fleet Numbers

```bash
./new-service.sh search-api search-team 2
./new-service.sh billing-api payments-team 1
./platform-check.sh | tail -5
```

Three services, one command each, all compliant, every one with an owner. That last line — the fraction on the current template — is a platform metric, not a service metric. Which brings us to how platforms fail.

---

## 🧨 Break It: Four Ways a Platform Fails

### Scenario 1: Drift — The Fix That Only New Services Get

**Break it.** You improve the template: a security fix, a new required label, a better probe. Bump the version as any real change would:

```bash
echo "1.3.0" > PLATFORM-VERSION
./new-service.sh reporting-api data-team 3 >/dev/null      # a new service gets it
./platform-check.sh | tail -6
```

**Symptom.**

```text
checked: 4 service(s)
on current template (1.3.0): 1/4
drifted: payments-api (1.2.0) search-api (1.2.0) billing-api (1.2.0)
✅ every service meets the platform contract
```

Read that carefully: **the contract passes.** Every service is compliant with what the platform promised *when it was generated*. Three of four are running last month's defaults, and nothing is failing. This is the platform equivalent of a base image you patched once and never rebuilt — and left alone it compounds, until "we have a golden path" means "we had one, once, per service".

**Investigate.**

```bash
grep -r platform-version services/*/service.yaml
diff <(SERVICE_NAME=payments-api OWNER=payments-team TIER=1 PLATFORM_VERSION=1.3.0 \
        envsubst '$SERVICE_NAME $OWNER $TIER $PLATFORM_VERSION' < templates/deployment.yml.tmpl) \
     services/payments-api/k8s/deployment.yml
```

That diff is what a service is missing — and it is also, notably, entangled with whatever the team changed themselves. Which is exactly why this is hard.

**Root cause.** A scaffold is a one-time copy. The moment it runs, the service and the template are independent, and nothing pulls improvements forward.

**Fix.** Pick a mechanism and be explicit about it, because "we'll remind teams" is not one:

| Approach | How | Cost |
|----------|-----|------|
| **Drift report** (this lab) | Version stamp + a check that lists who is behind | Cheap, visible; still needs someone to act |
| **Automated PRs** | The platform opens a pull request per service on a template change | ⭐ What most mature platforms do — teams keep control, defaults still move |
| **Runtime enforcement** | Admission policy rejects workloads missing the defaults | Strongest, and it fails at deploy time rather than at review time |
| **Shared library** | Reusable CI workflow, base image, Helm chart — improvements are inherited, not copied | Best where it fits; not everything can be centralised |

The realistic answer is layered: inherit what you can (the reusable workflow in `ci.yml.tmpl`), open PRs for the rest, and enforce the non-negotiables at admission.

```bash
echo "1.2.0" > PLATFORM-VERSION      # restore
```

### Scenario 2: The Cage — When the Path Cannot Express the Need

**Break it.** `search-team` needs a second port for a gRPC listener. The generator has no option for that. Watch what a reasonable engineer does next:

```bash
# They edit the generated manifest by hand, as they should — it's a real file
cat >> services/search-api/k8s/deployment.yml <<'EOF'
# team edit: gRPC listener, no platform support for a second port
EOF
sed -i '/livenessProbe/,+5d' services/search-api/k8s/deployment.yml   # and break something in passing
./platform-check.sh services/search-api | tail -8
```

**Symptom.**

```text
    ❌ liveness probe
    ...
❌ policy violations above
```

The gate catches the broken probe — good. But now consider the version of this where the gate is strict and there is *no* escape hatch: the team cannot ship their service, the platform has no way to express what they need, and the pull request sits there. What happens next is the actual failure mode: they stop using the path. They copy an old repo, or write their own manifests, and you find out a year later when an incident hits a service nobody knew existed.

**Root cause.** A golden path that cannot be left becomes a cage, and people climb out of cages. The requirement was legitimate; the platform simply did not have it yet.

**Fix.** Two things, together:

1. **Keep the escape hatch.** Generated output is plain files that a team may edit — the generated README says so explicitly. The gate still enforces the non-negotiables (probes, limits, non-root, owner), so leaving the path never means leaving the contract.
2. **Treat every bypass as a feature request.** A team going around the road is your highest-quality roadmap input, and it is free. Add `--extra-port` to the generator and the next four teams never hit it.

```bash
sed -i '/team edit: gRPC/d' services/search-api/k8s/deployment.yml
rm -rf services/search-api && ./new-service.sh search-api search-team 2 >/dev/null
```

> ⭐ Interviewers probe this exact tension. "How do you stop teams doing the wrong thing?" has a bad answer (prevent them) and a good one: make the right thing easier, enforce only what is genuinely non-negotiable, and treat every bypass as a gap you own.

### Scenario 3: A Service With No Human Attached

**Break it.** Try to skip the owner, the way any generator with an optional field eventually gets used:

```bash
./new-service.sh orphan-svc
```

**Symptom.**

```text
usage: ./new-service.sh <service-name> <owner-team> [tier]

  service-name   lowercase, hyphens only (becomes the k8s name and the image name)
  owner-team     the team that will be paged. NOT optional
```

Refused — because the field is *required*, not because someone reviewed it. Now see what the optional version costs you:

```bash
mkdir -p services/legacy-svc/k8s services/legacy-svc/app
cp services/payments-api/k8s/deployment.yml services/legacy-svc/k8s/
cp services/payments-api/app/app.py services/legacy-svc/app/
./platform-check.sh services/legacy-svc | head -4
```

```text
══ legacy-svc
    ❌ has a catalogue entry (service.yaml)
    ✅ liveness probe
```

**Root cause.** Ownership is the one piece of metadata that cannot be derived from the code, and the only one an incident absolutely requires. It is also the first field people make optional, because it is the only one that needs a human answer.

**Fix.** Required at creation, verified by the gate, and surfaced where it is used — the generated alerts carry `owner: ${OWNER}` as a label so a page routes itself. Ownership recorded in a wiki page is ownership you will not have at 3 a.m.

```bash
rm -rf services/legacy-svc
```

### Scenario 4: A Platform Nobody Measures

**Break it.** Nothing to break — this failure is an absence. Ask the three questions and see whether you can answer them:

```bash
./platform-check.sh | tail -4
```

```text
checked: 3 service(s)
on current template (1.2.0): 3/3
✅ every service meets the platform contract
```

**Symptom.** The gate reports on services it *knows about*. It has nothing to say about services that never used the path — and those are precisely the ones you need to find. A platform team looking only at this output concludes everything is fine while adoption quietly falls.

**Investigate.** The number that matters is a ratio against reality, not against your own directory:

```bash
# Adoption: services on the path ÷ services that exist. The denominator is the hard part —
# in a real org it comes from the cluster or the org's repositories, not from the platform.
on_path=$(find services -maxdepth 2 -name service.yaml | wc -l)
total=$(find services -mindepth 1 -maxdepth 1 -type d | wc -l)
echo "adoption: $on_path/$total"
```

**Root cause.** Without adoption, drift, and lead time, a platform team optimises for what is interesting to build. Falling adoption is the earliest signal you get that the road no longer goes where people are driving, and it is invisible unless you compute it.

**Fix.** Three numbers, reviewed on a schedule, with the denominator taken from outside the platform:

| Metric | From | Tells you |
|--------|------|-----------|
| **Adoption** | Services with a catalogue entry ÷ all deployed workloads | Whether the road is being used |
| **Drift** | Services on the current template ÷ services on the path | Whether improvements actually reach anyone |
| **Lead time** | Timestamp of `new-service.sh` → first production deploy | What the platform is actually worth |

And the one that outranks all three: did the **DORA metrics of the teams you serve** move? A platform that does not improve deployment frequency or time-to-restore has not worked, however elegant it is.

### Summary

| Failure | How you detect it | How you prevent it |
|---------|------------------|--------------------|
| Drift | Version stamps diverging; the contract passing while services run last month's defaults | Automated PRs on template change, inheritance where possible, admission for non-negotiables |
| Golden cage | Bypasses, forked templates, services outside the catalogue | Keep the escape hatch; treat every bypass as a feature request you own |
| No ownership | A catalogue entry missing, an alert with no routable owner | Required at creation, verified by the gate, used by the alert labels |
| Unmeasured | You cannot state adoption, drift, or lead time | Compute all three on a schedule, with the denominator from outside the platform |

⭐ **The theme of this lab**: the generator is fifty lines and the interesting parts are all organisational — who owns a service, what happens when the template moves, and what a team does when the path does not fit. That is why platform engineering is a *product* discipline. The technology is the easy half.

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
rm -rf services
```

Keep `templates/`, both scripts, and your metrics — a working golden path with a policy gate is unusually strong portfolio evidence, because it shows you thinking about other engineers as users.

---

## ✅ Validation

- [ ] Explain platform engineering versus a DevOps team that deploys on your behalf
- [ ] Name six defaults your template encodes and the failure each one prevents
- [ ] Measure lead time for a new service, and state the manual baseline you're comparing against
- [ ] Explain why the policy gate exists when the generator already produced good defaults
- [ ] Explain template drift and pick a mitigation, with its cost
- [ ] Explain why the escape hatch makes the platform stronger rather than weaker
- [ ] Say why ownership is required at creation rather than reviewed later
- [ ] State the three platform metrics, where each denominator comes from, and the one that outranks them

---

## 📝 What to Commit

- `new-service.sh`, `platform-check.sh`, `templates/`, `PLATFORM-VERSION`
- One generated service, as evidence of the output
- Your lead-time measurement, with the manual baseline
- The gate failing on a hand-edited manifest, and the drift report
- Your three platform metrics with real numbers
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: Message Queues and Async Failure](./lab-02-message-queues.md) | [Back to Module README](../README.md) | [Next Lab: Kafka — Partitions, Consumer Groups, and Offsets →](./lab-04-kafka-partitions.md)
