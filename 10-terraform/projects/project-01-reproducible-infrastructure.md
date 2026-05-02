# Project: Reproducible Infrastructure with Terraform

## Problem Statement

Use Terraform to provision a small piece of infrastructure and prove that it can be planned, applied, validated, and destroyed repeatably.

## Deliverables

- Terraform configuration with provider, resource, variables, and outputs
- `terraform fmt` and `terraform validate` clean result
- `plan` summary before apply
- Validation commands after apply
- Destroy proof

## Validation

Capture output for:

- `terraform fmt -check`
- `terraform validate`
- `terraform plan`
- `terraform apply`
- A service-specific validation command
- `terraform destroy`

## Failure Scenario

Introduce an invalid variable value or missing required argument. Document the Terraform error and how you corrected it.

## What to Commit

- Terraform files
- Example variable file without secrets
- Validation notes
- Destroy proof
