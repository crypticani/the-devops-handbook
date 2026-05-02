# Project: Small Cloud Environment Walkthrough

## Problem Statement

Create a minimal cloud environment and document the core building blocks: network, compute, access control, security boundary, validation, cost, and cleanup.

## Deliverables

- Architecture note covering VPC/network, subnet, instance, IAM, and security group/firewall
- Commands or console steps used to create the environment
- Validation output for access and network reachability
- Cost estimate and cleanup checklist

## Validation

Prove that the instance or service is reachable only through the intended path. Capture the command output you used, such as SSH, HTTP, or cloud CLI checks.

## Failure Scenario

Intentionally block access with a security group/firewall rule. Document how the failure appears and how you identify the missing rule.

## Cleanup

Delete all resources and capture proof that no billable lab resources remain.

## What to Commit

- Architecture notes
- Validation output
- Failure investigation
- Cleanup proof
