# Module 10: Terraform — Cheat Sheet

> CLI, HCL, functions, and state surgery. Concepts live in the [module README](./README.md).
> Cross-module daily commands: **[QUICK-REFERENCE.md](../QUICK-REFERENCE.md)**

**Jump to:** [CLI](#cli) · [State commands](#state-commands) · [HCL blocks](#hcl-blocks) · [Variables](#variables--outputs) · [Meta-arguments](#meta-arguments) · [Functions](#function-reference) · [Modules](#modules) · [Backends](#backends--locking) · [Environments](#multiple-environments) · [Testing](#testing--policy) · [Errors](#error-decoder)

---

## CLI

```bash
terraform init                          # download providers/modules, configure the backend
terraform init -upgrade                 # bump providers within their version constraints
terraform init -reconfigure             # ignore the existing backend config
terraform init -migrate-state           # move state to a new backend
terraform init -backend-config=prod.hcl # partial backend configuration

terraform fmt -recursive                # ⭐ format everything
terraform fmt -check -recursive         # CI gate: fail if unformatted
terraform validate                      # syntax + internal consistency (no cloud calls)

terraform plan                          # preview
terraform plan -out=tfplan              # ⭐ save the plan — apply exactly this
terraform plan -var-file=prod.tfvars
terraform plan -target=module.network   # ⚠️ narrow scope; escape hatch, not routine
terraform plan -refresh=false           # faster; skips reading real infra
terraform plan -destroy                 # preview a teardown
terraform show -json tfplan | jq        # machine-readable plan for policy checks

terraform apply
terraform apply tfplan                  # ⭐ apply the reviewed plan, no re-prompt
terraform apply -auto-approve           # ⚠️ CI only, and only after a reviewed plan
terraform apply -parallelism=5          # default is 10
terraform apply -replace=aws_instance.web   # force recreate one resource

terraform destroy
terraform destroy -target=aws_instance.web

terraform output                        # all outputs
terraform output -json | jq
terraform output -raw db_endpoint       # ⭐ no quotes — pipe-friendly

terraform providers                     # provider requirements tree
terraform providers lock -platform=linux_amd64 -platform=darwin_arm64   # multi-OS lockfile
terraform version
terraform console                       # ⭐ REPL for testing expressions
terraform graph | dot -Tsvg > graph.svg
terraform workspace list|new|select|delete
terraform force-unlock <LOCK_ID>        # ⚠️ only when a lock is genuinely stale
terraform login / logout                # Terraform Cloud
```

**Environment variables:**

```bash
export TF_VAR_region="us-east-1"        # ⭐ sets variable "region"
export TF_LOG=DEBUG                     # TRACE|DEBUG|INFO|WARN|ERROR
export TF_LOG_PATH=./terraform.log
export TF_IN_AUTOMATION=1               # quieter output for CI
export TF_INPUT=0                       # never prompt
export TF_CLI_ARGS_plan="-lock-timeout=5m"
export TF_DATA_DIR=.terraform
```

---

## State Commands

```bash
terraform state list                             # every resource address
terraform state list | grep aws_instance
terraform state show aws_instance.web            # ⭐ full attributes of one resource
terraform state pull > backup.tfstate            # ⭐ ALWAYS back up before surgery
terraform state push backup.tfstate              # ⚠️ dangerous

terraform state mv aws_instance.old aws_instance.new           # rename in state
terraform state mv aws_instance.web module.compute.aws_instance.web
terraform state mv 'aws_instance.web[0]' 'aws_instance.web["a"]'   # count → for_each
terraform state rm aws_instance.web              # forget it WITHOUT destroying it
terraform state replace-provider hashicorp/aws registry.example/aws

terraform import aws_instance.web i-0abc123      # legacy CLI import
terraform refresh                                # deprecated; use: terraform apply -refresh-only
terraform apply -refresh-only                    # ⭐ reconcile state with reality, no changes
terraform taint aws_instance.web                 # deprecated; use -replace
```

### Declarative import and refactoring (Terraform 1.5+)

```hcl
# Reviewable in a PR, and can generate the config for you
import {
  to = aws_instance.web
  id = "i-0abc123def456"
}
```

```bash
terraform plan -generate-config-out=generated.tf    # ⭐ writes the resource block for you
terraform apply                                     # imports into state
# then delete the import block — it's a one-time operation
```

```hcl
# Rename or relocate WITHOUT destroy/recreate
moved {
  from = aws_instance.old
  to   = aws_instance.new
}

moved {
  from = aws_instance.web
  to   = module.compute.aws_instance.web
}

# Terraform 1.7+: intentional removal from state, keeping the real resource
removed {
  from = aws_instance.legacy
  lifecycle { destroy = false }
}
```

### State surgery playbook

| Situation | Steps |
|-----------|-------|
| Resource exists in cloud, not in state | Add an `import` block → `plan -generate-config-out` → `apply` |
| Renamed a resource in code | Add a `moved` block → `plan` shows "0 to change" → `apply` |
| Want Terraform to stop managing something | `terraform state rm ADDR` (or a `removed` block) |
| Someone changed it in the console (drift) | `terraform apply -refresh-only` to record it, then decide: revert or codify |
| State is locked and the job that held it died | Confirm nothing is running, then `terraform force-unlock <ID>` |
| Need to split one state into two | `state pull` backup → `state rm` from A → `import` into B |
| State file is corrupt | Restore from S3 versioning: `aws s3api list-object-versions` → download → `state push` |

> ⚠️ **`terraform state pull > backup.tfstate` before every state operation.** State surgery is the one part of Terraform with no plan step and no undo.

---

## HCL Blocks

```hcl
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"        # ⭐ >= 5.40, < 6.0
    }
  }
  backend "s3" {
    bucket         = "my-tf-state"
    key            = "prod/network/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      ManagedBy   = "terraform"
      Environment = var.environment
      Repo        = "github.com/myorg/infra"
    }
  }
}

provider "aws" {
  alias  = "us_west"            # ⭐ second region
  region = "us-west-2"
}

resource "aws_instance" "web" {
  ami           = data.aws_ami.al2023.id
  instance_type = var.instance_type
  tags          = { Name = "web-${var.environment}" }
}

data "aws_ami" "al2023" {       # read-only lookup
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

locals {
  name_prefix = "${var.project}-${var.environment}"
  common_tags = {
    Project     = var.project
    Environment = var.environment
  }
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  name    = local.name_prefix
  cidr    = var.vpc_cidr
}

output "vpc_id" {
  value       = module.vpc.vpc_id
  description = "ID of the created VPC"
}
```

**Version constraint operators:**

| Constraint | Allows |
|------------|--------|
| `= 5.40.0` | Exactly that version |
| `>= 5.40` | That or newer |
| `~> 5.40` | `>= 5.40, < 6.0` — ⭐ allows minor and patch |
| `~> 5.40.0` | `>= 5.40.0, < 5.41.0` — patch only |
| `>= 5.0, < 6.0` | Explicit range |

> 💡 Commit `.terraform.lock.hcl`. It pins exact provider versions and checksums so every machine and CI run resolves identically.

---

## Variables & Outputs

```hcl
variable "instance_type" {
  type        = string
  default     = "t3.micro"
  description = "EC2 instance size"
}

variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "db_password" {
  type      = string
  sensitive = true            # ⭐ redacted from plan/apply output (still plaintext in state)
  nullable  = false
}

variable "subnet_cidrs" {
  type    = list(string)
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "server_config" {
  type = object({
    instance_type = string
    disk_gb       = number
    monitoring    = optional(bool, true)     # ⭐ optional with a default
  })
}

variable "rules" {
  type = list(object({
    port        = number
    cidr_blocks = list(string)
  }))
  default = []
}
```

**Precedence (later wins):** defaults → `TF_VAR_*` env vars → `terraform.tfvars` → `*.auto.tfvars` (alphabetical) → `-var-file` → `-var` on the command line.

```hcl
output "db_endpoint" {
  value       = aws_db_instance.main.endpoint
  description = "Connection endpoint"
}

output "db_password" {
  value     = random_password.db.result
  sensitive = true
}

output "instance_ips" {
  value = [for i in aws_instance.web : i.private_ip]
}
```

---

## Meta-Arguments

```hcl
# count — simple repetition, indexed by number
resource "aws_instance" "web" {
  count         = var.instance_count
  instance_type = "t3.micro"
  tags          = { Name = "web-${count.index}" }
}
# addresses: aws_instance.web[0], aws_instance.web[1]

# for_each — ⭐ preferred: keyed, so removing one doesn't shift the others
resource "aws_instance" "web" {
  for_each      = toset(["web-a", "web-b", "web-c"])
  instance_type = "t3.micro"
  tags          = { Name = each.key }
}
# addresses: aws_instance.web["web-a"], ...

resource "aws_instance" "app" {
  for_each      = var.servers          # map(object)
  instance_type = each.value.instance_type
  subnet_id     = each.value.subnet_id
  tags          = { Name = each.key }
}

# Conditional creation
resource "aws_instance" "bastion" {
  count = var.create_bastion ? 1 : 0
}

depends_on = [aws_iam_role_policy.app]   # explicit ordering when there's no implicit reference
provider   = aws.us_west                 # use an aliased provider

lifecycle {
  create_before_destroy = true           # ⭐ zero-downtime replacement
  prevent_destroy       = true           # ⚠️ guard for databases and state buckets
  ignore_changes        = [tags["LastScanned"], ami]
  replace_triggered_by  = [aws_launch_template.app.latest_version]
  precondition {
    condition     = data.aws_ami.al2023.architecture == "x86_64"
    error_message = "AMI must be x86_64."
  }
  postcondition {
    condition     = self.public_ip != ""
    error_message = "Instance must receive a public IP."
  }
}
```

> ⚠️ **`count` vs `for_each` matters more than it looks.** With `count`, deleting the middle item of a 3-element list renumbers everything after it — Terraform destroys and recreates resources that didn't change. `for_each` keys by a stable string, so removing one touches only that one. **Default to `for_each`.**

---

## Function Reference

```hcl
# Strings
format("%s-%03d", "web", 7)             # "web-007"
join("-", ["a", "b"])                   # "a-b"
split(",", "a,b,c")                     # ["a","b","c"]
replace(var.name, "/[^a-z0-9]/", "-")
lower() upper() title() trimspace()
substr("hello", 0, 3)                   # "hel"
startswith(s, "prefix")  endswith(s, "suffix")
trimprefix("v1.2.3", "v")               # "1.2.3"
regex("v(\\d+)", "v42")                 # "42"
regexall("[0-9]+", s)

# Collections
length(list)  concat(a, b)  distinct(list)  sort(list)  reverse(list)
flatten([[1,2],[3]])                    # [1,2,3]
element(list, 2)   slice(list, 1, 3)
contains(list, item)   index(list, item)
merge(map1, map2)                       # ⭐ later keys win — how you compose tags
keys(map)  values(map)  lookup(map, key, default)
zipmap(["a","b"], [1,2])                # {a=1, b=2}
setproduct(a, b)   setunion(a, b)   setintersection(a, b)
coalesce(var.a, var.b, "fallback")      # first non-null/non-empty
coalescelist(list_a, list_b)
try(local.maybe.missing, "default")     # ⭐ swallow an evaluation error
one(aws_instance.bastion[*].id)         # 0-or-1 list → single value or null

# Encoding & files
jsonencode(obj)   jsondecode(str)
yamlencode(obj)   yamldecode(str)
base64encode()    base64decode()
file("${path.module}/policy.json")
templatefile("${path.module}/init.sh.tpl", { port = 8080 })   # ⭐
fileset(path.module, "configs/*.yaml")
filebase64sha256("lambda.zip")          # triggers redeploy when the artifact changes

# Networking  ⭐ these save real time
cidrsubnet("10.0.0.0/16", 8, 3)         # "10.0.3.0/24"
cidrhost("10.0.1.0/24", 5)              # "10.0.1.5"
cidrnetmask("10.0.1.0/24")              # "255.255.255.0"
[for i in range(3) : cidrsubnet(var.vpc_cidr, 8, i)]

# Type conversion & misc
tostring() tonumber() tolist() toset() tomap()
can(regex("^v", var.tag))               # boolean form of try()
uuid()   timestamp()   timeadd(timestamp(), "24h")
formatdate("YYYY-MM-DD", timestamp())
md5() sha256() bcrypt()
```

**Path and workspace references:** `path.module` (this module's dir) · `path.root` (root module dir) · `path.cwd` · `terraform.workspace` · `self.<attr>` (in provisioners/lifecycle) · `each.key`/`each.value` · `count.index`

### Expressions

```hcl
# Conditional
instance_type = var.environment == "prod" ? "m5.large" : "t3.micro"

# for expression — list
subnet_ids = [for s in aws_subnet.private : s.id]
upper_names = [for n in var.names : upper(n) if length(n) > 3]

# for expression — map
name_to_id = { for s in aws_subnet.private : s.tags.Name => s.id }

# Splat
all_ips = aws_instance.web[*].private_ip

# Dynamic blocks — ⭐ generate repeated nested blocks
resource "aws_security_group" "app" {
  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      from_port   = ingress.value.port
      to_port     = ingress.value.port
      protocol    = "tcp"
      cidr_blocks = ingress.value.cidr_blocks
    }
  }
}

# Heredoc
user_data = <<-EOT
  #!/bin/bash
  echo "port=${var.port}" >> /etc/app.conf
EOT
```

---

## Modules

```
modules/
└── vpc/
    ├── main.tf          # resources
    ├── variables.tf     # inputs
    ├── outputs.tf       # outputs
    ├── versions.tf      # required_providers
    └── README.md        # ⭐ document inputs/outputs/examples
```

```hcl
module "vpc" {
  source = "./modules/vpc"                                    # local
  # source = "terraform-aws-modules/vpc/aws"                  # registry
  # version = "~> 5.0"
  # source = "git::https://github.com/org/modules.git//vpc?ref=v1.2.0"   # ⭐ pin the ref
  # source = "git@github.com:org/modules.git//vpc?ref=v1.2.0"

  cidr_block  = "10.0.0.0/16"
  environment = var.environment
  tags        = local.common_tags
}

# Reference its outputs
subnet_id = module.vpc.private_subnet_ids[0]

# Repeat a whole module
module "service" {
  source   = "./modules/service"
  for_each = var.services
  name     = each.key
  port     = each.value.port
}
```

**Module design rules:**

| Rule | Why |
|------|-----|
| **Never** hardcode a provider block inside a module | Callers must control region/credentials |
| Expose a `tags` input and merge it | Lets callers apply org-wide tagging |
| Output everything a caller might need | Adding an output later is free; guessing isn't |
| Pin git sources with `?ref=` a **tag**, not a branch | A branch can change under you between applies |
| Keep modules focused | A "does everything" module is harder to reuse than three small ones |
| `terraform-docs markdown . > README.md` | Auto-generate the input/output tables |

```bash
terraform get -update                 # refresh module sources
terraform-docs markdown table . > README.md
```

---

## Backends & Locking

```hcl
# S3 + DynamoDB (classic)
terraform {
  backend "s3" {
    bucket         = "my-tf-state"
    key            = "prod/network/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"        # ⭐ the lock
    encrypt        = true
    kms_key_id     = "arn:aws:kms:..."
  }
}

# S3 native locking (Terraform 1.10+) — no DynamoDB table needed
terraform {
  backend "s3" {
    bucket       = "my-tf-state"
    key          = "prod/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
```

**Bootstrap the backend** (chicken-and-egg: create these once, by hand or with local state):

```bash
aws s3api create-bucket --bucket my-tf-state --region us-east-1
aws s3api put-bucket-versioning --bucket my-tf-state \
  --versioning-configuration Status=Enabled                  # ⭐ your state undo button
aws s3api put-bucket-encryption --bucket my-tf-state \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket my-tf-state \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
aws dynamodb create-table --table-name terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

```hcl
# Read another state's outputs
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "my-tf-state"
    key    = "prod/network/terraform.tfstate"
    region = "us-east-1"
  }
}

