#!/usr/bin/env python3
"""Estimate the monthly cost of a Terraform plan, grouped by tag, before you apply it.

The point is not precision — it is a number, at review time, attributable to a team. A
review that says "this adds about £250/month, £66 of which is NAT gateways" changes designs;
a review that says nothing about cost gets you a surprise on the invoice.

    ./cost-estimate.py                                   # the bundled sample plan
    ./cost-estimate.py --plan plan.json --group-by service
    ./cost-estimate.py --requests 5000000                 # also print cost per 1k requests
    ./cost-estimate.py --suggest                          # what to fix, biggest win first

Getting a plan from your own infrastructure:

    terraform plan -out=tfplan && terraform show -json tfplan > plan.json

For numbers you can defend to finance, use Infracost — it carries real price data. This
script exists so the mechanism is not a black box, and so the lab needs no cloud account.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
UNTAGGED = "«untagged»"


def load(path: pathlib.Path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        sys.exit(f"not found: {path}")
    except json.JSONDecodeError as exc:
        sys.exit(f"{path}: not valid JSON ({exc})")


def resources(plan: dict):
    """Every resource in the plan, including inside modules."""

    def walk(module):
        yield from module.get("resources", [])
        for child in module.get("child_modules", []):
            yield from walk(child)

    root = plan.get("planned_values", {}).get("root_module")
    if root is None:
        sys.exit("no planned_values in this file — is it `terraform show -json` output?")
    yield from walk(root)


def monthly_cost(res: dict, p: dict) -> tuple[float, str]:
    """Return (monthly cost, what drove it). Unpriced types return 0 — say so, don't hide it."""
    t, v = res["type"], res.get("values", {})

    if t == "aws_nat_gateway":
        return p["nat_gateway_per_month"], "hourly, whether or not anything uses it"

    if t == "aws_eip":
        return p["public_ipv4_per_month"], "every public IPv4 is charged, attached or not"

    if t == "aws_lb":
        return p["alb_per_month"], "hourly + LCUs not modelled here"

    if t == "aws_instance":
        itype = v.get("instance_type", "")
        cost = p["instance_per_month"].get(itype, 0.0)
        note = f"{itype}, on-demand, 24×7"
        for dev in v.get("root_block_device") or []:
            size = dev.get("volume_size") or 0
            vol = dev.get("volume_type") or "gp2"
            cost += size * p["ebs_per_gb_month"].get(vol, 0.11)
            note += f" + {size}GB {vol} root"
        return cost, note

    if t == "aws_ebs_volume":
        size, vol = v.get("size") or 0, v.get("type") or "gp2"
        return size * p["ebs_per_gb_month"].get(vol, 0.11), f"{size}GB {vol}"

    if t == "aws_db_instance":
        cls = v.get("instance_class", "")
        cost = p["db_instance_per_month"].get(cls, 0.0)
        note = f"{cls}"
        if v.get("multi_az"):
            cost *= 2
            note += ", multi-AZ (×2)"
        size = v.get("allocated_storage") or 0
        stype = v.get("storage_type") or "gp2"
        cost += size * p["rds_storage_per_gb_month"].get(stype, 0.127)
        return cost, note + f" + {size}GB {stype}"

    if t == "aws_cloudwatch_log_group":
        gb = p["cloudwatch_logs_assumed_gb_per_month"]
        cost = gb * p["cloudwatch_logs_storage_per_gb_month"]
        if not v.get("retention_in_days"):
            # Unbounded: the cost is not this month's, it is this month's times forever.
            return cost, f"~{gb}GB/mo, NO RETENTION — grows every month, never shrinks"
        return cost, f"~{gb}GB/mo, {v['retention_in_days']}d retention"

    return 0.0, "not priced by this script"


def group_key(res: dict, tag: str) -> str:
    tags = res.get("values", {}).get("tags_all") or res.get("values", {}).get("tags") or {}
    return tags.get(tag) or UNTAGGED


