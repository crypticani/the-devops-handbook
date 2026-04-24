# Module 06: CI/CD — Resources

---

## 📖 Essential Reading

| Resource | Type | Difficulty | Notes |
|----------|------|------------|-------|
| [GitHub Actions Documentation](https://docs.github.com/en/actions) | Documentation | Beginner | Official reference — start with "Understanding GitHub Actions" |
| [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions) | Reference | Intermediate | **Bookmark this** — complete YAML syntax reference |
| [Jenkins Pipeline Syntax](https://www.jenkins.io/doc/book/pipeline/syntax/) | Documentation | Intermediate | Declarative vs Scripted pipeline reference |
| [Continuous Delivery (Jez Humble)](https://www.oreilly.com/library/view/continuous-delivery/9780321670250/) | Book | Advanced | The definitive CI/CD book — foundational reading |
| [The DevOps Handbook (Kim, Humble, et al.)](https://itrevolution.com/product/the-devops-handbook-second-edition/) | Book | Intermediate | Broader DevOps context for CI/CD practices |

---

## 🎥 Videos & Courses

| Resource | Type | Duration | Notes |
|----------|------|----------|-------|
| [GitHub Actions Tutorial (TechWorld with Nana)](https://www.youtube.com/watch?v=R8_veQiYBjI) | Video | 1 hour | Best beginner GitHub Actions walkthrough |
| [GitHub Actions CI/CD (Fireship)](https://www.youtube.com/watch?v=eB0nUzAI7M8) | Video | 8 min | Quick, high-level overview |
| [Jenkins Full Course (TechWorld with Nana)](https://www.youtube.com/watch?v=7KCS70sCoK0) | Video | 3 hours | Comprehensive Jenkins deep dive |
| [CI/CD Explained (IBM Technology)](https://www.youtube.com/watch?v=scEDHsr3APg) | Video | 8 min | Great conceptual overview for interviews |
| [Deployment Strategies Explained](https://www.youtube.com/watch?v=AWVTKBUnoIg) | Video | 15 min | Rolling, blue-green, canary visually explained |

---

## 🧰 Tools & References

| Resource | Type | Notes |
|----------|------|-------|
| [act](https://github.com/nektos/act) | Tool | Run GitHub Actions locally — essential for debugging |
| [GitHub Actions Marketplace](https://github.com/marketplace?type=actions) | Registry | Reusable actions (checkout, setup-python, docker, etc.) |
| [actionlint](https://github.com/rhysd/actionlint) | Linter | Static analysis for GitHub Actions workflow YAML |
| [Jenkins Blue Ocean](https://www.jenkins.io/projects/blueocean/) | Plugin | Modern Jenkins UI with pipeline visualization |
| [Jenkins Pipeline Linter](https://www.jenkins.io/doc/book/pipeline/development/#linter) | Tool | Validate Jenkinsfile syntax before pushing |
| [GitHub Actions Cheat Sheet](https://github.github.io/actions-cheat-sheet/actions-cheat-sheet.html) | Reference | Quick reference for common patterns |

---

## 🎯 Recommended Practice Path

1. **Week 1**: Build a GitHub Actions CI pipeline for a real project (lint → test → build Docker image). Use `act` to test locally.
2. **Week 2**: Add CD with environment protection rules. Set up Jenkins in Docker and replicate the same pipeline in a Jenkinsfile.
3. **Tool**: Install `actionlint` and lint every workflow YAML before pushing.
