# Module 02: Networking — Lab Code

The backend application sitting behind the Nginx reverse proxy.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

---

## Contents

### `lab-03/`

A minimal Python HTTP service that reports which instance answered — used to prove the proxy is load balancing.

```
lab-03/
└── app.py
```

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/02-networking && cd ~/devops-labs/02-networking
cp -r /path/to/the-devops-handbook/02-networking/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 02 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
