# Lab 01: AWS Fundamentals — EC2, VPC, S3, and IAM

## 🎯 Objective

Get hands-on with the four foundational AWS services. You'll launch an EC2 instance inside a custom VPC, configure security groups and IAM, and work with S3 — the building blocks of every cloud deployment.

---

## 📋 Prerequisites

- An AWS account (free tier eligible)
- AWS CLI installed and configured (`aws configure`)
- SSH client (built into Linux/macOS, use PuTTY on Windows)
- Completed Module 02 (Networking basics)

> ⚠️ **Cost Warning:** All resources in this lab are free-tier eligible. Always clean up resources when done to avoid charges.

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Commands you ran and the important output you used for validation
- Any files, scripts, configs, manifests, or workflows you created
- A short failure note describing one thing that broke, how you diagnosed it, and how you fixed it
- Cleanup commands or confirmation that no long-running resources remain

Treat the validation section as the minimum proof that the lab worked.

---

## 🔬 Exercise 1: Create a VPC with Public and Private Subnets

### Step 1: Create the VPC

```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=devops-lab-vpc}]' \
  --query 'Vpc.VpcId' --output text)

echo "VPC created: $VPC_ID"

# Enable DNS hostnames
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames '{"Value": true}'
```

### Step 2: Create Subnets

```bash
# Public subnet (AZ a)
PUB_SUBNET=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-subnet}]' \
  --query 'Subnet.SubnetId' --output text)

# Private subnet (AZ a)
PRIV_SUBNET=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=private-subnet}]' \
  --query 'Subnet.SubnetId' --output text)

# Auto-assign public IPs in public subnet
aws ec2 modify-subnet-attribute --subnet-id $PUB_SUBNET --map-public-ip-on-launch

echo "Public subnet: $PUB_SUBNET"
echo "Private subnet: $PRIV_SUBNET"
```

### Step 3: Create Internet Gateway

```bash
# Create and attach Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=devops-lab-igw}]' \
  --query 'InternetGateway.InternetGatewayId' --output text)

aws ec2 attach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID

# Create route table for public subnet
PUB_RT=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=public-rt}]' \
  --query 'RouteTable.RouteTableId' --output text)

# Add route to internet
aws ec2 create-route --route-table-id $PUB_RT --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID

# Associate public subnet with route table
aws ec2 associate-route-table --route-table-id $PUB_RT --subnet-id $PUB_SUBNET
```

**✅ Checkpoint:** You have a VPC with a public subnet (internet access) and a private subnet (no internet). Verify in the AWS Console: VPC → Your VPCs.

---

## 🔬 Exercise 2: Launch an EC2 Instance

### Step 1: Create a Security Group

```bash
# Create security group
SG_ID=$(aws ec2 create-security-group \
  --group-name devops-lab-sg \
  --description "Allow SSH and HTTP" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

# Allow SSH (port 22) from your IP
MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID --protocol tcp --port 22 --cidr ${MY_IP}/32

# Allow HTTP (port 80) from anywhere
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0

echo "Security Group: $SG_ID"
```

### Step 2: Create a Key Pair

```bash
aws ec2 create-key-pair \
  --key-name devops-lab-key \
  --query 'KeyMaterial' --output text > devops-lab-key.pem

chmod 400 devops-lab-key.pem
```

### Step 3: Launch the Instance

```bash
# Find latest Amazon Linux 2023 AMI
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-2023*-x86_64" "Name=state,Values=available" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' --output text)

# Launch instance
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t2.micro \
  --key-name devops-lab-key \
  --security-group-ids $SG_ID \
  --subnet-id $PUB_SUBNET \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=devops-lab-web}]' \
  --query 'Instances[0].InstanceId' --output text)

echo "Instance launched: $INSTANCE_ID"

# Wait for it to be running
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo "Public IP: $PUBLIC_IP"
```

### Step 4: SSH and Deploy a Web Page

```bash
# SSH into the instance
ssh -i devops-lab-key.pem ec2-user@$PUBLIC_IP

# On the instance, install and start a web server
sudo dnf install -y httpd
echo "<h1>Hello from AWS EC2!</h1><p>Instance: $(hostname)</p>" | sudo tee /var/www/html/index.html
sudo systemctl start httpd
sudo systemctl enable httpd
exit
```

Open `http://<PUBLIC_IP>` in your browser — you should see your web page!

**✅ Checkpoint:** EC2 instance running with a web server accessible from the internet.

---

## 🔬 Exercise 3: Work with S3

