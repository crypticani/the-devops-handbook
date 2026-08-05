# Repository Maintenance Scripts

> ### 📖 Learners: you can ignore this directory entirely.
>
> Nothing here is part of the curriculum. These scripts maintain the handbook itself — they
> check that the lab files still work as tool versions change. They are not something to read,
> run, or learn from. **Go back to [the module list](../README.md#-module-hierarchy).**

---

For maintainers and contributors only.

| Script | Purpose |
|--------|---------|
| `validate.sh` | Runs every automated check: internal links, Mermaid diagrams, and every file under `*/code/` (YAML, JSON, Python, Bash, Compose, Terraform, Ansible, Go). Same script CI runs |
| `validate-mermaid.mjs` | Parses every ` ```mermaid ` block and reports syntax errors. Called by `validate.sh`; not run directly |
| `update-lab-index.py` | Regenerates the "🧪 Labs and Projects" table in each module README from what's on disk |

## Usage

```bash
./scripts/validate.sh                    # everything the machine has tools for
./scripts/validate.sh links yaml         # only the checks you care about
python3 scripts/update-lab-index.py      # refresh module lab tables after adding a lab
```

Checks whose tool isn't installed are **skipped, not failed**, so a partial environment still
gives useful signal.

See [CONTRIBUTING.md](../CONTRIBUTING.md#5-before-you-open-a-pr) for the full contributor workflow.
