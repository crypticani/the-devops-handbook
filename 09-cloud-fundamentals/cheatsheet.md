# Module 09: Cloud Fundamentals — Cheat Sheet

> AWS CLI reference by service, plus IAM policy patterns and cost controls. Concepts live in the [module README](./README.md).
> Cross-module daily commands: **[QUICK-REFERENCE.md](../QUICK-REFERENCE.md)**

**Jump to:** [CLI setup](#cli-setup--profiles) · [EC2](#ec2) · [VPC](#vpc--networking) · [S3](#s3) · [IAM](#iam) · [RDS](#rds) · [ELB & Route 53](#load-balancing--dns) · [ECS & EKS](#containers-ecr-ecs-eks) · [Lambda](#lambda) · [Logs & monitoring](#cloudwatch) · [Cost](#cost-control) · [Query patterns](#query-patterns) · [Equivalents](#cross-cloud-equivalents)

---

## CLI Setup & Profiles

```bash
aws configure                                  # interactive; writes ~/.aws/credentials
aws configure --profile prod
aws configure list
aws configure list-profiles

export AWS_PROFILE=prod                        # ⭐ set once per shell
export AWS_REGION=us-east-1
aws sts get-caller-identity                    # ⭐ ALWAYS run this first: WHO am I, WHICH account?
```

```ini
# ~/.aws/config — prefer SSO or role assumption over static keys
[profile prod]
region = us-east-1
output = json

[profile prod-admin]
role_arn = arn:aws:iam::123456789012:role/Admin
source_profile = prod
mfa_serial = arn:aws:iam::123456789012:mfa/alice

[profile sso-prod]
sso_start_url = https://myorg.awsapps.com/start
sso_region = us-east-1
sso_account_id = 123456789012
sso_role_name = PowerUserAccess
```

```bash
aws sso login --profile sso-prod
aws --profile prod-admin s3 ls                 # per-command profile
aws --region eu-west-1 ec2 describe-instances  # per-command region

aws --output json|table|text|yaml ...
aws --dry-run ec2 run-instances ...            # ⭐ permission check without side effects
aws --debug ...                                # full request/response trace
aws ... --no-cli-pager                         # stop it opening less
```

> ⚠️ **Before every destructive command, run `aws sts get-caller-identity`.** Running the right command in the wrong account is the most expensive mistake in cloud ops. Consider a shell prompt that shows `$AWS_PROFILE`.

---

## EC2

```bash
aws ec2 describe-instances
aws ec2 describe-instances --instance-ids i-0abc123
aws ec2 describe-instances --filters "Name=tag:Environment,Values=prod" \
                                     "Name=instance-state-name,Values=running"

# ⭐ Readable inventory
aws ec2 describe-instances --query \
 'Reservations[].Instances[].{ID:InstanceId,Type:InstanceType,State:State.Name,IP:PrivateIpAddress,Name:Tags[?Key==`Name`]|[0].Value}' \
 --output table

aws ec2 start-instances    --instance-ids i-0abc123
aws ec2 stop-instances     --instance-ids i-0abc123
aws ec2 reboot-instances   --instance-ids i-0abc123
aws ec2 terminate-instances --instance-ids i-0abc123        # ⚠️ irreversible

aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.micro \
  --key-name my-key \
  --security-group-ids sg-0abc123 \
  --subnet-id subnet-0abc123 \
  --iam-instance-profile Name=AppRole \
  --metadata-options "HttpTokens=required" \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=web-01},{Key=Environment,Value=prod}]'

aws ec2 describe-instance-status --instance-ids i-0abc123
aws ec2 get-console-output --instance-id i-0abc123          # ⭐ boot log when SSH fails
aws ec2 describe-images --owners amazon \
  --filters "Name=name,Values=al2023-ami-*-x86_64" \
  --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text

# Session Manager — SSH without open port 22 or a bastion
aws ssm start-session --target i-0abc123
aws ssm start-session --target i-0abc123 \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["5432"],"localPortNumber":["5432"]}'

# Volumes and snapshots
aws ec2 describe-volumes --filters "Name=status,Values=available"     # ⭐ unattached = wasted money
aws ec2 create-snapshot --volume-id vol-0abc --description "pre-upgrade"
aws ec2 describe-snapshots --owner-ids self --query 'Snapshots[?StartTime<=`2026-01-01`]'
```

**Instance metadata (IMDSv2 — from inside an instance):**

```bash
TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
curl -sH "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id
curl -sH "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

> ⚠️ Always enforce IMDSv2 (`HttpTokens=required`). IMDSv1's simple GET is what turns a server-side request forgery bug into stolen IAM credentials.

---

## VPC & Networking

```bash
aws ec2 describe-vpcs
aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-0abc"
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=vpc-0abc"
aws ec2 describe-internet-gateways
aws ec2 describe-nat-gateways
aws ec2 describe-network-acls

# Security groups
aws ec2 describe-security-groups --group-ids sg-0abc123
aws ec2 describe-security-groups \
  --query 'SecurityGroups[?IpPermissions[?contains(IpRanges[].CidrIp, `0.0.0.0/0`)]].{ID:GroupId,Name:GroupName}' \
  --output table          # ⭐ AUDIT: which SGs are open to the world?

aws ec2 authorize-security-group-ingress \
  --group-id sg-0abc123 --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress \
  --group-id sg-db --protocol tcp --port 5432 --source-group sg-app   # ⭐ SG-to-SG, not CIDR
aws ec2 revoke-security-group-ingress \
  --group-id sg-0abc123 --protocol tcp --port 22 --cidr 0.0.0.0/0
```

| Layer | Stateful? | Applies to | Rules |
|-------|-----------|------------|-------|
| **Security Group** | ✅ Stateful — return traffic is automatic | ENI / instance | **Allow only** |
| **Network ACL** | ❌ Stateless — you must allow both directions | Subnet | Allow **and** deny, numbered and ordered |

**Reference VPC layout:**

```
VPC 10.0.0.0/16
├── Public subnets   10.0.0.0/24 (az-a), 10.0.1.0/24 (az-b)
│   └── route: 0.0.0.0/0 → Internet Gateway
│   └── contains: ALB, NAT Gateway, bastion
├── Private subnets  10.0.10.0/24 (az-a), 10.0.11.0/24 (az-b)
│   └── route: 0.0.0.0/0 → NAT Gateway
│   └── contains: app servers, EKS nodes
└── Data subnets     10.0.20.0/24 (az-a), 10.0.21.0/24 (az-b)
    └── route: local only — NO internet route
    └── contains: RDS, ElastiCache
```

> 💡 **NAT Gateways are a top-3 surprise on cloud bills** — roughly $32/month each plus per-GB processing, and you need one per AZ for high availability. Use **VPC endpoints** for S3, ECR, and other AWS services so that traffic never traverses the NAT: `aws ec2 create-vpc-endpoint --vpc-id vpc-0abc --service-name com.amazonaws.us-east-1.s3 --route-table-ids rtb-0abc`

---

## S3

```bash
aws s3 ls                                      # buckets
aws s3 ls s3://my-bucket/path/ --recursive --human-readable --summarize   # ⭐ size
aws s3 cp file.txt s3://my-bucket/path/
aws s3 cp s3://my-bucket/file.txt .
aws s3 cp . s3://my-bucket/ --recursive --exclude "*" --include "*.log"
aws s3 sync ./local s3://my-bucket/prefix/ --delete --dry-run     # ⭐ preview first
aws s3 mv s3://a/f s3://b/f
aws s3 rm s3://my-bucket/file.txt
aws s3 rm s3://my-bucket/prefix/ --recursive   # ⚠️
aws s3 mb s3://new-bucket --region us-east-1
aws s3 rb s3://old-bucket --force              # ⚠️ delete bucket + contents
aws s3 presign s3://my-bucket/file.pdf --expires-in 3600          # temporary public link

# Lower-level API
aws s3api head-object --bucket my-bucket --key file.txt
aws s3api list-object-versions --bucket my-bucket --prefix path/
aws s3api get-bucket-versioning --bucket my-bucket
aws s3api get-bucket-encryption --bucket my-bucket
aws s3api get-public-access-block --bucket my-bucket
aws s3api get-bucket-policy --bucket my-bucket --query Policy --output text | jq
```

**Hardening a bucket:**

```bash
aws s3api put-public-access-block --bucket my-bucket \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

aws s3api put-bucket-versioning --bucket my-bucket \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption --bucket my-bucket \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"},"BucketKeyEnabled":true}]}'

# Lifecycle: transition then expire — the main storage-cost lever
aws s3api put-bucket-lifecycle-configuration --bucket my-bucket \
  --lifecycle-configuration '{"Rules":[{
    "ID":"archive-and-expire","Status":"Enabled","Filter":{"Prefix":"logs/"},
    "Transitions":[{"Days":30,"StorageClass":"STANDARD_IA"},
                   {"Days":90,"StorageClass":"GLACIER_IR"}],
    "Expiration":{"Days":365},
    "AbortIncompleteMultipartUpload":{"DaysAfterInitiation":7}
  }]}'