subnet_id = data.terraform_remote_state.network.outputs.private_subnet_ids[0]
```

> ⚠️ **State contains secrets in plaintext** — RDS passwords, generated keys, `sensitive` outputs. Encrypt the bucket, restrict access with an IAM policy, enable versioning, and never commit `*.tfstate` to git.

---

## Multiple Environments

**Directory-per-environment (recommended for production):**

```
environments/
├── dev/
│   ├── main.tf          # calls shared modules
│   ├── terraform.tfvars
│   └── backend.tf       # key = "dev/terraform.tfstate"
├── staging/
└── prod/
modules/
├── network/
└── compute/
```

✅ Fully isolated state · different backends and accounts possible · explicit and reviewable
❌ Some duplication in the root modules

**Workspaces (fine for small, identical environments):**

```bash
terraform workspace new dev
terraform workspace select prod
terraform workspace list
terraform workspace show
```

```hcl
locals {
  env = terraform.workspace
  instance_type = {
    dev     = "t3.micro"
    staging = "t3.small"
    prod    = "m5.large"
  }[terraform.workspace]
}
```

✅ One codebase, no duplication
❌ **All environments share one backend** — a misconfigured backend or a wrong `select` can point prod operations at the wrong state. Not recommended for prod isolation.

---

## Packer — Golden Images

```bash
packer init .
packer fmt -check .                       # CI should enforce this, same as terraform fmt
packer validate -var region=eu-west-1 .
PACKER_LOG=1 packer build .               # ⭐ the only way to debug a build that hangs
packer build -only=amazon-ebs.ubuntu .
jq -r '.builds[-1].artifact_id' manifest.json    # the image id, for the next pipeline stage
```

```hcl
source "amazon-ebs" "ubuntu" {
  source_ami_filter {                     # ⭐ resolve the base image, never hardcode an id
    filters     = { name = "ubuntu/images/*22.04-amd64-server-*" }
    owners      = ["099720109477"]
    most_recent = true
  }
  ami_name = "app-base-{{timestamp}}"
  tags     = { GitCommit = "{{ env `GIT_COMMIT` }}" }   # trace an instance back to a commit
}

