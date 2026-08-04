# Lab 01: Mapping a Software Delivery Pipeline

## 🎯 Objective

Understand how software gets from a developer's machine to production by mapping a real delivery pipeline. This builds the mental model you'll implement throughout this course.

---

## 📋 Prerequisites

- A piece of paper or a diagramming tool (draw.io, Excalidraw, or even a text editor)
- No technical setup required for this lab

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Commands you ran and the important output you used for validation
- Any files, scripts, configs, manifests, or workflows you created
- A short failure note describing one thing that broke, how you diagnosed it, and how you fixed it
- Cleanup commands or confirmation that no long-running resources remain

Treat the validation section as the minimum proof that the lab worked.

---

## 🔬 Exercise 1: Map a Manual Deployment Process

### Scenario

You work at a company where the deployment process looks like this:

1. Developer writes code on their laptop
2. Developer emails a `.zip` file to the team lead
3. Team lead reviews code by reading files
4. Team lead sends the `.zip` to the QA team
5. QA manually tests on their machine
6. QA sends a "Go" email to the Ops team
7. Ops person SSHs into the production server
8. Ops person stops the old application
9. Ops person copies new files to the server
10. Ops person starts the application
11. Ops person manually checks if it's working

### Task

1. Draw this process as a flowchart
2. Identify every **risk** at each step
3. Identify every **manual step** that could be automated
4. Estimate the total time this process takes

### Expected Analysis

| Step | Risk | Can Automate? |
|------|------|---------------|
| Email zip file | File could be wrong version, corrupted, or intercepted | ✅ Version control (Git) |
| Manual code review | Inconsistent, reviewer might miss issues | ✅ PR reviews + automated linting |
| Manual testing | Tests might be skipped, inconsistent coverage | ✅ Automated test suites |
| SSH to production | Human error, no audit trail | ✅ CI/CD pipeline |
| Manual health check | Might miss subtle issues | ✅ Automated monitoring |

**Total manual time estimate**: 2-8 hours per deployment, depending on issues found.

---

## 🔬 Exercise 2: Design the DevOps Version

### Task

Redesign the same process using DevOps practices. Write out:

1. What happens when a developer pushes code
2. What automated checks run
3. How the deployment happens
4. How you know if it worked

### Expected Design

```
Developer pushes to GitHub
        │
        ▼
GitHub Actions triggers
        │
        ├── Build application
        ├── Run unit tests
        ├── Run linting/static analysis
        ├── Run security scan
        │
        ▼
All checks pass? ──── No ──▶ Developer gets notification, fixes issues
        │
        Yes
        │
        ▼
Deploy to staging environment
        │
        ├── Run integration tests
        ├── Run smoke tests
        │
        ▼
All staging tests pass? ──── No ──▶ Alert team, block deployment
        │
        Yes
        │
        ▼
Deploy to production (automated or one-click)
        │
        ├── Rolling/blue-green deployment
        ├── Health checks run automatically
        ├── Monitoring verifies metrics
        │
        ▼
Production healthy? ──── No ──▶ Auto-rollback to previous version
        │
        Yes
        │
        ▼
✅ Deployment complete (notification sent)
```

**Total automated time**: 5-15 minutes per deployment.

---

## 🔬 Exercise 3: Calculate the Business Impact

### Task

Compare the two approaches using these numbers:

| Metric | Manual Process | DevOps Pipeline |
|--------|---------------|-----------------|
| Time per deployment | 4 hours | 10 minutes |
| Deployments per month | 1 | 30 |
| Failure rate | 30% | 5% |
| Recovery time | 4 hours | 15 minutes |

### Questions to Answer

1. How many engineer-hours per month does the manual process cost?
2. How much faster can the DevOps team respond to a critical bug?
3. If the company loses $10,000 per hour of downtime, what's the cost difference?

### Expected Calculations

**Manual process monthly cost:**
- Deployment time: 1 × 4 hours = 4 hours
- Failure recovery: 0.30 × 4 hours = 1.2 hours
- Total: ~5.2 engineer-hours
- Downtime cost: 0.30 × 4 hours × $10,000 = $12,000

**DevOps pipeline monthly cost:**
- Deployment time: 30 × 0.17 hours = 5.1 hours (but fully automated)
- Failure recovery: 0.05 × 30 × 0.25 hours = 0.375 hours
- Total human time: ~1 hour (monitoring/intervention)
- Downtime cost: 0.05 × 30 × 0.25 hours × $10,000 = $3,750

**Net savings**: ~$8,250/month in downtime + significant engineer time back.

---

## 🔬 Exercise 4: Blameless Postmortem Practice

### Scenario

Imagine this incident happened:

> At 3:00 PM on Tuesday, the production API started returning 500 errors for 40% of requests. The on-call engineer was paged. After 45 minutes of investigation, they found that a database migration script deleted an important index. The script was part of a deployment that went out at 2:45 PM. It was not tested in staging because "staging doesn't have production data." The fix was to recreate the index, which took 20 minutes. Total impact: 65 minutes of degraded service affecting ~12,000 users.

### Task

Write a blameless postmortem using this template:

