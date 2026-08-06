## What this changes

<!-- One or two sentences. For corrections, reference the file and line numbers. -->

## Type

- [ ] Correction (typo, broken command, wrong output, dead link)
- [ ] New or expanded prose section
- [ ] New lab or project
- [ ] Diagram
- [ ] Cheat sheet / quick reference
- [ ] Repository tooling (`scripts/`, CI)

## Checklist

- [ ] `./scripts/validate.sh` passes — and I read the `skipped:` line, because a skipped check
      is not a passing one ([CONTRIBUTING.md](../CONTRIBUTING.md#5-before-you-open-a-pr) lists
      how to install the missing tools)
- [ ] Every command I added, I actually ran, and the output shown is the output I got
- [ ] Diagrams are Mermaid fenced blocks, each with a sentence of setup and a takeaway
- [ ] No secrets, account IDs, bucket names, or real resource IDs — placeholders ship as
      `<name>.example`

If this PR adds or changes a lab:

- [ ] The lab has a `## 🧨 Break It` section, structured **break → symptom → investigate →
      root cause → fix**, and every scenario restores state afterwards
- [ ] Every file the lab creates also exists under `<module>/code/lab-XX/`, mirroring the lab's
      directory structure, and the inline listing and the real file match
- [ ] `<module>/code/README.md` describes the new files

## Anything a reviewer should know

<!-- Tradeoffs, things you weren't sure about, follow-up work you deliberately left out. -->
