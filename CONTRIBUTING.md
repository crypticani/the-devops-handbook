# Contributing to The DevOps Handbook

Thank you for your interest in contributing! This project aims to be the most comprehensive, practical DevOps learning resource available.

## How to Contribute

### 1. Reporting Issues

- Use GitHub Issues for bugs, typos, or outdated content
- Include the module name and file path
- For labs, include your OS and tool versions

### 2. Adding Content

#### New Labs
- Follow the existing lab format (Objective → Prerequisites → Steps → Validation → Cleanup)
- Include expected output for every command
- Add at least one "Break It" scenario
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

```bash
# No broken internal links
python3 - <<'EOF'
import os, re, glob
bad = []
for f in glob.glob('**/*.md', recursive=True):
    d = os.path.dirname(f)
    for m in re.finditer(r'\]\((?!https?:|#|mailto:)([^)#]+)', open(f).read()):
        p = os.path.normpath(os.path.join(d, m.group(1).strip()))
        if not os.path.exists(p):
            bad.append((f, m.group(1)))
print("broken links:", len(bad))
[print(" ", *b) for b in bad]
EOF

# Every Mermaid diagram parses (needs node)
npx -y @mermaid-js/mermaid-cli -i yourfile.md -o /dev/null   # or paste into mermaid.live

# Shell snippets are sane
shellcheck path/to/script.sh
```

### 6. Content Quality Standards

- **No shallow content**: Every section must provide genuine learning value
- **Practical context**: Theory must be tied to real-world scenarios
- **Debugging focus**: Include common errors and how to fix them
- **Interview relevance**: Note what's frequently asked in interviews

## Code of Conduct

Be respectful, constructive, and focused on helping learners succeed.

## Questions?

Open an issue with the `question` label if you're unsure about anything.
