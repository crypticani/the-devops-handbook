# Module 14: System Design Devops — Lab Code

A load-balanced multi-instance stack for the HA lab, a RabbitMQ queue you can break in four
ways, and a working golden path with its policy gate.

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
├── nginx/nginx.conf
├── nginx/nginx.least-conn.conf
└── nginx/nginx.weighted.conf
```

### `lab-02/`

Message queues. One image is both producer and consumer (`MODE`), and every failure the lab
induces is an environment variable — no scenario needs a code edit. `watch-queue.sh` prints the
four numbers that tell you whether a queue is healthy.

```
lab-02/
├── app/Dockerfile
├── app/app.py              # quorum queue + DLX; PREFETCH / IDEMPOTENT / DELIVERY_LIMIT toggles
├── app/requirements.txt
├── docker-compose.yml      # rabbitmq + producer + scalable consumer
└── watch-queue.sh          # depth · unacked · consumers · DLQ
```

### `lab-03/`

A golden path: one command scaffolds a service with probes, limits, a pipeline, alerts, and an
owner, and `platform-check.sh` verifies every one of those promises is still there. Generated
services land in `services/`, which is lab output rather than part of the platform.

```
lab-03/
├── new-service.sh          # the paved road — envsubst over templates, deliberately boring
├── platform-check.sh       # the policy gate + the drift report
├── PLATFORM-VERSION        # stamped into every generated service
└── templates/
    ├── alerts.yml.tmpl     # four golden-signal alerts, owner label included
    ├── app.py.tmpl         # /healthz · /readyz · /metrics
    ├── ci.yml.tmpl         # lint → policy gate → build → scan
    ├── deployment.yml.tmpl # both probes, requests AND limits, non-root
    ├── Dockerfile.tmpl
    ├── requirements.txt.tmpl
    └── service.yaml.tmpl   # the catalogue entry: owner, tier, platform version
```

`nginx.conf` is the round-robin config from Exercise 1. The two variants are the
Exercise 4 algorithms — copy one over `nginx.conf` to compare their behaviour.

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
