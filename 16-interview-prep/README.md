# Module 16: Interview Prep

> *"The best interview answers come from real experience — not memorized definitions." — Hiring Manager*

---

## 🎯 Why This Module Matters

You have the skills. Now you need to **communicate them under pressure**. DevOps interviews combine technical depth, operational judgment, and the ability to think through ambiguous problems in real time. This module prepares you for all three.

**DevOps interviews typically include**:

- Technical knowledge questions (tools, concepts, protocols)
- Scenario-based problems (debug this, design that)
- System design discussions (architecture trade-offs)
- Behavioral questions (how you work, how you handle failure)
- Live debugging or hands-on exercises

---

## 📚 Table of Contents

1. [Interview Format Overview](#1-interview-format-overview)
2. [Technical FAQs by Domain](#2-technical-faqs-by-domain)
3. [Scenario-Based Questions](#3-scenario-based-questions)
4. [System Design Interview Framework](#4-system-design-interview-framework)
5. [Behavioral Questions](#5-behavioral-questions)
6. [Mock Incident Debugging](#6-mock-incident-debugging)
7. [Common Mistakes in Interviews](#7-common-mistakes-in-interviews)
8. [Preparation Checklist](#8-preparation-checklist)
9. [Certification Map](#9-certification-map)
10. [Resume, LinkedIn, and the Job Search](#10-resume-linkedin-and-the-job-search)

---

## 1. Interview Format Overview

```
TYPICAL DEVOPS INTERVIEW PIPELINE:

Round 1: Recruiter Screen (30 min)
  → Resume walkthrough, motivation, salary expectations

Round 2: Technical Phone Screen (45-60 min)
  → Linux, networking, Docker, CI/CD questions
  → Maybe a live debugging exercise

Round 3: System Design (60 min)
  → "Design a deployment pipeline for..."
  → "How would you make this system highly available?"

Round 4: Hands-On / Take-Home (60-120 min)
  → Write a Terraform config, fix a broken pipeline
  → Debug a Kubernetes deployment, automate a task

Round 5: Behavioral / Culture Fit (45 min)
  → Teamwork, incident handling, communication style

KEY PRINCIPLE:
  Don't just answer WHAT — explain WHY and WHEN.
  "I'd use Terraform" → ❌
  "I'd use Terraform because the team needs multi-cloud
   support and we want declarative, version-controlled
   infrastructure with a plan-before-apply workflow" → ✅
```

---

## 2. Technical FAQs by Domain

### Linux & System Administration

**Q: How do you troubleshoot a server that's running slow?**
> Systematic approach: 1) Check load average with `uptime`. 2) Identify CPU-heavy processes with `top` or `htop`. 3) Check memory with `free -h` — look for swap usage. 4) Check disk I/O with `iostat` or `iotop`. 5) Check disk space with `df -h`. 6) Check network with `ss -tlnp` and `netstat`. 7) Review logs in `/var/log/syslog` or `journalctl`. The goal is to narrow down whether it's CPU, memory, disk, network, or application-level.

**Q: What's the difference between a process and a thread?**
> A process is an independent execution unit with its own memory space. A thread is a lightweight unit within a process that shares the process's memory. Multiple threads in a process can communicate through shared memory (fast but needs synchronization), while processes communicate through IPC mechanisms like pipes or sockets. In DevOps context: Nginx uses multiple worker processes, while Java apps often use multiple threads within one process.

**Q: Explain file permissions in Linux.**
> Three permission types (read, write, execute) for three categories (owner, group, others). Represented as `rwxrwxrwx` or octal (755 = rwxr-xr-x). The sticky bit prevents users from deleting others' files in shared directories. SUID/SGID lets a program run as the file owner/group. For DevOps: SSH keys must be 600, directories should be 755, and sensitive configs should be 640 or stricter.

### Networking

**Q: What happens when you type a URL in a browser?**
>
> 1) DNS resolution: browser cache → OS cache → recursive resolver → authoritative DNS. 2) TCP connection: three-way handshake (SYN, SYN-ACK, ACK). 3) TLS handshake if HTTPS. 4) HTTP request sent. 5) Server processes and returns response. 6) Browser renders the page. In DevOps context, issues can occur at any layer — DNS misconfiguration, firewall blocking ports, expired TLS certificates, application errors.

