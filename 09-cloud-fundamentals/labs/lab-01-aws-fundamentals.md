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

## ✅ Validation

- [ ] Create a VPC with public and private subnets using AWS CLI
- [ ] Launch an EC2 instance and deploy a web server
- [ ] Configure security groups to allow only necessary traffic
- [ ] Create an S3 bucket, upload files, and enable versioning
- [ ] Create an IAM role and attach it to EC2 (no access keys!)
- [ ] Verify least-privilege access (read works, write fails)
- [ ] Clean up all resources to avoid charges
- [ ] Explain the difference between public and private subnets

---

[← Back to Module README](../README.md)
