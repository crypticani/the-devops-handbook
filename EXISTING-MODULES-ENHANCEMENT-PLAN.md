# Existing Modules Enhancement Plan

> ✅ **All phases completed** — May 2026

This plan focused on Modules 00-13, enhancing the labs and projects with portfolio-ready guidance. Modules 14-16 have also been fully populated with content.

## Goal

Improve practical learning by making each existing module produce evidence that a learner can actually do the work:

- Reproducible commands, configs, scripts, or manifests
- Clear validation output
- At least one realistic failure and recovery path
- A small deliverable that can be committed to a portfolio repo
- Cleanup instructions for local and cloud resources

## Enhancement Order

### Phase 1: Normalize Lab Structure ✅

Apply this to all existing labs in Modules 00-13.

- Add a "Deliverables" section near the top of each lab
- Add a "Validation" section with commands and expected results
- Add or strengthen a "Break It" scenario
- Add a "Cleanup" section where resources are created
- Add "What to Commit" guidance for portfolio evidence

This phase should not add new tools. It should improve the labs already present.

### Phase 2: Add Module-Level Practical Checkpoints ✅

Add a short "Practical Checkpoint" section to each module README.

Each checkpoint should answer:

- What should the learner be able to build or debug after this module?
- What files or notes should they keep as proof?
- Which common failure should they know how to diagnose?

### Phase 3: Fill Existing Project Directories ✅

Most module `projects/` directories already exist but are empty. Add one small project per completed module before creating large capstones.

Recommended project scope:

| Module | First Practical Project |
|--------|-------------------------|
| 00 Foundations | Delivery pipeline map and improvement proposal |
| 01 Linux | Server health report script |
| 02 Networking | DNS and HTTP troubleshooting runbook |
| 03 Git | Branching workflow with conflict-resolution evidence |
| 04 Scripting | Log parser or backup automation script |
| 05 Docker | Containerized app with Compose and healthcheck |
| 06 CI/CD | Pull-request pipeline with lint, tests, and artifact |
| 07 Observability | Prometheus and Grafana dashboard with alert |
| 08 Logging | Centralized logging investigation report |
| 09 Cloud Fundamentals | Small cloud network and compute walkthrough |
| 10 Terraform | Reproducible infrastructure with destroy proof |
| 11 Ansible | Idempotent service configuration playbook |
| 12 Kubernetes | Multi-service deployment with rollback proof |
| 13 Security Basics | Scan, fix, and residual-risk report |

### Phase 4: Add Review Rubrics ✅

Each module project should include a short rubric:

- Reproducibility
- Correctness
- Debugging quality
- Security basics
- Cleanup quality
- Explanation clarity

### Phase 5: Only Then Resume Modules 14-16 ✅

After Modules 00-13 have consistent practical checkpoints and at least one project each, resume:

- Module 14: System design for DevOps
- Module 15: Integrated portfolio projects
- Module 16: Interview prep and mock incidents

## Suggested First Changes

Start with narrow, high-value updates:

1. Add Practical Checkpoints to Modules 00-03.
2. Add Deliverables, Validation, Break It, Cleanup, and What to Commit sections to one representative lab in each of Modules 00-03.
3. Use that pattern as the template for Modules 04-13.
4. Add one small project file to each existing `projects/` directory after the labs are normalized.

## Definition of Done

An enhanced module is done when:

- Its README has a practical checkpoint
- Every lab has explicit validation
- Every lab that creates resources has cleanup
- At least one lab includes intentional debugging
- The module has at least one portfolio-ready project
- A learner knows exactly what to commit as evidence
