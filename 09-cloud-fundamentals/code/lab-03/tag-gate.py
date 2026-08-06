#!/usr/bin/env python3
"""Fail a plan that creates resources nobody can be billed for.

Allocation is step one of FinOps, and tags applied "later" are never applied. So this runs in
CI, on the plan, before apply — the only moment when adding a tag is free.

    ./tag-gate.py                                  # the bundled sample plan
    ./tag-gate.py --plan plan.json --require owner env service cost-center
    ./tag-gate.py --quiet && echo "allocatable"

Exit code 1 means untagged resources would be created, which is what makes it a gate rather
than a report.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent

# Resource types that genuinely cannot carry tags. Anything else missing tags is a finding,
# not an exception — keep this list short and justified, or the gate becomes decorative.
UNTAGGABLE = {
    "aws_route_table_association",
    "aws_route",
    "aws_iam_role_policy_attachment",
    "aws_lb_listener_rule",
    "aws_db_subnet_group",
}


def resources(plan: dict):
    def walk(module):
        yield from module.get("resources", [])
        for child in module.get("child_modules", []):
            yield from walk(child)

    root = plan.get("planned_values", {}).get("root_module")
    if root is None:
        sys.exit("no planned_values — is this `terraform show -json` output?")
    yield from walk(root)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", type=pathlib.Path, default=HERE / "sample-plan.json")
    ap.add_argument("--require", nargs="+", default=["owner", "env", "service"],
                    help="tags every taggable resource must carry")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    try:
        plan = json.loads(args.plan.read_text())
    except FileNotFoundError:
        sys.exit(f"not found: {args.plan}")

    findings, checked = [], 0
    for res in resources(plan):
        if res["type"] in UNTAGGABLE:
            continue
        values = res.get("values", {})
        # tags_all includes provider default_tags, which is where these SHOULD come from.
        if "tags_all" not in values and "tags" not in values:
            continue
        checked += 1
        tags = values.get("tags_all") or values.get("tags") or {}
        missing = [t for t in args.require if not tags.get(t)]
        if missing:
            findings.append((res.get("address", res["type"]), missing))

    if not args.quiet:
        print(f"\n  TAG GATE — {checked} taggable resource(s), requiring: {', '.join(args.require)}\n")
        if findings:
            for addr, missing in findings:
                print(f"  ❌ {addr:<48} missing: {', '.join(missing)}")
            covered = checked - len(findings)
            print(f"\n  coverage: {covered}/{checked} ({covered / checked * 100:.0f}%)")
            print("\n  ⭐ Fix it in ONE place — the provider's default_tags — not per resource:\n")
            print("      provider \"aws\" {")
            print("        default_tags {")
            print("          tags = {")
            for t in args.require:
                print(f"            {t:<11}= var.{t.replace('-', '_')}")
            print("          }")
            print("        }")
            print("      }\n")
        else:
            print(f"  ✅ all {checked} taggable resources carry {', '.join(args.require)}\n")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