**Q: Explain the difference between TCP and UDP.**
> TCP is connection-oriented with guaranteed delivery, ordering, and flow control. Used for HTTP, SSH, databases. UDP is connectionless — faster but no delivery guarantee. Used for DNS, video streaming, monitoring (StatsD). For DevOps: most services use TCP. Health checks usually use TCP or HTTP. Load balancers can operate at L4 (TCP) or L7 (HTTP).

### Docker & Containers

**Q: What's the difference between a Docker image and a container?**
> An image is a read-only template with the filesystem and configuration. A container is a running instance of an image with its own writable layer. Like a class vs an object in programming. You can run multiple containers from the same image. Images are built in layers (each Dockerfile instruction = one layer), which enables caching and sharing.

**Q: How do you reduce Docker image size?**
> Use multi-stage builds (build in one stage, copy artifacts to a slim runtime stage). Use slim/alpine base images. Combine RUN commands to reduce layers. Use `.dockerignore` to exclude unnecessary files. Don't install development tools in the final image. Pin specific versions instead of `:latest`.

**Q: What happens when a Docker container runs out of memory?**
> If memory limits are set, the kernel OOM-killer terminates the container's main process. Docker reports it as exit code 137 (SIGKILL). Without limits, the container can consume all host memory, potentially crashing other containers or the host itself. Always set memory limits in production. Monitor with `docker stats` or Prometheus cAdvisor metrics.

### CI/CD

**Q: Describe a CI/CD pipeline you've built.**
> Use the STAR method: Situation (what the team needed), Task (what you built), Action (specific tools and design decisions), Result (measurable outcome). Example: "We had manual deployments taking 2 hours with frequent rollbacks. I built a GitHub Actions pipeline with lint, test, Docker build, image scan, and deployment stages. Deployments went from 2 hours to 8 minutes with a 90% reduction in post-deploy incidents."

**Q: What's the difference between continuous delivery and continuous deployment?**
> Continuous delivery: every commit that passes CI is deployable, but a human approves production releases. Continuous deployment: every commit that passes CI is automatically deployed to production. Most teams start with continuous delivery and move to continuous deployment as confidence grows. The key enabler is comprehensive automated testing.

### Infrastructure as Code

**Q: What is Terraform state and why does it matter?**
> State is Terraform's record of what it has created. It maps your configuration to real infrastructure. Without state, Terraform can't know what exists and would try to create duplicates. State should be stored remotely (S3 + DynamoDB for locking) in team environments. Never commit state to git — it may contain secrets. Use `terraform plan` to preview changes before applying.

**Q: Terraform vs Ansible — when to use each?**
> Terraform is declarative and excels at provisioning infrastructure (VMs, networks, databases). Ansible is procedural/declarative and excels at configuring software on existing machines. Use Terraform to create the servers, Ansible to configure them. Some overlap exists — Terraform has provisioners, Ansible has cloud modules — but each tool is strongest in its primary domain.

### Kubernetes

**Q: How does a Kubernetes Deployment work?**
> A Deployment manages a ReplicaSet, which manages Pods. When you update a Deployment, K8s creates a new ReplicaSet with updated pods while scaling down the old one (rolling update). If the new pods fail health checks, the rollout pauses. You can rollback with `kubectl rollout undo`. The Deployment controller ensures the desired state matches actual state continuously.

**Q: How do you debug a pod that won't start?**
>
> 1) `kubectl get pods` — check status (Pending, CrashLoopBackOff, ImagePullBackOff). 2) `kubectl describe pod <name>` — check events for errors (scheduling, image pull, volume mount). 3) `kubectl logs <name>` — check application logs (add `--previous` for crashed containers). 4) Common causes: wrong image tag, insufficient resources, failed readiness probe, missing ConfigMap/Secret, node scheduling constraints.

### Monitoring & Logging

