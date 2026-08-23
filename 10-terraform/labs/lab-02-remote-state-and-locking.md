# Lab 02: Remote State and Locking

## 🎯 Objective

Move Terraform state off your laptop and into shared, versioned, encrypted, **locked** storage — the change that makes Terraform usable by more than one person. You'll bootstrap the backend, migrate existing state into it, watch a lock actually block a second apply, recover a corrupted state from object versioning, and read another stack's outputs without duplicating configuration.

---

## 📋 Prerequisites

- Completed [Lab 01: Terraform Basics](./lab-01-terraform-basics.md)
- AWS CLI configured, Terraform ≥ 1.10 (S3 native locking needs 1.10+)
- Two terminals (you'll need them for the locking exercise)

```bash
aws sts get-caller-identity      # ⭐ confirm the account before anything else
terraform version
```

> 💰 **Cost**: S3 storage for a few KB is effectively free, and S3 native locking adds no extra resource to pay for. Cleanup instructions are at the end — the backend bucket is the one thing you may want to keep.

---

## 📦 Deliverables and Evidence

- Bootstrap configuration for the state backend (S3 with native locking)
- Output of a state migration from local to remote
- A screenshot or transcript of a **real lock conflict** between two terminals
- Evidence of recovering a previous state version from S3
- A second stack reading the first stack's outputs via `terraform_remote_state`
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-02/`](../code/lab-02/).

```bash
cp -r /path/to/the-devops-handbook/10-terraform/code/lab-02/. .
```

---

## 🔬 Exercise 1: Why Local State Fails

### Step 1: See the Problem First

```bash
mkdir -p tf-state-lab/app && cd tf-state-lab/app

cat > main.tf <<'HCL'
terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      ManagedBy = "terraform"
      Lab       = "10-terraform-lab-02"
    }
  }
}

resource "random_pet" "suffix" {
  length = 2
}

resource "aws_s3_bucket" "app_data" {
  bucket        = "tf-lab-app-${random_pet.suffix.id}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "app_data" {
  bucket                  = aws_s3_bucket.app_data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
HCL

cat > variables.tf <<'HCL'
variable "region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}
HCL

cat > outputs.tf <<'HCL'
output "bucket_name" {
  description = "Name of the application data bucket"
  value       = aws_s3_bucket.app_data.id
}

output "bucket_arn" {
  description = "ARN of the application data bucket"
  value       = aws_s3_bucket.app_data.arn
}
HCL

terraform init
terraform apply -auto-approve
```

### Step 2: Look at What You Just Created

```bash
ls -la terraform.tfstate
terraform state list

# ⭐ State is a plaintext JSON file sitting in your working directory
python3 -c "
import json
s = json.load(open('terraform.tfstate'))
print('version:  ', s['version'])
print('serial:   ', s['serial'])
print('lineage:  ', s['lineage'])
print('resources:', [r['type'] + '.' + r['name'] for r in s['resources']])
"
```

**Three problems, all fatal for a team:**

| Problem | Consequence |
|---------|-------------|
| The file is on **one machine** | Nobody else can plan or apply. A second person starts from empty state and recreates everything |
| There is **no lock** | Two simultaneous applies interleave writes and corrupt state |
| It is **plaintext** | Database passwords, generated keys, and every `sensitive` output are readable by anyone with the file |

```bash
# Prove the third one — create something with a secret and look for it in state
cat >> main.tf <<'HCL'

resource "random_password" "db" {
  length  = 24
  special = true
}
HCL
terraform apply -auto-approve

# ⭐ The "sensitive" value, in plaintext, in a file you might have gitignored but not encrypted
python3 -c "
import json
s = json.load(open('terraform.tfstate'))
for r in s['resources']:
    if r['type'] == 'random_password':
        print('password in state:', r['instances'][0]['attributes']['result'])
"
```

> ⚠️ `sensitive = true` only redacts a value from **CLI output**. It does nothing to state. Anything Terraform creates or reads — RDS passwords, private keys, API tokens — lands in state in the clear. This is the single strongest argument for an encrypted remote backend.

---

## 🔬 Exercise 2: Bootstrap the Backend

The backend is a chicken-and-egg problem: Terraform needs the bucket to store state, but you'd normally create the bucket with Terraform. Solve it once, by hand or with a throwaway local-state stack.

### Step 1: Create the Bucket and Lock Table

```bash
cd ..
export AWS_REGION=${AWS_REGION:-us-east-1}
export TF_STATE_BUCKET="tf-state-$(aws sts get-caller-identity --query Account --output text)-${AWS_REGION}"
echo "state bucket: $TF_STATE_BUCKET"

# S3 bucket
if [ "$AWS_REGION" = "us-east-1" ]; then
  aws s3api create-bucket --bucket "$TF_STATE_BUCKET"
else
  aws s3api create-bucket --bucket "$TF_STATE_BUCKET" --region "$AWS_REGION" \
    --create-bucket-configuration LocationConstraint="$AWS_REGION"
fi

# ⭐ Versioning — this is your undo button for state corruption. Non-negotiable.
aws s3api put-bucket-versioning --bucket "$TF_STATE_BUCKET" \
  --versioning-configuration Status=Enabled

# Encryption at rest
aws s3api put-bucket-encryption --bucket "$TF_STATE_BUCKET" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"},"BucketKeyEnabled":true}]}'

# Block all public access
aws s3api put-public-access-block --bucket "$TF_STATE_BUCKET" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Lifecycle: keep old versions for 90 days, then expire them
aws s3api put-bucket-lifecycle-configuration --bucket "$TF_STATE_BUCKET" \
  --lifecycle-configuration '{"Rules":[{
    "ID":"expire-old-state-versions","Status":"Enabled","Filter":{"Prefix":""},
    "NoncurrentVersionExpiration":{"NoncurrentDays":90},
    "AbortIncompleteMultipartUpload":{"DaysAfterInitiation":7}}]}'