```

| Storage class | Use for | Retrieval |
|---------------|---------|-----------|
| `STANDARD` | Active data | Instant |
| `INTELLIGENT_TIERING` | ⭐ Unknown/changing access patterns | Instant, auto-tiered |
| `STANDARD_IA` | Backups accessed monthly | Instant, per-GB retrieval fee |
| `GLACIER_IR` | Archives you might need fast | Instant |
| `GLACIER_FLEXIBLE` | Compliance archives | Minutes–hours |
| `DEEP_ARCHIVE` | Cheapest; 7-year retention | 12+ hours |

---

## IAM

```bash
aws sts get-caller-identity                                # ⭐ who am I
aws iam list-users / list-roles / list-groups
aws iam get-role --role-name MyRole
aws iam list-attached-role-policies --role-name MyRole
aws iam list-role-policies --role-name MyRole              # inline policies
aws iam get-policy-version --policy-arn arn:... --version-id v3

# ⭐ Audit: find stale credentials
aws iam generate-credential-report && aws iam get-credential-report \
  --query Content --output text | base64 -d | column -t -s,

aws iam list-access-keys --user-name alice
aws iam get-access-key-last-used --access-key-id AKIA...
aws iam update-access-key --user-name alice --access-key-id AKIA... --status Inactive
aws iam delete-access-key --user-name alice --access-key-id AKIA...

