# Module 07: Observability — Lab Code

A complete Prometheus + Grafana + Alertmanager stack, and an instrumented app.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

---

## Contents

### `lab-01/`

Prometheus config, alert rules, Alertmanager routing, and the Compose stack.

```
lab-01/
├── alertmanager/alertmanager.yml
├── docker-compose.yml
├── prometheus/alert_rules.yml
└── prometheus/prometheus.yml
```

### `lab-02/`

A Flask app instrumented with prometheus_client, plus the scrape config and alert rules that watch it.

```
lab-02/
├── app/Dockerfile
├── app/app.py
├── app/requirements.txt
├── docker-compose.yml
├── prometheus/alert_rules.yml
└── prometheus/prometheus.yml
```

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/07-observability && cd ~/devops-labs/07-observability
cp -r /path/to/the-devops-handbook/07-observability/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 07 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