```markdown
## Incident Report: [Title]

**Date**: 
**Duration**: 
**Severity**: 
**Impact**: 

### Timeline
[Chronological events with timestamps]

### Root Cause
[Technical root cause — NOT "someone made a mistake"]

### Contributing Factors
[System/process gaps that allowed this]

### Action Items
- [ ] [Action] — Owner — Due Date
- [ ] [Action] — Owner — Due Date
- [ ] [Action] — Owner — Due Date

### Lessons Learned
[What changes to process/tooling will prevent this]
```

### Key Points for Your Postmortem

Your action items should include things like:
- ✅ Add database migration testing to CI pipeline
- ✅ Create staging database with realistic (anonymized) data
- ✅ Add database performance checks to deployment pipeline
- ✅ Set up alerts for sudden increases in 500 error rates

Things **not** to write:
- ❌ "Bob should be more careful with migrations"
- ❌ "We need to approve all database changes manually"

---

## 🧨 Break It: Pre-Mortem on Your Own Pipeline

There's no running system in this lab, so you can't break one. You can do something more valuable at this stage: **break the pipeline you designed in Exercise 2, on paper, before you build it.**

A pre-mortem inverts the postmortem. Instead of asking *"why did this fail?"* after the fact, you assume failure has already happened and work backwards to the cause. Teams consistently find more real risks this way than by asking "what could go wrong?" — because the assumption of failure removes the optimism.

### The Exercise

Open your Exercise 2 pipeline design. Then write this sentence at the top of a page and finish it four times:

> *"It's six months from now. The pipeline we designed has caused a serious production incident. Here is exactly what happened."*

Force yourself to write **specific, concrete stories** — not "the tests were bad" but "the integration test suite took 40 minutes, so someone added `--skip-integration` to the deploy job in March to unblock a hotfix, and nobody removed it."

### The Four Failures You Must Account For

Every pipeline design has these four holes until it's proven otherwise. Write a paragraph on each:

**1. The pipeline is green but the deploy is broken.**
What can pass every check you designed and still take production down? Consider: a config change no test covers, a database migration that's valid in isolation but incompatible with the currently-running code, an environment variable that exists in staging but not production, a dependency that resolved to a different version at build time.

- What's your **detection** time? (How long before anyone knows?)
- What's your **rollback** procedure, and who can run it at 3am?

**2. Someone bypasses the pipeline.**
Under what pressure does a human go around your automation — and how? Direct SSH to a server? A manual `kubectl apply`? A merge with admin override? Disabling a required check "temporarily"?

- What would make the pipeline **faster than the workaround**? (This is the only durable fix.)
- What makes a bypass **visible** after the fact?

**3. The pipeline itself fails.**
Your CI provider has an outage. The registry is unreachable. A third-party action you pinned to `@v1` is compromised. Your only person who understands the Jenkins config is on leave.

- Can you deploy a **critical security fix** with the pipeline down? Write the manual procedure.
- What's your single point of failure? (There is one. Name it.)

**4. It works perfectly and nobody notices the real problem.**
Deploys are fast and green. Error rates are flat. And the feature you shipped last Tuesday has been quietly corrupting 2% of orders since then, because nothing in your pipeline validates *business* correctness.

- What would have caught it? A canary with real traffic? An SLO on a business metric rather than a technical one? A smoke test that exercises a real user journey?

### Turn It Into Design Changes

For each of the four stories, write **one concrete change** to your Exercise 2 diagram. Add them to the design:

| Failure story | Design change it forces |
|---------------|-------------------------|
| Green pipeline, broken deploy | Post-deploy smoke test + automatic rollback on SLO breach |
| Someone bypassed it | Branch protection with no admin override + audit alert on direct pushes |
| Pipeline itself down | A documented, tested manual deploy runbook — practised quarterly |
| Silent business-logic failure | An alert on a business metric (orders/min), not just HTTP 500s |

### Deliverable

Add a `pre-mortem.md` to your portfolio containing:

- [ ] Four failure stories, written as if they already happened, with specific detail
- [ ] The design change each one forces
- [ ] An updated Exercise 2 pipeline diagram showing those changes
- [ ] One sentence on which of the four you think is **most likely** in a real team, and why

> ⭐ **Why this belongs in Module 00**: every later module in this handbook has a "Break It" section where you break something real. The habit those sections build is *thinking in failure modes*. Starting it here — before you know any tools — proves the habit is about judgement, not tooling. Most production incidents are not caused by a tool that malfunctioned; they're caused by a system that worked exactly as designed, in a situation nobody designed for.

---

## ✅ Validation

You've completed this lab successfully when you can:

- [ ] Explain why manual processes are risky
- [ ] Design a basic CI/CD pipeline conceptually
- [ ] Calculate business impact of DevOps adoption
- [ ] Write a blameless postmortem
- [ ] Articulate the difference between blame culture and learning culture

---

## 💡 Key Takeaways

1. DevOps isn't about tools — it's about reducing the risk and cost of delivering software
2. Automation reduces human error and frees engineers for creative work
3. Blameless postmortems fix systems, not people
4. The business case for DevOps is measurable and compelling


## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- Your delivery pipeline diagram (manual vs DevOps version)
- Business impact analysis with calculated metrics
- Blameless postmortem document from Exercise 4
- Notes on bottlenecks identified and proposed improvements

---

[← Back to Module README](../README.md) | [Next Lab: DevOps Self-Assessment →](./lab-02-devops-self-assessment.md)