**Q: What's the difference between metrics, logs, and traces?**
> Metrics are numeric measurements over time (CPU usage, request count, error rate). Best for alerting and dashboards. Logs are timestamped text records of events. Best for debugging specific issues. Traces follow a single request across multiple services. Best for understanding latency in distributed systems. Together they form the "three pillars of observability."

**Q: How do you design alerts that don't cause alert fatigue?**
> Alert on symptoms (user-facing impact), not causes. Use SLO-based alerting — alert when error budget is burning too fast. Set appropriate thresholds with hysteresis (different thresholds for firing and resolving). Page only for actionable, urgent issues. Use severity levels: page for critical, ticket for warning, dashboard for info. Review and tune alerts quarterly.

---

## 3. Scenario-Based Questions

### Scenario 1: Production Outage

**Q: "Users are reporting that the website is slow. Walk me through how you'd investigate."**

```
FRAMEWORK: Symptom → Scope → Isolate → Root Cause → Fix → Prevent

1. CONFIRM THE SYMPTOM
   - Check monitoring dashboards (Grafana)
   - Verify with synthetic checks (curl response times)
   - Check error rates in metrics

2. DETERMINE THE SCOPE
   - All users or specific regions?
   - All pages or specific endpoints?
   - Started gradually or suddenly?

3. ISOLATE THE LAYER
   - CDN/DNS → check DNS resolution time, CDN cache hit rate
   - Load balancer → check backend health, connection count
   - Application → check response times, error logs, CPU/memory
   - Database → check query latency, connection pool, slow query log
   - External dependency → check third-party API response times

4. ROOT CAUSE
   - Correlate with recent changes (deployments, config changes)
   - Check for traffic spikes or resource exhaustion
   - Review application logs for errors

5. FIX AND COMMUNICATE
   - Apply fix (rollback, scale up, config change)
   - Communicate status to stakeholders
   - Monitor for recovery

6. PREVENT
   - Post-incident review
   - Add missing monitoring/alerts
   - Improve deployment safety (canary, feature flags)
```

### Scenario 2: Deployment Gone Wrong

**Q: "You deployed a new version and error rates jumped to 15%. What do you do?"**
> Immediately roll back to the previous version — restore service first, investigate later. Verify error rates return to normal. Then analyze: check the diff between versions, review error logs from the brief window, check if the issue was caught in staging. Root cause might be a code bug, a missing environment variable, a database migration issue, or an incompatible dependency. Add the failure scenario to your CI/CD tests.

### Scenario 3: Security Incident

**Q: "You discover that database credentials were committed to a public GitHub repo 3 hours ago. What do you do?"**
>
> 1) Immediately rotate the database credentials. 2) Revoke the old credentials. 3) Check database audit logs for unauthorized access in the 3-hour window. 4) Update all services that use those credentials. 5) Remove credentials from git history (BFG or git filter-repo). 6) Force-push (coordinate with team). 7) Add pre-commit hooks (gitleaks) to prevent recurrence. 8) Document the incident and conduct a blameless review.

### Scenario 4: Capacity Planning

**Q: "Your application currently handles 1,000 requests per second. Marketing says traffic will 5x in 3 months due to a product launch. How do you prepare?"**
>
> 1) Load test current capacity — find the actual breaking point, not the theoretical one. 2) Identify bottlenecks: database connection limits, CPU-bound processing, memory per connection. 3) Plan horizontal scaling for stateless tiers (app servers behind load balancer, auto-scaling). 4) Plan vertical scaling or read replicas for the database. 5) Add caching where appropriate (Redis for hot data, CDN for static assets). 6) Set up auto-scaling policies with appropriate metrics. 7) Run load tests at 5x and 10x to validate. 8) Set up alerting at 60% capacity so you know before users do.

---

## 4. System Design Interview Framework