# ⭐ No lock table. S3 native locking (Terraform 1.10+) takes the lock with a
# conditional write on a <key>.tflock object in this same bucket.
echo "✅ backend ready"
```

> ⚠️ **Older guides create a DynamoDB `terraform-locks` table here.** DynamoDB-based
> locking is [deprecated and will be removed in a future minor version](https://developer.hashicorp.com/terraform/language/backend/s3#state-locking).
> The bucket you just made is the whole backend now — one less resource to bootstrap,
> pay for, and forget to grant IAM on.

### Step 2: Verify the Guard Rails

```bash
aws s3api get-bucket-versioning  --bucket "$TF_STATE_BUCKET"
aws s3api get-bucket-encryption  --bucket "$TF_STATE_BUCKET" --query 'ServerSideEncryptionConfiguration.Rules[0]'
aws s3api get-public-access-block --bucket "$TF_STATE_BUCKET" --query PublicAccessBlockConfiguration
```

**✅ Checkpoint:** Versioning `Enabled`, encryption configured, all four public-access blocks `true`.

---

## 🔬 Exercise 3: Migrate to the Backend

### Step 1: Add the Backend Block

Backend configuration **cannot use variables or expressions** — it is read before Terraform evaluates anything. Use partial configuration instead.

```bash
cd app

cat > backend.tf <<'HCL'
terraform {
  backend "s3" {
    # Intentionally minimal: the rest comes from -backend-config at init time,
    # which is how you point the same code at different environments.
    key          = "lab-02/app/terraform.tfstate"
    encrypt      = true
    use_lockfile = true    # ⭐ locking is a property of the code, not the environment
  }
}
HCL

cat > backend.hcl <<HCL
bucket = "$TF_STATE_BUCKET"
region = "$AWS_REGION"
HCL
```

### Step 2: Migrate

```bash
terraform init -backend-config=backend.hcl -migrate-state
# Terraform detects existing local state and offers to copy it up.
# Answer: yes
```

### Step 3: Verify the Migration

```bash
# State is now in S3
aws s3 ls "s3://$TF_STATE_BUCKET/lab-02/app/"

