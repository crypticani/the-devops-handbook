# Module 09: Cloud Fundamentals — Lab Code

IAM policy documents and trust policies from the AWS labs.

These are the real files from this module's labs. Every one is JSON-validated in CI.

The labs still show each policy inline — **read them line by line the first time**; an IAM
policy is only useful if you understand every field. Use these when you want a starting
point or a reference to diff against.

> ⚠️ **These contain placeholders.** `REPLACE-BUCKET-NAME` and the example account ID
> `123456789012` must be substituted with your own values before use. The labs generate them
> with shell interpolation; the copies here are deliberately inert so nothing here is tied to
> a real account.

---

## Contents

### `lab-01/`

The EC2 trust policy attached to the lab's instance role.

```
lab-01/
└── trust-policy.json
```

### `lab-02/`

Policy documents built across the least-privilege lab.

```
lab-02/
├── github-trust.json      OIDC trust policy for GitHub Actions — no stored keys
├── policy-abac.json       Tag-based access control; one policy for any number of teams
├── policy-anatomy.json    The five policy elements, annotated
├── policy-arn-trap.json   ❌ The bucket-vs-object ARN mistake, kept as a counter-example
├── policy-conditions.json TLS, encryption, source IP, and MFA conditions
├── policy-correct.json    The corrected least-privilege S3 policy
└── trust-policy.json      Same-account assume-role trust
```

> `policy-arn-trap.json` is **wrong on purpose** — it's the `s3:ListBucket` + `s3:GetObject`
> ARN mistake from Exercise 1. Compare it against `policy-correct.json`.

### `lab-03/`

A FinOps cost review that needs no cloud account: the Project 03 environment as Terraform, a
real `terraform show -json` of it, and two scripts that turn a plan into a number somebody owns.

```
lab-03/
├── infra/main.tf      the environment, written the way it gets written first (⚠️ markers)
├── sample-plan.json   a real plan of that config, so the lab runs offline
├── prices.json        illustrative monthly prices, as DATA you can correct per region
├── cost-estimate.py   plan + prices → cost by resource and by tag, + ranked optimisations
└── tag-gate.py        ⭐ blocking: fails a plan that creates unattributable resources
```

---

## Using these files

```bash
mkdir -p ~/devops-labs/09-cloud && cd ~/devops-labs/09-cloud
cp -r /path/to/the-devops-handbook/09-cloud-fundamentals/code/lab-02/. .

# Substitute the placeholders
sed -i "s/REPLACE-BUCKET-NAME/my-actual-bucket/; s/123456789012/$(aws sts get-caller-identity --query Account --output text)/" ./*.json

# ⭐ Always simulate before attaching
aws iam simulate-principal-policy --policy-source-arn "$ROLE_ARN" \
  --action-names s3:GetObject --resource-arns "arn:aws:s3:::my-actual-bucket/app/x"
```

---

<div align="center">

[← Module 09 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