build {
  sources = ["source.amazon-ebs.ubuntu"]
  provisioner "shell"   { inline = ["cloud-init status --wait"] }   # ⭐ or apt races it
  provisioner "ansible" { playbook_file = "../ansible/playbooks/base.yml" }
  provisioner "shell"   { inline = ["systemctl is-enabled node_exporter"] }  # verify, then ship
  post-processor "manifest" { output = "manifest.json" }
}
```

| Bake into the image | Configure at boot |
|---------------------|-------------------|
| Slow installs, agents, OS hardening | Config, secrets, environment names |
| Anything you want identical fleet-wide | Anything that changes more often than you rebuild |

```bash
# Old AMIs are free; their snapshots are not
aws ec2 describe-images --owners self \
  --query 'sort_by(Images,&CreationDate)[].[CreationDate,ImageId,Name]' --output table
aws ec2 deregister-image --image-id ami-xxx    # ⚠️ does NOT delete the snapshot
aws ec2 delete-snapshot --snapshot-id snap-xxx
```

⚠️ `data "aws_ami"` with `most_recent = true` means a Packer build silently changes your next
`terraform plan`. Fine in dev; pin production to an explicit id and promote deliberately.

---

## Testing & Policy

```bash
tflint                                  # ⭐ provider-aware linting (invalid instance types, etc.)
tflint --init && tflint --recursive
tfsec .                                 # security scanning
trivy config .                          # ⭐ IaC misconfiguration scanning (supersedes tfsec)
checkov -d .                            # policy-as-code scanning
terraform-compliance -f features -p tfplan.json
infracost breakdown --path .            # ⭐ cost estimate BEFORE you apply
infracost diff --path . --compare-to base.json

