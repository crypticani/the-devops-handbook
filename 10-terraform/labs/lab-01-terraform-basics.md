# Lab 01: Terraform Basics — Provision AWS Infrastructure

## 🎯 Objective

Write your first Terraform configurations, provision real AWS resources, understand state, and practice the plan/apply/destroy workflow.

---

## 📋 Prerequisites

- AWS account (free tier) with CLI configured (`aws configure`)
- Terraform installed (`terraform version`)
- Completed Module 09 (Cloud Fundamentals)

> ⚠️ **Cost Warning:** All resources here are free-tier eligible. Always run `terraform destroy` when done.

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Commands you ran and the important output you used for validation
- Any files, scripts, configs, manifests, or workflows you created
- A short failure note describing one thing that broke, how you diagnosed it, and how you fixed it
- Cleanup commands or confirmation that no long-running resources remain

Treat the validation section as the minimum proof that the lab worked.

---

## 📂 Lab Files

Every file this lab creates also exists as a real, CI-validated file in
[`../code/lab-01/`](../code/lab-01/) (2 files).

```bash
# Option A — type them out yourself (recommended the first time; that's the learning)
# Option B — start from the reference copies
cp -r /path/to/the-devops-handbook/10-terraform/code/lab-01/. .
```

Use Option B when you're comparing against a known-good version, or when something
won't start and you need to rule out a typo. See [`../code/README.md`](../code/README.md).

---

## 🔬 Exercise 1: Your First Terraform Configuration

### Step 1: Create Project

```bash
mkdir -p terraform-lab && cd terraform-lab
```

### Step 2: Write the Configuration

```bash
cat > main.tf << 'HCL'
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Look up latest Amazon Linux AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

# Security group allowing SSH and HTTP
resource "aws_security_group" "web" {
  name        = "terraform-lab-sg"
  description = "Allow SSH and HTTP"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name      = "terraform-lab-sg"
    ManagedBy = "terraform"
  }
}

# EC2 instance with a simple web server
resource "aws_instance" "web" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t2.micro"
  vpc_security_group_ids = [aws_security_group.web.id]

  user_data = <<-EOF
    #!/bin/bash
    dnf install -y httpd
    echo "<h1>Hello from Terraform!</h1><p>Instance: $(hostname)</p>" > /var/www/html/index.html
    systemctl start httpd
    systemctl enable httpd
  EOF

  tags = {
    Name        = "terraform-lab-web"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

output "instance_id" {
  value = aws_instance.web.id
}

output "public_ip" {
  value = aws_instance.web.public_ip
}

output "public_url" {
  value = "http://${aws_instance.web.public_ip}"
}
HCL
```

### Step 3: Init, Plan, Apply

```bash
# Initialize — download the AWS provider
terraform init

# Format the code
terraform fmt

# Validate syntax
terraform validate

# Plan — see what will be created
terraform plan

# Apply — create the resources (type "yes" to confirm)
terraform apply
```

### Step 4: Verify

```bash
# Check outputs
terraform output

# Visit the URL
curl $(terraform output -raw public_url)

# List resources in state
terraform state list

# Show details
terraform state show aws_instance.web
```

**✅ Checkpoint:** EC2 instance running with a web page served. You should see "Hello from Terraform!" in your browser.

---

## 🔬 Exercise 2: Modify Infrastructure

### Step 1: Add a Variable

```bash
cat > variables.tf << 'HCL'
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "dev"
}
HCL
```

Update `main.tf` — change the instance resource to use variables:

```hcl
resource "aws_instance" "web" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type        # Changed
  vpc_security_group_ids = [aws_security_group.web.id]

  tags = {
    Name        = "terraform-lab-web"
    Environment = var.environment                   # Changed
    ManagedBy   = "terraform"
  }
}
```

### Step 2: Plan the Change

```bash
terraform plan
# Should show: ~ update in-place (tag change only)
# No destroy — safe change!

terraform apply -auto-approve
```

**✅ Checkpoint:** You modified infrastructure in-place. The plan showed `~` (modify), not `-/+` (replace).

---

## 🔬 Exercise 3: Destroy and Clean Up

```bash
# Plan the destruction
terraform plan -destroy

# Destroy all resources
terraform destroy
# Type "yes" to confirm

# Verify nothing remains
terraform state list
# Should be empty
```

**✅ Checkpoint:** All AWS resources cleaned up. No charges.

---

## 🧨 Break It: Four State Failures

Terraform's plan step protects you from most mistakes. **State** is where the remaining ones live — and state has no plan step and no undo. Every scenario here starts with the same rule:

```bash
# ⭐ ALWAYS back up state before touching it. Every single time.
terraform state pull > /tmp/state-backup-$(date +%s).tfstate
```

### Scenario 1: The Rename That Destroys Production

**Break it:**

