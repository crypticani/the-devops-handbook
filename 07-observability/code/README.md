# Module 07: Observability — Lab Code

A complete Prometheus + Grafana + Alertmanager stack, an instrumented app, and a two-service
OpenTelemetry tracing pipeline.

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

### `lab-03/`

A two-service OpenTelemetry trace pipeline: apps → collector → Tempo → Grafana. `app/` is one
image run twice — environment variables decide whether it's `checkout` or `payment`, which is
the smallest thing that produces a trace spanning two services.

```
lab-03/
├── app/Dockerfile
├── app/app.py                  # OTel setup, manual spans, trace-id log filter
├── app/requirements.txt        # ⭐ SDK 1.25.0 pairs with instrumentation 0.46b0
├── docker-compose.yml
├── grafana/provisioning/datasources/tempo.yml
├── otel-collector/config.yml   # receivers → processors → exporters (tail_sampling ready)
└── tempo/tempo.yml
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
