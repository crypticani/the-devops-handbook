# Module 09: Cloud Fundamentals

> *"The cloud is just someone else's computer — but understanding HOW it works is what separates a DevOps engineer from everyone else."*

---

## 🎯 Why This Module Matters

Every DevOps role requires cloud knowledge. Whether it's AWS, GCP, or Azure, the **concepts are the same** — compute, storage, networking, IAM, and managed services. This module teaches cloud-agnostic fundamentals first, then maps them to AWS (the market leader).

**In real-world DevOps work**, you will:
- Provision virtual machines, networks, and storage in the cloud
- Configure IAM roles, policies, and security groups
- Deploy applications to cloud compute services
- Manage DNS, load balancers, and CDNs
- Understand cloud billing and cost optimization
- Design for high availability and disaster recovery

---

## 📚 Table of Contents

1. [Cloud Computing Fundamentals](#1-cloud-computing-fundamentals)
2. [Cloud Service Models](#2-cloud-service-models)
3. [AWS Core Services](#3-aws-core-services)
4. [Compute — EC2](#4-compute--ec2)
5. [Networking — VPC](#5-networking--vpc)
6. [Storage — S3, EBS, EFS](#6-storage--s3-ebs-efs)
7. [Identity & Access Management (IAM)](#7-identity--access-management-iam)
8. [DNS & Load Balancing](#8-dns--load-balancing)
9. [Managed Services Overview](#9-managed-services-overview)
10. [Cost Management](#10-cost-management)
11. [Common Mistakes and Anti-Patterns](#11-common-mistakes-and-anti-patterns)
12. [Interview Insights](#12-interview-insights)

---

## 1. Cloud Computing Fundamentals

### What Is Cloud Computing?

```
Traditional (On-Premise):
  Buy servers → Rack them → Cable them → Install OS → Wait 6 weeks
  You own and maintain EVERYTHING.

Cloud Computing:
  Click a button → Server ready in 60 seconds → Pay per hour
  Someone else owns the hardware. You rent what you need.
```

### Five Characteristics of Cloud (NIST Definition)

```
1. ON-DEMAND SELF-SERVICE
   Provision resources without human interaction (API/console)

2. BROAD NETWORK ACCESS
   Access from anywhere over the internet

3. RESOURCE POOLING
   Provider's resources shared across many customers (multi-tenant)

4. RAPID ELASTICITY
   Scale up/down instantly based on demand

5. MEASURED SERVICE
   Pay only for what you use (metered billing)
```

### Cloud Providers Market Share

```
┌──────────────────────────────────────────────┐
│  AWS          ████████████████████  ~31%      │
│  Azure        ████████████████     ~25%      │
│  Google Cloud ████████████         ~11%      │
│  Others       ████████████████████████ ~33%  │
└──────────────────────────────────────────────┘
```

> 💡 **Why we focus on AWS:** Largest market share, most job listings, and concepts transfer directly to Azure/GCP.

---

## 2. Cloud Service Models

```
┌────────────────────────────────────────────────────────────┐
│                    YOU MANAGE ↑ / PROVIDER MANAGES ↓        │
├──────────────┬───────────────┬──────────────┬──────────────┤
│  On-Premise  │     IaaS      │    PaaS      │    SaaS      │
├──────────────┼───────────────┼──────────────┼──────────────┤
│ Applications │ Applications  │ Applications │              │
│ Data         │ Data          │ Data         │              │
│ Runtime      │ Runtime       │              │              │
│ Middleware   │ Middleware    │              │    Provider   │
│ OS           │ OS            │   Provider   │    manages   │
│ Virtualize   │               │   manages    │   EVERYTHING │
│ Servers      │   Provider    │   these      │              │
│ Storage      │   manages     │              │              │
│ Networking   │   these       │              │              │
└──────────────┴───────────────┴──────────────┴──────────────┘
```

| Model | What You Get | AWS Example | When to Use |
|-------|-------------|-------------|-------------|
| **IaaS** | Virtual machines, networks, storage | EC2, VPC, S3 | Full control needed, custom apps |
| **PaaS** | Runtime environment, auto-scaling | Elastic Beanstalk, Lambda | Deploy code, don't manage servers |
| **SaaS** | Ready-to-use application | Gmail, Slack, Salesforce | End-user tools |

### Deployment Models

```
PUBLIC CLOUD:   AWS, Azure, GCP — shared infrastructure, pay-per-use
PRIVATE CLOUD:  Your own data center with cloud-like features (OpenStack)
HYBRID CLOUD:   Mix of on-premise + public cloud (most enterprises)
MULTI-CLOUD:    Using multiple providers (AWS + GCP for redundancy)
```

---

## 3. AWS Core Services

### The Services That Matter for DevOps

```
┌─────────────────────────────────────────────────────────┐
│                    AWS SERVICE MAP                        │
├──────────┬──────────────────────────────────────────────┤
│ COMPUTE  │ EC2, Lambda, ECS, EKS                        │
│ STORAGE  │ S3, EBS, EFS                                 │
│ DATABASE │ RDS, DynamoDB, ElastiCache                    │
│ NETWORK  │ VPC, Route 53, CloudFront, ELB               │
│ SECURITY │ IAM, KMS, Security Groups, WAF               │
│ MONITOR  │ CloudWatch, CloudTrail, X-Ray                 │
│ CI/CD    │ CodePipeline, CodeBuild, CodeDeploy           │
│ IaC      │ CloudFormation (→ we use Terraform instead)   │
│ CONTAIN  │ ECR, ECS, EKS (→ covered in K8s module)      │
└──────────┴──────────────────────────────────────────────┘
```

### AWS Global Infrastructure

```
REGIONS (30+):
  Geographically isolated areas (us-east-1, eu-west-1, ap-south-1)
  Each region is fully independent.

AVAILABILITY ZONES (90+):
  2-6 data centers per region, connected by low-latency links.
  Deploy across AZs for high availability.

EDGE LOCATIONS (400+):
  CDN/caching points for CloudFront (content delivery).

  Region: us-east-1 (N. Virginia)
  ├── AZ: us-east-1a
  ├── AZ: us-east-1b
  ├── AZ: us-east-1c
  ├── AZ: us-east-1d
  ├── AZ: us-east-1e
  └── AZ: us-east-1f
```

---

## 4. Compute — EC2

### What is EC2?

**Elastic Compute Cloud** — virtual servers (instances) in the cloud. You choose the OS, size, and configuration.

### Instance Types

```
NAMING: m5.xlarge
         │ │  │
         │ │  └─ Size (nano → metal)
         │ └──── Generation (higher = newer)
         └────── Family (purpose)

FAMILIES:
  t3/t4g  — Burstable (web servers, dev/test)     💰 Cheapest
  m5/m6i  — General purpose (balanced)             ⚖️  Default choice
  c5/c6i  — Compute optimized (CPU-heavy)          🔥 Processing
  r5/r6i  — Memory optimized (databases, caching)  🧠 RAM-heavy
  g5      — GPU (ML, video encoding)                🎮 Specialized
```

### Key Concepts

```
AMI (Amazon Machine Image):
  Template for the instance — OS + preinstalled software.
  Like a Docker image but for entire VMs.
  Common: Amazon Linux 2023, Ubuntu 22.04

Key Pairs:
  SSH access to instances. Create once, use for many instances.
  NEVER lose your private key — no recovery!

Security Groups:
  Virtual firewall for instances. Controls inbound/outbound traffic.
  Default: all inbound BLOCKED, all outbound ALLOWED.

Elastic IP:
  Static public IP that persists across instance stop/start.
  Free when attached to a running instance.
```

### EC2 Pricing Models

| Model | Discount | Commitment | Use Case |
|-------|----------|-----------|----------|
| **On-Demand** | None (full price) | None | Dev/test, unpredictable workloads |
| **Reserved** | Up to 72% | 1 or 3 years | Production, steady-state workloads |
| **Spot** | Up to 90% | None (can be interrupted) | Batch processing, CI/CD runners |
| **Savings Plans** | Up to 72% | $/hour commitment | Flexible reserved pricing |

---

## 5. Networking — VPC

### What is a VPC?

**Virtual Private Cloud** — your own isolated network in AWS. You control the IP ranges, subnets, routing, and security.

### VPC Architecture

```
┌─────────────────── VPC (10.0.0.0/16) ──────────────────┐
│                                                          │
│  ┌──── AZ: us-east-1a ────┐  ┌──── AZ: us-east-1b ────┐│
│  │                         │  │                         ││
│  │  ┌─ Public Subnet ──┐  │  │  ┌─ Public Subnet ──┐  ││
│  │  │  10.0.1.0/24     │  │  │  │  10.0.2.0/24     │  ││
│  │  │  • Web Server    │  │  │  │  • Web Server    │  ││
│  │  │  • NAT Gateway   │  │  │  │  • Load Balancer │  ││
│  │  └──────────────────┘  │  │  └──────────────────┘  ││
│  │                         │  │                         ││
│  │  ┌─ Private Subnet ─┐  │  │  ┌─ Private Subnet ─┐  ││
│  │  │  10.0.3.0/24     │  │  │  │  10.0.4.0/24     │  ││
│  │  │  • App Server    │  │  │  │  • App Server    │  ││
│  │  │  • Database      │  │  │  │  • Database      │  ││
│  │  └──────────────────┘  │  │  └──────────────────┘  ││
│  └─────────────────────────┘  └─────────────────────────┘│
│                                                          │
│  Internet Gateway ──── Route Tables ──── NAT Gateway     │
└──────────────────────────────────────────────────────────┘
```

### Key Components

```
SUBNET:
  A segment of the VPC's IP range. Exists in ONE Availability Zone.
  Public subnet  → has route to Internet Gateway (internet access)
  Private subnet → NO direct internet (uses NAT Gateway for outbound)

INTERNET GATEWAY (IGW):
  Allows resources in PUBLIC subnets to reach the internet.

NAT GATEWAY:
  Allows resources in PRIVATE subnets to reach the internet
  (outbound only — no inbound from internet).

ROUTE TABLE:
  Rules that determine where network traffic goes.
  Public RT:  0.0.0.0/0 → Internet Gateway
  Private RT: 0.0.0.0/0 → NAT Gateway

SECURITY GROUP:
  Stateful firewall at the instance level.
  If you allow inbound, the response is automatically allowed out.

NACL (Network ACL):
  Stateless firewall at the subnet level. Second layer of defense.
```

---

## 6. Storage — S3, EBS, EFS

### Storage Types Compared

| Service | Type | Analogy | Use Case |
|---------|------|---------|----------|
| **S3** | Object storage | Google Drive | Static files, backups, logs, data lakes |
| **EBS** | Block storage | Hard drive | Attached to EC2 — databases, OS disk |
| **EFS** | File storage | NFS share | Shared across multiple EC2 instances |

### S3 (Simple Storage Service)

```
S3 CONCEPTS:
  Bucket:  Top-level container (globally unique name)
  Object:  File + metadata (key-value)
  Key:     Object path (e.g., "images/logo.png")

STORAGE CLASSES (cost vs access speed):
  Standard         → Frequent access         💰💰💰💰
  Standard-IA      → Infrequent access       💰💰💰
  Glacier Instant  → Archive, instant access  💰💰
  Glacier Deep     → Long-term archive        💰

VERSIONING:
  Keep all versions of an object. Protects against accidental deletion.

LIFECYCLE POLICIES:
  Auto-move objects to cheaper storage after N days.
  Example: Move to IA after 30 days, Glacier after 90, delete after 365.
```

---

## 7. Identity & Access Management (IAM)

### The Most Important AWS Service

> 🔐 IAM misconfigurations are the #1 cause of cloud security breaches.

```
IAM ENTITIES:
  USER:   A person (dev, admin) with long-term credentials
  GROUP:  Collection of users (developers, admins, readonly)
  ROLE:   Temporary credentials for services (EC2 → S3 access)
  POLICY: JSON document defining permissions

GOLDEN RULE: LEAST PRIVILEGE
  Grant only the minimum permissions needed. Never use root for daily work.
```

### IAM Policy Anatomy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3ReadOnly",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ]
    }
  ]
}
```

### IAM Best Practices

```
✅ Enable MFA on root account and all human users
✅ Use ROLES for services (not access keys)
✅ Use GROUPS to manage permissions (not individual users)
✅ Use AWS Organizations for multi-account strategy
✅ Rotate access keys regularly
✅ Use IAM Access Analyzer to find unused permissions
❌ NEVER use the root account for daily work
❌ NEVER put access keys in code or git
❌ NEVER use wildcard (*) permissions in production
```

---

## 8. DNS & Load Balancing

### Route 53 (DNS)

```
RECORD TYPES:
  A      → Domain → IPv4 address (example.com → 93.184.216.34)
  AAAA   → Domain → IPv6 address
  CNAME  → Domain → another domain (www.example.com → example.com)
  ALIAS  → Domain → AWS resource (example.com → ALB DNS name)

ROUTING POLICIES:
  Simple       → One destination
  Weighted     → Split traffic (80% v1, 20% v2) — canary deploys!
  Latency      → Route to lowest-latency region
  Failover     → Primary/secondary (disaster recovery)
  Geolocation  → Route by user's location
```

### Elastic Load Balancer (ELB)

```
                   Internet
                      │
               ┌──────▼──────┐
               │ Load Balancer│  ← Distributes traffic
               └──┬───┬───┬──┘
                  │   │   │
            ┌─────▼┐ ┌▼───┐ ┌▼─────┐
            │EC2 a │ │EC2 b│ │EC2 c │
            └──────┘ └─────┘ └──────┘

TYPES:
  ALB (Application LB) → HTTP/HTTPS, path-based routing   ← Most common
  NLB (Network LB)     → TCP/UDP, ultra-low latency
  CLB (Classic LB)     → Legacy, don't use for new projects
```

---

## 9. Managed Services Overview

### Why Managed Services?

```
SELF-MANAGED (EC2 + install MySQL):
  ✅ Full control
  ❌ You handle: patching, backups, replication, failover, scaling

MANAGED (RDS for MySQL):
  ✅ Auto: patching, backups, replication, failover, scaling
  ❌ Less control, slightly higher cost
  ✅ You focus on your application, not database operations
```

| Self-Managed | Managed Service | Benefit |
|-------------|-----------------|---------|
| MySQL on EC2 | RDS | Auto backups, multi-AZ, read replicas |
| Redis on EC2 | ElastiCache | Auto failover, scaling |
| Kubernetes on EC2 | EKS | Managed control plane |
| Docker on EC2 | ECS/Fargate | No server management |
| Jenkins on EC2 | CodePipeline | No CI/CD server to maintain |

> 💡 **DevOps principle:** Use managed services when possible. Your job is to deliver value, not babysit databases.

---

## 10. Cost Management

### Cost Optimization Strategies

```
1. RIGHT-SIZING
   Don't use m5.2xlarge when t3.medium is enough.
   Use CloudWatch metrics to check actual CPU/memory usage.

2. RESERVED / SAVINGS PLANS
   Commit for 1-3 years for steady workloads → up to 72% savings.

3. SPOT INSTANCES
   Use for fault-tolerant workloads → up to 90% savings.
   CI/CD runners, batch jobs, dev environments.

4. CLEANUP
   Delete unused resources: unattached EBS volumes, old snapshots,
   idle EC2 instances, orphaned Elastic IPs.

5. S3 LIFECYCLE POLICIES
   Move old data to cheaper storage classes automatically.

6. AUTO SCALING
   Scale down during low-traffic periods (nights, weekends).
```

### Key Tools

```
AWS Cost Explorer     → Visualize spending trends
AWS Budgets           → Set alerts when spending exceeds threshold
AWS Trusted Advisor   → Recommendations for cost, security, performance
Billing Dashboard     → Monthly cost breakdown by service
```

---

## 11. Common Mistakes and Anti-Patterns

### ❌ Using Root Account for Daily Work

```
BAD:  Login as root → full access to everything → one mistake = disaster
GOOD: Create IAM users with limited permissions, enable MFA on root
```

### ❌ Public S3 Buckets

```
BAD:  S3 bucket with public access → data breach headline
GOOD: Block public access by default, use presigned URLs for temporary access
```

### ❌ Single AZ Deployment

```
BAD:  Everything in one AZ → AZ goes down → total outage
GOOD: Deploy across 2+ AZs with a load balancer
```

### ❌ Hardcoded Credentials

```
BAD:  Access keys in code, environment variables, or config files
GOOD: Use IAM roles for EC2/Lambda/ECS — no credentials to manage
```

---

## 12. Interview Insights

**Q: What's the difference between IaaS, PaaS, and SaaS?**
> IaaS gives you virtual infrastructure (compute, storage, network) — you manage the OS and everything above. PaaS gives you a platform to deploy code — the provider manages the OS and runtime. SaaS is a complete application you use as-is. AWS EC2 is IaaS, Elastic Beanstalk is PaaS, Gmail is SaaS.

**Q: Explain the difference between a public and private subnet.**
> A public subnet has a route to an Internet Gateway, so resources can be reached from the internet (with a public IP). A private subnet has no direct internet route — resources can reach the internet through a NAT Gateway for outbound traffic only. Databases and app servers go in private subnets; load balancers go in public subnets.

**Q: What is the principle of least privilege?**
> Grant only the minimum permissions required to perform a task. An EC2 instance running a web app should have permission to read from S3 and write to CloudWatch — nothing else. This limits the blast radius if credentials are compromised.

**Q: How do you design for high availability in AWS?**
> Deploy across multiple Availability Zones. Use an Application Load Balancer to distribute traffic. Use Auto Scaling Groups to replace failed instances. Use RDS Multi-AZ for database failover. Use S3 for durable storage (99.999999999% durability). Design every component to handle the failure of one AZ.

**Q: What's the difference between Security Groups and NACLs?**
> Security Groups are stateful firewalls at the instance level — if inbound is allowed, outbound response is auto-allowed. NACLs are stateless firewalls at the subnet level — you must explicitly allow both inbound and outbound. Security Groups are your primary tool; NACLs are a second defense layer.

**Q: How do you manage costs in AWS?**
> Right-size instances using CloudWatch metrics. Use Reserved Instances or Savings Plans for steady workloads. Use Spot Instances for fault-tolerant jobs. Set up AWS Budgets for alerts. Clean up unused resources regularly. Use S3 lifecycle policies for storage optimization. Tag everything for cost allocation.

---

## ➡️ What's Next?

With cloud fundamentals understood, you're ready to automate cloud infrastructure using code — Infrastructure as Code with Terraform.

**[Module 10: Terraform →](../10-terraform/)**

---

<div align="center">

**Module 09 Complete** ✅

[← Back to Logging](../08-logging/) | [Next: Terraform →](../10-terraform/)

</div>