# ⭐ Test a policy WITHOUT running the action
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:role/AppRole \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::my-bucket/file.txt

# Assume a role manually
aws sts assume-role --role-arn arn:aws:iam::123:role/Deploy --role-session-name cli
```

### Policy structure

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ReadAppBucket",
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::my-app-bucket",
      "arn:aws:s3:::my-app-bucket/*"
    ],
    "Condition": {
      "StringEquals": {"aws:PrincipalTag/Environment": "production"},
      "IpAddress":    {"aws:SourceIp": ["203.0.113.0/24"]},
      "Bool":         {"aws:SecureTransport": "true"}
    }
  }]
}
```

**Evaluation order:** explicit `Deny` → SCP → resource policy → identity policy → permission boundary. **An explicit Deny anywhere always wins.**

| Principle | In practice |
|-----------|-------------|
| **Roles, not users** | EC2 → instance profile; EKS → IRSA/Pod Identity; CI → OIDC. Static keys are the last resort |
| **Least privilege** | Start from nothing; add what CloudTrail shows is actually used |
| **Scope resources** | `"Resource": "*"` is almost always too broad |
| **Add conditions** | Restrict by source IP, VPC endpoint, MFA, tag, or TLS |
| **Permission boundaries** | Cap what a delegated admin can grant |
| **SCPs at the org level** | Guardrails no account admin can override |
| **Rotate and audit** | Credential report monthly; delete unused keys and roles |

```json
// Trust policy for GitHub Actions OIDC — no stored credentials at all
{
  "Effect": "Allow",
  "Principal": {"Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"},
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
    "StringLike": {"token.actions.githubusercontent.com:sub": "repo:myorg/myrepo:ref:refs/heads/main"}
  }
}
```

---

## RDS

