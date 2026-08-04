# Module 12: Kubernetes — Lab Code

Kubernetes manifests for the deploy/scale/rollback lab.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

---

## Contents

### `lab-01/`

Deployment with probes and resource limits, a Service, and a pod wired to a ConfigMap and Secret.

```
lab-01/
├── configured-pod.yml
├── deployment.yml
└── service.yml
```

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/12-kubernetes && cd ~/devops-labs/12-kubernetes
cp -r /path/to/the-devops-handbook/12-kubernetes/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 12 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