```bash
cd ~/devops-labs/module-10/terraform-basics   # or wherever your lab lives

# Re-create something to work with
terraform apply -auto-approve
terraform state list

# Now do the most innocent-looking edit in Terraform: rename a resource
sed -i.bak 's/resource "aws_s3_bucket" "demo"/resource "aws_s3_bucket" "demo_bucket"/' main.tf
grep -rn 'aws_s3_bucket.demo' *.tf | head    # fix any references too

terraform plan
```

**Symptom:**

```
Plan: 1 to add, 0 to change, 1 to destroy.
  # aws_s3_bucket.demo will be destroyed
  # aws_s3_bucket.demo_bucket will be created
```

You changed a **name in your code** and Terraform wants to **delete real infrastructure**. On an RDS instance or an EBS volume, that's data loss. On anything with a globally unique name (S3 buckets, IAM roles), the create fails after the destroy succeeds — and you're left with nothing.

**Investigate:**

```bash
terraform state list
# aws_s3_bucket.demo        ← state still holds the OLD address
# Your config now says      aws_s3_bucket.demo_bucket
# Terraform matches by ADDRESS, not by the real resource ID.
```

**Root cause:** Terraform identifies resources by their **address in state** (`type.name`), not by any property of the real resource. A rename creates a new address and orphans the old one. Terraform has no way to know they're the same thing unless you tell it.

**Fix — a `moved` block. State-only change, zero downtime:**

```hcl
# moved.tf
moved {
  from = aws_s3_bucket.demo
  to   = aws_s3_bucket.demo_bucket
}
```

```bash
terraform plan
# Plan: 0 to add, 0 to change, 0 to destroy.   ⭐ this is the goal
terraform apply
# Delete moved.tf on a later commit, once every environment has applied it.
```

The pre-1.5 equivalent, still useful for one-offs:

```bash
terraform state mv aws_s3_bucket.demo aws_s3_bucket.demo_bucket
```

> ⭐ **The rule**: any plan showing `destroy` for something you only *renamed or moved* is a `moved` block, never an apply. Read every plan for the word `destroy` before you type yes.

---

### Scenario 2: Someone Changed It in the Console (Drift)

**Break it:**

```bash
# Simulate a colleague "just quickly fixing something" in the AWS console
BUCKET=$(terraform output -raw bucket_name 2>/dev/null || terraform state show aws_s3_bucket.demo_bucket | awk '/^ *bucket /{print $3}' | tr -d '"')
aws s3api put-bucket-tagging --bucket "$BUCKET" \
  --tagging 'TagSet=[{Key=Owner,Value=manual-edit},{Key=Ticket,Value=INC-4821}]'

terraform plan
```

**Symptom:** The plan wants to **remove** tags you didn't touch — Terraform is about to revert someone's emergency fix without anyone noticing.

**Investigate:**

```bash
# ⭐ Reconcile state with reality WITHOUT changing infrastructure
terraform apply -refresh-only
# Terraform shows exactly what drifted and offers to record it in state

terraform show -json | jq '.values.root_module.resources[] | {address, tags: .values.tags}'
```

**Root cause:** Terraform is declarative — it makes reality match the config. Anything changed outside Terraform is, by definition, something Terraform will undo on the next apply. This is a **feature**, but only if you notice before it happens.

**Fix — two valid answers, and you must choose deliberately:**

```hcl
# (a) The manual change was correct → codify it
tags = {
  Owner  = "manual-edit"
  Ticket = "INC-4821"
}

# (b) The field is legitimately managed elsewhere → tell Terraform to stop caring
lifecycle {
  ignore_changes = [tags["LastScanned"], tags["kubernetes.io/cluster/prod"]]
}
```

**Prevention:** run `terraform plan -detailed-exitcode` on a schedule. Exit code `2` means drift exists — alert on it.

```bash
terraform plan -detailed-exitcode
echo "exit=$?"    # 0 = no changes, 1 = error, 2 = drift/changes pending
```

---

### Scenario 3: The Resource That Already Exists

**Break it:**

```bash
# Create something outside Terraform, then try to manage it
aws s3api create-bucket --bucket "tf-lab-manual-$(whoami)-$RANDOM" 2>/dev/null
MANUAL_BUCKET=$(aws s3api list-buckets --query "Buckets[?starts_with(Name,'tf-lab-manual')].Name | [0]" --output text)
echo "created: $MANUAL_BUCKET"

cat >> main.tf <<EOF

resource "aws_s3_bucket" "manual" {
  bucket = "$MANUAL_BUCKET"
}
EOF

terraform apply
```

**Symptom:**

```
Error: creating S3 Bucket (tf-lab-manual-...): BucketAlreadyOwnedByYou
```

Terraform doesn't know the bucket exists, so it tries to create it and fails. The apply is now **partially applied** — some resources created, this one failed.

**Investigate:**

```bash
terraform state list | grep manual        # nothing — state has no record
aws s3api head-bucket --bucket "$MANUAL_BUCKET" && echo "but it EXISTS in AWS"
```

**Root cause:** Config says "should exist", reality says "exists", state says "doesn't exist". Terraform trusts state.

**Fix — a declarative `import` block (Terraform 1.5+), which is reviewable in a PR:**

