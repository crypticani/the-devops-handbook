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
