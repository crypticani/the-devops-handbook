# Module 06: Ci Cd — Lab Code

GitHub Actions workflows, a sample app with tests, and a Jenkins setup.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

---

## Contents

### `lab-01/`

A Python app with pytest tests, a Dockerfile, and two workflows (hello world + full CI).

```
lab-01/
├── .github/workflows/ci.yml
├── .github/workflows/hello.yml
├── Dockerfile
├── requirements.txt
├── src/app.py
└── tests/test_app.py
```

### `lab-02/`

A Compose stack that runs Jenkins locally, plus a declarative Jenkinsfile.

```
lab-02/
├── Jenkinsfile
└── docker-compose.yml
```

### `lab-03/`

The lab-01 pipeline in GitLab's dialect — same application, same stages. Ships only the CI
config, because the point is that **the application does not change**: copy `src/`, `tests/`,
`requirements.txt` and `Dockerfile` from `lab-01/` alongside it.

```
lab-03/
└── .gitlab-ci.yml    # workflow rules · cache keyed on requirements · junit report
                      # · dind build · trivy gate · manual deploy with a secret guard
```

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/06-ci-cd && cd ~/devops-labs/06-ci-cd
cp -r /path/to/the-devops-handbook/06-ci-cd/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 06 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
