<![CDATA[<div align="center">

# 🛠️ The DevOps Handbook

### A Complete, Structured Learning System for Becoming a Job-Ready DevOps Engineer

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Modules](https://img.shields.io/badge/Modules-17-orange.svg)](#-module-hierarchy)
[![Hands-On](https://img.shields.io/badge/Hands--On-60%25-red.svg)](#-hands-on-philosophy)

---

*From zero to production-ready DevOps engineer. No fluff, no shortcuts — just real skills.*

</div>

---

## 📌 What Is This Repository?

This is **not** another collection of DevOps bookmarks or a surface-level overview. This is a **structured, opinionated, hands-on learning system** designed to take you from absolute beginner to a **job-ready DevOps Engineer**.

Every module follows a progression: **understand → practice → debug → build**. You will not just learn tools — you will learn **how to think like a DevOps engineer**.

### Who Is This For?

| Audience | Starting Point | What You'll Gain |
|----------|---------------|------------------|
| **Absolute Beginners** | No DevOps experience, maybe some coding | Complete DevOps foundation + practical skills |
| **Developers Transitioning** | Can code, but unfamiliar with infra/ops | Production-grade operational skills |

### What You'll Be Able to Do After Completion

- ✅ Set up and manage Linux servers in production
- ✅ Containerize any application with Docker
- ✅ Build CI/CD pipelines from scratch (GitHub Actions, Jenkins)
- ✅ Monitor and debug production systems (Prometheus, Grafana, ELK)
- ✅ Provision infrastructure as code (Terraform)
- ✅ Deploy and manage Kubernetes clusters
- ✅ Implement security best practices across the stack
- ✅ Debug production incidents methodically
- ✅ Design scalable, reliable deployment architectures
- ✅ **Pass DevOps engineer interviews with confidence**

---

## 🧭 The DevOps Roadmap

This roadmap is **strictly ordered**. Do NOT skip ahead. Each module builds on the previous one.

```
 PHASE 1: FUNDAMENTALS          PHASE 2: CORE TOOLS            PHASE 3: PRODUCTION SKILLS
 ┌─────────────────────┐        ┌─────────────────────┐        ┌─────────────────────┐
 │  00 Foundations      │        │  05 Docker           │        │  09 Cloud            │
 │  01 Linux            │───────▶│  06 CI/CD            │───────▶│  10 Terraform        │
 │  02 Networking       │        │  07 Observability ⚠️ │        │  11 Ansible          │
 │  03 Git              │        │  08 Logging ⚠️       │        │  12 Kubernetes       │
 │  04 Scripting        │        └─────────────────────┘        └─────────────────────┘
 └─────────────────────┘                                                 │
                                                                         ▼
                                 PHASE 4: MASTERY
                                 ┌─────────────────────┐
                                 │  13 Security         │
                                 │  14 System Design    │
                                 │  15 Projects         │
                                 │  16 Interview Prep   │
                                 └─────────────────────┘
```

> ⚠️ **CRITICAL**: Observability & Logging are taught **before** Kubernetes, Terraform, and Ansible. You must understand how systems behave and how to debug failures **before** you automate or scale them.

---

## 📁 Module Hierarchy

| # | Module | Focus | Est. Time |
|---|--------|-------|-----------|
| **Phase 1: Fundamentals** |||
| 00 | [Foundations](./00-foundations/) | DevOps culture, SDLC, Agile, tooling overview | 1 week |
| 01 | [Linux](./01-linux/) | Ubuntu, filesystem, processes, permissions, systemd | 2 weeks |
| 02 | [Networking](./02-networking/) | TCP/IP, DNS, HTTP, firewalls, troubleshooting | 1.5 weeks |
| 03 | [Git](./03-git/) | Version control, branching, PRs, Git workflows | 1 week |
| 04 | [Scripting](./04-scripting/) | Bash scripting, Python basics for automation | 2 weeks |
| **Phase 2: Core Tools** |||
| 05 | [Containers & Docker](./05-containers-docker/) | Images, containers, Compose, registries | 2 weeks |
| 06 | [CI/CD](./06-ci-cd/) | GitHub Actions, Jenkins, pipelines, testing | 2 weeks |
| 07 | [Observability](./07-observability/) | Prometheus, Grafana, metrics, alerting | 2 weeks |
| 08 | [Logging](./08-logging/) | ELK stack, Loki, centralized logging, debugging | 1.5 weeks |
| **Phase 3: Production Skills** |||
| 09 | [Cloud Fundamentals](./09-cloud-fundamentals/) | Cloud-agnostic concepts, then AWS specifics | 2 weeks |
| 10 | [Terraform](./10-terraform/) | Infrastructure as Code, state, modules | 2 weeks |
| 11 | [Ansible](./11-ansible/) | Configuration management, playbooks, roles | 1 week |
| 12 | [Kubernetes](./12-kubernetes/) | Pods, Services, Deployments, Helm, debugging | 3 weeks |
| **Phase 4: Mastery** |||
| 13 | [Security Basics](./13-security-basics/) | Secrets, RBAC, container security, secure CI/CD | 1.5 weeks |
| 14 | [System Design](./14-system-design-devops/) | Architecture, scaling, HA, load balancing | 1 week |
| 15 | [Projects](./15-projects/) | Beginner → Advanced real-world projects | 3-4 weeks |
| 16 | [Interview Prep](./16-interview-prep/) | FAQs, scenarios, debugging questions | 1-2 weeks |

**Total Estimated Duration**: 24-28 weeks (6-7 months) at ~10-15 hours/week

---

## 🔧 Opinionated Tool Stack

We use a **specific, industry-relevant** stack throughout this handbook. No tool-agnostic hand-waving.

| Category | Tool(s) | Why |
|----------|---------|-----|
| **Operating System** | Ubuntu (Linux) | Industry standard for servers |
| **Version Control** | Git + GitHub | Universal adoption, GitHub Actions integration |
| **Scripting** | Bash + Python | Bash for system tasks, Python for complex automation |
| **Containers** | Docker + Docker Compose | Industry standard containerization |
| **CI/CD** | GitHub Actions (primary), Jenkins (secondary) | Modern + legacy exposure |
| **Monitoring** | Prometheus + Grafana | De facto open-source observability stack |
| **Logging** | ELK Stack (Elasticsearch, Logstash, Kibana) + Loki | Enterprise + lightweight options |
| **Cloud** | Cloud-agnostic concepts → AWS | Largest market share, transferable skills |
| **IaC** | Terraform | Multi-cloud, declarative, huge adoption |
| **Config Management** | Ansible | Agentless, simple, widely used |
| **Orchestration** | Kubernetes | Industry standard container orchestration |
| **Reverse Proxy** | Nginx | Performance, widespread use, versatile |
| **Security** | Integrated across all modules | Security is not a bolt-on |

---

## 🚀 How to Use This Repository

### Option 1: Sequential Learning (Recommended)

Follow the modules in order, 00 → 16. Each module's README explains concepts, then the `labs/` directory provides hands-on practice.

```bash
# Clone the repository
git clone https://github.com/crypticani/the-devops-handbook.git
cd the-devops-handbook

# Start with Module 00
cd 00-foundations
# Read README.md first, then work through labs/
```

### Option 2: Targeted Learning (For Developers)

If you already have Linux/Git experience, you can start from Module 04 or 05, but **verify your knowledge first** by completing the labs in earlier modules.

### For Every Module, Follow This Order:

1. **Read** `README.md` — understand the concepts and why they matter
2. **Study** the commands and tools — don't just memorize, understand
3. **Do** every lab in `labs/` — hands-on is non-negotiable
4. **Break things** — intentional failure scenarios teach debugging
5. **Build** mini-projects in `projects/` — apply what you learned
6. **Check** `resources.md` — deepen your knowledge
7. **Review** interview insights — prep continuously, not at the end

---

## 📊 Progress Tracker

Use this checklist to track your progress. Copy it to a separate file or use GitHub's checkbox feature.

### Phase 1: Fundamentals
- [ ] **00 - Foundations**: DevOps concepts, culture, SDLC
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Review resources
- [ ] **01 - Linux**: Filesystem, processes, permissions, services
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Complete mini-projects
  - [ ] Review resources
- [ ] **02 - Networking**: TCP/IP, DNS, HTTP, firewalls
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Review resources
- [ ] **03 - Git**: Branching, PRs, workflows, conflicts
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Review resources
- [ ] **04 - Scripting**: Bash + Python automation
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Complete scripting projects
  - [ ] Review resources

### Phase 2: Core Tools
- [ ] **05 - Docker**: Images, containers, Compose, registries
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Complete Docker projects
  - [ ] Review resources
- [ ] **06 - CI/CD**: GitHub Actions, Jenkins, pipelines
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Build a full pipeline
  - [ ] Review resources
- [ ] **07 - Observability**: Prometheus, Grafana, alerting
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Build dashboards
  - [ ] Review resources
- [ ] **08 - Logging**: ELK, Loki, log analysis
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Debug using logs
  - [ ] Review resources

### Phase 3: Production Skills
- [ ] **09 - Cloud Fundamentals**: Cloud concepts, AWS basics
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Review resources
- [ ] **10 - Terraform**: IaC, state management, modules
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Provision real infrastructure
  - [ ] Review resources
- [ ] **11 - Ansible**: Playbooks, roles, configuration
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Review resources
- [ ] **12 - Kubernetes**: Pods, Services, Deployments, debugging
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Deploy multi-service app
  - [ ] Review resources

### Phase 4: Mastery
- [ ] **13 - Security**: Secrets, RBAC, secure pipelines
  - [ ] Read README.md
  - [ ] Complete all labs
  - [ ] Security audit exercise
  - [ ] Review resources
- [ ] **14 - System Design**: Architecture, scaling, HA
  - [ ] Read README.md
  - [ ] Design exercises
  - [ ] Review resources
- [ ] **15 - Projects**: Build all projects
  - [ ] Beginner projects
  - [ ] Intermediate projects
  - [ ] Advanced projects
- [ ] **16 - Interview Prep**: Practice all scenarios
  - [ ] Technical FAQs
  - [ ] Scenario-based questions
  - [ ] Mock debugging sessions

---

## 📅 Suggested Weekly Plan

| Week | Module | Focus |
|------|--------|-------|
| 1 | 00 - Foundations | DevOps culture, SDLC, tool overview |
| 2-3 | 01 - Linux | Commands, filesystem, processes, services |
| 4-5 | 02 - Networking | TCP/IP, DNS, HTTP, troubleshooting |
| 6 | 03 - Git | Version control, branching, workflows |
| 7-8 | 04 - Scripting | Bash + Python for DevOps |
| 9-10 | 05 - Docker | Containers, images, Compose |
| 11-12 | 06 - CI/CD | GitHub Actions, Jenkins, pipelines |
| 13-14 | 07 - Observability | Prometheus, Grafana, alerting |
| 15-16 | 08 - Logging | ELK, Loki, log debugging |
| 17-18 | 09 - Cloud | Cloud concepts, AWS fundamentals |
| 19-20 | 10 - Terraform | Infrastructure as Code |
| 21 | 11 - Ansible | Configuration management |
| 22-24 | 12 - Kubernetes | Container orchestration |
| 25 | 13 - Security | Security practices |
| 26 | 14 - System Design | Architecture for DevOps |
| 27-30 | 15 - Projects | Build portfolio projects |
| 31-32 | 16 - Interview Prep | Get job-ready |

---

## 📋 Prerequisites

You need very little to start:

- ✅ A computer (any OS — we'll set up Linux via VM/WSL/cloud)
- ✅ Basic comfort with using a terminal
- ✅ Curiosity and willingness to break things
- ✅ ~10-15 hours per week to dedicate

**Not required**: Prior DevOps experience, cloud accounts (free tiers are sufficient), expensive hardware.

---

## 🧠 The DevOps Thinking Model

Throughout this handbook, we reinforce four core principles:

1. **Automation Mindset** — If you do it twice, automate it
2. **Infrastructure as Code** — Everything declared, version-controlled, reproducible
3. **Observability First** — You can't fix what you can't see
4. **Security as Culture** — Baked in, not bolted on

These aren't just buzzwords — they're practiced in every lab and project.

---

## 🔐 Security Philosophy

Security is **not** isolated to Module 13. It is embedded throughout:

- **Linux**: File permissions, SSH hardening, sudo practices
- **Git**: `.gitignore`, secrets prevention, signed commits
- **Docker**: Image scanning, non-root containers, minimal base images
- **CI/CD**: Secret management, SAST/DAST integration
- **Cloud**: IAM, least privilege, network security groups
- **Kubernetes**: RBAC, network policies, pod security

Module 13 serves as consolidation, not introduction.

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this handbook.

We welcome:
- Bug fixes and corrections
- Additional labs and exercises
- New resources and references
- Translations
- Real-world scenario contributions

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with 💻 by [crypticani](https://github.com/crypticani)**

*"The best time to start learning DevOps was yesterday. The second best time is now."*

⭐ If this helped you, consider starring the repo!

</div>
]]>