```
FRAMEWORK FOR SYSTEM DESIGN QUESTIONS:

1. CLARIFY REQUIREMENTS (2-3 min)
   - What are the functional requirements?
   - What are the non-functional requirements? (scale, latency, availability)
   - What's the expected traffic? (requests/sec, data volume)
   - What's the team size and operational capability?

2. HIGH-LEVEL DESIGN (5-10 min)
   - Draw the major components (client, LB, app, DB, cache)
   - Show the data flow
   - Identify stateless vs stateful components

3. DEEP DIVE (10-15 min)
   - Pick the most interesting or challenging component
   - Discuss trade-offs for technology choices
   - Address scaling, failure, and security

4. OPERATIONAL CONCERNS (5 min)
   - How do you deploy changes?
   - How do you monitor and alert?
   - How do you handle failures?
   - What does disaster recovery look like?

5. TRADE-OFFS AND ALTERNATIVES (5 min)
   - What did you NOT choose, and why?
   - What would change at 10x scale?
   - What would you do differently with more time/budget?
```

---

## 5. Behavioral Questions

### The STAR Method

```
SITUATION: Describe the context
TASK: What was your responsibility
ACTION: What YOU specifically did (not the team)
RESULT: Measurable outcome
```

### Common Questions

**Q: "Tell me about a time you dealt with a production incident."**
> Use STAR. Focus on: how you stayed calm, how you communicated (incident channel, status updates), how you diagnosed systematically, and what you did to prevent recurrence. Show that you follow blameless postmortem culture.

**Q: "Describe a time you disagreed with a team member about a technical decision."**
> Show that you: listened to their perspective, presented data to support your view, found a compromise or agreed to test both approaches, and prioritized the team outcome over being right.

**Q: "Tell me about a project where you had to learn a new technology quickly."**
> Show your learning process: documentation first, then small proof-of-concept, then incremental adoption. Mention specific resources you used. Emphasize that you validated your understanding before applying it to production.

**Q: "How do you prioritize when everything is on fire?"**
> Triage by user impact. Production-down outages first, then degraded performance, then non-user-facing issues. Communicate clearly about what's being worked on and what's waiting. Don't try to fix everything simultaneously — focus on the highest-impact item.

---

## 6. Mock Incident Debugging

Practice these scenarios to build your debugging muscle memory. Each one maps to a realistic production problem.

**Detailed hands-on exercises**: [lab-01-mock-incident-debugging.md](./labs/lab-01-mock-incident-debugging.md)

### Scenario Quick Reference

| Scenario | Symptoms | Key Debugging Tools |
|----------|----------|-------------------|
| Container crash loop | Pod status: CrashLoopBackOff | `kubectl logs`, `kubectl describe` |
| DNS failure | Connection refused, name resolution errors | `dig`, `nslookup`, `/etc/resolv.conf` |
| Disk full | Write errors, application crashes | `df -h`, `du -sh`, `find / -size +100M` |
| Memory leak | OOM kills, increasing memory usage | `free -h`, `top`, container metrics |
| Certificate expiry | TLS errors, browser warnings | `openssl s_client`, `curl -v` |
| Firewall misconfiguration | Connection timeout, no response | `ss -tlnp`, `iptables -L`, `ufw status` |

---

## 7. Common Mistakes in Interviews

### ❌ Answering with Definitions Only

```
BAD:  "Kubernetes is a container orchestration platform."
GOOD: "Kubernetes manages containerized workloads. I've used it
       to deploy microservices with rolling updates, and I once
       debugged a pod scheduling issue caused by node resource
       pressure that I found using kubectl describe and top."
```

### ❌ Not Asking Clarifying Questions

```
BAD:  Immediately designing a solution for a vague requirement
GOOD: "Before I design this, can I clarify: what's the expected
       traffic? Is this an internal or external-facing service?
       What's the team's operational maturity?"
```

### ❌ Ignoring Trade-Offs

```
BAD:  "I'd use microservices and Kubernetes."
GOOD: "For this scale and team size, I'd start with a monolith
       on Docker Compose with CI/CD. Moving to K8s adds
       operational complexity the team may not be ready for."
```

### ❌ Not Showing Debugging Process

```
BAD:  "I'd restart the server."
GOOD: "First I'd check if the issue is isolated to one server
       or system-wide. Then I'd look at resource utilization,
       application logs, and recent deployment history before
       deciding on a fix."
```

