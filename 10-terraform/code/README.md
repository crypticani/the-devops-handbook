# Module 10: Terraform — Lab Code

Terraform configurations for every lab: a first config, a shared remote-state backend,
and a reusable module deployed to two environments.

These are the real, runnable files from this module's labs. `terraform fmt` and
`terraform validate` run against all of them in CI.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

> ⚠️ **`*.example` files need editing before use.** `backend.hcl.example` and
> `import.tf.example` contain placeholders (`<ACCOUNT_ID>`, `REPLACE-WITH-…`) because the real
> values are specific to your account. Copy them to the real filename and fill them in.

> 💰 **These create real AWS resources.** Everything is free-tier eligible, but run
> `terraform destroy` when you're done. The prod module in lab-03 sets `force_destroy = false`
> on purpose — its bucket survives `destroy`, which is the safety feature working.

---

## Contents

### `lab-01/`

Provider, resource, data source, variables and outputs — the config used for the init/plan/apply walkthrough.

```
lab-01/
├── main.tf
└── variables.tf
```

### `lab-02/`

Two stacks sharing an S3 + DynamoDB backend: `app/` produces outputs, `consumer/` reads them via `terraform_remote_state`.

```
lab-02/
├── app/backend.hcl.example
├── app/backend.tf
├── app/main.tf
├── app/outputs.tf
├── app/variables.tf
├── consumer/backend.hcl.example
├── consumer/main.tf
└── consumer/variables.tf
```

### `lab-03/`

A reusable, secure-by-default S3 module called by separate `dev` and `prod` root modules, plus a drift-detection script.

```
lab-03/
├── drift-check.sh
├── environments/dev/backend.hcl.example
├── environments/dev/backend.tf
├── environments/dev/import.tf.example
├── environments/dev/main.tf
├── environments/dev/moved.tf
├── environments/prod/backend.hcl.example
├── environments/prod/backend.tf
├── environments/prod/main.tf
├── modules/bucket/README.md
├── modules/bucket/main.tf
├── modules/bucket/outputs.tf
├── modules/bucket/variables.tf
└── modules/bucket/versions.tf
```

---

## Using these files

```bash
mkdir -p ~/devops-labs/10-terraform && cd ~/devops-labs/10-terraform
cp -r /path/to/the-devops-handbook/10-terraform/code/lab-03/. .

# Fill in the placeholders
cp environments/dev/backend.hcl.example environments/dev/backend.hcl
$EDITOR environments/dev/backend.hcl

cd environments/dev
terraform init -backend-config=backend.hcl
terraform plan -out=tfplan     # ⭐ always read the plan before applying
terraform apply tfplan
```

---

<div align="center">

[← Module 10 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