# The local file is now an empty stub Terraform keeps for backup
cat terraform.tfstate 2>/dev/null | head -5
ls -la terraform.tfstate.backup 2>/dev/null

# ⭐ Terraform still knows about everything — nothing was recreated
terraform state list
terraform plan          # "No changes. Your infrastructure matches the configuration."
```

**✅ Checkpoint:** `terraform plan` reports **no changes**. Migration moved the bookkeeping, not the infrastructure.

### Step 4: Confirm Encryption and Versioning Are Active

```bash
aws s3api head-object --bucket "$TF_STATE_BUCKET" --key lab-02/app/terraform.tfstate \
  --query '{Encryption:ServerSideEncryption,Size:ContentLength,Modified:LastModified}'

# Every apply creates a new version
terraform apply -auto-approve >/dev/null
aws s3api list-object-versions --bucket "$TF_STATE_BUCKET" --prefix lab-02/app/terraform.tfstate \
  --query 'Versions[].{Version:VersionId,Modified:LastModified,Latest:IsLatest}' --output table
```

> 💡 **Inheriting a DynamoDB backend?** You will meet `dynamodb_table = "terraform-locks"`
> in most existing repos, and it still works — but it is deprecated and slated for removal.
> Migrate by setting **both** for one release:
>
> ```hcl
> terraform {
>   backend "s3" {
>     bucket         = "my-tf-state"
>     key            = "prod/terraform.tfstate"
>     region         = "us-east-1"
>     encrypt        = true
>     use_lockfile   = true                 # ⭐ new path
>     dynamodb_table = "terraform-locks"    # keep until everyone is on 1.10+
>   }
> }
> ```
>
> Terraform takes both locks, so a colleague still on an older CLI is still protected.
> Once every runner and laptop is on 1.10+, delete the `dynamodb_table` line, then the table.

---

## 🔬 Exercise 4: Watch the Lock Work

This is the exercise that makes locking real rather than theoretical.

### Step 1: Start a Slow Apply

**Terminal 1:**

```bash
cd tf-state-lab/app

# Add something that takes a while to create
cat >> main.tf <<'HCL'

resource "time_sleep" "slow" {
  create_duration = "90s"
}
HCL

cat >> main.tf <<'HCL'

terraform {
  required_providers {
    time = { source = "hashicorp/time", version = "~> 0.11" }
  }
}
HCL

terraform init -backend-config=backend.hcl
terraform apply -auto-approve      # ⭐ this will hold the lock for ~90 seconds
```

### Step 2: Try a Second Operation

**Terminal 2**, while terminal 1 is still running:

```bash
cd tf-state-lab/app
terraform plan
```

**Symptom:**

```
╷
│ Error: Error acquiring the state lock
│
│ Error message: operation error S3: PutObject, https response error StatusCode: 412,
│                api error PreconditionFailed: At least one of the pre-conditions you
│                specified did not hold
│ Lock Info:
│   ID:        3f8a91c2-...
│   Path:      tf-state-.../lab-02/app/terraform.tfstate
│   Operation: OperationTypeApply
│   Who:       you@your-laptop
│   Version:   1.10.x
│   Created:   2026-08-04 11:42:07 UTC
╵
```

**✅ Checkpoint:** The second operation was **refused**, not queued and not silently allowed. Without this, both would have read the same state, made different changes, and the last write would have erased the other's record — leaving orphaned, untracked infrastructure.

### Step 3: Inspect the Lock Directly

**Terminal 2**, still while the apply runs:

```bash
# ⭐ The lock IS an object: <state key>.tflock, right next to the state
aws s3 ls "s3://$TF_STATE_BUCKET/lab-02/app/"