---

## 8. Preparation Checklist

### One Month Before

- [ ] Complete at least one capstone project from Module 15
- [ ] Review technical FAQs for each domain in this module
- [ ] Practice explaining your projects out loud (5-minute walkthrough)
- [ ] Review your resume — can you explain every line in depth?

### One Week Before

- [ ] Do the mock incident debugging lab
- [ ] Practice 5 scenario-based questions with a timer (5 min each)
- [ ] Prepare 3 STAR stories for behavioral questions
- [ ] Review the system design framework

### Day Before

- [ ] Get a good night's sleep
- [ ] Prepare your environment (stable internet, quiet space, water)
- [ ] Have your portfolio repo URL ready to share
- [ ] Review the company's tech stack (job posting, engineering blog)

### During the Interview

- [ ] Think out loud — show your reasoning process
- [ ] Ask clarifying questions before designing solutions
- [ ] Discuss trade-offs, not just solutions
- [ ] Say "I don't know, but here's how I'd find out" when stuck
- [ ] Be specific — use real numbers, real tool names, real experiences

---

## 9. Certification Map

### What Certifications Do and Don't Do

They get your CV past a filter, they give an unstructured subject a syllabus, and for some employers (consultancies, partners with vendor quotas, public-sector contracts) they are a hard requirement. What they do not do is convince an engineer in a technical interview — that is what your projects are for.

The honest ordering: **projects first, then one certification in the area you want to be hired for.** Three certificates and no repository reads as someone who studies rather than builds, and the follow-up questions expose it in minutes.

### The Map

Each row lists the modules that cover the material. Prices and durations are **illustrative 2026 figures — check current pricing**, and note that most vendor exams are discounted or free through training events.

| Certification | Covers modules | Cost (approx) | Valid | Worth it when |
|---------------|----------------|--------------:|-------|---------------|
| **AWS Certified Cloud Practitioner** | 00, 09 | £75 | 3 yr | You need vocabulary and a first credential fast. Skip it if you can pass SAA |
| **AWS Solutions Architect – Associate** (SAA) | 09, 14 | £120 | 3 yr | ⭐ The highest-signal first cloud cert. Widely recognised, genuinely broad |
| **AWS SysOps Administrator / DevOps Engineer – Pro** | 06, 07, 09, 10 | £120 / £240 | 3 yr | You already work in AWS and want depth, not breadth |
| **HashiCorp Terraform Associate** | 10 | £55 | 2 yr | ⭐ Cheap, quick, and maps almost exactly onto Module 10. Excellent value |
| **CKA — Certified Kubernetes Administrator** | 12 | £300 | 2 yr | ⭐ The strongest technical signal on this list. Hands-on exam in a real cluster — you cannot pass it by memorising |
| **CKAD — Application Developer** | 12 | £300 | 2 yr | You deploy on Kubernetes more than you operate it |
| **CKS — Security Specialist** | 12, 13 | £300 | 2 yr | After CKA (it is a prerequisite), and only if security is the direction |
| **LFCS / RHCSA** | 01, 04 | £250 / £330 | 3 yr | Your Linux is the weak part, or the employer is a RHEL shop. RHCSA is hands-on and well respected |
| **Azure AZ-104 / AZ-400, Google ACE** | 09 (concepts transfer) | £120–150 | 1–2 yr | The job you want is on that cloud. Concepts transfer; the exam does not |
| **Certified Jenkins Engineer, Docker DCA** | 05, 06 | varies | varies | Rarely asked for now. Do a project instead |

### Choosing

```
Career-changer, no professional experience yet
  → 1 capstone project → AWS SAA → Terraform Associate
     (breadth + a credential that survives a CV filter)

Sysadmin moving into DevOps
  → RHCSA or LFCS if Linux is your story → CKA
     (you already have the ops instinct; prove the platform)

Developer moving into DevOps/platform
  → CKAD or CKA → Terraform Associate
     (you can code; prove you can operate)

Already in the role, want the next band
  → CKA → CKS, or AWS DevOps Pro
     (depth in the thing you already do)
```

