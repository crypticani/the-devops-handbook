# Glossary

Every term this handbook uses without stopping to define it, in one place. Definitions are
deliberately short — enough to unblock a sentence you were reading, not a replacement for the
module. The number at the end of each entry links to the module that teaches it properly.

Jump: [A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) · [I](#i) · [J](#j) · [K](#k) · [L](#l) · [M](#m) · [N](#n) · [O](#o) · [P](#p) · [Q](#q) · [R](#r) · [S](#s) · [T](#t) · [U](#u) · [V](#v) · [W](#w) · [X](#x) · [Y](#y) · [Z](#z)

---

## A

- **A record** — DNS record mapping a hostname to an IPv4 address. `AAAA` is the IPv6 equivalent. [02]
- **Active-active** — Disaster recovery posture where every site serves live traffic, so failover is just traffic shifting. The expensive end of the DR spectrum. [14]
- **Ad-hoc command** — A single Ansible module run from the command line (`ansible web -m ping`) with no playbook. Useful for checks, not for anything you need to repeat. [11]
- **Agentless** — Managing a machine without installing software on it. Ansible only needs SSH and Python on the target. [11]
- **Alertmanager** — Prometheus companion that receives fired alerts and handles routing, grouping, silencing, and inhibition. Prometheus decides *whether*; Alertmanager decides *who and how*. [07]
- **Ambient mesh** — Service mesh without a sidecar per pod: a per-node proxy handles L4 and mTLS, with an L7 proxy only where needed. Much lower overhead than sidecars, and newer. [12]
- **Ansible** — Agentless configuration management tool that pushes idempotent modules over SSH. [11]
- **API server** — The Kubernetes control plane component that every request passes through and the only one that talks to etcd. [12]
- **Argo CD** — Kubernetes GitOps controller: it watches a Git repository, reports whether live state matches it (`Synced` / `OutOfSync`), and applies the difference when configured to. `selfHeal` and `prune` both default to off. [12]
- **Artifact** — The built output a pipeline produces and promotes: a container image, a binary, a package. Build it once, deploy that exact thing everywhere. [06]
- **At-least-once delivery** — What nearly every message broker actually guarantees: a consumer that crashes after doing the work but before acknowledging will see the message again. Design for duplicates with an idempotency key. [14]
- **Attribute (span)** — Key-value metadata on a span. Searchable, and the right home for unique values like an order id — unlike the span *name*, which must stay low-cardinality. [07]
- **Autoscaling** — Adding and removing capacity automatically in response to a signal (CPU, queue depth, request rate). Requires stateless workloads to be useful. [09] [14]
- **Availability Zone (AZ)** — An isolated datacenter within a cloud region. Spanning two AZs is the cheapest meaningful step up in availability. [09]

## B

- **Backend (Terraform)** — Where state is stored. A remote backend (S3 with `use_lockfile` for locking, HCP Terraform) is what makes team use safe. [10]
- **Backpressure** — What happens when consumers can't keep up: either the queue grows (memory, disk, cost) or producers must be slowed. Choose deliberately and set retention, or the broker chooses for you. [14]
- **Base image** — The image a Dockerfile starts `FROM`. Everything in it ships in your image, including its vulnerabilities. [05] [13]
- **Bastion host** — A hardened, audited jump host that is the only SSH entry point into a private network. [09] [13]
- **Bind mount** — Mounting a host directory into a container. Convenient in development, a permissions and portability problem in production; prefer named volumes. [05]
- **Bisect** — `git bisect`: binary search through history for the commit that introduced a bug. Ten steps for a thousand commits. [03]
- **Blameless postmortem** — Incident review that treats human error as a symptom of system design. Blame buys silence, and silence costs you the data. [00]
- **Blast radius** — How much breaks when this breaks. The first question in both incident response and change review. [13] [14]
- **Blue-green deployment** — Two complete environments; traffic switches from one to the other at once. Instant rollback, double the infrastructure. [06]
- **Branch protection** — Repository rules that stop direct pushes to a branch and require review and passing checks. The mechanism behind "all changes go through a PR". [03]

## C

- **Canary release** — Sending a small share of real traffic to the new version and watching metrics before shifting the rest. [06]
- **Capability (Linux)** — A slice of root's power (`NET_BIND_SERVICE`, `SYS_ADMIN`) grantable independently. Dropping all and adding back one is far safer than running as root. [01] [13]
- **Cardinality** — The number of distinct label-value combinations in a metric or log stream. High cardinality (user IDs as labels) is the standard way to melt Prometheus or Loki. [07] [08]
- **CDN** — Cache of your static content at edge locations near users. Cuts latency and origin load; introduces a cache invalidation problem. [14]
- **cgroups** — Linux kernel feature that limits and accounts for a process group's CPU, memory, and I/O. The "limits" half of containers. [05]
- **Change failure rate** — Share of deployments that cause a degradation needing a fix or rollback. One of the four DORA metrics. [00]
- **CIDR** — `10.0.0.0/16` notation: the number after the slash is how many leading bits are the network, the rest are hosts. [02]
- **Circuit breaker** — Pattern that stops calling a dependency that is clearly failing, so retries do not finish it off. [14]
- **CI (Continuous Integration)** — Every commit is merged to shared main and automatically built and tested. The practice long-lived branches quietly abandon. [06]
- **CD (Continuous Delivery / Deployment)** — Delivery: every green build is releasable and a human decides. Deployment: that decision is automated. [06]
- **ClusterIP** — Default Kubernetes Service type: a stable virtual IP reachable only inside the cluster. [12]
- **Collector (OpenTelemetry)** — Standalone process that receives telemetry, processes it (batching, sampling, redaction), and exports it onward. Where you change sampling or add a backend without redeploying a single application. [07]
- **ConfigMap** — Kubernetes object holding non-secret configuration, consumed as environment variables or mounted files. [12]
- **Consumer lag** — The gap between what has been produced and what has been consumed, and whether it is growing. The real health metric for a queue — not CPU, not depth alone. [14]
- **Container** — A process isolated with namespaces and constrained with cgroups, sharing the host kernel. Not a small VM. [05]
- **Container runtime** — The component that actually starts containers (containerd, CRI-O, runc underneath). Docker is a toolchain on top of one. [05] [12]
- **Context propagation** — Carrying trace context across a process boundary, in HTTP via the W3C `traceparent` header. Every "our traces are broken" is a boundary where this didn't happen. [07]
- **Control plane** — The components that make cluster-wide decisions: API server, etcd, scheduler, controller manager. Distinct from the nodes that run workloads. [12]
- **Correlation ID** — An identifier generated at ingress and propagated through every downstream call, so one request's log lines can be joined across services. [08]
- **Counter** — Prometheus metric type that only increases and resets on restart. Always query it through `rate()`. [07]
- **CrashLoopBackOff** — Kubernetes state where a container keeps exiting and being restarted with growing delay. A symptom with a dozen causes; `describe` and `logs --previous` tell you which. [12]
- **Cron** — Time-based scheduler on Unix. Its minimal environment is why a job that works in your shell fails under cron. [01]
- **CVE** — A publicly catalogued vulnerability with an identifier. Presence in an image is not the same as exploitability in your application. [13]

## D

- **DaemonSet** — Kubernetes workload that runs exactly one pod per node. What log shippers, node exporters, and CNI plugins use. [12]
- **DAST** — Dynamic application security testing: probing the running application from the outside. Finds what static analysis cannot see. [13]
- **Dead letter queue (DLQ)** — Where messages go after N failed attempts, so a poison message stops blocking the queue. An unmonitored DLQ is a folder of work nobody is doing. [14]
- **Declarative** — You describe the desired end state and the tool works out the steps. The opposite of imperative scripts that describe the steps and hope about the state. [10] [12]
- **Defense in depth** — Layering controls so no single failure is fatal: non-root user, read-only filesystem, network policy, scoped IAM. [13]
- **Deployment (Kubernetes)** — Controller that manages a ReplicaSet to run N interchangeable pods and perform rolling updates and rollbacks. [12]
- **Digest** — The immutable content hash of an image (`sha256:…`). Pinning by digest guarantees the image you scanned is the image you run. [05] [13]
- **Disaster recovery (DR)** — The plan for losing a whole site or region, sized by RTO and RPO. [14]
- **DNS** — The name-to-address lookup system, and the first thing to check when "the site is down". [02]
- **Docker Compose** — Defines a multi-container application in one YAML file, with a shared network where services resolve each other by name. [05]
- **Dockerfile** — The build recipe for an image. Each instruction is a cached layer, which is why instruction order determines build speed. [05]
- **DORA metrics** — Deployment frequency, lead time for changes, change failure rate, time to restore service. Speed and stability, measured together. [00]
- **Drift** — Real infrastructure no longer matching the code that created it, usually because someone used the console. `terraform plan` is the detector. [10]

## E

- **EBS** — AWS block storage volume attached to a single instance in a single AZ. Not shared storage. [09]
- **EC2** — AWS virtual machines. The unit you stop paying for by remembering to terminate it. [09]
- **EFS** — Managed NFS filesystem that many instances can mount at once, at several times the per-GB price of EBS. [09]
- **Egress** — Traffic leaving your network. The cloud bill line item nobody estimates in advance. [09]
- **ELK** — Elasticsearch, Logstash, Kibana. Full-text indexes every log body: powerful queries, expensive storage and memory. [08]
- **Endpoint (Kubernetes)** — The set of pod IPs currently backing a Service. A failing readiness probe removes a pod from this set. [12]
- **Ephemeral** — Designed to be destroyed and recreated rather than repaired. The property that makes autoscaling and immutable deploys possible. [05] [14]
- **Error budget** — The failure your SLO permits (99.9% means 43 minutes a month). While budget remains you ship; when it is spent you fix reliability. [14]
- **etcd** — The distributed key-value store holding all Kubernetes state. Back it up; losing it is losing the cluster. [12]
- **Exemplar** — A trace ID attached to a Prometheus histogram bucket, so a latency spike on a graph links to a request that was actually that slow. [07]
- **Exit code** — A process's numeric result. `0` is success, `137` is SIGKILL (usually OOM), `139` is a segfault. The cheapest diagnostic there is. [01] [12]
- **Exponential backoff** — Waiting progressively longer between retries, with jitter, so a recovering service is not immediately flattened again. [14]

## F

- **Facts (Ansible)** — Data gathered from the target at the start of a play (OS family, IPs, memory), usable as variables. Gathering costs time you can skip when you do not need them. [11]
- **Fast-forward merge** — Merge with no divergence, so the branch pointer just moves forward and no merge commit is created. [03]
- **Feature flag** — Shipping code disabled and enabling it separately, which decouples deploy from release and makes rollback a config change. [06]
- **Filesystem Hierarchy Standard** — The convention behind `/etc`, `/var`, `/usr`, `/opt`: knowing where things live is how you navigate an unfamiliar server. [01]
- **FinOps** — Treating cloud cost as an engineering metric: allocate it with enforced tags, measure unit cost, then optimise. The loop is inform → optimise → operate, and "inform" is the step that changes behaviour. [09]
- **Firewall** — Rules that permit or drop traffic. A dropped packet produces a timeout; a rejected one produces "connection refused". [02]
- **Fork** — Your own server-side copy of a repository, the basis of the contribution model for repositories you cannot push to. [03]

## G

- **Gauge** — Prometheus metric type that can go up and down. Read it directly: queue depth, memory in use, replica count. [07]
- **GitHub Actions** — GitHub's CI/CD system: workflows of jobs and steps triggered by repository events. [06]
- **GitLab CI** — GitLab's built-in CI/CD: one `.gitlab-ci.yml`, stages and jobs, and every job running inside a container image you name. No action marketplace, so more of the pipeline is shell you wrote. [06]
- **GitOps** — Git as the single source of truth for infrastructure and deployment state, with a controller continuously reconciling the cluster to the repository. [06] [12]
- **Golden image** — A pre-baked machine or container image with everything installed, so instances boot ready rather than configuring themselves. [09] [11]
- **Golden path** — The supported, paved route for a common task (create a service, ship to prod) that a platform team maintains. It must be easier than doing it yourself, and must have an escape hatch. [14]
- **Graceful shutdown** — Handling SIGTERM by finishing in-flight requests and closing connections before exiting. Its absence is why rolling updates drop traffic. [05] [12]
- **Grafana** — Dashboarding and visualization layer over Prometheus, Loki, and other data sources. [07]
- **group_vars** — Ansible directory holding variables that apply to every host in an inventory group. Where environment differences belong. [11]

## H

- **Handler (Ansible)** — A task that runs only when notified by a changed task, and by default only at the end of the play. How you restart a service once after several config changes. [11]
- **HCL** — HashiCorp Configuration Language, the syntax Terraform is written in. [10]
- **Health check** — An endpoint a load balancer or orchestrator polls to decide whether an instance should receive traffic. Too shallow keeps broken instances in rotation; too deep drains the whole fleet at once. [14]
- **Helm** — Kubernetes package manager: templated, versioned, parameterized manifest bundles ("charts") you can install and roll back. [12]
- **High availability (HA)** — Designing so that a component failure does not become an outage: redundancy plus automatic failover, tested. [14]
- **Histogram** — Prometheus metric type that buckets observations, so quantiles like p95 and p99 can be computed from it. [07]
- **Horizontal scaling** — Adding more instances behind a load balancer. Needs statelessness; has no ceiling. [14]
- **Hypervisor** — The layer that runs virtual machines, each with its own kernel. What containers deliberately do without. [05]

## I

- **IaaS / PaaS / SaaS** — Rented infrastructure / rented platform / rented application. The boundary decides who patches what. [09]
- **IAM** — Identity and Access Management: who (or what) may do which action to which resource. The cloud control that matters most. [09] [13]
- **Idempotence** — Running the operation again changes nothing further. The property that makes automation safe to re-run, which it will be. [11]
- **Image layer** — A filesystem diff produced by one build instruction, cached and shared between images. Deleting a file in a later layer does not remove it from the image. [05]
- **Immutable infrastructure** — Never patching a running server: build a new image, replace the instance. Kills configuration drift and snowflake servers. [09] [10]
- **Incident commander (IC)** — The person running an incident: decisions, severity, delegation, escalation. Explicitly *not* debugging — the moment the IC is head-down in logs, nobody is running the incident. [16]
- **Ingress (Kubernetes)** — HTTP routing into the cluster by host and path, implemented by a controller such as nginx or Traefik. [12]
- **Init container** — A container that must complete before the main containers in a pod start. For migrations, waits, and setup. [12]
- **Inode** — Filesystem metadata entry per file. Exhausting inodes produces "no space left on device" while `df` shows free bytes; `df -i` reveals it. [01]
- **Inventory (Ansible)** — The list of managed hosts and their groups, static or generated dynamically from a cloud API. [11]

## J

- **Jaeger** — CNCF distributed tracing backend: stores traces and serves the waterfall UI. Tempo is the Grafana-stack alternative; OpenTelemetry is how you get spans into either. [07]
- **Jenkins** — Long-established self-hosted automation server, pipelines defined in a `Jenkinsfile`. Still everywhere in enterprises. [06]
- **Jitter** — Deliberate randomness added to timers (retries, TTLs, scrape offsets) so many clients stop synchronizing into a thundering herd. [14]
- **Job / CronJob (Kubernetes)** — Workloads that run to completion, once or on a schedule, rather than staying up. [12]
- **journald** — systemd's structured log store, queried with `journalctl`. Where a service's output goes when it does not write its own file. [01]

## K

- **kubectl** — The CLI for the Kubernetes API. `get`, `describe`, `logs`, and `events` answer most questions. [12]
- **kubelet** — Node agent that starts the containers assigned to it and reports their status back. [12]
- **kube-proxy** — Node component that programs the routing rules making Service virtual IPs work. [12]
- **Kubernetes** — Container orchestrator built on control loops that continuously reconcile actual state toward declared state. [12]

## L

- **Label** — Key-value metadata. In Kubernetes, selectors use labels to attach Services to pods. In Prometheus, labels are the dimensions of a metric — and the source of cardinality problems. [07] [12]
- **Layer 4 / Layer 7** — Load balancing on IP and port (fast, protocol-blind) versus on HTTP (routing by host and path, TLS termination, retries). [02] [14]
- **Lead time for changes** — Time from commit to running in production. A DORA metric, and the honest measure of your pipeline. [00]
- **Least privilege** — Grant only the permissions actually needed, scoped to specific resources. Reached by starting from nothing and adding what failed — never by tightening a wildcard later. [13]
- **Liveness probe** — Kubernetes check that restarts a container when it fails. Using one where you needed a readiness probe restart-loops a merely busy application. [12]
- **Load balancer** — Distributes traffic across healthy backends and removes unhealthy ones. Also the place TLS usually terminates. [02] [14]
- **Lock (state)** — Mutual exclusion so two people cannot `terraform apply` simultaneously and corrupt state. [10]
- **Log level** — ERROR / WARN / INFO / DEBUG. A policy nobody follows produces a stream where everything is an error, which means nothing is. [08]
- **Loki** — Log store that indexes only labels and keeps compressed chunks. Far cheaper than Elasticsearch; full-text search is a scan. [08]

## M

- **Managed service** — Cloud-operated version of something you would otherwise run (RDS, EKS, MSK). You trade cost and control for not being paged about it. [09]
- **Manifest** — A YAML file declaring a Kubernetes object's desired state. [12]
- **Merge conflict** — Two branches changed the same lines and Git will not guess. Resolving means choosing or combining, then removing the markers. [03]
- **Module (Terraform)** — A reusable, parameterized group of resources with inputs and outputs. The unit of reuse across environments. [10]
- **MTTA** — Mean time to acknowledge: alert fired → a human owns it. Distinct from MTTR, and the one an on-call rotation is actually judged on. [16]
- **MTTR** — Mean time to restore service. The DORA metric that improves most when rollback is automated. [00]
- **mTLS** — Mutual TLS: both sides present certificates, so identity is verified in both directions. What a service mesh gives you across every service, in any language, without app changes. [12] [13]
- **Multi-stage build** — Dockerfile with several `FROM` stages so build tooling stays out of the final image. Smaller image, much smaller attack surface. [05]
- **Mutable tag** — An image tag like `:latest` or `:3.19` whose meaning can change under you. The reason to pin digests. [05] [13]

## N

- **NACL** — Stateless subnet-level firewall in AWS, supporting deny rules and requiring both directions to be allowed. Contrast with security groups. [09]
- **Namespace (Kubernetes)** — Logical partition of cluster objects, the scope for RBAC, quotas, and network policy. [12]
- **Namespace (Linux)** — Kernel isolation of a process's view of PIDs, mounts, network, users. The "isolation" half of containers. [05]
- **NAT gateway** — Lets private-subnet resources reach the internet without being reachable from it. Bills by the hour and by the gigabyte, forever, whether used or not. [09]
- **Network policy** — Kubernetes firewall rules between pods. Without one, every pod can talk to every other pod. [12] [13]
- **Node** — A machine that runs workloads: EC2 instance, VM, or bare metal, running kubelet in a Kubernetes cluster. [12]
- **Non-root user** — Running the application as an unprivileged account so a compromise does not start with full control. [05] [13]

## O

- **Observability** — Whether your telemetry lets you answer questions you did not anticipate. Monitoring covers the failures you predicted. [07]
- **OIDC federation** — Letting CI or a workload exchange a signed identity token for short-lived cloud credentials, so no long-lived key exists to leak. [06] [13]
- **OOMKilled** — The kernel killed the process to reclaim memory (exit 137). In Kubernetes it means the container exceeded its memory limit. [01] [12]
- **OpenTelemetry** — Vendor-neutral standard and SDK set for emitting traces, metrics, and logs. The current answer to the tracing pillar. [07]
- **Orchestration** — Scheduling, scaling, healing, and networking containers across many machines. The problem Kubernetes exists to solve. [12]
- **OSI model** — Seven-layer network reference model. Its practical value is giving you an order to debug in. [02]
- **OTLP** — OpenTelemetry's wire protocol (gRPC or HTTP). One protocol every SDK, collector, and backend speaks, which is what ended per-vendor agents. [07]

## P

- **p95 / p99** — The latency 95% or 99% of requests come in under. Averages hide the users who are actually suffering. [07]
- **Packer** — Builds machine images (AMIs, VM templates) so instances boot ready instead of configuring themselves. The mechanism behind golden images and immutable infrastructure. [10]
- **Persistent volume (PV/PVC)** — Kubernetes storage that outlives the pod using it, claimed by a PVC and bound to a volume. [12]
- **Pipeline** — The automated sequence a change passes through: lint, test, build, scan, deploy. Ordered cheapest-first so feedback is fast. [06]
- **Platform engineering** — Treating internal tooling as a product whose users are engineers: golden paths, self-service, and service teams still owning production. Not a team that deploys on your behalf. [14]
- **Playbook** — An Ansible YAML file mapping plays (host groups) to tasks. [11]
- **Pod** — The smallest deployable Kubernetes unit: one or more containers sharing a network namespace and storage. [12]
- **Portfolio project** — A project with a stated problem, constraints, a decision you can defend, and setup a stranger can reproduce. A replayed tutorial is not one. [15]
- **Poison message** — A message that can never succeed (malformed, or referencing deleted data). Retried forever it blocks a partition or burns consumers indefinitely — cap attempts and route it to a DLQ. [14]
- **Postmortem** — Written incident review: timeline, contributing causes, and actions with owners. Worthless if it names people instead of mechanisms. [00] [13]
- **Privileged container** — A container with host-level capabilities. Not a hardening tradeoff — effectively node ownership. [13]
- **Probe** — Kubernetes health check: liveness (restart), readiness (remove from Service), startup (delay liveness). [12]
- **Prometheus** — Metrics system that scrapes `/metrics` endpoints, stores time series, evaluates alert rules, and answers PromQL. [07]
- **PromQL** — Prometheus query language. `rate()`, `sum by ()`, and `histogram_quantile()` cover most real dashboards. [07]
- **Provider (Terraform)** — Plugin that translates Terraform resources into a specific API's calls (AWS, Kubernetes, GitHub). [10]
- **Pull request (PR)** — Proposing a change for review before merge. The gate where CI, review, and branch protection meet. [03]
- **Push vs pull (monitoring)** — Targets send metrics, or the monitoring system scrapes them. Prometheus pulls, so a dead target is itself a signal. [07]

## Q

- **Quorum** — The majority a distributed system needs to accept writes. Why etcd clusters have an odd number of members. [12] [14]
- **Quota (ResourceQuota)** — Namespace-level cap on how much CPU, memory, or how many objects a team can consume. [12]

## R

- **`rate()`** — PromQL function giving per-second average increase of a counter over a window, handling resets. Almost every counter query needs it. [07]
- **RBAC** — Role-based access control: roles grant verbs on resources, bindings attach roles to subjects. Kubernetes' authorization model. [12] [13]
- **Readiness probe** — Removes a pod from Service endpoints without restarting it. The right probe for "temporarily cannot serve". [12]
- **Rebase** — Replaying your commits on top of another branch for linear history. Never on a branch others have pulled. [03]
- **Reconciliation loop** — Controller pattern: observe actual state, compare to desired, act, repeat. Why a pod you deleted comes back. [12]
- **Registry** — Server storing container images (Docker Hub, ECR, GHCR). Pull limits and image provenance both live here. [05]
- **Remote state** — Terraform state in shared, locked, encrypted storage instead of on a laptop. The prerequisite for more than one operator. [10]
- **Replica** — One instance of an identical workload. `replicas: 3` is a desired count a controller maintains. [12]
- **Requests and limits** — Requests are what the scheduler reserves and you are guaranteed; limits are the ceiling where you get throttled (CPU) or killed (memory). [12]
- **Retry storm** — Retries multiplying load on an already failing dependency until it cannot recover. Backoff, jitter, and circuit breakers exist for this. [14]
- **Reverse proxy** — Server that terminates client connections and forwards to backends, adding TLS, caching, routing, and rate limiting. [02]
- **Revert** — A new commit that undoes an earlier one, leaving history intact. The safe undo on shared branches. [03]
- **Role (Ansible)** — A reusable unit with fixed directories for tasks, handlers, templates, and defaults. [11]
- **Role (IAM)** — An identity a workload assumes to get short-lived credentials. Always preferable to a static access key. [09] [13]
- **Rollback** — Returning to the previous known-good version. If it is not automated and rehearsed, it does not exist. Note the contrast with a *restart*: a restart that recovers the service and then recurs is not a mitigation, it is a way to spend your night. [06] [16]
- **Rolling update** — Replacing instances a few at a time so the service stays up. Needs readiness probes and graceful shutdown to be truly zero-downtime. [06] [12]
- **Route table** — What actually decides whether a subnet is public: a route to an internet gateway, to a NAT gateway, or to nowhere. [09]
- **RPO** — Recovery point objective: how much data you can afford to lose. Sets backup frequency and replication. [14]
- **RTO** — Recovery time objective: how long you can be down. Sets the DR architecture and its cost. [14]
- **Runbook** — Step-by-step procedure for a known operational task or alert. An alert without one is a page without an action. [01] [07]

## S

- **Sampling (head vs tail)** — Head sampling decides at the start of a trace, in the SDK: cheap, and blind to whether the request will fail or be slow. Tail sampling decides in the collector once the trace is complete, so you can keep every error and every slow trace. [07]
- **SAST** — Static analysis of your own source for dangerous patterns, run in the pipeline. [13]
- **SBOM** — Software bill of materials: the inventory of everything in your artefact. What makes "are we affected?" answerable in minutes. [13]
- **SCA** — Software composition analysis: checking your dependencies against known vulnerabilities. Most of your code is someone else's. [13]
- **Scheduler** — Kubernetes component that picks a node for each unassigned pod, using requests, affinity, taints, and topology. [12]
- **Scrape** — Prometheus fetching `/metrics` from a target on an interval. A failed scrape sets `up == 0`, which is itself alertable. [07]
- **Secret (Kubernetes)** — Base64-encoded, not encrypted. Protect it with RBAC, encryption at rest, and for anything valuable an external secret store. [12] [13]
- **Secrets management** — Storing credentials outside code, with rotation and audit: Vault, cloud secret managers, SOPS, Ansible Vault. [13]
- **Security group** — Stateful, instance-level cloud firewall with allow rules only; return traffic is automatic. Contrast with NACLs. [09]
- **Selector** — Label query that decides which objects something applies to — which pods a Service sends traffic to, for instance. [12]
- **Service (Kubernetes)** — Stable name and virtual IP in front of a changing set of pods, with endpoints maintained by readiness. [12]
- **Service mesh** — Sidecar-proxy layer providing mTLS, retries, traffic splitting, and per-call telemetry without application changes. Real capability, real operational cost. [12] [14]
- **`set -euo pipefail`** — Bash prelude: exit on unhandled error, error on an unset variable, and fail a pipeline when any stage fails. Without the last part, `curl broken | jq .` reports success. [04]
- **Severity (SEV1/2/3)** — Declared classification of an incident that decides who is woken, who is told, and how much you may break to fix it. Anyone may declare; over-declare and downgrade later. [16]
- **Shebang** — The `#!/usr/bin/env bash` first line that tells the kernel which interpreter runs the script. Without it you are relying on whatever shell happens to invoke it. [04]
- **Shift left** — Moving checks earlier — tests, scans, review — because defects get more expensive the further right they surface. [00] [13]
- **Sidecar** — A helper container in the same pod as the application: log shipper, proxy, credential refresher. [12]
- **SLA / SLO / SLI** — The contract with consequences / your internal target / the actual measurement. The SLA is always looser than the SLO. [14]
- **Span** — One timed operation in a trace: name, duration, parent, status, attributes. A trace is the tree of them; the tree is what tells you which hop was slow. [07]
- **SPOF** — Single point of failure: the component whose loss takes everything with it. Finding them is the point of an HA review. [14]
- **`ss`** — Modern replacement for `netstat`. `ss -ltnp` answers "what is listening on that port". [01] [02]
- **STAR method** — Situation, Task, Action, Result: the structure for behavioural interview answers. The Result, with a number in it, is the part most people skip. [16]
- **State (Terraform)** — The mapping from configuration to real resources. Also a secret, since it stores attribute values in plain text. [10]
- **StatefulSet** — Kubernetes workload giving pods stable identities, stable per-pod storage, and ordered rollout. For databases and quorum systems. [12]
- **Structured logging** — Emitting logs as key-value events (usually JSON) instead of sentences, so they can be filtered and aggregated without regex. [08]
- **Subnet** — An IP range within a VPC, tied to one availability zone, public or private according to its route table. [02] [09]
- **systemd** — The init and service manager on most Linux distributions. `systemctl` controls units; `enable` is boot, `start` is now. [01]

## T

- **Taint / toleration** — Node marking that repels pods unless they explicitly tolerate it. How you reserve nodes for particular workloads. [12]
- **TCP vs UDP** — Ordered, reliable, connection-oriented versus fire-and-forget with lower latency. HTTP and SSH versus DNS and metrics. [02]
- **Tempo** — Grafana's trace backend: stores traces in object storage and is queried with TraceQL. Cheap because it indexes almost nothing. [07]
- **Terraform** — Declarative infrastructure-as-code tool that plans a diff against recorded state and applies it through providers. [10]
- **Three pillars** — Metrics, logs, and traces. Most teams have the first two and improvise the third. [07]
- **TLS** — Encryption and server identity for connections. `openssl s_client -connect` is how you debug the handshake instead of guessing. [02] [13]
- **Toil** — Manual, repetitive operational work that scales with traffic and produces no lasting value. The thing automation is for. [00]
- **TraceQL** — Tempo's query language for finding traces by span attributes, duration, and status — `{ status = error && duration > 500ms }`. [07]
- **`trap`** — Bash builtin that runs a command on a signal or on exit. `trap 'rm -rf "$tmp"' EXIT` is how cleanup happens even when the script fails. [04]
- **Trunk-based development** — Everyone integrates into main constantly behind short-lived branches and feature flags. What makes CI actually continuous. [03] [06]
- **TTL** — How long a cached record stays valid. Short TTLs make DNS cutovers fast; long ones survive an outage of the authority. [02] [14]

## U

- **Uptime "nines"** — 99.9% is 43 minutes down per month; 99.99% is 4.3. Each nine multiplies cost, so someone should say why it is needed. [14]
- **Unit cost** — Cost per unit of work: per 1,000 requests, per order, per tenant. The metric that distinguishes growth from an efficiency regression, which total spend cannot. [09]
- **Upstream** — The remote you track (`git`), or the backend a proxy forwards to (`nginx`). Context decides which. [02] [03]

## V

- **Variable precedence** — The order competing definitions of a variable resolve in. In Ansible, role defaults are weakest and `-e` beats everything. [11]
- **Vault** — HashiCorp's secret store with dynamic short-lived credentials, leases, and audit. Ansible Vault is a different thing: encrypted files at rest. [11] [13]
- **Version pinning** — Specifying exact versions or digests for dependencies, base images, and actions, so builds are reproducible and reviewable. [06] [13]
- **Vertical scaling** — A bigger machine. Simple, immediate, has a hard ceiling, and usually needs a restart. [14]
- **Volume** — Storage that outlives the container writing to it. Anything written to the container's own writable layer dies with it. [05] [12]
- **VPC** — Your isolated virtual network in the cloud: subnets, route tables, gateways, and the security boundaries between them. [09]

## W

- **Wall of confusion** — The hand-off between a dev team rewarded for change and an ops team rewarded for stability. The problem DevOps was invented to solve. [00]
- **Webhook** — HTTP callback one system sends another on an event; how pushes trigger pipelines and alerts reach chat. [06]
- **Worker node** — A cluster machine that runs workloads, as opposed to control plane components. [12]
- **Workspace (Terraform)** — Multiple named states from one configuration. Workable for small variations; separate directories or a module per environment scales better. [10]

## X

- **X-Forwarded-For** — Header a proxy uses to record the original client IP, since the backend only sees the proxy's address. Trust it only from your own proxy. [02]

## Y

- **YAML anchor** — `&name` to define a block and `*name` to reuse it, avoiding duplication in Compose and CI files. Powerful, and easy to make unreadable. [05] [06]

## Z

- **Zero-downtime deployment** — Releasing without dropping requests. Requires rolling or blue-green deploys, readiness probes, graceful shutdown, and backward-compatible migrations — all four. [06] [12]
- **Zone (DNS)** — The portion of the namespace an authoritative server is responsible for, holding its records. [02]

---

[00]: ./00-foundations/
[01]: ./01-linux/
[02]: ./02-networking/
[03]: ./03-git/
[04]: ./04-scripting/
[05]: ./05-containers-docker/
[06]: ./06-ci-cd/
[07]: ./07-observability/
[08]: ./08-logging/
[09]: ./09-cloud-fundamentals/
[10]: ./10-terraform/
[11]: ./11-ansible/
[12]: ./12-kubernetes/
[13]: ./13-security-basics/
[14]: ./14-system-design-devops/
[15]: ./15-projects/
[16]: ./16-interview-prep/

<div align="center">

[← Back to README](./README.md) | [📋 Quick Reference](./QUICK-REFERENCE.md) | [🧭 Practical Learning](./PRACTICAL-LEARNING.md)

</div>