```bash
aws rds describe-db-instances \
  --query 'DBInstances[].{ID:DBInstanceIdentifier,Engine:Engine,Class:DBInstanceClass,Status:DBInstanceStatus,MultiAZ:MultiAZ,Public:PubliclyAccessible}' \
  --output table

aws rds describe-db-instances --db-instance-identifier mydb
aws rds create-db-snapshot --db-instance-identifier mydb --db-snapshot-identifier mydb-pre-upgrade
aws rds describe-db-snapshots --db-instance-identifier mydb
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier mydb-restored --db-snapshot-identifier mydb-pre-upgrade
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier mydb --target-db-instance-identifier mydb-pitr \
  --restore-time 2026-08-04T09:00:00Z
aws rds modify-db-instance --db-instance-identifier mydb \
  --backup-retention-period 30 --apply-immediately
aws rds describe-events --source-identifier mydb --source-type db-instance --duration 1440

# ⭐ Audit: any publicly accessible databases?
aws rds describe-db-instances \
  --query 'DBInstances[?PubliclyAccessible==`true`].DBInstanceIdentifier'
```

---

## Load Balancing & DNS

```bash
aws elbv2 describe-load-balancers
aws elbv2 describe-target-groups
aws elbv2 describe-target-health --target-group-arn arn:...    # ⭐ why is a target unhealthy
aws elbv2 describe-listeners --load-balancer-arn arn:...
aws elbv2 describe-rules --listener-arn arn:...

aws route53 list-hosted-zones
aws route53 list-resource-record-sets --hosted-zone-id Z123 --output table
aws route53 change-resource-record-sets --hosted-zone-id Z123 --change-batch '{
  "Changes":[{"Action":"UPSERT","ResourceRecordSet":{
    "Name":"api.example.com","Type":"A",
    "AliasTarget":{"HostedZoneId":"Z35SXDOTRQ7X7K","DNSName":"my-alb-123.us-east-1.elb.amazonaws.com","EvaluateTargetHealth":true}
  }}]}'
aws route53 get-change --id /change/C123                       # wait for INSYNC

aws acm list-certificates
aws acm describe-certificate --certificate-arn arn:...         # validation status, expiry
```

| Type | Layer | Use for |
|------|-------|---------|
| **ALB** | 7 (HTTP/S) | Path/host routing, WebSockets, gRPC, OIDC auth |
| **NLB** | 4 (TCP/UDP) | Extreme throughput, static IPs, non-HTTP protocols |
| **GWLB** | 3 | Inline firewall/IDS appliances |

---

## Containers (ECR, ECS, EKS)

```bash
# ECR
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
aws ecr create-repository --repository-name myapp --image-scanning-configuration scanOnPush=true
aws ecr describe-images --repository-name myapp \
  --query 'sort_by(imageDetails,&imagePushedAt)[-5:].[imageTags[0],imagePushedAt]' --output table
aws ecr describe-image-scan-findings --repository-name myapp --image-id imageTag=v1
aws ecr put-lifecycle-policy --repository-name myapp --lifecycle-policy-text \
  '{"rules":[{"rulePriority":1,"selection":{"tagStatus":"untagged","countType":"sinceImagePushed","countUnit":"days","countNumber":7},"action":{"type":"expire"}}]}'

# ECS
aws ecs list-clusters / list-services --cluster prod
aws ecs describe-services --cluster prod --services api
aws ecs update-service --cluster prod --service api --force-new-deployment
aws ecs describe-tasks --cluster prod --tasks arn:...
aws ecs execute-command --cluster prod --task arn:... --container app --interactive --command "/bin/sh"

# EKS
aws eks list-clusters
aws eks update-kubeconfig --name my-cluster --region us-east-1     # ⭐ configures kubectl
aws eks describe-cluster --name my-cluster --query 'cluster.{Version:version,Status:status,Endpoint:endpoint}'
aws eks list-nodegroups --cluster-name my-cluster
aws eks describe-addon-versions --kubernetes-version 1.30
```

---

## Lambda

```bash
aws lambda list-functions --query 'Functions[].{Name:FunctionName,Runtime:Runtime,Memory:MemorySize,Timeout:Timeout}' --output table
aws lambda get-function --function-name myfn
aws lambda invoke --function-name myfn --payload '{"key":"value"}' \
  --cli-binary-format raw-in-base64-out out.json && cat out.json
aws lambda update-function-code --function-name myfn --zip-file fileb://fn.zip
aws lambda update-function-configuration --function-name myfn --memory-size 512 --timeout 30
aws lambda get-function-concurrency --function-name myfn
aws logs tail /aws/lambda/myfn --follow          # ⭐ live logs
```

---

## CloudWatch