> 💡 **Two traps.** The first is treating a certificate as a substitute for the lab work in this handbook — a CKA holder who has never debugged a CrashLoopBackOff under pressure gets found out in the first scenario question. The second is letting them expire silently: put the renewal date in a calendar the day you pass, because an expired certification on a CV is worse than none.

---

## 10. Resume, LinkedIn, and the Job Search

Module 15 §8 covers how to *present a project*. This section is about the documents and the search itself.

### The Resume Bullet Formula

**Action verb + what you built + the tool + the measurable outcome.** The outcome is the part almost everyone omits, and it is the only part that distinguishes you.

| ❌ Weak | ✅ Strong |
|---------|-----------|
| "Responsible for CI/CD pipelines" | "Built a GitHub Actions pipeline with image scanning that cut mean time from commit to production from 3 days to 40 minutes" |
| "Used Terraform for infrastructure" | "Codified a two-AZ VPC and EKS cluster in Terraform with remote state and locking; environment rebuild went from a day of console work to a 20-minute apply" |
| "Monitored systems with Prometheus" | "Instrumented 4 services with RED metrics and replaced 40 threshold alerts with 6 symptom-based ones, ending alert fatigue on the on-call rotation" |
| "Knowledge of Kubernetes" | "Migrated 3 Compose services to Kubernetes with probes, resource limits, and an HPA; rollbacks went from manual to a single automated step" |

No numbers because it is a personal project? Use the numbers you *do* have: image size before and after, build time, replicas, requests handled in a load test, minutes to rebuild from scratch, cost per month. "Reduced image from 1.2 GB to 78 MB with a multi-stage build" is a real measurement from a personal project.

### Structure and the ATS

Most applications are parsed by software before a human sees them. That imposes boring constraints — accept them:

- **One page** with under ~5 years of experience, two at most beyond that
- **Order**: contact → 2-line summary → skills → experience → projects → education/certs. Career-changers put **projects above experience**
- **Plain single-column layout.** No tables, no text boxes, no icons, no photo, no two-column PDF — parsers mangle all of these. Send PDF unless told otherwise
- **Mirror the posting's vocabulary.** If it says "IaC" and you wrote "infrastructure as code", write both once. This is not gaming the system; it is answering the question they asked
- **Link your portfolio repository in the header**, and make sure its README is the thing you want read first

### GitHub and LinkedIn

Your GitHub is the artefact a technical reviewer actually opens:

- Pin the portfolio repository; make its README the tour, with the architecture diagram visible without scrolling
- Commit history that shows iteration beats one "initial commit" of finished work
- No secrets, anywhere, in any history. This is checked, and it is disqualifying

LinkedIn is a search index, not a CV:

- Headline states the target role, not the current one: "DevOps Engineer — Kubernetes, Terraform, AWS"
- The About section is the same two-minute project pitch you rehearsed for interviews
- Turn on "open to work" for recruiters only, and put the tools in the skills list because that is literally what recruiters filter on

### Running the Search

```
Weekly rhythm that works:
  5-8 targeted applications  ← tailored, researched, one paragraph of why this company
  1 project improvement      ← something new to talk about every week
  2-3 outreach messages      ← engineers at target companies, not recruiters
  1 mock interview           ← out loud, timed, with someone or recording yourself

What does NOT work:
  ❌ 50 applications a day with the same CV
  ❌ Waiting until the portfolio is "finished" — it never is
  ❌ Only applying to postings; most roles are filled through referrals
```

Read the posting for what is actually required rather than the wishlist — "5 years Kubernetes" on a mid-level posting is usually aspirational, and applying anyway is free. Do research one level deeper than the job ad: their engineering blog, their public repositories, their stack. One specific sentence about *their* system in a cover note outperforms a page of enthusiasm.

### Take-Homes and Offers

