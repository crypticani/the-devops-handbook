# Module 10: Terraform — Lab Code

A minimal but complete Terraform configuration.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

---

## Contents

### `lab-01/`

Provider, resource, data source, variables and outputs — the config used for the init/plan/apply walkthrough.

```
lab-01/
├── main.tf
└── variables.tf
```

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/10-terraform && cd ~/devops-labs/10-terraform
cp -r /path/to/the-devops-handbook/10-terraform/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 10 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
