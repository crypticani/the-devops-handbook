# Module 09: Cloud Fundamentals — Lab Code

IAM policy documents used by the AWS CLI lab.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

---

## Contents

### `lab-01/`

The EC2 trust policy attached to the lab's instance role.

```
lab-01/
└── trust-policy.json
```

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/09-cloud-fundamentals && cd ~/devops-labs/09-cloud-fundamentals
cp -r /path/to/the-devops-handbook/09-cloud-fundamentals/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 09 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