- **Take-home exercises**: timebox them, and if it exceeds four hours, say what you would have done next rather than working the weekend. Include a README with your tradeoffs — that is what is actually being assessed
- **Salary**: know your range before the first call, from local market data. When asked what you are looking for, give a researched range with a reason attached
- **Negotiation**: one round is expected and does not cost you the offer. Ask for the whole package in writing before deciding, and ask about the on-call rotation and its compensation — you are interviewing the job too
- **The questions you ask** are part of the evaluation. "What does your on-call rotation look like?", "How long does a one-line change take to reach production?", and "What happened in your last incident?" tell you more about a DevOps job than any answer they give about culture

---

## 🧪 Labs and Projects

Read the sections above first, then work through these **in order**. Every lab ends with a 🧨 **Break It** section — those are not optional; they are where the debugging skill actually comes from.

| # | Lab | What you'll do |
|---|-----|----------------|
| 1 | **[Mock Incident Debugging](./labs/lab-01-mock-incident-debugging.md)** | Practice diagnosing and resolving simulated production incidents using Docker. |
| 2 | **[Incident Response — Running the Process](./labs/lab-02-incident-response.md)** | Get paged with traffic still arriving: declare a severity, communicate before you know the cause, mitigate rather than root-cause, then write the postmortem. |

**Portfolio project:**

- [Project: Interview Portfolio](./projects/project-01-interview-portfolio.md) — Compile your DevOps learning journey into an interview-ready portfolio.

**Reference code** for every lab: [`code/`](./code/) — real files, validated in CI.

---

## ✅ Self-Check

Answer these from memory before you expand them. If more than two give you trouble, re-read the sections they come from — the labs assume this material is solid.

<details>
<summary><strong>1. "The service is down — walk me through it." How do you structure the answer?</strong></summary>

State what you would confirm first (are users affected, or only a monitor), then work outward through the layers naming the signal that would confirm or kill each hypothesis: recent deploys, DNS, load balancer, application, dependencies, database. Say what you would do to restore service before you talk about root cause. Structure is what is being assessed, not the answer.

</details>

<details>
<summary><strong>2. Why is "roll back first" such a strong answer?</strong></summary>

Because restoring service and understanding the failure are two different jobs, and doing them in that order is the whole discipline. You stop the bleeding, preserve the evidence — logs, a snapshot, the failing pod — and investigate afterwards. Debugging live while users are down is the mistake interviewers are listening for.

</details>

<details>
<summary><strong>3. What is STAR, and what do most candidates leave out?</strong></summary>

Situation, Task, Action, Result. The Result — with a number in it — is what most people skip, and the honest "what I would do differently" that follows it is what distinguishes a senior answer from a competent one.

</details>

<details>
<summary><strong>4. You have 45 minutes for a system design question. What order?</strong></summary>

Clarify requirements and get real numbers first, sketch the high-level request path, then go deep wherever the interviewer pushes. Leave time for failure modes, monitoring, and cost. Drawing boxes before asking questions is the most common way this interview is lost.

</details>

<details>
<summary><strong>5. How do you handle a question you cannot answer?</strong></summary>

Say what you do know, how you would find out, and what you would expect to be true — then move on without dwelling. An invented specific is far worse than an admitted gap: once one detail is caught as fabricated, every other answer is suspect.

</details>

<details>
<summary><strong>6. What preparation actually differentiates candidates?</strong></summary>

Having built things and broken them, so you can answer follow-ups with specifics: the actual error message, the number you measured, the tradeoff you accepted. Memorized definitions survive the first question and collapse on the second.

</details>

---

## Practical Checkpoint

Before considering yourself interview-ready, you should be able to:

- Answer any technical FAQ in this module fluently and with real examples.
- Walk through a production incident scenario using the systematic debugging framework.
- Design a system architecture on a whiteboard, explaining trade-offs at each decision point.

Portfolio evidence to keep:

- Your capstone projects from Module 15 with polished READMEs.
- Written answers to 10 scenario-based questions.
- At least 3 STAR stories documented and practiced.

Suggested project: [Interview Portfolio](./projects/project-01-interview-portfolio.md)

---

<div align="center">

**Module 16 Complete** ✅

**🎉 Congratulations — You've Completed The DevOps Handbook! 🎉**

[← Back to Projects](../15-projects/) | [Back to Main README →](../README.md)

</div>
