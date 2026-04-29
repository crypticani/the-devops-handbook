# Module 13: Security Basics — Resources

---

## 📖 Essential Reading

| Resource | Type | Difficulty | Notes |
|----------|------|------------|-------|
| [OWASP Top 10](https://owasp.org/www-project-top-ten/) | Guide | Beginner | The 10 most critical web application security risks — **must know** |
| [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks) | Guide | Intermediate | Security configuration baselines for Linux, Docker, K8s |
| [AWS Security Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html) | Documentation | Intermediate | IAM and cloud security fundamentals |
| [Kubernetes Security (Liz Rice)](https://www.oreilly.com/library/view/kubernetes-security/9781492039075/) | Book | Intermediate | Container and K8s security deep dive |
| [The DevSecOps Playbook](https://www.oreilly.com/library/view/the-devsecops-playbook/9781098162641/) | Book | Intermediate | Integrating security into DevOps workflows |

---

## 🎥 Videos & Courses

| Resource | Type | Duration | Notes |
|----------|------|----------|-------|
| [DevSecOps Explained (TechWorld with Nana)](https://www.youtube.com/watch?v=nrhxNNH5lt0) | Video | 15 min | Best DevSecOps overview |
| [Container Security (Liz Rice)](https://www.youtube.com/watch?v=lbJK28whV1Q) | Video | 45 min | Container security from first principles |
| [Kubernetes Security Best Practices (CNCF)](https://www.youtube.com/watch?v=oBf5lrmquYI) | Video | 40 min | K8s security from the CNCF |
| [OWASP Top 10 Explained (IBM Technology)](https://www.youtube.com/watch?v=rWHvp7rUka8) | Video | 12 min | Quick overview of top web vulnerabilities |
| [HashiCorp Vault Tutorial](https://www.youtube.com/watch?v=VYfl-DGun_A) | Video | 30 min | Centralized secrets management |

---

## 🧰 Tools & References

| Resource | Type | Notes |
|----------|------|-------|
| [Trivy](https://github.com/aquasecurity/trivy) | Scanner | Container image, filesystem, IaC, and K8s scanning |
| [gitleaks](https://github.com/gitleaks/gitleaks) | Scanner | Detect secrets in git repos |
| [Semgrep](https://semgrep.dev/) | SAST | Static code analysis for security bugs |
| [Checkov](https://github.com/bridgecrewio/checkov) | Scanner | IaC security scanning (Terraform, K8s, Docker) |
| [Snyk](https://snyk.io/) | Platform | Dependency and container vulnerability scanning |
| [HashiCorp Vault](https://www.vaultproject.io/) | Tool | Centralized secrets management |
| [Falco](https://falco.org/) | Tool | Runtime security for K8s (detect anomalous behavior) |
| [kube-bench](https://github.com/aquasecurity/kube-bench) | Tool | Check K8s cluster against CIS benchmark |

---

## 🎯 Recommended Practice Path

1. **Week 1**: Install Trivy and scan your Docker images from previous modules. Install gitleaks as a pre-commit hook. Harden an SSH config. Set up UFW firewall rules. Run `lynis audit system` on a Linux box.
2. **Week 2**: Add security scanning to a GitHub Actions pipeline (secret scan + SAST + image scan). Create a K8s pod with full security context. Write a least-privilege IAM policy. Practice the incident response framework on a mock scenario.
