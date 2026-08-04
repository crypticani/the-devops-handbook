# Module 13: Security Basics — Lab Code

Deliberately vulnerable and hardened artifacts, for scanner practice.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

> ⚠️ **The files in `lab-01/` are intentionally insecure.** They contain hardcoded credentials, a world-open security group, a public S3 bucket, and a privileged root pod. They exist so your scanners have something to find. Never copy them into a real project.

---

## Contents

### `lab-01/`

An insecure and a hardened Dockerfile, a file with planted secrets, and misconfigured Terraform and Kubernetes manifests.

```
lab-01/
├── .gitignore
├── Dockerfile.bad
├── Dockerfile.good
├── config.py
├── main.tf
└── pod.yml
```

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/13-security-basics && cd ~/devops-labs/13-security-basics
cp -r /path/to/the-devops-handbook/13-security-basics/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 13 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