```bash
# Create a bucket (name must be globally unique)
BUCKET_NAME="devops-lab-$(date +%s)"
aws s3 mb s3://$BUCKET_NAME

# Upload a file
echo "Hello from S3!" > hello.txt
aws s3 cp hello.txt s3://$BUCKET_NAME/

# List bucket contents
aws s3 ls s3://$BUCKET_NAME/

# Download the file
aws s3 cp s3://$BUCKET_NAME/hello.txt downloaded.txt
cat downloaded.txt

# Enable versioning
aws s3api put-bucket-versioning --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled

# Upload a new version
echo "Updated content" > hello.txt
aws s3 cp hello.txt s3://$BUCKET_NAME/

# List versions
aws s3api list-object-versions --bucket $BUCKET_NAME --prefix hello.txt
```

**✅ Checkpoint:** You created an S3 bucket, uploaded/downloaded files, and enabled versioning.

---

## 🔬 Exercise 4: Create an IAM Role for EC2

```bash
# Create a trust policy (allows EC2 to assume this role)
cat > trust-policy.json << 'POLICY'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "ec2.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
POLICY

# Create the role
aws iam create-role \
  --role-name devops-lab-ec2-role \
  --assume-role-policy-document file://trust-policy.json

# Attach S3 read-only policy
aws iam attach-role-policy \
  --role-name devops-lab-ec2-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Create instance profile and add role
aws iam create-instance-profile --instance-profile-name devops-lab-profile
aws iam add-role-to-instance-profile \
  --instance-profile-name devops-lab-profile \
  --role-name devops-lab-ec2-role

# Attach to your EC2 instance
aws ec2 associate-iam-instance-profile \
  --instance-id $INSTANCE_ID \
  --iam-instance-profile Name=devops-lab-profile
```

Now SSH into the instance and verify:

```bash
ssh -i devops-lab-key.pem ec2-user@$PUBLIC_IP

# This should work (role has S3 read access)
aws s3 ls

# This should FAIL (role is read-only)
aws s3 mb s3://test-bucket-should-fail
```

**✅ Checkpoint:** EC2 instance can read S3 using an IAM role — no access keys needed!

---

## 🧹 Cleanup (IMPORTANT — avoid charges!)

```bash
# Terminate EC2 instance
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
aws ec2 wait instance-terminated --instance-ids $INSTANCE_ID

# Delete S3 bucket
aws s3 rb s3://$BUCKET_NAME --force

# Remove IAM role
aws iam remove-role-from-instance-profile --instance-profile-name devops-lab-profile --role-name devops-lab-ec2-role
aws iam delete-instance-profile --instance-profile-name devops-lab-profile
aws iam detach-role-policy --role-name devops-lab-ec2-role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
aws iam delete-role --role-name devops-lab-ec2-role

# Delete VPC resources
aws ec2 delete-key-pair --key-name devops-lab-key
aws ec2 detach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID
aws ec2 delete-internet-gateway --internet-gateway-id $IGW_ID
aws ec2 delete-subnet --subnet-id $PUB_SUBNET
aws ec2 delete-subnet --subnet-id $PRIV_SUBNET
aws ec2 delete-security-group --group-id $SG_ID
aws ec2 delete-route-table --route-table-id $PUB_RT
aws ec2 delete-vpc --vpc-id $VPC_ID

# Clean up local files
rm -f devops-lab-key.pem hello.txt downloaded.txt trust-policy.json

echo "All resources cleaned up!"
```

---

## 🧨 Break It: Four Cloud Failures (and the Bill That Follows)

Do these **before** the cleanup step above, then clean up. Every scenario here is a real incident pattern — three of them cost money and one of them is how accounts get compromised.

> ⚠️ Run `aws sts get-caller-identity` before every command in this section. Confirm you are in your **lab account**, not production.

### Scenario 1: The Instance in the Private Subnet That Can't Reach Anything

**Break it:**

```bash
aws sts get-caller-identity          # ⭐ right account?

# Launch an instance in the PRIVATE subnet
PRIV_INSTANCE=$(aws ec2 run-instances \
  --image-id "$AMI_ID" --instance-type t3.micro \
  --subnet-id "$PRIV_SUBNET" --security-group-ids "$SG_ID" \
  --iam-instance-profile Name=devops-lab-profile \
  --user-data '#!/bin/bash
yum install -y httpd && systemctl enable --now httpd' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=private-test}]' \
  --query 'Instances[0].InstanceId' --output text)
echo "launched: $PRIV_INSTANCE"

aws ec2 wait instance-running --instance-ids "$PRIV_INSTANCE"
aws ssm start-session --target "$PRIV_INSTANCE" 2>&1 | head -3
```

