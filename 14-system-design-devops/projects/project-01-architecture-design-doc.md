# Project: Architecture Design Document

## Problem Statement

Design a production-ready architecture for a web application that must handle growing traffic, survive component failures, and be operationally maintainable. Document your design decisions with trade-off analysis.

## Scenario

You are the DevOps engineer for a team launching a content platform. The application has:
- A web frontend (React/static files)
- An API backend (REST, stateless)
- A PostgreSQL database
- User-uploaded media (images, documents)
- Expected traffic: 500 concurrent users at launch, growing to 5,000 within 6 months

## Deliverables

- Architecture diagram showing all components and their connections
- Component list with justification for each technology choice
- Scaling plan: what happens at 2x, 5x, and 10x current traffic
- Failure mode analysis: what happens when each component fails
- SLO definitions: at least 3 SLIs with target SLOs and error budgets
- Cost estimate: rough monthly cost at current and projected scale
- DR plan: RPO, RTO, and recovery steps

## Validation

Your architecture document should answer these questions:
- Where are the single points of failure, and how are they mitigated?
- Can you scale each tier independently?
- What is the estimated cost difference between your design and a simpler alternative?
- How long would it take to recover from a database failure?
- Can a new team member understand the architecture from your document alone?

## Failure Scenario

Include a section analyzing what happens when:
1. The primary database crashes during peak traffic
2. A deployment introduces a bug that returns 500 errors on 30% of requests
3. Traffic spikes to 10x normal due to a viral event

For each scenario, describe: detection (how you know), impact (what users experience), response (what you do), and prevention (how to avoid next time).

## What to Commit

- Architecture diagram (draw.io, Mermaid, or hand-drawn scan)
- Design document with all sections above
- ADR (Architecture Decision Record) for at least 2 key decisions
- Cost comparison spreadsheet or table

## Review Rubric

Use this rubric to self-assess your work or have a peer review it.

| Criteria | What to Look For | Score (1-5) |
|----------|-----------------|-------------|
| **Reproducibility** | Architecture can be implemented from the document alone |  |
| **Correctness** | Component choices and sizing match the stated requirements |  |
| **Debugging quality** | Failure modes are realistic with concrete detection and response steps |  |
| **Security basics** | Network segmentation, least privilege, encryption in transit and at rest |  |
| **Cleanup quality** | Cost analysis includes teardown or scale-down procedures |  |
| **Explanation clarity** | Trade-offs are explicit; a reader understands why, not just what |  |

**Scoring**: 1 = Not attempted, 2 = Partial, 3 = Meets expectations, 4 = Exceeds expectations, 5 = Production quality
