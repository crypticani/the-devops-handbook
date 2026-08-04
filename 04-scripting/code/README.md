# Module 04: Scripting — Lab Code

Production-shaped Bash and Python automation scripts.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

---

## Contents

### `lab-01/`

A deployment script with argument parsing, locking, logging and traps; plus a multi-service health monitor.

```
lab-01/
├── deploy.sh
└── health_monitor.sh
```

### `lab-02/`

A concurrent multi-service health checker and an Nginx log analyser.

```
lab-02/
├── health_checker.py
└── log_analyzer.py
```

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/04-scripting && cd ~/devops-labs/04-scripting
cp -r /path/to/the-devops-handbook/04-scripting/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 04 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
