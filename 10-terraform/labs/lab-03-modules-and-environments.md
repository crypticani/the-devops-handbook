# Lab 03: Modules, Environments, and Drift

## 🎯 Objective

Stop copy-pasting `.tf` files between environments. You'll write a reusable module with a real interface, run the same module for dev and prod with different inputs, refactor without destroying anything, adopt existing infrastructure with `import`, and detect drift automatically before it surprises a deploy.

---

## 📋 Prerequisites

- Completed [Lab 02: Remote State and Locking](./lab-02-remote-state-and-locking.md) — you'll reuse the state backend
- Terraform ≥ 1.6 (this lab uses `import`, `moved`, and `removed` blocks)

```bash
aws sts get-caller-identity
terraform version
export AWS_REGION=${AWS_REGION:-us-east-1}
export TF_STATE_BUCKET="tf-state-$(aws sts get-caller-identity --query Account --output text)-${AWS_REGION}"
aws s3 ls "s3://$TF_STATE_BUCKET" >/dev/null && echo "✅ backend available"
```

---

## 📦 Deliverables and Evidence

- A module with `variables.tf`, `outputs.tf`, validation rules, and a README
- Two environments calling the same module with different inputs and separate state
- A `moved` block refactor that produces a **0-change** plan
- An `import` block adopting a resource created outside Terraform
- Drift detection output with `-detailed-exitcode`
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-03/`](../code/lab-03/).

```bash
cp -r /path/to/the-devops-handbook/10-terraform/code/lab-03/. .
```

---

## 🔬 Exercise 1: Write a Module

### Step 1: Set Up the Layout

```bash
mkdir -p tf-modules-lab/{modules/bucket,environments/{dev,prod}}
cd tf-modules-lab
tree -L 3 2>/dev/null || find . -type d | sort
```

The layout that scales:

```
tf-modules-lab/
├── modules/
│   └── bucket/            ← reusable, environment-agnostic
│       ├── main.tf
│       ├── variables.tf   ← the module's PUBLIC INTERFACE
│       ├── outputs.tf
│       ├── versions.tf
│       └── README.md
└── environments/
    ├── dev/               ← thin: calls modules, supplies values
    │   ├── main.tf
    │   ├── backend.tf
    │   └── terraform.tfvars
    └── prod/
        └── ...
```

### Step 2: The Module

```bash
cat > modules/bucket/versions.tf <<'HCL'
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # ⚠️ NEVER put a `provider` block in a module.
  # The caller must control region and credentials.
}
HCL

cat > modules/bucket/variables.tf <<'HCL'
variable "name" {
  description = "Base name for the bucket. A suffix is appended for global uniqueness."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,40}[a-z0-9]$", var.name))
    error_message = "name must be lowercase alphanumeric with hyphens, 3-42 characters."
  }
}

