# Module 14: System Design Devops — Lab Code

A load-balanced multi-instance stack for the HA lab.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

---

## Contents

### `lab-01/`

A Flask app that reports its own instance ID, an Nginx load balancer config, and the Compose stack that runs three replicas.

```
lab-01/
├── Dockerfile
├── app.py
├── docker-compose.yml
└── nginx/nginx.conf
```

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/14-system-design-devops && cd ~/devops-labs/14-system-design-devops
cp -r /path/to/the-devops-handbook/14-system-design-devops/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 14 README](../README.md) · [Labs](../labs/) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
