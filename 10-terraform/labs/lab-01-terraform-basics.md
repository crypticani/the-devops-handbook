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

## ✅ Validation

- [ ] Write a Terraform config with provider, resource, data source, and output
- [ ] Run the init → plan → apply workflow
- [ ] Read and understand plan output symbols (+, ~, -, -/+)
- [ ] Use variables and outputs
- [ ] Modify existing infrastructure and observe in-place updates
- [ ] Destroy all resources cleanly
- [ ] Explain what the state file does and why it matters

---

[← Back to Module README](../README.md)
