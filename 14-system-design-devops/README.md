# Module 14: System Design for DevOps

> *"Good architecture is less about picking the right technology and more about knowing why you picked it." — Production Engineering Principle*

---

## 🎯 Why This Module Matters

Every production outage, every scaling failure, and every "it works on my machine" moment traces back to a system design decision. As a DevOps engineer, you don't just run infrastructure — you **design, evaluate, and defend architectural choices** that keep systems reliable, scalable, and recoverable.

**In real-world DevOps work**, you will:
- Evaluate whether a system can handle 10x traffic growth
- Design deployment architectures that survive component failures
- Choose between scaling vertically or horizontally
- Implement load balancing, caching, and CDN strategies
- Define SLAs, SLOs, and SLIs that drive operational decisions
- Plan for disaster recovery and business continuity

---

## 📚 Table of Contents

1. [High Availability — Designing for Failure](#1-high-availability--designing-for-failure)
2. [Load Balancing](#2-load-balancing)
3. [Scaling Strategies](#3-scaling-strategies)
4. [Caching](#4-caching)
5. [Database Considerations for DevOps](#5-database-considerations-for-devops)
6. [CDN and Edge Architecture](#6-cdn-and-edge-architecture)
7. [SLAs, SLOs, and SLIs](#7-slas-slos-and-slis)
8. [Disaster Recovery](#8-disaster-recovery)
9. [Architecture Decision Framework](#9-architecture-decision-framework)
10. [Common Mistakes and Anti-Patterns](#10-common-mistakes-and-anti-patterns)
11. [Interview Insights](#11-interview-insights)

---

## 1. High Availability — Designing for Failure

### The Nines of Availability

```
AVAILABILITY   DOWNTIME/YEAR    DOWNTIME/MONTH   CONTEXT
99%            3.65 days        7.3 hours         Acceptable for internal tools
99.9%          8.77 hours       43.8 minutes      Standard web application
99.95%         4.38 hours       21.9 minutes      Business-critical service
99.99%         52.6 minutes     4.38 minutes      Financial/healthcare systems
99.999%        5.26 minutes     26.3 seconds      Telecom, life-safety systems

EACH ADDITIONAL NINE ≈ 10x MORE ENGINEERING EFFORT AND COST
```

### Single Points of Failure (SPOF)

```
A SINGLE POINT OF FAILURE is any component whose failure
brings down the entire system.

COMMON SPOFs:
  ❌ Single database server (no replica)
  ❌ Single load balancer
  ❌ Single DNS provider
  ❌ Single availability zone
  ❌ Single deployment pipeline
  ❌ One person who knows the system ("bus factor = 1")

FIX: Redundancy at every layer
  ✅ Database primary + replica(s)
  ✅ Active-passive or active-active load balancers
  ✅ Multi-AZ or multi-region deployment
  ✅ Multiple CI/CD paths (or at least manual fallback)
  ✅ Documented runbooks so anyone can operate the system
```

### HA Architecture Patterns

```
ACTIVE-PASSIVE (Failover):
  ┌──────────┐     heartbeat     ┌──────────┐
  │  Active  │◄─────────────────▶│ Passive  │
  │ (serves  │                   │ (standby,│
  │ traffic) │                   │  warm/hot)│
  └──────────┘                   └──────────┘
  Pro: Simpler, consistent state
  Con: Passive server is idle cost; failover delay

ACTIVE-ACTIVE:
  ┌──────────┐                   ┌──────────┐
  │ Active 1 │◄── shared state ─▶│ Active 2 │
  │ (serves  │     (replicated   │ (serves  │
  │ traffic) │      DB, cache)   │ traffic) │
  └──────────┘                   └──────────┘
  Pro: Full utilization, no failover delay
  Con: State synchronization complexity, split-brain risk
```

---

## 2. Load Balancing

### How Load Balancers Work

```
                    Internet
                       │
                 ┌─────▼─────┐
                 │    Load    │
                 │  Balancer  │
                 └─────┬─────┘
              ┌────────┼────────┐
              ▼        ▼        ▼
          ┌──────┐ ┌──────┐ ┌──────┐
          │ App  │ │ App  │ │ App  │
          │  #1  │ │  #2  │ │  #3  │
          └──────┘ └──────┘ └──────┘

PURPOSE:
  - Distribute traffic across healthy backends
  - Detect and stop sending to unhealthy servers
  - Terminate TLS (offload encryption from app servers)
  - Enable zero-downtime deployments
```

### Load Balancing Algorithms

```
ROUND ROBIN:
  Request 1 → Server A
  Request 2 → Server B
  Request 3 → Server C
  Request 4 → Server A ...
  Use when: All servers are identical

LEAST CONNECTIONS:
  Send to the server with fewest active connections
  Use when: Requests have varying processing times

WEIGHTED:
  Server A (weight 5): gets 5x more traffic than Server C (weight 1)
  Use when: Servers have different capacities

IP HASH:
  hash(client_ip) % server_count → always same server
  Use when: You need sticky sessions without cookies

HEALTH-CHECK BASED:
  All algorithms should include health checks:
  - HTTP GET /health → 200 OK means healthy
  - Failed checks → remove from pool
  - Recovered → add back after N consecutive passes
```

### Layer 4 vs Layer 7

```
LAYER 4 (Transport — TCP/UDP):
  Routes based on: IP address, port number
  Cannot inspect: HTTP headers, URLs, cookies
  Performance: Very fast, minimal overhead
  Tools: AWS NLB, HAProxy (TCP mode), iptables
  Use for: Database connections, non-HTTP protocols, raw performance

LAYER 7 (Application — HTTP/HTTPS):
  Routes based on: URL path, headers, cookies, content type
  Can do: Path-based routing, header manipulation, TLS termination
  Performance: Slightly slower, more CPU for inspection
  Tools: AWS ALB, Nginx, HAProxy (HTTP mode), Envoy
  Use for: Microservices routing, A/B testing, canary deploys
```

---

## 3. Scaling Strategies

### Vertical vs Horizontal

```
VERTICAL SCALING (Scale Up):
  ┌─────────────┐         ┌─────────────┐
  │   2 CPU     │         │   16 CPU    │
  │   4 GB RAM  │   ──▶   │   64 GB RAM │
  │   Small     │         │   Large     │
  └─────────────┘         └─────────────┘
  Pro: No code changes, simple
  Con: Hardware ceiling, single point of failure, expensive at top

HORIZONTAL SCALING (Scale Out):
  ┌───────┐               ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
  │  App  │         ──▶   │  App  │ │  App  │ │  App  │ │  App  │
  └───────┘               └───────┘ └───────┘ └───────┘ └───────┘
  Pro: Near-infinite scale, redundancy built in, cost-efficient
  Con: Stateless design required, distributed system complexity

WHEN TO USE WHICH:
  Database (primary)     → Vertical first, then read replicas
  Application servers    → Horizontal (behind load balancer)
  Cache layer            → Horizontal (Redis Cluster, sharding)
  Static content         → CDN (horizontally distributed by design)
```

### Auto-Scaling

```
AUTO-SCALING COMPONENTS:
  1. METRIC     → What triggers scaling (CPU, memory, request count, queue depth)
  2. THRESHOLD  → When to scale (CPU > 70% for 5 minutes)
  3. POLICY     → How much to scale (add 2 instances, or increase by 50%)
  4. COOLDOWN   → Wait period before scaling again (prevent thrashing)

EXAMPLE AUTO-SCALING POLICY:
  Scale Out: CPU > 70% for 5 min → add 2 instances (cooldown: 5 min)
  Scale In:  CPU < 30% for 15 min → remove 1 instance (cooldown: 10 min)

  ⚠️ Scale out FAST, scale in SLOW
  ⚠️ Always set minimum and maximum instance counts
```

### Stateless vs Stateful Applications

```
STATELESS (easy to scale horizontally):
  - Any server can handle any request
  - Session stored externally (Redis, database, JWT)
  - No local file storage (use S3, shared volume)
  - Configuration from environment, not local files

STATEFUL (harder to scale):
  - Server holds session data in memory
  - Local file uploads tied to one server
  - Sticky sessions needed at the load balancer
  - Database connections with local connection pools

RULE: Make your applications STATELESS whenever possible.
      Push state to dedicated, purpose-built stores.
```

---

## 4. Caching

### Cache Layers

```
CLIENT ──▶ CDN CACHE ──▶ REVERSE PROXY ──▶ APP CACHE ──▶ DB CACHE ──▶ DATABASE
           (CloudFront)   (Nginx/Varnish)   (Redis)       (query cache)

EACH LAYER:
  Hit  → Return cached data (fast, cheap)
  Miss → Forward to next layer (slower, more expensive)

RULE: Cache as close to the user as possible.
```

### Caching Strategies

```
CACHE-ASIDE (Lazy Loading):
  App checks cache → miss → reads DB → writes to cache → returns
  Pro: Only requested data is cached; cache failure doesn't break reads
  Con: First request is always slow; data can go stale

WRITE-THROUGH:
  App writes to cache AND DB simultaneously
  Pro: Cache is always fresh
  Con: Write latency increases; cache may hold never-read data

WRITE-BEHIND (Write-Back):
  App writes to cache → cache async writes to DB
  Pro: Fast writes
  Con: Data loss risk if cache crashes before DB write

TTL (Time to Live):
  Set expiry on cached data → auto-evict after N seconds
  Short TTL (30s): Near-real-time, higher DB load
  Long TTL (1h): Lower DB load, staler data
  Pick based on how stale your users can tolerate
```

### Cache Invalidation

```
"There are only two hard things in computer science:
 cache invalidation and naming things." — Phil Karlton

STRATEGIES:
  1. TTL-based    → Data expires after a fixed time
  2. Event-based  → Publish invalidation on data change
  3. Version-based → Cache key includes version (v2:user:123)
  4. Manual purge  → Explicit API call to clear cache
```

---

## 5. Database Considerations for DevOps

### Replication Patterns

```
PRIMARY-REPLICA (Read Replicas):
  ┌─────────┐     async/sync     ┌──────────┐
  │ Primary │──────────────────▶ │ Replica  │
  │ (R+W)   │                    │ (R only) │
  └─────────┘                    └──────────┘
  Writes → Primary only
  Reads  → Distributed across replicas
  Use for: Read-heavy workloads, reporting queries

PRIMARY-PRIMARY (Multi-Master):
  ┌──────────┐                  ┌──────────┐
  │ Primary  │◄────────────────▶│ Primary  │
  │  (R+W)   │  bidirectional   │  (R+W)   │
  └──────────┘                  └──────────┘
  Pro: Write availability in multiple regions
  Con: Conflict resolution complexity, data consistency challenges
```

### Backup Strategy

```
BACKUP TYPES:
  Full     → Complete database copy (slow, large, complete)
  Incremental → Only changes since last backup (fast, small)
  Point-in-time → Transaction log replay to any moment

3-2-1 RULE:
  3 copies of your data
  2 different storage types (disk + object storage)
  1 offsite copy (different region or provider)

ALWAYS TEST RESTORES — An untested backup is not a backup.
```

---

## 6. CDN and Edge Architecture

```
WITHOUT CDN:
  User (Sydney) ──── 250ms ────▶ Origin (US-East) ──▶ Response
  Every request crosses the ocean.

WITH CDN:
  User (Sydney) ──── 10ms ────▶ Edge (Sydney) ──▶ Cached Response
  First request: Edge fetches from origin, caches it.
  Subsequent: Served from edge. Massively faster.

CDN USE CASES:
  ✅ Static assets (images, CSS, JS, fonts)
  ✅ Video and media streaming
  ✅ API responses that are cacheable (GET, public data)
  ✅ Whole-site acceleration (with edge compute)

CDN PROVIDERS: CloudFront (AWS), Cloudflare, Akamai, Fastly
```

---

## 7. SLAs, SLOs, and SLIs

```
SLI — Service Level Indicator
  A measurable metric: "What are we measuring?"
  Examples: Request latency, error rate, throughput, availability

SLO — Service Level Objective
  A target for the SLI: "What is acceptable?"
  Examples: p99 latency < 300ms, error rate < 0.1%, 99.9% uptime

SLA — Service Level Agreement
  A contract with consequences: "What happens if we fail?"
  Examples: Below 99.9% uptime → service credits, penalty clauses

RELATIONSHIP:
  SLI (measurement) ──▶ SLO (internal target) ──▶ SLA (external promise)

  ⚠️ SLOs should be STRICTER than SLAs
  ⚠️ Measure SLIs continuously, alert when SLO is at risk
  ⚠️ Use error budgets: if SLO is 99.9%, you have 0.1% error budget
```

### Error Budgets

```
ERROR BUDGET = 1 - SLO

If SLO = 99.9% uptime per month:
  Error budget = 0.1% = 43.8 minutes of downtime

Budget remaining > 50%:
  → Ship features, take calculated risks, deploy frequently

Budget remaining < 25%:
  → Slow down, focus on reliability, reduce deploy frequency

Budget exhausted:
  → Feature freeze, all engineering effort on stability
```

---

## 8. Disaster Recovery

### Recovery Objectives

```
RPO — Recovery Point Objective
  "How much data can we afford to lose?"
  RPO = 1 hour → backups must run at least every hour
  RPO = 0      → synchronous replication required

RTO — Recovery Time Objective
  "How fast must we recover?"
  RTO = 4 hours → must be back online within 4 hours of disaster
  RTO = 0       → active-active with automatic failover required

         data loss           downtime
  ◄──────────────────┤ DISASTER ├──────────────────►
         RPO                        RTO
```

### DR Strategies (Cost vs Speed)

```
BACKUP & RESTORE (Cheapest, Slowest):
  RPO: Hours     RTO: Hours to days
  Restore from backups to new infrastructure
  Cost: $ (storage only)

PILOT LIGHT (Low cost, moderate speed):
  RPO: Minutes   RTO: 30-60 minutes
  Core systems always running (DB replica), scale up on failover
  Cost: $$ (minimal always-on infra)

WARM STANDBY (Moderate cost, fast):
  RPO: Seconds   RTO: Minutes
  Scaled-down copy of production always running
  Cost: $$$ (partial duplicate infrastructure)

MULTI-REGION ACTIVE-ACTIVE (Most expensive, fastest):
  RPO: Zero      RTO: Seconds
  Full production in multiple regions, traffic split
  Cost: $$$$ (full duplicate infrastructure)
```

---

## 9. Architecture Decision Framework

### How to Evaluate Architecture Trade-Offs

```
For every design decision, evaluate:

1. AVAILABILITY   → What happens when this component fails?
2. SCALABILITY    → Can this handle 10x traffic?
3. COST           → What does this cost at current and projected scale?
4. COMPLEXITY     → Can the team operate and debug this?
5. SECURITY       → What is the blast radius of a breach here?
6. DATA INTEGRITY → Can we lose data? How much?
7. LATENCY        → Does this meet user-facing performance requirements?

DOCUMENT YOUR DECISIONS:
  Use Architecture Decision Records (ADRs):
  - Title: Short description of the decision
  - Context: What problem are we solving?
  - Decision: What did we choose?
  - Consequences: Trade-offs, risks, and what we accept
  - Status: Proposed / Accepted / Superseded
```

### GitOps — Declarative Deployment Architecture

GitOps is a deployment pattern where **Git is the single source of truth** for both application code and infrastructure. Instead of CI/CD pushing changes to clusters, a GitOps operator **pulls** the desired state from Git and reconciles it continuously.

```
TRADITIONAL (Push-based CI/CD):
  Developer → push → CI pipeline → build → test → push image → deploy to K8s
  The pipeline HAS credentials to the cluster.

GITOPS (Pull-based):
  Developer → push → CI pipeline → build → test → push image → update Git manifest
  ArgoCD/Flux WATCHES Git → detects change → applies to K8s
  The cluster pulls its own state. CI never touches the cluster directly.

  ┌──────────┐    ┌──────────┐    ┌─────────────┐    ┌─────────────┐
  │Developer │───▶│CI Pipeline│───▶│ Git (manifests)│◀───│ ArgoCD/Flux │
  │          │    │build+test │    │ (desired state)│    │ (reconciles)│
  └──────────┘    └──────────┘    └─────────────┘    └──────┬──────┘
                                                            │
                                                    ┌───────▼──────┐
                                                    │  Kubernetes   │
                                                    │  (actual state)│
                                                    └──────────────┘
```

```
GITOPS BENEFITS:
  ✅ Auditable — every change is a Git commit (who, what, when, why)
  ✅ Rollback = git revert (instant, tested, safe)
  ✅ Drift detection — ArgoCD alerts if cluster state ≠ Git state
  ✅ Security — CI/CD pipeline doesn't need cluster credentials
  ✅ Self-healing — if someone manually changes the cluster, ArgoCD reverts it

WHEN TO USE GITOPS:
  ✅ Kubernetes-based infrastructure (primary use case)
  ✅ Multiple environments managed from Git branches or directories
  ✅ Teams that want strong audit trails and compliance

WHEN GITOPS IS OVERKILL:
  ❌ Single-server deployments (Docker Compose on one host)
  ❌ Very small teams (1-3 people) with simple deployment needs
  ❌ Non-Kubernetes workloads (GitOps tooling is K8s-native)

KEY TOOLS:
  ArgoCD — UI-driven, popular, CNCF graduated project
  Flux    — CLI-driven, lightweight, CNCF graduated project
```

> 💡 **GitOps is increasingly common in interviews.** Know the pull vs push model distinction and when GitOps makes sense versus traditional CI/CD.

### Capacity Planning

```
CAPACITY PLANNING STEPS:
  1. MEASURE current usage (CPU, memory, disk, network, request rate)
  2. IDENTIFY growth trend (linear, exponential, seasonal)
  3. PROJECT future needs (3 months, 6 months, 1 year)
  4. ADD headroom (30-50% buffer for spikes)
  5. PLAN procurement or auto-scaling rules

EXAMPLE:
  Current: 1000 req/s, 4 servers at 60% CPU
  Growth: 20% per quarter
  In 6 months: 1440 req/s → need 6 servers
  With headroom: 8 servers or auto-scaling 4-10
```

---

## 10. Common Mistakes and Anti-Patterns

### ❌ Premature Optimization

```
BAD:  Building for 1M users on day one (10 actual users)
GOOD: Design for 10x current load, have a plan for 100x
```

### ❌ Ignoring Failure Modes

```
BAD:  "The database will never go down"
GOOD: "When the database goes down, the app serves cached data
       and queues writes for replay"
```

### ❌ Distributed Monolith

```
BAD:  Microservices that all depend on each other synchronously
      (you split the code but kept the coupling)
GOOD: Services communicate asynchronously where possible,
      can degrade gracefully when dependencies are down
```

### ❌ No Observability in the Design

```
BAD:  Build first, figure out monitoring later
GOOD: Metrics, logging, and tracing are part of the architecture
      from day one — they are not optional add-ons
```

---

## 11. Interview Insights

**Q: How would you design a system for high availability?**
> Eliminate single points of failure at every layer. Use multiple application servers behind a load balancer with health checks. Deploy across multiple availability zones. Use database replication with automated failover. Implement health checks and circuit breakers. Define RTO/RPO and choose a DR strategy that matches. Monitor everything and alert on SLO violations, not just server metrics.

**Q: Explain the difference between vertical and horizontal scaling.**
> Vertical scaling adds resources to a single machine (bigger CPU, more RAM). It's simple but has a hardware ceiling and remains a single point of failure. Horizontal scaling adds more machines behind a load balancer. It requires stateless application design but offers near-unlimited growth and built-in redundancy. Most production systems use both: scale the database vertically first, then add read replicas; scale application servers horizontally from the start.

**Q: What are SLAs, SLOs, and SLIs?**
> SLIs are measurable metrics like latency and error rate. SLOs are internal targets for those metrics ("p99 latency under 200ms"). SLAs are external contracts with penalties for missing targets. SLOs should be stricter than SLAs. Error budgets — the allowed failure margin — drive the balance between shipping features and investing in reliability.

**Q: How do you approach capacity planning?**
> Measure current utilization across all resources (CPU, memory, disk, network). Identify growth trends from historical data. Project needs for 3-6-12 months. Add 30-50% headroom for unexpected spikes. Implement auto-scaling where possible with appropriate policies. Review and adjust quarterly.

**Q: Describe a caching strategy and when it can go wrong.**
> Cache-aside is the most common: the app checks cache first, falls back to the database on miss, then populates the cache. It goes wrong when cache invalidation is missed — users see stale data. Cache stampede happens when many keys expire simultaneously and all requests hit the database. Mitigate with jittered TTLs, write-through on critical paths, and circuit breakers that serve stale data over no data.

**Q: Walk me through a disaster recovery plan.**
> Define RPO and RTO based on business requirements. For a typical web application: RPO of 5 minutes (continuous DB replication), RTO of 15 minutes (warm standby). Maintain a replica environment in a second region. Automate failover with DNS and health checks. Test the DR plan quarterly with actual failover drills — an untested plan is not a plan. Document the runbook so any on-call engineer can execute it.

---

## Practical Checkpoint

Before moving on, you should be able to:

- Draw a high-availability architecture for a web application with no single points of failure.
- Explain the trade-offs between at least two scaling strategies for a given scenario.
- Define SLIs, SLOs, and error budgets for a service you've worked with in previous modules.

Portfolio evidence to keep:

- An architecture diagram with annotations explaining design decisions.
- A written trade-off analysis comparing two approaches (e.g., active-passive vs active-active).
- SLO definitions with error budget calculations for a realistic service.

Suggested project: [Architecture Design Document](./projects/project-01-architecture-design-doc.md)

---

## ➡️ What's Next?

With system design fundamentals covered, you're ready to combine everything into real-world portfolio projects.

**[Module 15: Capstone Projects →](../15-projects/)**

---

<div align="center">

**Module 14 Complete** ✅

[← Back to Security Basics](../13-security-basics/) | [Next: Projects →](../15-projects/)

</div>
