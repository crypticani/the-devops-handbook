# Module 05: Containers Docker — Lab Code

A containerised Flask app, its Dockerfile, and a Compose stack.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

---

## Contents

### `lab-01/`

Flask app, Dockerfile, .dockerignore, Nginx config, and a two-service Compose stack.

```
lab-01/
├── .dockerignore
├── Dockerfile
├── app.py
├── docker-compose.yml
└── nginx.conf
```

### `lab-02/`

A Go service with single-stage and multi-stage Dockerfiles for size comparison.

```
lab-02/
├── Dockerfile.multi
├── Dockerfile.single
├── go.mod
└── main.go
```

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/05-containers-docker && cd ~/devops-labs/05-containers-docker
cp -r /path/to/the-devops-handbook/05-containers-docker/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 05 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