variable "environment" {
  description = "Deployment environment."
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "versioning_enabled" {
  description = "Enable S3 object versioning."
  type        = bool
  default     = true
}

variable "lifecycle_rules" {
  description = "Object lifecycle transitions and expiry."
  type = object({
    transition_to_ia_days      = optional(number, 30)
    transition_to_glacier_days = optional(number, 90)
    expiration_days            = optional(number, 0) # 0 = never expire
  })
  default = {}
}

variable "force_destroy" {
  description = "Allow terraform destroy to delete a non-empty bucket. NEVER true in prod."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags merged over the module's own."
  type        = map(string)
  default     = {}
}
HCL

cat > modules/bucket/main.tf <<'HCL'
locals {
  # The module owns these; the caller can add to them but not remove them.
  common_tags = merge(
    {
      Environment = var.environment
      Module      = "bucket"
      ManagedBy   = "terraform"
    },
    var.tags,
  )
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "this" {
  bucket        = "${var.name}-${var.environment}-${random_id.suffix.hex}"
  force_destroy = var.force_destroy
  tags          = local.common_tags

  lifecycle {
    # ⭐ A module consumer can't accidentally delete a prod bucket by removing
    #    the module block, IF they set force_destroy = false.
    ignore_changes = [tags["LastScanned"]]
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = var.versioning_enabled ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  # Lifecycle config requires versioning to be settled first
  depends_on = [aws_s3_bucket_versioning.this]

  rule {
    id     = "tiering"
    status = "Enabled"
    filter {}

    transition {
      days          = var.lifecycle_rules.transition_to_ia_days
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = var.lifecycle_rules.transition_to_glacier_days
      storage_class = "GLACIER_IR"
    }

    dynamic "expiration" {
      for_each = var.lifecycle_rules.expiration_days > 0 ? [1] : []
      content {
        days = var.lifecycle_rules.expiration_days
      }
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
HCL

cat > modules/bucket/outputs.tf <<'HCL'
output "id" {
  description = "Bucket name."
  value       = aws_s3_bucket.this.id
}

output "arn" {
  description = "Bucket ARN."
  value       = aws_s3_bucket.this.arn
}

output "domain_name" {
  description = "Regional domain name for the bucket."
  value       = aws_s3_bucket.this.bucket_regional_domain_name
}

output "tags" {
  description = "Tags actually applied, after merging."
  value       = aws_s3_bucket.this.tags_all
}
HCL

cat > modules/bucket/README.md <<'MD'
# Module: bucket

An opinionated, secure-by-default S3 bucket. Public access is always blocked and
encryption is always on — neither is configurable, on purpose.

## Usage

```hcl
module "app_data" {
  source = "../../modules/bucket"

  name        = "myapp-data"
  environment = "prod"

  lifecycle_rules = {
    transition_to_ia_days = 60
    expiration_days       = 365
  }

  tags = { CostCentre = "platform" }
}
```

## Inputs

| Name | Type | Default | Required | Description |
|------|------|---------|:--------:|-------------|
| `name` | `string` | — | yes | Base name; a random suffix is appended |
| `environment` | `string` | — | yes | One of `dev`, `staging`, `prod` |
| `versioning_enabled` | `bool` | `true` | no | Enable object versioning |
| `lifecycle_rules` | `object` | `{}` | no | Transition and expiry days |
| `force_destroy` | `bool` | `false` | no | ⚠️ Never `true` in prod |
| `tags` | `map(string)` | `{}` | no | Merged over the module's own tags |

## Outputs

| Name | Description |
|------|-------------|
| `id` | Bucket name |
| `arn` | Bucket ARN |
| `domain_name` | Regional domain name |
| `tags` | Effective tags after merge |

## Notes

- Public access blocking and encryption are **not** configurable. If you need a
  public bucket, this is the wrong module.
- The module declares no `provider` block; the caller supplies region and credentials.
MD

```

**✅ Checkpoint:** The module has a validated input interface, useful outputs, secure defaults that can't be turned off, and a README. That's the difference between a module and a directory of `.tf` files.

### Step 3: Module Design Rules

| Rule | Why |
|------|-----|
| **Never** declare a `provider` block inside a module | The caller must control region, credentials, and aliases |
| Put every knob in `variables.tf` with a `description` | The variables file **is** the API documentation |
| Use `validation` blocks | Fail at plan time with a clear message, not at apply time with a cloud error |
| Expose a `tags` input and `merge()` it | Lets callers apply org-wide tagging without forking the module |
| Output everything a caller might plausibly need | Adding an output later is free; guessing what they need is not |
| Make the secure choice non-configurable | A module that lets you disable encryption will have encryption disabled somewhere |
| Pin git module sources to a **tag**, never a branch | A branch can change between plan and apply |

---

## 🔬 Exercise 2: Two Environments, One Module

### Step 1: Dev

```bash
cat > environments/dev/backend.tf <<'HCL'
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
  backend "s3" {
    key     = "lab-03/dev/terraform.tfstate"   # ⭐ separate state per environment
    encrypt = true
  }
}
HCL

cat > environments/dev/main.tf <<'HCL'
provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Environment = "dev"
      Repo        = "the-devops-handbook"
    }
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

module "app_data" {
  source = "../../modules/bucket"

  name        = "handbook-appdata"
  environment = "dev"

  versioning_enabled = false          # dev doesn't need it
  force_destroy      = true           # ⭐ safe in dev, so cleanup is easy

  lifecycle_rules = {
    transition_to_ia_days = 7
    expiration_days       = 30        # dev data is disposable
  }

  tags = { CostCentre = "engineering" }
}

output "bucket" {
  value = module.app_data.id
}
HCL

cat > environments/dev/backend.hcl <<HCL
bucket         = "$TF_STATE_BUCKET"
region         = "$AWS_REGION"
dynamodb_table = "terraform-locks"
HCL

cd environments/dev
terraform init -backend-config=backend.hcl
terraform apply -auto-approve
terraform output
```

### Step 2: Prod — Same Module, Different Inputs

```bash
cd ../prod
sed 's|lab-03/dev/|lab-03/prod/|' ../dev/backend.tf > backend.tf
cp ../dev/backend.hcl .

cat > main.tf <<'HCL'
provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Environment = "prod"
      Repo        = "the-devops-handbook"
    }
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

module "app_data" {
  source = "../../modules/bucket"

  name        = "handbook-appdata"
  environment = "prod"

  versioning_enabled = true           # ⭐ prod keeps history
  force_destroy      = false          # ⭐ terraform destroy CANNOT wipe it

  lifecycle_rules = {
    transition_to_ia_days      = 90
    transition_to_glacier_days = 365
    expiration_days            = 0    # never expire prod data
  }

  tags = { CostCentre = "platform", Compliance = "sox" }
}

output "bucket" {
  value = module.app_data.id
}
HCL

sed -i 's|lab-03/dev/|lab-03/prod/|' backend.tf
terraform init -backend-config=backend.hcl
terraform apply -auto-approve
terraform output
```

### Step 3: Verify the Separation

```bash
cd ../..
echo "── dev ──";  (cd environments/dev  && terraform state list | head -3)
echo "── prod ──"; (cd environments/prod && terraform state list | head -3)

aws s3api list-objects-v2 --bucket "$TF_STATE_BUCKET" --prefix lab-03/ \
  --query 'Contents[].Key' --output table

# Different settings, same module
DEV=$(cd environments/dev && terraform output -raw bucket)
PROD=$(cd environments/prod && terraform output -raw bucket)
aws s3api get-bucket-versioning --bucket "$DEV"   --query Status
aws s3api get-bucket-versioning --bucket "$PROD"  --query Status
```

**✅ Checkpoint:** Two environments, one module definition, **separate state files**. A mistake in dev cannot touch prod state, and the two can even live in different AWS accounts.

### Step 4: Directory-per-Environment vs Workspaces

| | Directory per environment | Workspaces |
|---|--------------------------|------------|
| **State isolation** | ⭐ Separate backend key, can be a separate account | One backend, one bucket, keyed by workspace |
| **Config differences** | Explicit, visible in the file | `terraform.workspace` conditionals scattered through the code |
| **Blast radius of a mistake** | Contained | `terraform workspace select` typo hits the wrong environment |
| **Duplication** | Some, in the thin root modules | None |
| **Right for** | ⭐ Production. Anything with a compliance boundary | Short-lived, identical environments (per-PR previews) |

---

## 🔬 Exercise 3: Refactor Without Destroying

### Step 1: Rename Something

```bash
cd environments/dev

# A perfectly reasonable rename
sed -i 's|module "app_data"|module "application_data"|' main.tf
sed -i 's|module.app_data.id|module.application_data.id|' main.tf

terraform plan
```

**Symptom:**

```
Plan: 5 to add, 0 to change, 5 to destroy.
  # module.app_data.aws_s3_bucket.this will be destroyed
  # module.application_data.aws_s3_bucket.this will be created
```

You renamed a **variable in your code** and Terraform wants to delete a bucket and all its contents.

### Step 2: Fix It With `moved`

```bash
cat > moved.tf <<'HCL'
moved {
  from = module.app_data
  to   = module.application_data
}
HCL

terraform plan
# ⭐ Plan: 0 to add, 0 to change, 0 to destroy.
terraform apply -auto-approve
```

**✅ Checkpoint:** A **0-change plan**. That's the target for every refactor.

`moved` blocks handle every shape of refactor:

```hcl
moved { from = aws_instance.old,                to = aws_instance.new }                    # rename
moved { from = aws_instance.web,                to = module.compute.aws_instance.web }     # into a module
moved { from = module.old_name,                 to = module.new_name }                     # rename a module
moved { from = aws_instance.web[0],             to = aws_instance.web["primary"] }         # count → for_each
moved { from = module.app,                      to = module.app["us-east-1"] }             # module → for_each
```

> 💡 Keep the `moved` block for at least one release cycle so every environment and every colleague's working copy applies it. Then delete it — it's a migration, not permanent configuration.

### Step 3: Remove Without Destroying

```bash
cat > removed.tf <<'HCL'
# Hand a resource over to another team / another stack without deleting it.
removed {
  from = module.application_data.aws_s3_bucket_lifecycle_configuration.this

  lifecycle {
    destroy = false      # ⭐ forget it, don't delete it
  }
}
HCL

terraform plan     # shows a removal from state, not a destroy
# (Don't apply — we want the resource for the next exercise.)
rm removed.tf
```

---

## 🔬 Exercise 4: Adopt Existing Infrastructure

### Step 1: Create Something Outside Terraform

```bash
cd ../..
ORPHAN="handbook-orphan-$(date +%s | tail -c 6)-$RANDOM"
aws s3api create-bucket --bucket "$ORPHAN" >/dev/null
aws s3api put-bucket-tagging --bucket "$ORPHAN" \
  --tagging 'TagSet=[{Key=Origin,Value=console},{Key=Owner,Value=someone-who-left}]'
echo "created outside terraform: $ORPHAN"
```

This is the normal state of most real environments: someone clicked a button in 2023 and nobody knows what depends on it.

### Step 2: Try the Naive Approach

```bash
cd environments/dev
cat >> main.tf <<HCL

resource "aws_s3_bucket" "adopted" {
  bucket = "$ORPHAN"
}
HCL

terraform apply -auto-approve 2>&1 | tail -5
```

**Symptom:** `Error: creating S3 Bucket: BucketAlreadyOwnedByYou`. Terraform doesn't know it exists, so it tries to create it.

### Step 3: Import It Properly

```bash
cat > import.tf <<HCL
import {
  to = aws_s3_bucket.adopted
  id = "$ORPHAN"
}
HCL

# ⭐ Terraform can WRITE the resource block for you from the real resource
terraform plan -generate-config-out=generated.tf
cat generated.tf
```

```bash
# Replace your guess with the generated, accurate config
python3 - <<'PY'
import pathlib, re
main = pathlib.Path("main.tf")
s = main.read_text()
s = re.sub(r'\nresource "aws_s3_bucket" "adopted" \{.*?\n\}\n', "\n", s, flags=re.S)
main.write_text(s)
PY

terraform plan
# ⭐ Plan: 1 to import, 0 to add, 0 to change, 0 to destroy.
terraform apply -auto-approve
terraform state list | grep adopted
```

### Step 4: Clean Up the Import Block

```bash
rm import.tf          # ⭐ imports are ONE-TIME operations — delete once applied everywhere
terraform plan        # ✅ no changes
```

> ⚠️ Never commit an `import` block with a placeholder or an un-substituted variable in it —
> a later `apply` in a different environment will fail, or worse, import the wrong resource.
> The reference copy ships as `import.tf.example` for exactly this reason.

| | `import` block (1.5+) | `terraform import` CLI |
|---|----------------------|------------------------|
| Reviewable in a PR | ✅ It's code | ❌ A command someone ran |
| Can generate config | ✅ `-generate-config-out` | ❌ You write it by hand and hope |
| Shows a plan first | ✅ | ❌ Modifies state immediately |
| Works in CI | ✅ | Awkward |
| Bulk import | ✅ `for_each` over a map | One at a time |

```hcl
# Import many at once
import {
  for_each = toset(["bucket-a", "bucket-b", "bucket-c"])
  to       = aws_s3_bucket.legacy[each.key]
  id       = each.key
}
```

---

## 🔬 Exercise 5: Detect Drift Before It Bites

### Step 1: Cause Some Drift

```bash
BUCKET=$(terraform output -raw bucket)
aws s3api put-bucket-tagging --bucket "$BUCKET" \
  --tagging 'TagSet=[{Key=Environment,Value=dev},{Key=Module,Value=bucket},{Key=ManagedBy,Value=terraform},{Key=CostCentre,Value=engineering},{Key=EmergencyFix,Value=INC-4821}]'
echo "someone added a tag in the console"
```

### Step 2: Detect It

```bash
# ⭐ The scriptable form. Exit code 2 == there are pending changes.
terraform plan -detailed-exitcode -out=drift.tfplan
echo "exit code: $?"
```

| Exit code | Meaning |
|-----------|---------|
| `0` | No changes — infrastructure matches configuration |
| `1` | Error |
| `2` | ⭐ Changes pending — either drift, or un-applied config |

```bash
# Machine-readable diff, for a CI comment or an alert
terraform show -json drift.tfplan | python3 -c '
import json, sys
plan = json.load(sys.stdin)
for rc in plan.get("resource_changes", []):
    actions = rc["change"]["actions"]
    if actions != ["no-op"]:
        print(f"{'"'"','"'"'.join(actions):10} {rc[\"address\"]}")'
```

### Step 3: Decide — Revert or Codify

Drift is not automatically wrong. Someone made that change for a reason.

```bash
# Option A: the manual change was WRONG → revert it
terraform apply drift.tfplan

# Option B: the manual change was RIGHT → record it in state, then codify it
terraform apply -refresh-only -auto-approve
#   Then add the tag to the module call so the next plan is clean:
#   tags = { CostCentre = "engineering", EmergencyFix = "INC-4821" }

# Option C: the field is legitimately managed elsewhere → tell Terraform to ignore it
#   lifecycle { ignore_changes = [tags["EmergencyFix"]] }
```

### Step 4: Automate the Detection

```bash
cat > ../../drift-check.sh <<'SH'
#!/usr/bin/env bash
# Run on a schedule. Alerts when reality has diverged from code.
set -uo pipefail
STATUS=0
for env in environments/*/; do
  name=$(basename "$env")
  ( cd "$env" && terraform init -backend-config=backend.hcl -input=false >/dev/null 2>&1 )
  ( cd "$env" && terraform plan -detailed-exitcode -input=false -lock-timeout=5m >/dev/null 2>&1 )
  case $? in
    0) echo "✅ $name: no drift" ;;
    2) echo "⚠️  $name: DRIFT DETECTED"; STATUS=1
       ( cd "$env" && terraform plan -no-color -input=false 2>/dev/null | grep -E '^\s+[~+-]' | head -20 ) ;;
    *) echo "❌ $name: plan failed"; STATUS=1 ;;
  esac
done
exit $STATUS
SH
chmod +x ../../drift-check.sh
cd ../.. && ./drift-check.sh
```

Wire it into CI on a nightly schedule:

```yaml
- name: Detect drift
  run: ./drift-check.sh
- name: Alert
  if: failure()
  run: echo "Drift detected — see the plan output above" # → Slack / PagerDuty
```

> ⭐ **Drift detection is the difference between finding a manual change on your schedule and finding it during an incident.** A `plan` that has been clean for a week means the next `apply` will do exactly what it says.

---

## 🧨 Break It: Four Module and Environment Failures

### Scenario 1: The Provider Inside the Module

**Break it:**

```bash
cat > modules/bucket/provider-bad.tf <<'HCL'
provider "aws" {
  region = "eu-west-1"        # ❌ a module must never do this
}
HCL

cd environments/dev
terraform init -backend-config=backend.hcl 2>&1 | tail -6
terraform plan 2>&1 | tail -12
```

**Symptom:** Warnings about provider configuration in a shared module, and — depending on version — resources planned in the **wrong region**, or a hard error when you try to use `for_each` on the module.

**Investigate:**

```bash
terraform providers
# The module declares its own provider, so the caller's region is ignored for its resources.
```

**Root cause:** A provider block inside a module makes that module unusable with `for_each`/`count`, impossible to deploy to a second region, and it silently overrides the caller's intent. Terraform has deprecated the pattern for exactly these reasons.

**Fix:**

```bash
rm ../../modules/bucket/provider-bad.tf
terraform init -backend-config=backend.hcl >/dev/null
```

If a module genuinely needs a second provider (a replica bucket in another region), declare a **requirement** and let the caller pass it:

```hcl
# modules/bucket/versions.tf
terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 5.0"
      configuration_aliases = [aws.replica]      # ⭐ a requirement, not a definition
    }
  }
}

# The CALLER supplies it:
module "bucket" {
  source    = "../../modules/bucket"
  providers = { aws = aws, aws.replica = aws.us_west }
}
```

---

### Scenario 2: `count` Renumbering Destroys the Wrong Resources

**Break it:**

```bash
cd ../..
mkdir -p count-trap && cd count-trap
cat > main.tf <<'HCL'
terraform {
  required_providers { random = { source = "hashicorp/random", version = "~> 3.6" } }
}

variable "names" {
  type    = list(string)
  default = ["alpha", "bravo", "charlie"]
}

resource "random_pet" "server" {
  count  = length(var.names)          # ❌ indexed by POSITION
  prefix = var.names[count.index]
}
HCL
terraform init >/dev/null && terraform apply -auto-approve >/dev/null
terraform state list

# Now remove the FIRST item — a one-word change
sed -i 's|\["alpha", "bravo", "charlie"\]|["bravo", "charlie"]|' main.tf
terraform plan
```

**Symptom:**

```
Plan: 0 to add, 2 to change, 1 to destroy.
  # random_pet.server[0] must be replaced   (was alpha, now bravo)
  # random_pet.server[1] must be replaced   (was bravo, now charlie)
  # random_pet.server[2] will be destroyed
```

You removed **one** item and Terraform is replacing **all three**. With EC2 instances or RDS databases, that's a full outage caused by editing a list.

**Investigate:**

```bash
terraform state list
# random_pet.server[0]   ← state keys resources by INDEX
# random_pet.server[1]
# random_pet.server[2]
# Removing element 0 shifts every subsequent index by one.
```

**Fix — `for_each` keys by a stable string:**

```bash
cat > main.tf <<'HCL'
terraform {
  required_providers { random = { source = "hashicorp/random", version = "~> 3.6" } }
}

variable "names" {
  type    = set(string)
  default = ["alpha", "bravo", "charlie"]
}

resource "random_pet" "server" {
  for_each = var.names               # ⭐ keyed by VALUE, not position
  prefix   = each.key
}
HCL

# Migrate the existing state from count-indexes to for_each keys
cat > moved.tf <<'HCL'
moved { from = random_pet.server[0], to = random_pet.server["alpha"] }
moved { from = random_pet.server[1], to = random_pet.server["bravo"] }
moved { from = random_pet.server[2], to = random_pet.server["charlie"] }
HCL

terraform plan     # ⭐ 0 to add, 0 to change, 0 to destroy
terraform apply -auto-approve >/dev/null
terraform state list

# NOW remove one and see the difference
sed -i 's|\["alpha", "bravo", "charlie"\]|["bravo", "charlie"]|' main.tf
rm moved.tf
terraform plan     # ⭐ Plan: 0 to add, 0 to change, 1 to destroy — only the one you removed
```

| | `count` | `for_each` |
|---|---------|-----------|
| Keyed by | Position (`[0]`, `[1]`) | A stable string (`["alpha"]`) |
| Removing a middle item | ⚠️ Renumbers and **replaces** everything after it | Removes only that one |
| Reordering the list | ⚠️ Replaces everything | No effect |
| Right for | A simple on/off (`count = var.enabled ? 1 : 0`) | ⭐ Everything else |

```bash
terraform destroy -auto-approve >/dev/null; cd ..; rm -rf count-trap
```

---

### Scenario 3: The Unpinned Module Source

**Break it:**

```bash
cd environments/dev
cat > unpinned.tf <<'HCL'
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"    # ❌ no version constraint
  name   = "unpinned-demo"
  cidr   = "10.99.0.0/16"
  azs    = ["us-east-1a"]
}
HCL
terraform init 2>&1 | grep -iE 'vpc|version' | head -5
terraform providers | head -20
```

**Symptom:** `init` resolves to whatever the newest version is **today**. Your colleague, running `init` next week, gets a different one. A CI runner with a cold cache gets a third. The same commit produces different infrastructure depending on when you ran it.

**Investigate:**

```bash
cat .terraform/modules/modules.json 2>/dev/null | python3 -m json.tool | head -20
# Shows the version actually downloaded — and nothing pins it.
```

**Root cause:** No `version` for a registry module, or a **branch** ref for a git module (`?ref=main`), means the source is mutable. Terraform's `.terraform.lock.hcl` pins *providers*, not modules.

**Fix:**

```bash
rm unpinned.tf
```

```hcl
# Registry — always pin
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.8"                       # ⭐ >= 5.8, < 6.0
}

# Git — pin a TAG or a commit SHA, never a branch
module "internal" {
  source = "git::https://github.com/myorg/tf-modules.git//vpc?ref=v1.4.2"
}

# Worst case, if you must track a branch, pin the exact commit
module "internal" {
  source = "git::https://github.com/myorg/tf-modules.git//vpc?ref=a1b2c3d4e5f6"
}
```

```bash
# Audit: any module source without a version or with a branch ref?
grep -rn 'source\s*=' --include='*.tf' . | grep -vE 'source\s*=\s*"\.\.?/' | grep -v 'ref=v' || echo "✅ all remote sources pinned"
```

---

### Scenario 4: The Shared State That Isn't Shared Safely

**Break it:**

```bash
# Prod's root module reaches into dev's state for "just one value"
cd ../prod
cat >> main.tf <<HCL

data "terraform_remote_state" "dev" {
  backend = "s3"
  config = {
    bucket = "$TF_STATE_BUCKET"
    key    = "lab-03/dev/terraform.tfstate"
    region = "$AWS_REGION"
  }
}

output "leaked_dev_bucket" {
  value = data.terraform_remote_state.dev.outputs.bucket
}
HCL
terraform init -backend-config=backend.hcl >/dev/null
terraform apply -auto-approve >/dev/null
terraform output leaked_dev_bucket
```

**Symptom:** It works, which is the problem. Prod now depends on dev's state file. Three consequences:

1. **A dev change can break a prod plan.** Rename an output in dev and prod's next apply errors.
2. **Whoever can run prod can read dev's entire state** — including every secret in it, not just the declared outputs.
3. **The dependency is invisible** — nothing in dev warns that prod reads from it.

**Investigate:**

```bash
# What does prod actually have access to?
terraform console <<'EOF'
data.terraform_remote_state.dev.outputs
EOF

# The blast radius: remove an output in dev and watch prod break
cd ../dev && sed -i 's|^output "bucket"|output "bucket_renamed"|' main.tf && terraform apply -auto-approve >/dev/null
cd ../prod && terraform plan 2>&1 | tail -6
#   Error: Unsupported attribute ... "bucket" is not an output of the remote state
```

**Root cause:** `terraform_remote_state` is a hard, invisible coupling between two stacks that grants full read access to the producer's state file.

**Fix:**

```bash
cd ../dev && sed -i 's|^output "bucket_renamed"|output "bucket"|' main.tf && terraform apply -auto-approve >/dev/null
cd ../prod
python3 -c "
import pathlib,re
p=pathlib.Path('main.tf'); s=p.read_text()
s=re.sub(r'\ndata \"terraform_remote_state\" \"dev\" \{.*?\n\}\n','\n',s,flags=re.S)
s=re.sub(r'\noutput \"leaked_dev_bucket\" \{.*?\n\}\n','\n',s,flags=re.S)
p.write_text(s)"
terraform apply -auto-approve >/dev/null && echo "✅ coupling removed"
```

**Better patterns, in order of preference:**

| Pattern | Coupling | Access granted |
|---------|----------|----------------|
| ⭐ **Input variable** | None — the caller decides | Nothing |
| ⭐ **SSM Parameter Store / cloud data source** | One named value | Just that parameter |
| **Data source by tag** (`aws_vpc` with a filter) | Real infrastructure, not state | Read-only cloud API |
| `terraform_remote_state` | The producer's entire state file | ⚠️ Everything in it, including secrets |

```hcl
# Producer publishes one value
resource "aws_ssm_parameter" "vpc_id" {
  name  = "/platform/${var.environment}/vpc_id"
  type  = "String"
  value = module.vpc.vpc_id
}

# Consumer reads exactly that one value, with its own IAM scope
data "aws_ssm_parameter" "vpc_id" {
  name = "/platform/prod/vpc_id"
}
```

> ⭐ **Never** let a production stack read a non-production state file. Beyond the coupling, it means anyone who can plan prod can read dev's secrets — and dev secrets are usually protected far less carefully.

---

### Summary

| Failure | Symptom | Fix |
|---------|---------|-----|
| Provider inside a module | Wrong region; `for_each` on the module fails | `configuration_aliases`; caller passes `providers` |
| `count` renumbering | Removing one item replaces many | `for_each` + `moved` blocks to migrate |
| Unpinned module source | Same commit, different infrastructure | `version = "~> x.y"`; git `?ref=vTAG` |
| Cross-environment state coupling | Dev change breaks prod; secrets exposed | Input variables, or SSM, not `terraform_remote_state` |
| Rename → destroy | Plan destroys what you only renamed | `moved` block; target a **0-change plan** |
| Undetected drift | A surprise in the middle of a deploy | Scheduled `plan -detailed-exitcode` |

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
cd ~/…/tf-modules-lab 2>/dev/null || cd tf-modules-lab
for e in environments/prod environments/dev; do
  ( cd "$e" && terraform destroy -auto-approve 2>/dev/null )
done

# The prod module sets force_destroy = false, so its bucket survives destroy —
# that's the safety feature working. Remove it deliberately:
aws s3 ls | grep handbook-appdata-prod
# aws s3 rb "s3://<the-prod-bucket>" --force

aws s3 ls | grep handbook-orphan
# aws s3 rb "s3://<the-orphan-bucket>" --force

cd .. && rm -rf tf-modules-lab
aws s3 ls | grep -E 'handbook-(appdata|orphan)' || echo "✅ nothing left"
```

---

## ✅ Validation

- [ ] Write a module with validated inputs, useful outputs, secure non-configurable defaults, and a README
- [ ] Explain why a module must never contain a `provider` block
- [ ] Deploy the same module to two environments with separate state
- [ ] Compare directory-per-environment against workspaces and justify a choice
- [ ] Refactor a rename with a `moved` block and achieve a **0-change plan**
- [ ] Adopt an existing resource with an `import` block and `-generate-config-out`
- [ ] Explain why `for_each` is safer than `count` for anything keyed
- [ ] Pin a registry module and a git module correctly
- [ ] Detect drift with `-detailed-exitcode` and decide between reverting and codifying
- [ ] Explain the security risk in `terraform_remote_state` and name two better patterns

---

## 📝 What to Commit

- The `modules/bucket/` directory including its README
- Both environment root modules
- The `moved.tf` and `import.tf` blocks, with a note on when you deleted them
- `drift-check.sh` and its output
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: Remote State and Locking](./lab-02-remote-state-and-locking.md) | [Back to Module README](../README.md) | [Next Lab: Packer and Golden Images →](./lab-04-packer-golden-images.md)
