# Module 10: Terraform — Resources

---

## 📖 Essential Reading

| Resource | Type | Difficulty | Notes |
|----------|------|------------|-------|
| [Terraform Documentation](https://developer.hashicorp.com/terraform/docs) | Documentation | Beginner | Official docs — start with "Get Started - AWS" |
| [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs) | Reference | Intermediate | **Bookmark this** — every AWS resource reference |
| [Terraform: Up & Running (Yevgeniy Brikman)](https://www.terraformupandrunning.com/) | Book | Intermediate | The best Terraform book — practical and opinionated |
| [Terraform Best Practices](https://www.terraform-best-practices.com/) | Guide | Intermediate | Community-maintained best practices |
| [Terraform Registry](https://registry.terraform.io/) | Registry | All | Pre-built modules and providers |

---

## 🎥 Videos & Courses

| Resource | Type | Duration | Notes |
|----------|------|----------|-------|
| [Terraform Course (TechWorld with Nana)](https://www.youtube.com/watch?v=7xngnjfIlK4) | Video | 2.5 hours | Best beginner Terraform walkthrough |
| [Terraform in 15 Minutes (Fireship)](https://www.youtube.com/watch?v=tomUWcQ0P3k) | Video | 15 min | Fast high-level overview |
| [Terraform State Explained (Spacelift)](https://www.youtube.com/watch?v=V4waklkBC38) | Video | 20 min | Deep dive into state management |
| [Terraform Modules (HashiCorp)](https://developer.hashicorp.com/terraform/tutorials/modules) | Tutorial | 2 hours | Official modules tutorial series |
| [Terraform Associate Cert Prep](https://www.youtube.com/watch?v=V4waklkBC38) | Video | 4 hours | Full certification study guide |

---

## 🧰 Tools & References

| Resource | Type | Notes |
|----------|------|-------|
| [Terraform CLI](https://developer.hashicorp.com/terraform/cli) | Tool | Core CLI for plan/apply/destroy |
| [tflint](https://github.com/terraform-linters/tflint) | Linter | Catch errors and enforce best practices |
| [checkov](https://github.com/bridgecrewio/checkov) | Scanner | Security and compliance scanning for Terraform |
| [infracost](https://github.com/infracost/infracost) | Tool | Cost estimation for Terraform changes |
| [terraform-docs](https://github.com/terraform-docs/terraform-docs) | Tool | Auto-generate documentation for modules |
| [Spacelift](https://spacelift.io/) | Platform | Terraform CI/CD and collaboration (alternative to Terraform Cloud) |
| [LocalStack](https://localstack.cloud/) | Tool | Mock AWS services locally for Terraform testing |

---

## 🎯 Recommended Practice Path

1. **Week 1**: Install Terraform. Create a VPC + EC2 instance on AWS free tier. Learn plan/apply/destroy. Use variables and outputs. Practice `terraform import` on existing resources.
2. **Week 2**: Set up remote state (S3 + DynamoDB). Build a reusable VPC module. Create dev and prod environments using the same module. Add tflint and checkov to your workflow.
