# Lab 03: FinOps — Reviewing Cost Before You Apply

## 🎯 Objective

Do a cost review the way it should happen: on the plan, before apply, with a number attributable to a team. You'll find out what a working-but-unreviewed environment costs, make it 60% cheaper without removing any capability, and turn both checks into a CI gate.

Then break the four things that make cloud bills surprising — spend nobody can attribute, storage with no retention, a commitment you re-architect away, and an efficiency regression that total spend cannot show you.

> ⭐ **No cloud account, no spend.** The lab analyses a Terraform *plan*, and a plan of the committed config ships with it. If you have an account, regenerate it with one command and the same tools work.

---

## 📋 Prerequisites

- Read [§10 Cost Management and FinOps](../README.md#10-cost-management-and-finops)
- Completed [Lab 02: IAM Least Privilege](./lab-02-iam-least-privilege.md), and Module 10 (you'll read Terraform)
- Python 3.10+. Terraform only if you want to regenerate the plan

```bash
python3 --version
```

---

## 📦 Deliverables and Evidence

- The starting cost estimate, with the top five line items
- Allocation coverage before and after fixing tags — the gate output both times
- Your optimised estimate, and the delta, with a sentence per change saying what capability it cost
- A unit-cost figure (per 1,000 requests), and the same figure after traffic halves
- A CI job that fails on untagged resources
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-03/`](../code/lab-03/).

```bash
cp -r /path/to/the-devops-handbook/09-cloud-fundamentals/code/lab-03/. .
chmod +x cost-estimate.py tag-gate.py
```

```text
infra/main.tf      the environment from Project 03, written the way it gets written first
sample-plan.json   a real `terraform show -json` of that config, so no account is needed
prices.json        illustrative monthly prices, as DATA so you can correct them
cost-estimate.py   plan + prices → monthly cost, grouped by tag, with ranked optimisations
tag-gate.py        fails when resources would be created that nobody can be billed for
```

---

## 🔬 Exercise 1: What Does This Cost, and Whose Is It?

### Step 1: Read the Infrastructure First

```bash
grep -n '⚠️' infra/main.tf
```

Every one of those is a decision that is *correct* in some context and expensive in this one. Before running any tool, write down your guess for the monthly total. Most people are out by a factor of two, in both directions — which is the reason to measure rather than reason.

### Step 2: Estimate

```bash
./cost-estimate.py
```

```text
  MONTHLY COST ESTIMATE (GBP, illustrative prices — see prices.json)

  resource                                          cost   driver
  -------------------------------------------- ---------   ----------------------------------------
  aws_db_instance.main                            126.70   db.t3.medium, multi-AZ (×2) + 100GB gp2
  aws_instance.app[0]                              72.10   t3.large, on-demand, 24×7 + 50GB gp2 root
  aws_instance.app[1]                              72.10   t3.large, on-demand, 24×7 + 50GB gp2 root
  aws_nat_gateway.main[0]                          32.85   hourly, whether or not anything uses it
  aws_nat_gateway.main[1]                          32.85   hourly, whether or not anything uses it
  aws_ebs_volume.data                              22.00   200GB gp2
  aws_lb.app                                       18.40   hourly + LCUs not modelled here
  aws_eip.nat[0]                                    3.60   every public IPv4 is charged, attached or not
  aws_eip.nat[1]                                    3.60   every public IPv4 is charged, attached or not
  aws_cloudwatch_log_group.app                      0.60   ~20GB/mo, NO RETENTION — grows every month, never shrinks

  TOTAL                                           384.80   (10 resources not priced by this script)
  per day                                          12.83
```

£12.83 a day for an environment nobody is using yet. Note the ranking, because it is the lesson: the database and two instances dominate, and **the two NAT gateways cost more than the load balancer** — which surprises almost everyone, and is the line item people leave running for months.

### Step 3: Now Try to Bill It to Someone

```bash
./cost-estimate.py --group-by service | tail -8
```

```text
  BY TAG 'service'

  «untagged»                                      384.80  100.0%  ⬅ unattributable

  ⚠️  100% of spend has no 'service' tag. Below ~90% coverage,
      every cost report you produce is fiction. Run ./tag-gate.py
```

```bash
./tag-gate.py; echo "exit: $?"
```

```text
  TAG GATE — 20 taggable resource(s), requiring: owner, env, service

  ❌ aws_cloudwatch_log_group.app     missing: owner, service
  ❌ aws_db_instance.main             missing: owner, service
  ...
  coverage: 0/20 (0%)
exit: 1
```

Every resource is missing `owner` and `service`. Not because someone was careless — look at `infra/main.tf`: the provider's `default_tags` sets `env` and `managed-by`, and stops there. Two words missing from one block, and the entire environment is unattributable.

### Step 4: Fix Allocation in One Place

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path('infra/main.tf'); t = p.read_text()
t = t.replace('''    tags = {
      env        = var.environment
      managed-by = "terraform"
    }''', '''    tags = {
      env        = var.environment
      managed-by = "terraform"
      owner      = var.owner
      service    = var.service
    }''')
t = t.replace('''variable "environment" {''', '''variable "owner" {
  type        = string
  description = "Team that gets the bill and the page. Required — no default on purpose."
}

variable "service" {
  type        = string
  description = "What this environment is FOR. The unit cost is computed per service."
}

variable "environment" {''')
p.write_text(t)
PY
```

Note there is deliberately **no default** on either variable: a plan cannot be produced without answering "whose is this?". Regenerate the plan if you have Terraform, or use the pre-tagged plan for the rest of the lab:

```bash
cd infra
terraform init -backend=false
terraform plan -out=tfplan -var owner=payments-team -var service=checkout \
  && terraform show -json tfplan > ../plan-tagged.json
cd ..
./tag-gate.py --plan plan-tagged.json
./cost-estimate.py --plan plan-tagged.json --group-by service | tail -5
```

```text
  ✅ all 20 taggable resources carry owner, env, service

  BY TAG 'service'

  checkout                                        384.80  100.0%
```

Same £384.80 — and now it belongs to `payments-team`, on a dashboard they can see. Nothing was optimised, and this is still the most valuable step in the lab: **inform before optimise**, because nobody acts on a number they cannot see.

---

## 🔬 Exercise 2: Make It Cheaper Without Making It Worse

### Step 1: Ask for the Ranked List

```bash
./cost-estimate.py --suggest | tail -12
```

```text
  OPTIMISATIONS, BIGGEST WIN FIRST

  ~  205.88/mo  Non-production off outside business hours: 8×5 is ~24% of 24×7 for identical work
  ~   94.81/mo  OR a Savings Plan on the MEASURED steady-state floor (~60-80% of baseline,
                never a forecast) — you cannot claim both this and the line above
  ~   57.00/mo  RDS multi-AZ → single-AZ for non-production (drops the standby instance)
  ~   32.85/mo  2 NAT gateways → 1 for non-production (keep one per AZ only where an AZ
                outage must not stop egress)
  ~    7.80/mo  400GB of gp2 → gp3: cheaper per GB AND faster. No downside
          —     1 log group(s) with no retention — set it today. Today's cost is small;
                the integral is not
```

Notice the two things that make this a *review* and not a coupon:

- The two largest items are **mutually exclusive** — you cannot both switch a machine off and pay a discount for reserving it 24×7. Any tool that adds them together is lying to you.
- Only one item (`gp2 → gp3`) is free. Every other line trades a capability away, and the review must say which.

### Step 2: Apply the Free One, and Two Judged Ones

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path('infra/main.tf'); t = p.read_text()
t = t.replace('volume_type = "gp2"', 'volume_type = "gp3"')        # free
t = t.replace('type              = "gp2"', 'type              = "gp3"')
t = t.replace('storage_type      = "gp2"', 'storage_type      = "gp3"')
t = t.replace('multi_az          = true', 'multi_az          = var.environment == "prod"')
t = t.replace('resource "aws_cloudwatch_log_group" "app" {\n  name = "/aws/app/prod"',
              'resource "aws_cloudwatch_log_group" "app" {\n  name              = "/aws/app/prod"\n  retention_in_days = 14')
# one NAT for non-production, one per AZ for prod
t = t.replace('resource "aws_nat_gateway" "main" {\n  count = length(var.azs)',
              'resource "aws_nat_gateway" "main" {\n  count = var.environment == "prod" ? length(var.azs) : 1')
t = t.replace('resource "aws_eip" "nat" {\n  count  = length(var.azs)',
              'resource "aws_eip" "nat" {\n  count  = var.environment == "prod" ? length(var.azs) : 1')
p.write_text(t)
PY
cd infra && terraform fmt && terraform validate
terraform plan -out=tfplan -var owner=payments-team -var service=checkout -var environment=dev \
  && terraform show -json tfplan > ../plan-dev.json
cd ..
./cost-estimate.py --plan plan-dev.json | tail -4
```

Route tables reference `aws_nat_gateway.main[count.index]`, so make that resilient to one NAT too:

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path('infra/main.tf'); t = p.read_text()
t = t.replace('nat_gateway_id = aws_nat_gateway.main[count.index].id',
              '# ⭐ one NAT in dev, one per AZ in prod — the route table must handle both\n'
              '    nat_gateway_id = aws_nat_gateway.main[min(count.index, length(aws_nat_gateway.main) - 1)].id')
p.write_text(t)
PY
cd infra && terraform fmt && terraform validate && cd ..
```

Write down, for each change, what capability you gave up:

| Change | Saved | What it costs you |
|--------|------:|-------------------|
| gp2 → gp3 | ~£8 | Nothing. This is strictly better |
| Multi-AZ only in prod | ~£57 | A dev database failure now means downtime and a restore |
| One NAT outside prod | ~£33 + £3.60 | An AZ failure takes dev's egress with it |
| 14-day log retention | small now | You cannot investigate a dev incident older than a fortnight |
| Off-hours shutdown | ~£206 | Nobody can use dev at 22:00 without starting it (a scheduler, and a documented way to wake it) |

That is a cost review. Not "we cut 60%", but "we cut 60% and here is precisely what we traded, per line, and who decided".

### Step 3: Unit Cost — The Number That Survives Growth

```bash
./cost-estimate.py --plan plan-tagged.json --requests 5000000 | tail -5
```

```text
  UNIT COST

  5,000,000 requests/month → GBP 0.0770 per 1,000 requests
```

Track this next to your golden signals (Module 07). It is the only cost metric that distinguishes growth from decay:

```bash
# Same infrastructure, traffic doubled — the environment got cheaper per unit of work
./cost-estimate.py --plan plan-tagged.json --requests 10000000 | grep 'per 1,000'
# Same infrastructure, traffic halved — the SAME total spend is now twice as expensive
./cost-estimate.py --plan plan-tagged.json --requests 2500000 | grep 'per 1,000'
```

```text
  10,000,000 requests/month → GBP 0.0385 per 1,000 requests
  2,500,000 requests/month → GBP 0.1539 per 1,000 requests
```

Total spend is identical in all three cases. That is scenario 4.

### Step 4: Make Both Checks a Gate

Cost review only happens if it is automatic. Add this to the pipeline that runs your Terraform:

```yaml
# .github/workflows/terraform.yml — the cost job
cost:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: hashicorp/setup-terraform@v3

    - name: Plan
      run: |
        cd infra
        terraform init -backend=false
        terraform plan -out=tfplan -var owner=${{ vars.OWNER }} -var service=${{ vars.SERVICE }}
        terraform show -json tfplan > ../plan.json

    # ⭐ BLOCKING: unallocatable resources never reach the account
    - name: Tag gate
      run: ./tag-gate.py --plan plan.json --require owner env service

    # Informational: the number goes in the PR, where the decision is being made
    - name: Cost estimate
      run: |
        ./cost-estimate.py --plan plan.json --suggest | tee cost.txt
        { echo '```'; cat cost.txt; echo '```'; } >> "$GITHUB_STEP_SUMMARY"
```

And put the budget in code too, so a new account is never unguarded:

```hcl
# infra/budget.tf — per ENVIRONMENT, not one for the whole account
resource "aws_budgets_budget" "monthly" {
  name         = "${var.service}-${var.environment}"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_gbp
  limit_unit   = "GBP"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = ["user:service$${var.service}"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80 # ⭐ warn at 80% of budget, not at 100%
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED" # forecast, so you hear before you spend it
    subscriber_email_addresses = [var.budget_email]
  }
}
```

> ⭐ For numbers you have to defend to finance, use **Infracost** — it carries real price data, comments on pull requests, and handles the pricing complexity this script deliberately does not. The script exists so the mechanism is not a black box, and so this lab needs no signup.

---

## 🧨 Break It: Four Ways Bills Surprise You

### Scenario 1: The Spend Nobody Owns

**Break it.** Add a resource type the gate does not think about — for instance, someone adds a queue, and the module they copied has explicit tags that override the provider defaults:

```bash
cat >> infra/main.tf <<'EOF'

# Added in a hurry, with explicit tags that REPLACE the inherited ones for this resource.
resource "aws_sqs_queue" "jobs" {
  name = "jobs"
  tags = { Name = "jobs" } # ⚠️ no owner, no service — and default_tags do not merge here
}
EOF
cd infra && terraform validate && terraform plan -out=tfplan \
  -var owner=payments-team -var service=checkout >/dev/null \
  && terraform show -json tfplan > ../plan-sqs.json; cd ..
./tag-gate.py --plan plan-sqs.json | tail -4
```

**Symptom.** One resource fails the gate — good, that is the gate working. Now the silent version: run the *cost* report instead.

```bash
./cost-estimate.py --plan plan-sqs.json --group-by service | tail -6
```

The queue costs nothing this script prices, so it appears nowhere and is attributed to nobody. In a real account it will appear on the bill next month as a line item under a service you cannot identify — and the team that created it will never see it on their dashboard, so it will grow.

**Root cause.** Two independent gaps. First, resource-level `tags` in the AWS provider **merge** with `default_tags`, but any key set locally wins — and a copied module often sets `Name` plus nothing else while overriding what it inherited. Second, "cost we cannot price" and "cost we cannot attribute" are different problems, and a report that shows £0 for something looks identical to a report that shows nothing at all.

**Fix.**

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path('infra/main.tf'); t = p.read_text()
t = t.replace('  tags = { Name = "jobs" } # ⚠️ no owner, no service — and default_tags do not merge here',
              '  tags = { Name = "jobs" } # inherits owner/env/service from provider default_tags')
p.write_text(t)
PY
./tag-gate.py --plan plan-sqs.json --require owner env service | tail -3
```

The durable fixes are: the gate is **blocking** in CI (a plan that cannot be attributed never applies), and allocation coverage is a tracked metric — the percentage of *billed* spend with an `owner`, taken from Cost Explorer rather than from your own plan.

### Scenario 2: The Cost That Is an Integral

**Break it.** Put the log retention back to the default:

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path('infra/main.tf'); t = p.read_text()
t = t.replace('  retention_in_days = 14\n', '')
p.write_text(t)
PY
./cost-estimate.py --plan sample-plan.json | grep log_group
```

**Symptom.**

```text
  aws_cloudwatch_log_group.app    0.60   ~20GB/mo, NO RETENTION — grows every month, never shrinks
```

Sixty pence. Nobody will ever raise a ticket about sixty pence, which is exactly why this survives:

```bash
python3 - <<'PY'
gb_per_month, price = 20, 0.03
total = 0
print(f"  {'month':>6}  {'stored GB':>10}  {'that month':>11}  {'cumulative':>11}")
for m in range(1, 61):
    stored = gb_per_month * m
    cost = stored * price
    total += cost
    if m in (1, 6, 12, 24, 36, 60):
        print(f"  {m:>6}  {stored:>10}  £{cost:>10.2f}  £{total:>10.2f}")
PY
```

```text
   month   stored GB   that month   cumulative
       1          20  £      0.60  £      0.60
       6         120  £      3.60  £     12.60
      12         240  £      7.20  £     46.80
      24         480  £     14.40  £    183.60
      36         720  £     21.60  £    410.40
      60        1200  £     36.00  £   1112.40
```

**Root cause.** Retention-less storage is not a monthly cost, it is an accumulating one. Every "small" line of this kind — logs, snapshots, old AMIs, versioned S3 objects with no lifecycle rule — grows without anyone deciding it should, and none of them is ever big enough to trigger a review on its own.

**Fix.** Set retention at creation, and make it impossible to forget:

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path('infra/main.tf'); t = p.read_text()
t = t.replace('resource "aws_cloudwatch_log_group" "app" {\n  name              = "/aws/app/prod"',
              'resource "aws_cloudwatch_log_group" "app" {\n  name              = "/aws/app/prod"\n  retention_in_days = 14')
p.write_text(t)
PY
cd infra && terraform fmt >/dev/null && terraform validate && cd ..
```

Then add it to the policy gate — the same pattern as the tag gate — plus a monthly sweep for the other accumulators: unattached volumes, snapshots older than your restore window, deregistered-image snapshots, and buckets with versioning and no lifecycle rule.

### Scenario 3: The Commitment You Re-Architected Away

**Break it.** No commands — this one is arithmetic, and it is the most expensive mistake on the list. Take the report's own suggestion:

```bash
./cost-estimate.py --suggest | grep -A1 'Savings Plan'
```

You commit to a 1-year Savings Plan covering the two `t3.large` instances and the RDS instance: about £95/month saved, £1,140 over the year. Two months later the team ships the Kubernetes migration from Project 03, and those EC2 instances disappear.

**Symptom.** Your bill does not fall. You are paying the committed hourly amount whether or not you consume it, so you now pay for the new platform *and* the commitment you no longer use:

```bash
python3 - <<'PY'
committed_monthly = 95 / 0.35 * 0.65   # what you pay hourly under the commitment
print(f"  committed spend still owed each month: £{committed_monthly:.2f}")
print(f"  months remaining after a 2-month migration: 10")
print(f"  wasted: £{committed_monthly * 10:.2f}")
print("\n  And it does not show up as an anomaly — it is exactly what you agreed to.")
PY
```

**Root cause.** A commitment is a bet on your architecture staying roughly the same. The discount is real, and so is the lock-in — and the team making the commitment (often finance or a central platform group) is frequently not the team planning the migration.

**Fix.**

- Commit to the **measured steady-state floor**, typically 60–80% of baseline, never 100%, and never to a forecast.
- Prefer **flexible** instruments (Compute Savings Plans cover EC2, Fargate and Lambda across families and regions) over instance-specific reservations, precisely so a migration does not orphan them.
- Ask "what is on the roadmap for the next 12 months?" before committing, and write the answer in the decision record.
- Re-check **commitment utilisation** monthly (`aws ce get-savings-plans-utilization`) — anything below ~95% is money already spent on nothing.

### Scenario 4: Flat Spend, Doubled Unit Cost

**Break it.** Nothing changes in the infrastructure. Traffic drops — a seasonal dip, a failed marketing campaign, a broken client release:

```bash
for r in 10000000 5000000 2500000; do
  printf '%12s requests → ' "$r"
  ./cost-estimate.py --plan sample-plan.json --requests "$r" | grep -o 'GBP [0-9.]* per 1,000'
done
```

```text
    10000000 requests → GBP 0.0385 per 1,000
     5000000 requests → GBP 0.0770 per 1,000
     2500000 requests → GBP 0.1539 per 1,000
```

**Symptom.** £384.80 every month, in all three cases. Every cost dashboard is flat, every budget alert is silent, and the business is now paying four times as much per request as it was. Nobody in the monthly cost review notices, because the only number on the slide is the total.

**Root cause.** Total spend measures the *bill*, not the *efficiency*. A cost that does not scale down with load looks identical to a cost that is being used well — and this is the normal state of affairs for anything provisioned rather than consumed: instances, NAT gateways, load balancers, reserved capacity.

**Fix.** Three things, in order of impact:

1. **Put unit cost on the dashboard**, next to latency and error rate. It is the only metric that connects spend to value delivered.
2. **Alert on the unit cost trend**, not the total: a 50% increase in cost per 1,000 requests over a fortnight is a real signal, whichever direction the total moved.
3. **Make the architecture scale down**, so efficiency is structural rather than vigilance: autoscaling with a low floor, spot for interruptible work, serverless for genuinely spiky load, and off-hours shutdown for non-production.

### Summary

| Failure | How you detect it | How you prevent it |
|---------|------------------|--------------------|
| Unattributable spend | Allocation coverage below ~90%; "untagged" as your biggest cost centre | Enforced tags via `default_tags`, a **blocking** gate on the plan, coverage tracked from Cost Explorer |
| Accumulating storage | A line item too small to review, growing monthly forever | Retention and lifecycle set at creation; a monthly sweep for volumes, snapshots, AMIs, versioned objects |
| Orphaned commitment | Utilisation below ~95%; spend not falling after a migration | Commit to the measured floor, prefer flexible instruments, check the roadmap first |
| Efficiency regression | Flat total spend, rising cost per unit of work | Unit cost on the dashboard, alerts on its trend, architecture that scales down |

⭐ **The theme of this lab**: cost is a non-functional requirement, and it behaves exactly like the others. It needs a measurement, an owner, a gate in the pipeline, and an alert on the *rate* rather than the *level*. The tactics — rightsizing, commitments, spot, tiering — are the easy part and every blog post covers them. The reason organisations stay expensive is that nobody can see their own number, and nobody is accountable for a trend.

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
rm -f plan-*.json infra/tfplan
rm -rf infra/.terraform infra/.terraform.lock.hcl
```

Nothing was ever provisioned, which is the point of reviewing the plan. Keep your before/after estimates — a documented cost review with the capability trade-offs written down is exactly the artefact `docs/cost.md` in Project 03 asks for.

---

## ✅ Validation

- [ ] Explain why "inform" precedes "optimise" in the FinOps loop
- [ ] Read a cost estimate and name the two largest drivers, and why NAT gateways surprise people
- [ ] Explain what `default_tags` does, and why resource-level tags can still leave a gap
- [ ] Make a tag gate blocking in CI, and say what it prevents
- [ ] Explain why two of the ranked optimisations cannot both be claimed
- [ ] For each optimisation you applied, state the capability you traded away
- [ ] Compute unit cost, and explain what flat spend with rising unit cost means
- [ ] Explain why retention-less storage is an integral rather than a monthly cost
- [ ] Explain how a commitment survives the architecture it was bought for, and how to avoid that
- [ ] Say when you would reach for Infracost instead of a script like this

---

## 📝 What to Commit

- `infra/main.tf` before and after, or the diff
- The starting estimate, the tag-gate failure, and both after fixing allocation
- Your optimised estimate with the capability-trade table
- Unit cost at three traffic levels, with the same total spend
- The CI job definition and the budget resource
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: IAM Least Privilege](./lab-02-iam-least-privilege.md) | [Back to Module README](../README.md) | [Module 10: Terraform →](../../10-terraform/)