# Its body is the same lock info Terraform printed in the error
aws s3 cp "s3://$TF_STATE_BUCKET/lab-02/app/terraform.tfstate.tflock" - | python3 -m json.tool
```

Wait for terminal 1 to finish, then:

```bash
# Gone — the lock object is deleted on exit
aws s3api head-object --bucket "$TF_STATE_BUCKET" \
  --key lab-02/app/terraform.tfstate.tflock 2>&1 | grep -q 'Not Found' && echo "✅ lock released"
terraform plan                                                    # ✅ works now
```

### Step 4: Use `-lock-timeout` Instead of Failing Fast

In CI you usually want to **wait** rather than fail:

```bash
terraform plan -lock-timeout=5m
# Retries acquiring the lock for up to 5 minutes before giving up.
# Set this in CI so a queued pipeline waits instead of erroring.
export TF_CLI_ARGS_plan="-lock-timeout=5m"
export TF_CLI_ARGS_apply="-lock-timeout=10m"
```

---

## 🔬 Exercise 5: Sharing Outputs Between Stacks

Real infrastructure is split into multiple state files — network, data, application — so a mistake in one can't destroy the others. They still need to reference each other.

### Step 1: Create a Second Stack

```bash
cd ..
mkdir -p consumer && cd consumer

cat > main.tf <<'HCL'
terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    key          = "lab-02/consumer/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region
}

# ⭐ Read the OTHER stack's outputs — read-only, no ability to modify it
data "terraform_remote_state" "app" {
  backend = "s3"
  config = {
    bucket = var.state_bucket
    key    = "lab-02/app/terraform.tfstate"
    region = var.region
  }
}

# Use a value produced by the other stack
resource "aws_s3_object" "marker" {
  bucket  = data.terraform_remote_state.app.outputs.bucket_name
  key     = "consumer/marker.txt"
  content = "written by the consumer stack at ${timestamp()}\n"

  lifecycle {
    ignore_changes = [content]   # timestamp() changes every plan
  }
}

output "referenced_bucket" {
  value = data.terraform_remote_state.app.outputs.bucket_name
}
HCL

cat > variables.tf <<'HCL'
variable "region" {
  type    = string
  default = "us-east-1"
}

variable "state_bucket" {
  description = "Bucket holding the shared Terraform state"
  type        = string
}
HCL

cp ../app/backend.hcl .
terraform init -backend-config=backend.hcl
terraform apply -auto-approve -var="state_bucket=$TF_STATE_BUCKET"
terraform output
```

**✅ Checkpoint:** The consumer stack read the app stack's `bucket_name` output without duplicating any configuration and without being able to modify it.

### Step 2: Understand the Coupling You Just Created

| | `terraform_remote_state` | A data source (e.g. `aws_s3_bucket`) | An input variable |
|---|---|---|---|
| **Couples to** | The other stack's **outputs** and state location | Real infrastructure, by tag or name | Nothing — the caller decides |
| **Breaks when** | The producer removes an output or moves its state | The resource is renamed or retagged | Never |
| **Requires** | Read access to the other state file (⚠️ **which contains its secrets**) | Read access to the cloud API | Nothing |
| **Best for** | Tightly related stacks owned by one team | Loosely coupled stacks, different teams | Values that genuinely vary per environment |

> ⚠️ **`terraform_remote_state` grants read access to the entire producer state file**, including any secrets in it — not just the declared outputs. For cross-team boundaries, prefer a data source lookup by tag, or publish values to SSM Parameter Store:
>
> ```hcl
> # Producer
> resource "aws_ssm_parameter" "bucket_name" {
>   name  = "/lab02/app/bucket_name"
>   type  = "String"
>   value = aws_s3_bucket.app_data.id
> }
> # Consumer — reads ONE value, with its own IAM scope
> data "aws_ssm_parameter" "bucket_name" {
>   name = "/lab02/app/bucket_name"
> }
> ```

---

## 🧨 Break It: Four Backend Failures

### Scenario 1: The Stale Lock After a Killed Apply

**Break it:**

```bash
cd ../app
terraform apply -auto-approve &
APPLY_PID=$!
sleep 4
kill -9 $APPLY_PID          # ⭐ SIGKILL — the cleanup handler never runs
sleep 2
terraform plan
```

**Symptom:** `Error acquiring the state lock`, and it never clears. Nobody on the team can plan or apply. The `Who:` field names someone whose laptop is now closed.

**Investigate — before you force anything:**

```bash
# What is the lock, and who holds it?
aws s3 cp "s3://$TF_STATE_BUCKET/lab-02/app/terraform.tfstate.tflock" - | python3 -m json.tool

