# Contributing to The DevOps Handbook

Thank you for your interest in contributing! This project aims to be the most comprehensive, practical DevOps learning resource available.

## How to Contribute

### 1. Reporting Issues

- Use GitHub Issues for bugs, typos, or outdated content
- Include the module name and file path
- For labs, include your OS and tool versions

### 2. Adding Content

#### New Labs
- Follow the existing lab format (Objective → Prerequisites → Steps → **Break It** → Validation → Cleanup)
- Include expected output for every command
- **Every lab needs a `## 🧨 Break It` section.** Structure each scenario as **Break it → Symptom → Investigate → Root cause → Fix**, with the real commands at each step. A scenario that only says "try breaking it" doesn't count
  - Prefer failures that are **silent** — the ones that produce green output while something is wrong teach far more than an obvious crash
  - Every scenario must be **safe and reversible**, and must restore state before the next one
  - Finish with a summary table (failure → detection → prevention) and a prompt to write `failure-notes.md`
  - The only exemption is a lab that is *entirely* failure scenarios (see `16-interview-prep/labs/lab-01`); say so explicitly in the objective rather than adding a redundant section
- Test Linux-specific steps on a fresh Debian/Ubuntu system and a RHEL-compatible system when practical; otherwise clearly label the supported family
- Use the rubric in [Practical Learning Guide](./PRACTICAL-LEARNING.md) to include evidence, validation, debugging, and cleanup expectations for completed modules

#### New Projects
- Include a problem statement, setup steps, validation commands, failure scenario, cleanup steps, and tradeoffs
- Keep deliverables reproducible: source code, configs, scripts, manifests, dashboards, and infrastructure code should be committed
- Do not rely on screenshots as the primary proof that a project works
- Include cloud cost notes and destroy/cleanup proof when a project provisions paid resources
- Prioritize projects for Modules 00-13 before adding capstones for Modules 14-16

#### Diagrams
- **Use Mermaid**, not images. Every diagram must be a ` ```mermaid ` fenced block so it renders on GitHub, diffs in review, and stays editable. Do not commit PNG or SVG diagrams
- Pick the diagram type that matches the content:
  - `flowchart` — architecture, decision trees, pipelines
  - `sequenceDiagram` — protocol exchanges, request paths (handshakes, DNS, TLS)
  - `stateDiagram-v2` — lifecycles and state machines (pod phases, alert states, container states)
  - `gitGraph` — branch, merge, and rebase topology
- **Keep ASCII** for content that is genuinely tabular or aligned (CIDR tables, layered box comparisons). Mermaid is for graphs, not for alignment
- Every diagram needs a sentence of setup before it and, where there's a practical consequence, a `> **💡 DevOps Impact**:` note after it. A diagram with no takeaway is decoration
- Quote node labels that contain punctuation: `A["text: with, punctuation"]`. Avoid `"` inside labels — use `<code>` and `<br/>` for formatting
- Validate before you push. Paste into [mermaid.live](https://mermaid.live), or run the parser locally

#### Lab Code
- Every file a lab creates must **also exist as a real file** under `<module>/code/lab-XX/`. The lab still shows it inline — learners type it out the first time — but the copy under `code/` is the one CI actually validates
- **These are maintained by hand, in the same PR.** Change a listing in a lab → change the file. Change the file → change the listing. There is deliberately no auto-generator: a heredoc scraper cannot model `cd`, shell interpolation, or files built up across several steps, and a wrong one silently ships broken code
- Mirror the lab's directory structure. If the lab does `cd environments/dev` before writing `main.tf`, the file belongs at `code/lab-XX/environments/dev/main.tf`
- Deliberately broken artifacts from Break It sections stay **inline only** — don't add them to `code/`
- Anything that needs a real account ID, bucket name, or resource ID ships as `<name>.example` with an obvious placeholder. Never commit a value derived from your own account
- Add a line to `<module>/code/README.md` describing what the new files are for
- Run `./scripts/validate.sh` before you push

#### Cheat Sheets
- Modules 01–13 have a `cheatsheet.md`. Additions should be **commands you have actually run**, not copied from documentation
- Group by task ("Find things", "Debug a crash loop"), not alphabetically
- Mark the handful of genuinely high-value entries with ⭐ — a cheat sheet where everything is highlighted highlights nothing
- Include an **error decoder table** entry when you learn what a confusing message actually means
- Cross-module commands belong in the root [QUICK-REFERENCE.md](./QUICK-REFERENCE.md); module-specific depth belongs in the module's `cheatsheet.md`

#### New Resources
- Add to the relevant module's `resources.md`
- Include: title, URL, type (video/article/docs), and difficulty level
- Prefer free resources; mark paid ones clearly

#### Corrections
- Fix typos, improve clarity, update outdated commands
- Reference the specific line numbers in your PR description

### 3. Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/add-lab-docker-security`)
3. Make your changes
4. Test all commands and labs you've added/modified
5. Submit a PR with a clear description

### 4. Style Guidelines

- Use clean Markdown formatting
- Commands should be in fenced code blocks with language hints
- Include comments in scripts explaining the "why"
- Every concept must connect to real-world usage
- Avoid generic content — be specific and practical
- Diagrams are Mermaid; command references live in `cheatsheet.md` (see above)

### 5. Before You Open a PR

Run the validator. It's the same script CI runs:

```bash
./scripts/validate.sh              # everything it has tools for
./scripts/validate.sh links yaml   # or just the checks you care about
```

Available checks: `links` · `mermaid` · `yaml` · `json` · `python` · `bash` · `compose` · `terraform` · `go` · `labs`

Checks whose tool isn't installed are **skipped, not failed**, so a partial local
environment still gives you useful signal. To run everything locally:

```bash
npm install --no-save mermaid jsdom      # mermaid
pip install pyyaml ruff                   # yaml, python
sudo apt-get install shellcheck           # bash
# terraform, docker, and go you probably already have
```

The `labs` check enforces two rules automatically: every lab has a Break It section,
and every `code/lab-XX/` directory has a matching lab file.

### 6. Content Quality Standards

- **No shallow content**: Every section must provide genuine learning value
- **Practical context**: Theory must be tied to real-world scenarios
- **Debugging focus**: Include common errors and how to fix them
- **Interview relevance**: Note what's frequently asked in interviews

## Code of Conduct

Be respectful, constructive, and focused on helping learners succeed.

## Questions?

Open an issue with the `question` label if you're unsure about anything.