def suggestions(rows: list[dict], p: dict) -> list[tuple[float, str]]:
    """Concrete, ranked by saving. Each one is a real change to the Terraform, not advice."""
    out = []

    nats = [r for r in rows if r["type"] == "aws_nat_gateway"]
    if len(nats) > 1:
        save = (len(nats) - 1) * p["nat_gateway_per_month"]
        out.append((save, f"{len(nats)} NAT gateways → 1 for non-production "
                          f"(keep one per AZ only where an AZ outage must not stop egress)"))

    # gp2 → gp3, priced on the GIGABYTES only. Taking a share of each resource's total
    # would count instance and database compute as storage, and overstate the win.
    ebs_gb = rds_gb = 0
    for r in rows:
        v = r["values"]
        if r["type"] == "aws_ebs_volume" and (v.get("type") or "gp2") == "gp2":
            ebs_gb += v.get("size") or 0
        if r["type"] == "aws_instance":
            for dev in v.get("root_block_device") or []:
                if (dev.get("volume_type") or "gp2") == "gp2":
                    ebs_gb += dev.get("volume_size") or 0
        if r["type"] == "aws_db_instance" and (v.get("storage_type") or "gp2") == "gp2":
            rds_gb += v.get("allocated_storage") or 0
    if ebs_gb or rds_gb:
        save = (ebs_gb * (p["ebs_per_gb_month"]["gp2"] - p["ebs_per_gb_month"]["gp3"])
                + rds_gb * (p["rds_storage_per_gb_month"]["gp2"] - p["rds_storage_per_gb_month"]["gp3"]))
        out.append((save, f"{ebs_gb + rds_gb}GB of gp2 → gp3: cheaper per GB AND faster. No downside"))

    # Multi-AZ costs exactly one extra instance, so that is the saving — not half the row.
    multiaz_save = sum(
        p["db_instance_per_month"].get(r["values"].get("instance_class", ""), 0.0)
        for r in rows if r["type"] == "aws_db_instance" and r["values"].get("multi_az")
    )
    if multiaz_save:
        out.append((multiaz_save,
                    "RDS multi-AZ → single-AZ for non-production (drops the standby instance)"))

    compute = sum(r["cost"] for r in rows if r["type"] in ("aws_instance", "aws_db_instance"))
    if compute:
        out.append((compute * (1 - p["off_hours_factor"]),
                    "Non-production off outside business hours: 8×5 is ~24% of 24×7 for identical work"))
        out.append((compute * p["savings_plan_discount"],
                    "OR a Savings Plan on the MEASURED steady-state floor (~60-80% of baseline, "
                    "never a forecast) — you cannot claim both this and the line above"))

    forever = [r for r in rows if "NO RETENTION" in r["note"]]
    if forever:
        out.append((0.0, f"{len(forever)} log group(s) with no retention — set it today. "
                         "Today's cost is small; the integral is not"))

    return sorted(out, key=lambda x: -x[0])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", type=pathlib.Path, default=HERE / "sample-plan.json")
    ap.add_argument("--prices", type=pathlib.Path, default=HERE / "prices.json")
    ap.add_argument("--group-by", default="service", help="tag to attribute cost to")
    ap.add_argument("--requests", type=float, default=0.0,
                    help="monthly requests, to compute cost per 1,000")
    ap.add_argument("--suggest", action="store_true", help="ranked optimisations")
    args = ap.parse_args()

    prices = load(args.prices)
    plan = load(args.plan)
    cur = prices.get("currency", "GBP")

    rows = []
    for res in resources(plan):
        cost, note = monthly_cost(res, prices)
        rows.append({"addr": res.get("address", res["type"]), "type": res["type"],
                     "cost": cost, "note": note, "group": group_key(res, args.group_by),
                     "values": res.get("values", {})})

    total = sum(r["cost"] for r in rows)
    priced = [r for r in rows if r["cost"] > 0]

    print(f"\n  MONTHLY COST ESTIMATE ({cur}, illustrative prices — see prices.json)\n")
    print(f"  {'resource':<44} {'cost':>9}   driver")
    print(f"  {'-' * 44} {'-' * 9}   {'-' * 40}")
    for r in sorted(priced, key=lambda r: -r["cost"]):
        print(f"  {r['addr']:<44} {r['cost']:>9.2f}   {r['note']}")

    unpriced = len(rows) - len(priced)
    print(f"\n  {'TOTAL':<44} {total:>9.2f}   ({unpriced} resources not priced by this script)")
    print(f"  {'per day':<44} {total / 30:>9.2f}")

    # ── Allocation. Cost you cannot attribute is cost nobody will act on.
    by_group: dict[str, float] = {}
    for r in rows:
        by_group[r["group"]] = by_group.get(r["group"], 0.0) + r["cost"]

    print(f"\n  BY TAG '{args.group_by}'\n")
    for g, c in sorted(by_group.items(), key=lambda kv: -kv[1]):
        share = (c / total * 100) if total else 0
        flag = "  ⬅ unattributable" if g == UNTAGGED and c > 0 else ""
        print(f"  {g:<44} {c:>9.2f}  {share:5.1f}%{flag}")

    if by_group.get(UNTAGGED, 0) > 0:
        pct = by_group[UNTAGGED] / total * 100
        print(f"\n  ⚠️  {pct:.0f}% of spend has no '{args.group_by}' tag. Below ~90% coverage,"
              f"\n      every cost report you produce is fiction. Run ./tag-gate.py")

    if args.requests:
        per_k = total / (args.requests / 1000)
        print(f"\n  UNIT COST\n\n  {args.requests:,.0f} requests/month → "
              f"{cur} {per_k:.4f} per 1,000 requests")
        print("  ⭐ This is the number to trend. Total spend rising with unit cost FALLING is\n"
              "     growth; flat spend with unit cost rising is a regression you'd never see.")

    if args.suggest:
        print("\n  OPTIMISATIONS, BIGGEST WIN FIRST\n")
        for save, text in suggestions(rows, prices):
            label = f"~{save:>8.2f}/mo" if save else "        —   "
            print(f"  {label}  {text}")
        print("\n  Rightsizing comes AFTER measurement: check p95 CPU and memory over a\n"
              "  fortnight before shrinking anything.")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
