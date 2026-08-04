#!/usr/bin/env python3
"""
Regenerate the "🧪 Labs and Projects" table in every module README.

The table is derived from what's actually on disk — lab filenames plus the first
sentence of each lab's Objective — so it can't drift out of sync with the labs.

  python3 scripts/update-lab-index.py            # rewrite the tables
  python3 scripts/update-lab-index.py --check    # fail if any table is stale

The generated block is delimited by the heading and the following `---`, and is
replaced wholesale each run. Everything else in the README is left alone.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEADING = "## 🧪 Labs and Projects"
ANCHOR = "## Practical Checkpoint"

INTRO = (
    "Read the sections above first, then work through these **in order**. "
    "Every lab ends with a 🧨 **Break It** section — those are not optional; "
    "they are where the debugging skill actually comes from."
)


def first_sentence(text: str, limit: int = 150) -> str:
    s = " ".join(text.split())
    s = re.split(r"(?<=[.!?])\s+", s)[0]
    return s[: limit - 1].rsplit(" ", 1)[0] + "…" if len(s) > limit else s


def lab_summary(p: pathlib.Path) -> str:
    m = re.search(r"##\s*🎯\s*Objective\s*\n+(.+?)(?:\n\n|\n>)", p.read_text(), re.S)
    return first_sentence(m.group(1)) if m else ""


def project_summary(p: pathlib.Path) -> str:
    t = p.read_text()
    for head in (r"##\s*Problem Statement", r"##\s*🎯\s*Objective", r"##\s*Overview"):
        m = re.search(head + r"\s*\n+(.+?)(?:\n\n|\n#|\n>)", t, re.S)
        if m:
            return first_sentence(m.group(1))
    return ""


def title(p: pathlib.Path) -> str:
    t = re.sub(r"^#\s*", "", p.read_text().split("\n", 1)[0]).strip()
    t = re.sub(r"^(Lab|Project)\s*\d+:\s*", "", t)
    return t.split(" — ")[0].strip()


def build(mod: pathlib.Path) -> str:
    labs = sorted((mod / "labs").glob("lab-*.md")) if (mod / "labs").is_dir() else []
    projs = sorted((mod / "projects").glob("*.md")) if (mod / "projects").is_dir() else []

    lines = [HEADING, "", INTRO, ""]
    if labs:
        lines += ["| # | Lab | What you'll do |", "|---|-----|----------------|"]
        for i, p in enumerate(labs, 1):
            lines.append(f"| {i} | **[{title(p)}](./labs/{p.name})** | {lab_summary(p)} |")
        lines.append("")
    if projs:
        lines += [f"**Portfolio project{'s' if len(projs) > 1 else ''}:**", ""]
        for p in projs:
            d = project_summary(p)
            lines.append(f"- [{title(p)}](./projects/{p.name})" + (f" — {d}" if d else ""))
        lines.append("")
    if (mod / "code").is_dir():
        lines += ["**Reference code** for every lab: [`code/`](./code/) — real files, validated in CI.", ""]
    lines += ["---", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="fail if any index is stale")
    args = ap.parse_args()

    stale, updated = [], 0

    for mod in sorted(p for p in ROOT.iterdir() if re.match(r"^\d\d-", p.name)):
        readme = mod / "README.md"
        if not readme.exists():
            continue
        if not ((mod / "labs").is_dir() or (mod / "projects").is_dir()):
            continue

        s = readme.read_text()
        anchor = re.search(rf"^{re.escape(ANCHOR)}", s, re.M)
        if not anchor:
            print(f"  ⚠️  {readme.relative_to(ROOT)}: no '{ANCHOR}' anchor, skipping")
            continue

        block = build(mod)
        existing = re.search(
            rf"{re.escape(HEADING)}\n.*?\n---\n(?=\n?{re.escape(ANCHOR)})", s, re.S
        )
        new = (
            s[: existing.start()] + block + s[existing.end():]
            if existing
            else s[: anchor.start()] + block + s[anchor.start():]
        )

        if new == s:
            continue
        if args.check:
            stale.append(str(readme.relative_to(ROOT)))
        else:
            readme.write_text(new)
            updated += 1

    if args.check:
        if stale:
            print(f"❌ {len(stale)} module README(s) have a stale lab index:")
            for p in stale:
                print("  ", p)
            print("\nRun: python3 scripts/update-lab-index.py")
            return 1
        print("✅ every module lab index is current")
        return 0

    print(f"✅ updated {updated} module README(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
