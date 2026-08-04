# Module 08: Logging — Lab Code

Two complete centralised-logging stacks, so you can compare them directly.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

---

## Contents

### `lab-01/`

Loki + Promtail + Grafana, with a JSON-logging demo app.

```
lab-01/
├── app/Dockerfile
├── app/app.py
├── app/requirements.txt
├── docker-compose.yml
├── loki/loki-config.yml
└── promtail/promtail-config.yml
```

### `lab-02/`

Elasticsearch + Logstash + Kibana + Filebeat, with the same demo app.

```
lab-02/
├── app/Dockerfile
├── app/app.py
├── app/requirements.txt
├── docker-compose.yml
├── filebeat/filebeat.yml
└── logstash/pipeline/logstash.conf
```

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/08-logging && cd ~/devops-labs/08-logging
cp -r /path/to/the-devops-handbook/08-logging/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 08 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