# ⭐ THE CRITICAL CHECK — is an apply genuinely still running?
#   1. Ask the person named in "Who"
#   2. Check CI for a running job on this workspace
#   3. Check CloudTrail for recent write activity in this account
aws cloudtrail lookup-events --max-results 10 \
  --query 'Events[?contains(EventName, `Create`) || contains(EventName, `Delete`)].{Time:EventTime,Event:EventName,User:Username}' \
  --output table
```

**Root cause:** The lock is acquired for the duration of an operation and released on exit. `kill -9`, an OOM, a CI timeout, or a dropped network connection leaves it orphaned. Nothing expires it automatically.

**Fix — only after confirming the operation is dead:**

```bash
LOCK_ID=$(aws s3 cp "s3://$TF_STATE_BUCKET/lab-02/app/terraform.tfstate.tflock" - \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["ID"])')
echo "lock id: $LOCK_ID"     # ⭐ same ID Terraform printed in the error
terraform force-unlock "$LOCK_ID"
terraform plan               # ✅ works again
```

> ⚠️ **`force-unlock` during a genuinely running apply is how state actually gets corrupted** — two processes writing different views of reality to the same file. A stuck lock costs you minutes; a corrupted state costs you a day. If you are not certain, wait.

---

### Scenario 2: Two Applies, One State, Silent Divergence

**Break it — this is what locking prevents, demonstrated by removing it:**

```bash
mkdir -p ../nolock && cd ../nolock
cat > main.tf <<'HCL'
terraform {
  required_providers { random = { source = "hashicorp/random", version = "~> 3.6" } }
}
resource "random_pet" "a" { length = 3 }
HCL
terraform init >/dev/null

# Two applies against the SAME local state, with locking disabled
terraform apply -auto-approve -lock=false >/dev/null 2>&1 &
terraform apply -auto-approve -lock=false >/dev/null 2>&1 &
wait

terraform state list
python3 -c "
import json; s=json.load(open('terraform.tfstate'))
print('serial:', s['serial'], '| resources:', len(s['resources']))
"
terraform plan     # may show drift, a recreate, or nothing — the result is not deterministic
```

**Symptom:** Depending on timing, you get a state file that reflects only one of the two applies. Anything created by the other run exists in the cloud but is **not in state** — it is now invisible to Terraform, will never be destroyed by `terraform destroy`, and will bill forever.

**Investigate:**

```bash
terraform state list                       # what Terraform thinks exists
terraform plan -detailed-exitcode; echo "exit=$?"
# exit 2 = there are changes pending — Terraform wants to reconcile a reality it doesn't recognise
```

**Root cause:** Terraform's write cycle is read state → compute diff → apply → write state. With two concurrent runs, both read the same starting state and the second write overwrites the first's record entirely. Nothing in the process detects it.

**Fix:** never disable locking. `-lock=false` exists for narrow recovery scenarios and should never appear in a pipeline.

```bash
grep -rn '\-lock=false' . 2>/dev/null || echo "✅ no -lock=false anywhere"
cd ../app
```

---

### Scenario 3: Corrupted State, and the Recovery

**Break it:**

```bash
# Simulate a truncated write (a killed upload, a disk-full CI runner)
terraform state pull > /tmp/good-state.json
python3 -c "
import json
s = json.load(open('/tmp/good-state.json'))
s['resources'] = s['resources'][:1]      # drop most resources
open('/tmp/broken-state.json','w').write(json.dumps(s))
"
terraform state push -force /tmp/broken-state.json
terraform state list        # ⭐ most of your infrastructure has vanished from state
terraform plan              # Terraform now wants to CREATE things that already exist
```

**Symptom:** `terraform plan` proposes creating resources that exist. Applying it would fail on globally-unique names (S3 buckets), or worse, succeed and create duplicates.

**Investigate:**

```bash
terraform state list                                   # what state now says
aws s3 ls | grep tf-lab-app                            # what actually exists
aws s3api list-object-versions --bucket "$TF_STATE_BUCKET" \
  --prefix lab-02/app/terraform.tfstate \
  --query 'Versions[:5].{V:VersionId,When:LastModified,Latest:IsLatest}' --output table