**Symptom:** Session Manager can't connect, and even if you reach the box some other way, `yum install` in the user-data hung and timed out. The instance is running and healthy by every AWS metric, and completely useless.

**Investigate — work the path outward:**

```bash
# 1. Does the subnet have a route to anywhere?
aws ec2 describe-route-tables \
  --filters "Name=association.subnet-id,Values=$PRIV_SUBNET" \
  --query 'RouteTables[].Routes[].{Dest:DestinationCidrBlock,GW:GatewayId,NAT:NatGatewayId}' --output table
# ⭐ Only 10.0.0.0/16 → local. No 0.0.0.0/0 anywhere.

# 2. Is there a NAT Gateway at all?
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=$VPC_ID" \
  --query 'NatGateways[].{ID:NatGatewayId,State:State}' --output table
# Empty.

# 3. Are there VPC endpoints (the cheap alternative)?
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'VpcEndpoints[].ServiceName' --output table
```

**Root cause:** "Private subnet" means exactly one thing: **no route to an Internet Gateway**. Nothing else is implied. Without either a NAT Gateway or VPC endpoints, the instance cannot reach yum repos, the SSM service, S3, or anything else outside the VPC.

**Fix — two options, and the cost difference is large:**

```bash
# Option A: NAT Gateway — works for all outbound traffic
#   💸 ~$0.045/hour (~$32/month) PER GATEWAY, plus ~$0.045 per GB processed.
#   Production HA needs one per AZ. That's ~$100/month before a byte moves.
EIP=$(aws ec2 allocate-address --domain vpc --query AllocationId --output text)
NAT=$(aws ec2 create-nat-gateway --subnet-id "$PUB_SUBNET" --allocation-id "$EIP" \
  --query 'NatGateway.NatGatewayId' --output text)
aws ec2 wait nat-gateway-available --nat-gateway-ids "$NAT"
PRIV_RT=$(aws ec2 create-route-table --vpc-id "$VPC_ID" --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route --route-table-id "$PRIV_RT" --destination-cidr-block 0.0.0.0/0 --nat-gateway-id "$NAT"
aws ec2 associate-route-table --route-table-id "$PRIV_RT" --subnet-id "$PRIV_SUBNET"

# Option B: VPC endpoints — ⭐ free for S3/DynamoDB (Gateway type), and
#   traffic never leaves the AWS network. Use these even when you have a NAT.
aws ec2 create-vpc-endpoint --vpc-id "$VPC_ID" \
  --service-name "com.amazonaws.${AWS_REGION:-us-east-1}.s3" \
  --route-table-ids "$PRIV_RT"
```

```bash
# ⚠️ NAT Gateways bill per hour whether you use them or not. Delete it now.
aws ec2 delete-nat-gateway --nat-gateway-id "$NAT" 2>/dev/null
aws ec2 terminate-instances --instance-ids "$PRIV_INSTANCE" >/dev/null
```

---

### Scenario 2: The Security Group Open to the World

**Break it:**

```bash
# The "I'll just open it temporarily to debug" rule
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" \
  --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" \
  --protocol tcp --port 3306 --cidr 0.0.0.0/0
```

**Symptom:** Nothing. It works, you carry on, and it stays open for eight months. On a public IP, SSH brute-force traffic starts within **minutes** — internet-wide scanners find new listeners almost immediately.

**Investigate:**

```bash
# ⭐ The audit query. Run this on a schedule, in every account.
aws ec2 describe-security-groups --query \
 'SecurityGroups[?IpPermissions[?contains(IpRanges[].CidrIp, `0.0.0.0/0`)]].{ID:GroupId,Name:GroupName,VPC:VpcId}' \
 --output table

# Which ports specifically?
aws ec2 describe-security-groups --group-ids "$SG_ID" --query \
 'SecurityGroups[].IpPermissions[?contains(IpRanges[].CidrIp, `0.0.0.0/0`)].{From:FromPort,To:ToPort,Proto:IpProtocol}' \
 --output table

# On the instance, watch it happen:
aws ssm start-session --target "$INSTANCE_ID"
#   sudo grep 'Failed password' /var/log/secure | wc -l
#   sudo lastb | head
```

**Root cause:** Security groups are allow-only and default-deny, which makes them feel safe — so people open them "temporarily" and never close them. There is no expiry mechanism and no alert.

**Fix:**