```bash
# Logs
aws logs describe-log-groups --query 'logGroups[].{Name:logGroupName,Retention:retentionInDays,Bytes:storedBytes}' --output table
aws logs tail /aws/lambda/myfn --follow --since 10m           # ⭐ the good one
aws logs tail /ecs/api --filter-pattern "ERROR"
aws logs put-retention-policy --log-group-name /ecs/api --retention-in-days 30   # ⭐ default is FOREVER

# Logs Insights
aws logs start-query \
  --log-group-name /ecs/api \
  --start-time $(date -d '1 hour ago' +%s) --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 50'
aws logs get-query-results --query-id <id>

# Metrics and alarms
aws cloudwatch list-metrics --namespace AWS/EC2
aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0abc --start-time 2026-08-04T00:00:00Z \
  --end-time 2026-08-04T12:00:00Z --period 300 --statistics Average
aws cloudwatch describe-alarms --state-value ALARM              # ⭐ what's firing now
aws cloudwatch put-metric-alarm --alarm-name high-cpu \
  --metric-name CPUUtilization --namespace AWS/EC2 --statistic Average \
  --period 300 --threshold 80 --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 --alarm-actions arn:aws:sns:us-east-1:123:alerts
```

**Logs Insights query patterns:**

```
fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 100
fields @timestamp, status, path | filter status >= 500 | stats count() by path | sort count desc
filter @type = "REPORT" | stats avg(@duration), max(@duration), pct(@duration, 99) by bin(5m)
fields @message | parse @message /duration=(?<dur>\d+)/ | filter dur > 1000
```

---

## Cost Control

```bash
# Month-to-date spend by service
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query 'ResultsByTime[0].Groups[].[Keys[0],Metrics.UnblendedCost.Amount]' --output table

aws ce get-cost-forecast --time-period Start=$(date -u +%Y-%m-%d),End=$(date -u -d '+1 month' +%Y-%m-01) \
  --metric UNBLENDED_COST --granularity MONTHLY

aws budgets describe-budgets --account-id 123456789012
aws ce get-rightsizing-recommendation --service AmazonEC2
```

**Find the waste** — run these monthly:

```bash
aws ec2 describe-volumes --filters "Name=status,Values=available" \
  --query 'Volumes[].{ID:VolumeId,Size:Size,Created:CreateTime}' --output table   # unattached EBS
aws ec2 describe-addresses --query 'Addresses[?AssociationId==null].PublicIp'     # idle Elastic IPs (billed!)
aws ec2 describe-snapshots --owner-ids self \
  --query 'Snapshots[?StartTime<=`2025-08-01`].[SnapshotId,VolumeSize,StartTime]' --output table
aws rds describe-db-instances --query 'DBInstances[?DBInstanceStatus==`stopped`].DBInstanceIdentifier'
aws logs describe-log-groups --query 'logGroups[?!retentionInDays].logGroupName'  # ⭐ never-expiring logs
aws elbv2 describe-load-balancers --query 'LoadBalancers[].LoadBalancerArn'       # cross-check for idle LBs
```

| Common bill surprise | Cause | Fix |
|----------------------|-------|-----|
| NAT Gateway | Hourly + per-GB, one per AZ | VPC endpoints for S3/ECR/DynamoDB |
| CloudWatch Logs | Default retention is **forever** | `put-retention-policy` on every log group |
| Unattached EBS volumes | Terminated instances leave volumes | Audit monthly; set `DeleteOnTermination` |
| Idle Elastic IPs | Charged when **not** attached | Release them |
| Cross-AZ data transfer | Chatty services split across AZs | Co-locate, or use topology-aware routing |
| S3 in STANDARD forever | No lifecycle rules | Add transitions + expiry |
| Oversized instances | Provisioned for peak, running at 5% | Rightsizing recommendations, auto-scaling |
| Forgotten dev/test environments | Nobody owns them | Mandatory `Owner`/`TTL` tags + a scheduled cleanup job |

> 💡 **Set a billing alarm on day one.** `aws budgets create-budget` with a threshold you'd be unhappy to exceed. Free-tier accounts can still generate four-figure bills through a misconfigured NAT or a runaway Lambda loop.

---

## FinOps