```

**Fix — this is exactly why you enabled versioning:**

```bash
# Find the version from before the bad push
GOOD_VERSION=$(aws s3api list-object-versions --bucket "$TF_STATE_BUCKET" \
  --prefix lab-02/app/terraform.tfstate \
  --query 'Versions[1].VersionId' --output text)
echo "restoring version: $GOOD_VERSION"

aws s3api get-object --bucket "$TF_STATE_BUCKET" \
  --key lab-02/app/terraform.tfstate --version-id "$GOOD_VERSION" /tmp/restored.tfstate

terraform state push /tmp/restored.tfstate
terraform state list      # ✅ everything is back
terraform plan            # ✅ no changes
```

> ⭐ **Without S3 versioning there is no recovery from this.** The state file is the only record mapping your code to real resource IDs; lose it and you rebuild the mapping by hand with `import` blocks, one resource at a time. Enabling versioning takes one command and is the difference between a five-minute fix and a two-day one.

---

### Scenario 4: The Backend Key Collision

**Break it:**

```bash
mkdir -p ../collision && cd ../collision
cat > main.tf <<'HCL'
terraform {
  required_providers { random = { source = "hashicorp/random", version = "~> 3.6" } }
  backend "s3" {
    key     = "lab-02/app/terraform.tfstate"   # ❌ THE SAME KEY as the app stack
    encrypt = true
  }
}
resource "random_pet" "collision" { length = 2 }
HCL
cp ../app/backend.hcl .
terraform init -backend-config=backend.hcl
terraform apply -auto-approve
```

**Symptom:** The apply succeeds. Now go back and look at the app stack:

```bash
cd ../app
terraform init -backend-config=backend.hcl -reconfigure >/dev/null
terraform state list
terraform plan
```

Your app stack's state has been **overwritten** by the collision stack. Terraform now believes your S3 buckets don't exist and wants to create them. The real buckets are orphaned — still billing, no longer managed.

**Investigate:**

```bash
terraform state list                      # only random_pet.collision
aws s3 ls | grep tf-lab-app               # ⭐ the real bucket is still there, now untracked

aws s3api list-object-versions --bucket "$TF_STATE_BUCKET" \
  --prefix lab-02/app/terraform.tfstate \
  --query 'Versions[:4].{V:VersionId,When:LastModified}' --output table

# The lineage tells you two different stacks wrote here
terraform state pull | python3 -c "import json,sys; print('lineage:', json.load(sys.stdin)['lineage'])"
```

**Root cause:** The backend `key` is the state file's identity. Two configurations pointing at the same key share one state file, and each apply overwrites the other's. Nothing warns you — Terraform has no way to know two different codebases meant to be separate.

**Fix:**

```bash
# 1. Restore the app state from a version written by the app stack
GOOD=$(aws s3api list-object-versions --bucket "$TF_STATE_BUCKET" \
  --prefix lab-02/app/terraform.tfstate --query 'Versions[2].VersionId' --output text)
aws s3api get-object --bucket "$TF_STATE_BUCKET" --key lab-02/app/terraform.tfstate \
  --version-id "$GOOD" /tmp/app-state.json
terraform state push /tmp/app-state.json
terraform state list && terraform plan