```bash
aws ec2 revoke-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 revoke-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 3306 --cidr 0.0.0.0/0

# ⭐ Reference another SECURITY GROUP, not a CIDR. Self-documenting and it
#    survives IP changes: "the database accepts connections from the app tier".
aws ec2 authorize-security-group-ingress --group-id "$DB_SG" \
  --protocol tcp --port 3306 --source-group "$APP_SG"

# And stop using SSH from the internet entirely — Session Manager needs no open port
aws ssm start-session --target "$INSTANCE_ID"
```

| Instead of | Do this |
|------------|---------|
| Port 22 open to `0.0.0.0/0` | SSM Session Manager — **no inbound port at all** |
| Database port open to the world | `--source-group` referencing the app tier's SG |
| "Temporarily" opening a port | A time-boxed change with a calendar reminder, or an automated revoke |
| Discovering it in an audit months later | AWS Config rule + Security Hub finding + a scheduled CLI audit |

---

### Scenario 3: The Public S3 Bucket

**Break it:**

```bash
# Disable the guard rails, then "just make this one object public"
aws s3api put-public-access-block --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
  "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

aws s3api put-bucket-policy --bucket "$BUCKET_NAME" --policy "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [{
    \"Effect\": \"Allow\", \"Principal\": \"*\",
    \"Action\": \"s3:GetObject\",
    \"Resource\": \"arn:aws:s3:::$BUCKET_NAME/*\"
  }]
}"

echo "internal-report" > secret.txt
aws s3 cp secret.txt "s3://$BUCKET_NAME/"

# Now fetch it with NO credentials at all
curl -s "https://$BUCKET_NAME.s3.amazonaws.com/secret.txt"
```

**Symptom:** The file comes back. Anyone on the internet who can guess or discover the bucket name can read **every object in it** — the policy is `/*`, not one file. Bucket names are guessable and there are search engines dedicated to finding open buckets.

**Investigate:**

```bash
aws s3api get-public-access-block --bucket "$BUCKET_NAME" 2>&1
aws s3api get-bucket-policy --bucket "$BUCKET_NAME" --query Policy --output text | jq
aws s3api get-bucket-policy-status --bucket "$BUCKET_NAME"     # ⭐ "IsPublic": true

# Account-wide audit
for b in $(aws s3api list-buckets --query 'Buckets[].Name' --output text); do
  status=$(aws s3api get-bucket-policy-status --bucket "$b" \
           --query PolicyStatus.IsPublic --output text 2>/dev/null || echo "n/a")
  block=$(aws s3api get-public-access-block --bucket "$b" \
          --query 'PublicAccessBlockConfiguration.BlockPublicPolicy' --output text 2>/dev/null || echo "NONE")
  printf '%-45s public=%-5s block=%s\n' "$b" "$status" "$block"
done
```

**Root cause:** Three independent mechanisms can make a bucket public — ACLs, bucket policies, and account settings — and disabling Block Public Access removes the safety net that would have stopped all of them.

**Fix:**

```bash
aws s3api delete-bucket-policy --bucket "$BUCKET_NAME"
aws s3api put-public-access-block --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

curl -s -o /dev/null -w '%{http_code}\n' "https://$BUCKET_NAME.s3.amazonaws.com/secret.txt"   # 403 ✅

# ⭐ Enforce it for the WHOLE ACCOUNT so no individual bucket can opt out
aws s3control put-public-access-block --account-id "$(aws sts get-caller-identity --query Account --output text)" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

To share a single object, use a **presigned URL** — time-limited, scoped to one key:

```bash
aws s3 presign "s3://$BUCKET_NAME/secret.txt" --expires-in 3600
```

---

### Scenario 4: The Resources You Forgot (a.k.a. The Bill)

**Break it:**

```bash
# Allocate an Elastic IP and DON'T attach it
ORPHAN_EIP=$(aws ec2 allocate-address --domain vpc --query AllocationId --output text)

# Create a volume and DON'T attach it
AZ=$(aws ec2 describe-subnets --subnet-ids "$PUB_SUBNET" --query 'Subnets[0].AvailabilityZone' --output text)
ORPHAN_VOL=$(aws ec2 create-volume --size 20 --volume-type gp3 --availability-zone "$AZ" \
  --query VolumeId --output text)