```hcl
# import.tf
import {
  to = aws_s3_bucket.manual
  id = "tf-lab-manual-yourname-1234"
}
```

```bash
# ⭐ Terraform can even write the resource block for you
terraform plan -generate-config-out=generated.tf
cat generated.tf

terraform plan       # should show: 1 to import, 0 to add, 0 to change, 0 to destroy
terraform apply
terraform state list | grep manual        # now managed
# Delete import.tf afterwards — it's a one-time operation.
```

The CLI equivalent (not reviewable, no config generation):

```bash
terraform import aws_s3_bucket.manual "$MANUAL_BUCKET"
```

---

### Scenario 4: The Stuck State Lock

**Break it:**

```bash
# Simulate an apply that died holding the lock (CI runner killed, laptop slept)
terraform apply -auto-approve &
APPLY_PID=$!
sleep 2
kill -9 $APPLY_PID 2>/dev/null      # SIGKILL — no cleanup, lock is never released
sleep 1

terraform plan
```

**Symptom:**

```
Error: Error acquiring the state lock
  Lock Info:
    ID:        7f3e2c1a-...
    Operation: OperationTypeApply
    Who:       alice@laptop
    Created:   2026-08-04 09:12:33 UTC
```

Nobody on the team can plan or apply. With a local backend you'll see `.terraform.tfstate.lock.info`; with S3+DynamoDB the lock row sits in the table.

**Investigate — before you force anything, confirm nothing is actually running:**

```bash
# Local backend
ls -la .terraform.tfstate.lock.info && cat .terraform.tfstate.lock.info | jq

# S3 + DynamoDB backend
aws dynamodb scan --table-name terraform-locks \
  --query 'Items[].{LockID:LockID.S,Info:Info.S}' --output json | jq

# ⭐ THE CRITICAL CHECK: is a real apply still in flight?
#   - Ask the person named in "Who"
#   - Check your CI system for a running job on this workspace
#   - Check CloudTrail for recent write activity
```

**Root cause:** The lock is held for the duration of an operation and released on exit. A `kill -9`, an OOM, a CI timeout, or a lost network connection leaves it orphaned.

**Fix — only after confirming the operation is genuinely dead:**

```bash
terraform force-unlock 7f3e2c1a-...        # use the exact ID from the error
```

> ⚠️ **`force-unlock` while an apply is genuinely running causes concurrent writes to state.** That's the one way to truly corrupt it — two processes writing different views of reality to the same file. Confirm first, always. If you're unsure, wait: a stuck lock costs you minutes, a corrupted state costs you a day.

**Recovering corrupted state** (S3 versioning is why you enabled it):

```bash
aws s3api list-object-versions --bucket my-tf-state --prefix prod/terraform.tfstate \
  --query 'Versions[:5].[VersionId,LastModified]' --output table
aws s3api get-object --bucket my-tf-state --key prod/terraform.tfstate \
  --version-id <GOOD_VERSION> restored.tfstate
terraform state push restored.tfstate
```

---

### The State Surgery Playbook

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| Plan destroys something you only renamed | State holds the old address | `moved` block |
| Plan creates something that already exists | Real ✅, state ❌ | `import` block + `-generate-config-out` |
| Plan reverts changes you didn't make | Drift | `apply -refresh-only`, then codify or revert |
| Plan destroys something you want to keep unmanaged | You deleted the config block | `terraform state rm`, or a `removed` block |
| `Error acquiring the state lock` | Orphaned lock | Confirm nothing is running → `force-unlock` |
| State file is corrupt | Concurrent writes | Restore from S3 object versioning → `state push` |

**Prevention checklist:**

- [ ] Remote backend with **versioning** and **encryption** enabled
- [ ] State locking configured (DynamoDB table, or S3 `use_lockfile`)
- [ ] `lifecycle { prevent_destroy = true }` on databases, state buckets, and anything holding data
- [ ] CI runs `terraform plan -out=tfplan`, posts it to the PR, and `apply`s **that exact file**
- [ ] Scheduled `plan -detailed-exitcode` to catch drift before it surprises a deploy
- [ ] `terraform state pull > backup` before any manual state operation
- [ ] Nobody has console write access to Terraform-managed resources in production

**Write this up** in `failure-notes.md`: symptom, the plan output that revealed it, root cause, the exact commands that fixed it.

---

## ✅ Validation

- [ ] Write a Terraform config with provider, resource, data source, and output
- [ ] Run the init → plan → apply workflow
- [ ] Read and understand plan output symbols (+, ~, -, -/+)
- [ ] Use variables and outputs
- [ ] Modify existing infrastructure and observe in-place updates
- [ ] Destroy all resources cleanly
- [ ] Explain what the state file does and why it matters

## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- Terraform configuration files (main.tf, variables.tf, outputs.tf)
- Plan output showing create, modify, and destroy operations
- State file summary (do NOT commit actual state with secrets)
- Destroy confirmation output proving clean teardown

---

[← Back to Module README](../README.md)
