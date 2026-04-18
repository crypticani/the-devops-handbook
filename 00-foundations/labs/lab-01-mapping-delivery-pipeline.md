<![CDATA[# Lab 01: Mapping a Software Delivery Pipeline

## 🎯 Objective

Understand how software gets from a developer's machine to production by mapping a real delivery pipeline. This builds the mental model you'll implement throughout this course.

---

## 📋 Prerequisites

- A piece of paper or a diagramming tool (draw.io, Excalidraw, or even a text editor)
- No technical setup required for this lab

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

---

[← Back to Module README](../README.md) | [Next Lab: DevOps Self-Assessment →](./lab-02-devops-self-assessment.md)
]]>