terraform test                          # native tests (1.6+), *.tftest.hcl
```

```hcl
# tests/vpc.tftest.hcl
run "creates_vpc_with_correct_cidr" {
  command = plan
  variables { cidr_block = "10.0.0.0/16" }
  assert {
    condition     = aws_vpc.main.cidr_block == "10.0.0.0/16"
    error_message = "VPC CIDR did not match the input"
  }
}
```

**CI pipeline shape:**

```yaml
- terraform fmt -check -recursive
- terraform init -backend=false
- terraform validate
- tflint --recursive
- trivy config .
- terraform init
- terraform plan -out=tfplan -input=false
- terraform show -json tfplan > plan.json
- infracost diff --path plan.json
- conftest test plan.json               # OPA policies
# post the plan as a PR comment; require approval
- terraform apply -input=false tfplan   # ⭐ applies the EXACT reviewed plan
```

---

## Error Decoder

| Error | Cause | Fix |
|-------|-------|-----|
| `Error acquiring the state lock` | Another apply is running, or a job died holding the lock | Wait. If genuinely stale: `terraform force-unlock <ID>` |
| `Error: Provider configuration not present` | Removed a provider that state still references | `terraform state replace-provider`, or re-add the provider block |
| `Objects have changed outside of Terraform` | Drift | `terraform apply -refresh-only`, then decide: revert or codify |
| `Resource already exists` | Created outside Terraform | Use an `import` block |
| Plan wants to destroy/recreate after a rename | State still has the old address | Add a `moved` block |
| `Cycle: a → b → a` | Circular dependency | Break it with `depends_on` on a narrower resource, or split the resource |
| `Invalid for_each argument ... unknown` | `for_each` depends on a value only known after apply | Use static keys, or apply in two stages / `-target` once |
| `count cannot be determined until apply` | Same root cause as above | Restructure to use known values |
| `Inconsistent dependency lock file` | Lockfile doesn't match `required_providers` | `terraform init -upgrade` |
| `Error: Unsupported argument` | Provider major version changed | Read the upgrade guide; pin with `~>` |
| Deleted a resource block → plan says destroy, but you wanted to keep it | Terraform manages what it knows | `terraform state rm`, or a `removed` block |
| `timeout while waiting for state to become 'available'` | Cloud operation is slower than the default timeout | Add a `timeouts { create = "60m" }` block |
| Secret leaked in CI logs | Output not marked `sensitive` | `sensitive = true`; mask in CI |

---

<div align="center">

[← Module 10 README](./README.md) · [Resources](./resources.md) · [Labs](./labs/) · [Handbook Quick Reference](../QUICK-REFERENCE.md)

</div>
