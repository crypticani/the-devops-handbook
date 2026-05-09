# Project: Idempotent Service Configuration

## Problem Statement

Use Ansible to configure a service on a local VM, container, or remote host in a repeatable way.

## Deliverables

- Inventory
- Playbook
- Variables
- Handler for service restart or reload
- Template or managed config file
- Validation task or separate validation commands

## Validation

Run the playbook twice. The second run should report no unnecessary changes except checks that are expected to run every time.

## Failure Scenario

Deploy a broken service config. Document how Ansible reports the issue, how you inspect the service logs, and how you fix or roll back the config.

## Cleanup

Stop or remove any lab hosts or containers you created.

## What to Commit

- Inventory and playbook files
- Templates and variables
- First and second run output notes
- Failure recovery notes

## Review Rubric

Use this rubric to self-assess your work or have a peer review it.

| Criteria | What to Look For | Score (1-5) |
|----------|-----------------|-------------|
| **Reproducibility** | Playbook runs successfully on a fresh target without manual prereqs | |
| **Correctness** | Service is configured and running as expected after playbook completes | |
| **Debugging quality** | Idempotency proven — second run shows zero changes | |
| **Security basics** | Secrets use Ansible Vault; no plaintext passwords in playbooks | |
| **Cleanup quality** | Teardown playbook or instructions remove all configured resources | |
| **Explanation clarity** | Role structure, variable precedence, and handler usage are documented | |

**Scoring**: 1 = Not attempted, 2 = Partial, 3 = Meets expectations, 4 = Exceeds expectations, 5 = Production quality
