# The infrastructure from Project 03, written the way it usually gets written first:
# correct, working, and about twice as expensive as it needs to be — with just enough
# missing tags that nobody can say which team owns what.
#
# You never apply this. The lab analyses its PLAN, so no cloud account is involved.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region

  # ⭐ default_tags is the single highest-leverage line in a FinOps setup: every resource
  # that supports tags inherits these. Note what is MISSING — owner and service. That gap
  # is why the tag gate fails, and why nobody can attribute this environment's cost.
  default_tags {
    tags = {
      env        = var.environment
      managed-by = "terraform"
    }
  }
}

variable "region" {
  type    = string
  default = "eu-west-1"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "azs" {
  type        = list(string)
  default     = ["eu-west-1a", "eu-west-1b"]
  description = "Two AZs. Each one gets its own NAT gateway below — see the cost report."
}

# ─────────────────────────────────────────────────────────────── network
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true

  tags = { Name = "main" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "main" }
}

resource "aws_subnet" "public" {
  count = length(var.azs)

  vpc_id                  = aws_vpc.main.id
  availability_zone       = var.azs[count.index]
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  map_public_ip_on_launch = true

  tags = { Name = "public-${var.azs[count.index]}" }
}

resource "aws_subnet" "private" {
  count = length(var.azs)

  vpc_id            = aws_vpc.main.id
  availability_zone = var.azs[count.index]
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 10)

  tags = { Name = "private-${var.azs[count.index]}" }
}

# ⚠️ One NAT gateway per AZ is the textbook HA answer, and it is also ~£30/month EACH plus
# per-GB. For a dev environment it is usually the largest line on the bill.
resource "aws_eip" "nat" {
  count  = length(var.azs)
  domain = "vpc"

  tags = { Name = "nat-${var.azs[count.index]}" }
}

resource "aws_nat_gateway" "main" {
  count = length(var.azs)

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = { Name = "nat-${var.azs[count.index]}" }
}

resource "aws_route_table" "private" {
  count = length(var.azs)

  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = { Name = "private-${var.azs[count.index]}" }
}

# ─────────────────────────────────────────────────────────────── compute
resource "aws_security_group" "app" {
  name        = "app"
  description = "App instances"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "app" }
}

# ⚠️ t3.large × 2, on-demand, 24×7. Check the p95 CPU before you accept this size, and ask
# whether a non-production environment needs to exist at 3 a.m. on a Sunday.
resource "aws_instance" "app" {
  count = 2

  ami           = "ami-0abcdef1234567890" # placeholder: a data source resolves this for real
  instance_type = "t3.large"
  subnet_id     = aws_subnet.private[count.index].id

  vpc_security_group_ids = [aws_security_group.app.id]

  root_block_device {
    volume_size = 50
    volume_type = "gp2" # ⚠️ gp3 is cheaper per GB AND faster. There is no reason to pick gp2
  }

  tags = { Name = "app-${count.index}" }
}

# An extra data volume that nobody remembers to delete when the instance goes.
resource "aws_ebs_volume" "data" {
  availability_zone = var.azs[0]
  size              = 200
  type              = "gp2"

  tags = { Name = "app-data" }
}

# ─────────────────────────────────────────────────────────────── load balancer
resource "aws_lb" "app" {
  name               = "app"
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.app.id]

  tags = { Name = "app" }
}

resource "aws_lb_target_group" "app" {
  name     = "app"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    path                = "/healthz"
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = { Name = "app" }
}

# ─────────────────────────────────────────────────────────────── database
# ⚠️ Multi-AZ doubles the instance cost. Correct for production; ask whether this
# environment is production before you accept it.
resource "aws_db_instance" "main" {
  identifier     = "app-db"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t3.medium"

  allocated_storage = 100
  storage_type      = "gp2"
  multi_az          = true

  username            = "appuser"
  password            = "CHANGE_ME_use_secrets_manager" # ⚠️ Module 13 §2 — never in code
  skip_final_snapshot = true

  backup_retention_period = 7

  tags = { Name = "app-db" }
}

# ─────────────────────────────────────────────────────────────── logs
# ⚠️ No retention_in_days means CloudWatch keeps these logs FOREVER, at £0.03/GB/month,
# growing every day, until someone finds it years later. This is the cheapest fix on the bill.
resource "aws_cloudwatch_log_group" "app" {
  name = "/aws/app/prod"

  tags = { Name = "app" }
}

output "nat_gateway_count" {
  description = "How many NAT gateways this environment pays for, hourly, forever."
  value       = length(aws_nat_gateway.main)
}