echo "Both of these are now billing. Neither appears in the EC2 instances list."
```

**Symptom:** Nothing visible. Elastic IPs are billed **specifically when they are *not* attached** (~$3.60/month each). The 20 GB volume bills ~$1.60/month forever. Neither shows up where anyone looks. Multiply by a year and a team, and this is how a lab account quietly costs hundreds.

**Investigate — the monthly waste audit:**

```bash
# ⭐ Unattached Elastic IPs — billed precisely because they're idle
aws ec2 describe-addresses --query 'Addresses[?AssociationId==null].[PublicIp,AllocationId]' --output table

# ⭐ Unattached EBS volumes
aws ec2 describe-volumes --filters "Name=status,Values=available" \
  --query 'Volumes[].{ID:VolumeId,GB:Size,Type:VolumeType,Created:CreateTime}' --output table

# Old snapshots
aws ec2 describe-snapshots --owner-ids self \
  --query 'Snapshots[?StartTime<=`2025-08-01`].[SnapshotId,VolumeSize,StartTime]' --output table

# ⭐ NAT Gateways — the biggest single surprise on most bills
aws ec2 describe-nat-gateways --filter "Name=state,Values=available" \
  --query 'NatGateways[].[NatGatewayId,VpcId]' --output table

# Load balancers with no healthy targets
aws elbv2 describe-load-balancers --query 'LoadBalancers[].[LoadBalancerName,State.Code]' --output table

# ⭐ CloudWatch log groups with NO retention — they keep data FOREVER
aws logs describe-log-groups --query 'logGroups[?!retentionInDays].[logGroupName,storedBytes]' --output table

# Month-to-date spend by service
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query 'ResultsByTime[0].Groups[?Metrics.UnblendedCost.Amount>`0.01`].[Keys[0],Metrics.UnblendedCost.Amount]' \
  --output table
```

**Fix:**

```bash
aws ec2 release-address --allocation-id "$ORPHAN_EIP"
aws ec2 delete-volume --volume-id "$ORPHAN_VOL"
```

**Prevention — set this up on day one, not after the first surprise bill:**

```bash
# Billing alarm
aws budgets create-budget --account-id "$(aws sts get-caller-identity --query Account --output text)" \
  --budget '{"BudgetName":"monthly-cap","BudgetLimit":{"Amount":"20","Unit":"USD"},
             "TimeUnit":"MONTHLY","BudgetType":"COST"}' \
  --notifications-with-subscribers '[{
    "Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN",
                    "Threshold":80,"ThresholdType":"PERCENTAGE"},
    "Subscribers":[{"SubscriptionType":"EMAIL","Address":"you@example.com"}]}]'
```

| Habit | Why |
|-------|-----|
| Tag everything with `Owner` and `TTL` | Makes an automated sweeper possible |
| `DeleteOnTermination=true` on every volume | Terminated instances stop leaving orphans |
| Retention on **every** CloudWatch log group | The default is forever |
| Terraform for lab work | `terraform destroy` is a complete, verifiable teardown |
| Run the waste audit monthly | Ten minutes; usually finds something |

> ⭐ **Why IaC matters more in the cloud than anywhere else**: the cleanup script at the top of this lab has ~15 steps in a strict dependency order, and missing one costs money silently forever. `terraform destroy` does the same job, in the right order, with a plan you can read first. That's the real argument for Module 10.

---

### Now Run the Cleanup

Go back to the [Cleanup section](#-cleanup-important--avoid-charges) above and run it in full, then **verify**:

```bash
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].InstanceId' --output text
aws ec2 describe-addresses --query 'Addresses[].PublicIp' --output text
aws ec2 describe-volumes --filters "Name=status,Values=available" --query 'Volumes[].VolumeId' --output text
aws ec2 describe-nat-gateways --filter "Name=state,Values=available" --query 'NatGateways[].NatGatewayId' --output text
aws s3 ls | grep devops-lab
# All of these should return NOTHING.
```

**Write this up** in `failure-notes.md`, and include the cost of each mistake — a per-month figure makes the lesson stick far better than "this is bad practice".

---

## ✅ Validation

- [ ] Create a VPC with public and private subnets using AWS CLI
- [ ] Launch an EC2 instance and deploy a web server
- [ ] Configure security groups to allow only necessary traffic
- [ ] Create an S3 bucket, upload files, and enable versioning
- [ ] Create an IAM role and attach it to EC2 (no access keys!)
- [ ] Verify least-privilege access (read works, write fails)
- [ ] Clean up all resources to avoid charges
- [ ] Explain the difference between public and private subnets


## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- AWS CLI commands you used with output summaries
- VPC and subnet architecture diagram or notes
- IAM role policy document you created
- Cleanup confirmation showing all resources terminated

---

[← Back to Module README](../README.md)
