# Module 01: Linux — Lab Code

Log-generation and analysis scripts for the text-processing lab.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

---

## Contents

### `lab-04/`

Generates a realistic Nginx access log and an application error log, then analyses them with grep/awk/sed.

```
lab-04/
├── app_errors.log
└── generate_logs.sh
```

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/01-linux && cd ~/devops-labs/01-linux
cp -r /path/to/the-devops-handbook/01-linux/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 01 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
