# Module 16: Interview Prep — Lab Code

Four pre-broken environments for the mock incident lab.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

> ⚠️ **These environments are intentionally broken, and these files are the STARTING
> state, not the fixed one.** Each fails in a specific, diagnosable way. The fixes live
> in the lab's "Expected Fix" sections — don't read those, or these files, before
> attempting the incident. That's the answer key.
>
> **These environments are intentionally broken.** Each one fails in a specific, diagnosable way. Don't read the Compose files before attempting the incident — that's the answer key.

---

## Contents

### `lab-01/`

Crash-looping container, disk-filling app, misconfigured reverse proxy, and a DNS failure — each with its own Compose file.

```
lab-01/
├── Dockerfile.crash
├── Dockerfile.disk
├── backend.py
├── crash_app.py
├── diskfill_app.py
├── dns_app.py
├── docker-compose-incident1.yml
├── docker-compose-incident2.yml
├── docker-compose-incident3.yml
├── docker-compose-incident4.yml
└── nginx-broken/default.conf
```

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/16-interview-prep && cd ~/devops-labs/16-interview-prep
cp -r /path/to/the-devops-handbook/16-interview-prep/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 16 README](../README.md) · [Labs](../labs/) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
