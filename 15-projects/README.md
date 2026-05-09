# Module 15: Capstone Projects

> *"You don't truly understand something until you've built it, broken it, and fixed it under pressure." — Engineering Wisdom*

---

## 🎯 Why This Module Matters

Everything you've learned across 14 modules means nothing if you can't combine it into working systems. This module is where you **prove** your skills by building real-world projects that integrate infrastructure, automation, monitoring, security, and operations into cohesive, production-quality deliverables.

**These projects are your portfolio.** They're what you show in interviews, link on your resume, and reference when discussing your capabilities. Each project is designed to demonstrate specific competencies that hiring managers look for.

---

## 📚 Table of Contents

1. [Project Philosophy](#1-project-philosophy)
2. [Project Progression](#2-project-progression)
3. [Portfolio Structure](#3-portfolio-structure)
4. [Project 1: Static Site Pipeline (Beginner)](#4-project-1-static-site-pipeline-beginner)
5. [Project 2: Microservices Platform (Intermediate)](#5-project-2-microservices-platform-intermediate)
6. [Project 3: Production Infrastructure (Advanced)](#6-project-3-production-infrastructure-advanced)
7. [Cross-Cutting Expectations](#7-cross-cutting-expectations)
8. [Presenting Your Work](#8-presenting-your-work)

---

## 1. Project Philosophy

### What Makes a Good Portfolio Project

```
GOOD PORTFOLIO PROJECT:
  ✅ Solves a realistic problem (not a toy example)
  ✅ Uses production patterns (CI/CD, monitoring, secrets management)
  ✅ Is reproducible (someone else can run it from your README)
  ✅ Shows debugging (you broke something and fixed it — documented)
  ✅ Has a clear README with architecture diagram
  ✅ Includes cleanup instructions

BAD PORTFOLIO PROJECT:
  ❌ "Hello World" deployed to Kubernetes (over-engineered, no substance)
  ❌ Followed a YouTube tutorial step-by-step (no original thinking)
  ❌ Works on your machine only (no README, no reproducibility)
  ❌ No monitoring or error handling (not production-ready)
  ❌ Secrets committed to git (immediate red flag)
```

### The "Explain It in an Interview" Test

For every project, you should be able to answer:
1. **What problem does this solve?** (Not "I wanted to learn X")
2. **Why did you choose this architecture?** (Trade-offs, alternatives considered)
3. **What would you do differently?** (Self-awareness, growth mindset)
4. **How does it handle failure?** (Monitoring, alerting, recovery)
5. **How would you scale it?** (Next steps, growth plan)

---

## 2. Project Progression

```
BEGINNER                    INTERMEDIATE                 ADVANCED
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ Static Site     │         │ Microservices   │         │ Production      │
│ Pipeline        │         │ Platform        │         │ Infrastructure  │
│                 │         │                 │         │                 │
│ • Docker        │         │ • Multi-service │         │ • Terraform     │
│ • GitHub Actions│  ──▶    │ • Monitoring    │  ──▶    │ • Kubernetes    │
│ • Basic CI/CD   │         │ • Logging       │         │ • Full stack    │
│ • Single host   │         │ • Load balance  │         │ • Security      │
└─────────────────┘         └─────────────────┘         └─────────────────┘
  Est: 1 week                 Est: 2 weeks                Est: 2-3 weeks

Skills demonstrated:          Skills demonstrated:          Skills demonstrated:
  Modules 01-06                 Modules 05-08                 Modules 09-14
```

---

## 3. Portfolio Structure

### Recommended Repository Layout

```
your-devops-portfolio/
├── README.md                    ← Overview with links to each project
├── project-01-static-pipeline/
│   ├── README.md                ← Architecture, setup, what you learned
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .github/workflows/
│   └── docs/
│       ├── architecture.md
│       └── troubleshooting.md
├── project-02-microservices/
│   ├── README.md
│   ├── services/
│   ├── monitoring/
│   ├── docker-compose.yml
│   └── docs/
└── project-03-production-infra/
    ├── README.md
    ├── terraform/
    ├── kubernetes/
    ├── ansible/
    └── docs/
```

### README Template for Each Project

```markdown
# Project Title

## Overview
One paragraph describing what this project does and why.

## Architecture
[Diagram here — Mermaid, draw.io, or ASCII]

## Technologies Used
- List each tool and WHY you chose it

## How to Run
Step-by-step instructions that work on a fresh machine.

## What I Learned
Key lessons, mistakes, and how you fixed them.

## What I'd Do Differently
Honest self-assessment.

## Cleanup
How to tear down all resources.
```

---

## 4. Project 1: Static Site Pipeline (Beginner)

**Goal**: Build a containerized static website with a full CI/CD pipeline.

**What this demonstrates to employers**:
- You can containerize an application
- You understand CI/CD fundamentals
- You write proper Dockerfiles (non-root, slim images)
- You automate testing and deployment

**Skills used**: Linux, Git, Docker, CI/CD, basic networking

**Detailed spec**: [project-01-static-site-pipeline.md](./projects/project-01-static-site-pipeline.md)

---

## 5. Project 2: Microservices Platform (Intermediate)

**Goal**: Deploy a multi-service application with monitoring, logging, and load balancing.

**What this demonstrates to employers**:
- You can operate multi-service architectures
- You instrument applications for observability
- You can diagnose issues using metrics and logs
- You understand service-to-service communication

**Skills used**: Docker Compose, Nginx, Prometheus, Grafana, Loki, networking

**Detailed spec**: [project-02-microservices-platform.md](./projects/project-02-microservices-platform.md)

---

## 6. Project 3: Production Infrastructure (Advanced)

**Goal**: Provision and manage a complete production environment using Infrastructure as Code, container orchestration, and full observability.

**What this demonstrates to employers**:
- You can design and provision cloud infrastructure
- You manage Kubernetes workloads
- You implement security at every layer
- You think about cost, scaling, and disaster recovery

**Skills used**: Terraform, Ansible, Kubernetes, Prometheus, Grafana, security scanning, CI/CD

**Detailed spec**: [project-03-production-infrastructure.md](./projects/project-03-production-infrastructure.md)

---

## 7. Cross-Cutting Expectations

Every project, regardless of difficulty level, must include:

### Security
- No secrets in code or git history
- Non-root containers
- Minimal permissions (IAM, RBAC, file permissions)
- Dependencies scanned for vulnerabilities

### Observability
- Health check endpoints
- At least basic metrics or logging
- Evidence of using observability to debug an issue

### Documentation
- Architecture diagram
- Setup instructions that work on a fresh machine
- Troubleshooting notes from real issues you hit

### Cleanup
- Clear teardown instructions
- All cloud resources, containers, and volumes removed
- Confirmation output proving cleanup is complete

---

## 8. Presenting Your Work

### In Your Resume

```
DEVOPS PROJECTS

Production Infrastructure Platform
  Provisioned multi-tier AWS infrastructure with Terraform.
  Deployed microservices on Kubernetes with Helm.
  Implemented Prometheus/Grafana monitoring with automated alerting.
  Achieved zero-downtime deployments via rolling updates.
  Tech: Terraform, Kubernetes, Helm, Prometheus, Grafana, GitHub Actions
```

### In Interviews

**Don't**: "I followed a tutorial and deployed Nginx to Kubernetes."

**Do**: "I built a multi-service platform with load balancing and monitoring. The hardest part was debugging a race condition where the API would fail health checks during deployment because the database migration hadn't completed. I solved it by adding readiness probes that checked the migration status endpoint, and I documented the issue in my troubleshooting guide."

### On GitHub

- Pin your portfolio repository
- Write clear, professional READMEs
- Include architecture diagrams
- Show evidence of iteration (meaningful commit history)
- Link from your LinkedIn profile

---

## Practical Checkpoint

Before moving on, you should be able to:

- Complete at least one project from each difficulty tier.
- Present any project in a 5-minute technical walkthrough.
- Answer "why" questions about every technology choice in your projects.

Portfolio evidence to keep:

- Completed projects in a public GitHub repository.
- Architecture diagrams for each project.
- Troubleshooting notes showing real problems you diagnosed and fixed.

---

## ➡️ What's Next?

With portfolio projects complete, you're ready for the final step — preparing for DevOps interviews.

**[Module 16: Interview Prep →](../16-interview-prep/)**

---

<div align="center">

**Module 15 Complete** ✅

[← Back to System Design](../14-system-design-devops/) | [Next: Interview Prep →](../16-interview-prep/)

</div>