```bash
# Spend by tag — only meaningful once tags are ENFORCED at creation
aws ce get-cost-and-usage --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY --metrics UnblendedCost --group-by Type=TAG,Key=service

# ⭐ Untagged spend: drive this number to zero, it's where waste hides
aws ce get-cost-and-usage --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY --metrics UnblendedCost \
  --filter '{"Tags":{"Key":"service","MatchOptions":["ABSENT"]}}'

aws ce get-savings-plans-utilization --time-period Start=2026-07-01,End=2026-08-01
aws ce get-anomaly-monitors                      # set one up on day one
aws budgets describe-budgets --account-id "$ACCT"  # per environment, not per account
```

| Lever | Saves | Watch out |
|-------|------:|-----------|
| Rightsizing | 20–40% | Measure p95, not average, before shrinking |
| Flexible commitments | 30–50% | Commit to the measured floor (~60–80% of baseline), never a forecast |
| Reserved (specific) | 40–60% | Locked to family and region |
| Spot | 70–90% | ⭐ 2-minute eviction notice — CI, batch, dev; never a DB primary |
| Off-hours shutdown (non-prod) | ~75% | 8×5 vs 24×7 for identical work |
| Storage tiering / retention | varies | Log groups with no retention are kept **forever** |

**Unit cost beats total cost.** Track cost per 1,000 requests, per order, or per tenant next to
your golden signals — total spend rising while unit cost falls is growth, not a regression.

---

## Query Patterns

The `--query` flag uses **JMESPath** and runs client-side; `--filters` runs server-side and is faster on large result sets.

```bash
--query 'Reservations[].Instances[].InstanceId'                # flatten nested lists
--query 'Instances[?State.Name==`running`]'                    # filter (backticks for literals)
--query 'Instances[?Tags[?Key==`Env`&&Value==`prod`]]'         # filter on a tag
--query 'Instances[].{ID:InstanceId,Name:Tags[?Key==`Name`]|[0].Value}'   # rename/reshape
--query 'sort_by(Images,&CreationDate)[-1].ImageId'            # newest item
--query 'length(Reservations[].Instances[])'                   # count
--query 'Buckets[].Name' --output text                         # plain list for xargs

# Combine with jq when JMESPath gets awkward
aws ec2 describe-instances | jq -r '.Reservations[].Instances[] | "\(.InstanceId) \(.State.Name)"'

# Pagination — the CLI auto-paginates, but for huge sets:
aws s3api list-objects-v2 --bucket b --max-items 1000 --starting-token "$TOKEN"
aws ec2 describe-instances --no-paginate
```

---

## Cross-Cloud Equivalents

| Concept | AWS | Azure | GCP |
|---------|-----|-------|-----|
| Virtual machine | EC2 | Virtual Machines | Compute Engine |
| Object storage | S3 | Blob Storage | Cloud Storage |
| Block storage | EBS | Managed Disks | Persistent Disk |
| Managed Kubernetes | EKS | AKS | GKE |
| Serverless functions | Lambda | Functions | Cloud Functions / Run |
| Container registry | ECR | ACR | Artifact Registry |
| Virtual network | VPC | VNet | VPC |
| Load balancer | ALB / NLB | Load Balancer / App Gateway | Cloud Load Balancing |
| Managed SQL | RDS / Aurora | Azure SQL / Flexible Server | Cloud SQL / Spanner |
| NoSQL | DynamoDB | Cosmos DB | Firestore / Bigtable |
| Identity | IAM | Entra ID + RBAC | Cloud IAM |
| Secrets | Secrets Manager / SSM | Key Vault | Secret Manager |
| Monitoring | CloudWatch | Monitor | Cloud Monitoring |
| IaC-native | CloudFormation / CDK | ARM / Bicep | Deployment Manager |
| CDN | CloudFront | Front Door / CDN | Cloud CDN |
| DNS | Route 53 | Azure DNS | Cloud DNS |
| Message queue | SQS | Service Bus | Pub/Sub |
| CLI | `aws` | `az` | `gcloud` |

> 💡 The **concepts** transfer completely; only the names and quirks change. Learn one cloud properly and the second takes weeks, not months.

---

<div align="center">

[← Module 09 README](./README.md) · [Resources](./resources.md) · [Labs](./labs/) · [Handbook Quick Reference](../QUICK-REFERENCE.md)

</div>