# 2. Give the other stack its own key
cd ../collision
sed -i 's|lab-02/app/terraform.tfstate|lab-02/collision/terraform.tfstate|' main.tf
terraform init -backend-config=backend.hcl -reconfigure -migrate-state
cd ../app
```

**Prevent it with a key convention that cannot collide:**

```
<environment>/<region>/<stack>/terraform.tfstate

prod/us-east-1/network/terraform.tfstate
prod/us-east-1/data/terraform.tfstate
prod/us-east-1/app/terraform.tfstate
staging/us-east-1/app/terraform.tfstate
```

Generate the key from the directory path in CI so it can never be wrong by hand.

---

### Summary

| Failure | Detection | Prevention |
|---------|-----------|------------|
| Stale lock | `Error acquiring the state lock` | Verify nothing is running, then `force-unlock`. Use `-lock-timeout` in CI |
| Concurrent applies | Non-deterministic drift; orphaned resources | Never `-lock=false`. Locking is the whole point of the backend |
| Corrupted state | Plan wants to create what exists | ⭐ **S3 versioning** + `state pull > backup` before any state surgery |
| Key collision | State replaced by another stack's | A strict `env/region/stack` key convention, generated in CI |
| Secrets exposed | — | Encryption at rest, tight IAM on the bucket, never commit state |

**The backend checklist:**

- [ ] Versioning **enabled** on the state bucket
- [ ] Encryption at rest (SSE-S3 minimum, SSE-KMS for regulated data)
- [ ] All four public-access blocks on
- [ ] Locking configured — `use_lockfile = true` (not the deprecated `dynamodb_table`)
- [ ] Lifecycle rule expiring noncurrent versions (they accumulate)
- [ ] Bucket IAM policy restricted to the roles that need it — **state contains secrets**
- [ ] A key convention that makes collisions structurally impossible
- [ ] `*.tfstate*` in `.gitignore` from the first commit

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
cd tf-state-lab
for d in consumer app collision nolock; do
  [ -d "$d" ] && (cd "$d" && terraform destroy -auto-approve 2>/dev/null)
done
cd .. && rm -rf tf-state-lab

# Optional: remove the backend itself. Keep it if you're continuing to Lab 03.
# aws s3 rm "s3://$TF_STATE_BUCKET" --recursive
# aws s3api delete-objects --bucket "$TF_STATE_BUCKET" --delete "$(aws s3api list-object-versions \
#   --bucket "$TF_STATE_BUCKET" --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}')" 2>/dev/null
# aws s3api delete-bucket --bucket "$TF_STATE_BUCKET"   # ⭐ nothing else to delete

# Verify nothing is left billing
aws s3 ls | grep tf-lab-app || echo "✅ no lab buckets remain"
```

---

## ✅ Validation

- [ ] Explain the three ways local state fails a team
- [ ] Show that a `sensitive` value is stored in plaintext in state
- [ ] Bootstrap an S3 backend with native locking, versioning, encryption, and public-access blocks
- [ ] Migrate existing state with `-migrate-state` and prove no infrastructure changed
- [ ] Use partial backend configuration with `-backend-config`
- [ ] Trigger and inspect a real lock conflict between two terminals
- [ ] Explain when `force-unlock` is safe and when it corrupts state
- [ ] Restore a previous state version from S3 object versioning
- [ ] Read another stack's outputs, and explain the coupling and the security implication
- [ ] Describe a state key convention that makes collisions impossible

---

## 📝 What to Commit

- `main.tf`, `variables.tf`, `outputs.tf`, `backend.tf`, `backend.hcl.example` (⚠️ not the real one if it names a private bucket)
- The bootstrap commands as a script
- Transcript of the lock conflict from both terminals
- Transcript of the state restore from a previous version
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: Terraform Basics](./lab-01-terraform-basics.md) | [Back to Module README](../README.md) | [Next Lab: Modules, Environments, and Drift →](./lab-03-modules-and-environments.md)
