# Lab 02: IAM and Least Privilege

## 🎯 Objective

Write IAM policies that grant exactly what's needed and nothing more — and, more importantly, learn to **test** them before they reach production. You'll build a policy from scratch, simulate it without running anything destructive, use conditions to constrain access, set up OIDC so CI never holds a long-lived key, and audit an account for the credentials nobody meant to leave behind.

---

## 📋 Prerequisites

- Completed [Lab 01: AWS Fundamentals](./lab-01-aws-fundamentals.md)
- AWS CLI configured with permissions to create IAM roles and policies

```bash
aws sts get-caller-identity      # ⭐ ALWAYS. Confirm the account before every IAM change.
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=${AWS_REGION:-us-east-1}
echo "account: $ACCOUNT_ID  region: $AWS_REGION"
```

> 💰 **Cost**: IAM roles, policies, and users are free. The S3 bucket used for testing costs pennies. Cleanup is at the end.

---

## 📦 Deliverables and Evidence

- A least-privilege policy you wrote from scratch, with conditions
- `iam simulate-principal-policy` output showing allowed and denied actions
- A role assumed via `sts assume-role`, with proof of what it can and can't do
- An OIDC provider and trust policy for GitHub Actions, with no stored keys
- Your account credential audit output
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-02/`](../code/lab-02/).

```bash
cp -r /path/to/the-devops-handbook/09-cloud-fundamentals/code/lab-02/. .
```

---

## 🔬 Exercise 1: Anatomy of a Policy

### Step 1: Set Up

```bash
mkdir -p iam-lab && cd iam-lab
export BUCKET="iam-lab-${ACCOUNT_ID}-$RANDOM"
aws s3api create-bucket --bucket "$BUCKET" >/dev/null
aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
echo "test bucket: $BUCKET"
```

### Step 2: The Five Elements

```bash
cat > policy-anatomy.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadAppObjects",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::$BUCKET/app/*",
      "Condition": {
        "Bool": { "aws:SecureTransport": "true" }
      }
    }
  ]
}
JSON
python3 -m json.tool policy-anatomy.json
```

| Element | Answers | Notes |
|---------|---------|-------|
| `Version` | Which policy language | Always `"2012-10-17"`. It is a **date, not a version number** — never change it |
| `Sid` | A label for humans | Optional but makes `simulate` output and audits readable |
| `Effect` | `Allow` or `Deny` | ⭐ An explicit `Deny` **always wins**, everywhere |
| `Action` | What API calls | `s3:GetObject`, not "read". Wildcards allowed: `s3:Get*` |
| `Resource` | Which objects | ⭐ The most commonly over-broad field |
| `Condition` | Under what circumstances | Where least privilege actually gets enforced |

### Step 3: The Bucket-vs-Object ARN Trap

This catches nearly everyone the first time.

```bash
cat > policy-arn-trap.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ThisWillNotWork",
    "Effect": "Allow",
    "Action": ["s3:ListBucket", "s3:GetObject"],
    "Resource": "arn:aws:s3:::$BUCKET/*"
  }]
}
JSON
```

`s3:ListBucket` acts on the **bucket**; `s3:GetObject` acts on an **object**. They need different ARNs:

```bash
cat > policy-correct.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListTheBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::$BUCKET",
      "Condition": {
        "StringLike": { "s3:prefix": ["app/*", "app/"] }
      }
    },
    {
      "Sid": "ReadWriteAppObjects",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::$BUCKET/app/*"
    }
  ]
}
JSON
python3 -m json.tool policy-correct.json >/dev/null && echo "✅ valid JSON"
```

| Action | ARN shape | Example |
|--------|-----------|---------|
| `s3:ListBucket`, `s3:GetBucketLocation` | The **bucket** | `arn:aws:s3:::my-bucket` |
| `s3:GetObject`, `s3:PutObject` | An **object** | `arn:aws:s3:::my-bucket/*` |

> 💡 The symptom of getting this wrong is `AccessDenied` on `aws s3 ls s3://bucket/` while `aws s3 cp` works fine — or vice versa. If one half of an S3 workflow fails, check your ARNs before anything else.

---

## 🔬 Exercise 2: Test Before You Trust

### Step 1: Create a Role to Test Against

```bash
cat > trust-policy.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::$ACCOUNT_ID:root" },
    "Action": "sts:AssumeRole"
  }]
}
JSON

aws iam create-role --role-name iam-lab-app \
  --assume-role-policy-document file://trust-policy.json \
  --description "Least-privilege app role for the IAM lab" >/dev/null

aws iam put-role-policy --role-name iam-lab-app \
  --policy-name app-s3-access \
  --policy-document file://policy-correct.json

aws iam list-role-policies --role-name iam-lab-app
```

### Step 2: Simulate — the Command Nobody Uses and Everybody Should

```bash
ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/iam-lab-app"

# ⭐ Test a policy WITHOUT performing the action
aws iam simulate-principal-policy \
  --policy-source-arn "$ROLE_ARN" \
  --action-names s3:GetObject s3:PutObject s3:DeleteObject s3:DeleteBucket \
  --resource-arns "arn:aws:s3:::$BUCKET/app/data.json" \
  --query 'EvaluationResults[].{Action:EvalActionName,Decision:EvalDecision}' \
  --output table
```

```
--------------------------------------------
|         SimulatePrincipalPolicy           |
+------------------+------------------------+
|      Action      |       Decision         |
+------------------+------------------------+
|  s3:GetObject    |  allowed               |
|  s3:PutObject    |  allowed               |
|  s3:DeleteObject |  allowed               |
|  s3:DeleteBucket |  implicitDeny          |  ⭐
+------------------+------------------------+
```

Test the path outside the allowed prefix:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn "$ROLE_ARN" \
  --action-names s3:GetObject \
  --resource-arns "arn:aws:s3:::$BUCKET/secrets/keys.txt" \
  --query 'EvaluationResults[].{Action:EvalActionName,Decision:EvalDecision}' --output table
#   implicitDeny ⭐ — the prefix restriction works
```

| Decision | Meaning |
|----------|---------|
| `allowed` | An `Allow` matched and no `Deny` overrode it |
| `implicitDeny` | Nothing granted it. The default — this is what least privilege looks like |
| `explicitDeny` | ⭐ A `Deny` statement, SCP, or permission boundary blocked it. **Cannot be overridden** |

> ⭐ Put this in CI. A test that asserts your app role **cannot** delete the bucket, and **cannot** read `secrets/`, catches an over-broad policy edit before it merges:
>
> ```bash
> aws iam simulate-principal-policy --policy-source-arn "$ROLE_ARN" \
>   --action-names s3:DeleteBucket --resource-arns "arn:aws:s3:::$BUCKET" \
>   --query 'EvaluationResults[0].EvalDecision' --output text | grep -q Deny \
>   || { echo "❌ role can delete the bucket"; exit 1; }
> ```

### Step 3: Assume It and Test for Real

```bash
CREDS=$(aws sts assume-role --role-arn "$ROLE_ARN" --role-session-name iam-lab-test \
  --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' --output text)
read -r AK SK ST <<<"$CREDS"

echo "hello" > /tmp/data.json
AWS_ACCESS_KEY_ID=$AK AWS_SECRET_ACCESS_KEY=$SK AWS_SESSION_TOKEN=$ST \
  aws s3 cp /tmp/data.json "s3://$BUCKET/app/data.json" && echo "✅ write to app/ allowed"

AWS_ACCESS_KEY_ID=$AK AWS_SECRET_ACCESS_KEY=$SK AWS_SESSION_TOKEN=$ST \
  aws s3 cp /tmp/data.json "s3://$BUCKET/secrets/data.json" 2>&1 | tail -1
#   ⭐ AccessDenied — outside the allowed prefix

AWS_ACCESS_KEY_ID=$AK AWS_SECRET_ACCESS_KEY=$SK AWS_SESSION_TOKEN=$ST \
  aws s3 ls "s3://$BUCKET/app/" && echo "✅ list of app/ allowed"

AWS_ACCESS_KEY_ID=$AK AWS_SECRET_ACCESS_KEY=$SK AWS_SESSION_TOKEN=$ST \
  aws s3api delete-bucket --bucket "$BUCKET" 2>&1 | tail -1
#   ⭐ AccessDenied
```

**✅ Checkpoint:** The simulation and reality agree. That agreement is what makes `simulate` trustworthy as a CI gate.

---

## 🔬 Exercise 3: Conditions

Conditions are where a merely-scoped policy becomes a genuinely safe one.

### Step 1: Constrain by Network, Encryption, and MFA

```bash
cat > policy-conditions.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RequireTLS",
      "Effect": "Deny",
      "Action": "s3:*",
      "Resource": ["arn:aws:s3:::$BUCKET", "arn:aws:s3:::$BUCKET/*"],
      "Condition": { "Bool": { "aws:SecureTransport": "false" } }
    },
    {
      "Sid": "RequireEncryptedUploads",
      "Effect": "Deny",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::$BUCKET/*",
      "Condition": {
        "StringNotEquals": { "s3:x-amz-server-side-encryption": "AES256" }
      }
    },
    {
      "Sid": "AllowFromOfficeOnly",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::$BUCKET/app/*",
      "Condition": {
        "IpAddress": { "aws:SourceIp": ["203.0.113.0/24", "198.51.100.0/24"] }
      }
    },
    {
      "Sid": "AllowDeleteOnlyWithMFA",
      "Effect": "Allow",
      "Action": "s3:DeleteObject",
      "Resource": "arn:aws:s3:::$BUCKET/app/*",
      "Condition": {
        "Bool": { "aws:MultiFactorAuthPresent": "true" },
        "NumericLessThan": { "aws:MultiFactorAuthAge": "3600" }
      }
    }
  ]
}
JSON
python3 -m json.tool policy-conditions.json >/dev/null && echo "✅ valid"
```

### Step 2: Simulate With Context

```bash
aws iam put-role-policy --role-name iam-lab-app \
  --policy-name conditional-access --policy-document file://policy-conditions.json

# From an allowed IP
aws iam simulate-principal-policy --policy-source-arn "$ROLE_ARN" \
  --action-names s3:GetObject --resource-arns "arn:aws:s3:::$BUCKET/app/x" \
  --context-entries 'ContextKeyName=aws:SourceIp,ContextKeyType=ip,ContextKeyValues=203.0.113.42' \
                    'ContextKeyName=aws:SecureTransport,ContextKeyType=boolean,ContextKeyValues=true' \
  --query 'EvaluationResults[0].EvalDecision' --output text

# From somewhere else
aws iam simulate-principal-policy --policy-source-arn "$ROLE_ARN" \
  --action-names s3:GetObject --resource-arns "arn:aws:s3:::$BUCKET/app/x" \
  --context-entries 'ContextKeyName=aws:SourceIp,ContextKeyType=ip,ContextKeyValues=8.8.8.8' \
                    'ContextKeyName=aws:SecureTransport,ContextKeyType=boolean,ContextKeyValues=true' \
  --query 'EvaluationResults[0].EvalDecision' --output text
```

**Condition keys worth knowing:**

| Key | Constrains to |
|-----|---------------|
| `aws:SourceIp` | A CIDR range. ⚠️ Doesn't apply to calls via a VPC endpoint — use `aws:SourceVpce` |
| `aws:SourceVpc` / `aws:SourceVpce` | Traffic arriving through your VPC |
| `aws:SecureTransport` | HTTPS only |
| `aws:MultiFactorAuthPresent` / `Age` | MFA, and how recently |
| `aws:PrincipalTag/<k>` | Attribute-based access control |
| `aws:RequestTag/<k>` / `aws:TagKeys` | What tags may be set at creation |
| `aws:ResourceTag/<k>` | ⭐ Acting only on resources with a given tag |
| `aws:PrincipalOrgID` | Principals inside your AWS Organization |
| `s3:x-amz-server-side-encryption` | Rejecting unencrypted uploads |

### Step 3: Tag-Based Access Control

Instead of listing resources, grant access to whatever carries the right tag:

```bash
cat > policy-abac.json <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ManageOwnTeamsInstances",
    "Effect": "Allow",
    "Action": ["ec2:StartInstances", "ec2:StopInstances", "ec2:RebootInstances"],
    "Resource": "arn:aws:ec2:*:*:instance/*",
    "Condition": {
      "StringEquals": {
        "aws:ResourceTag/Team": "${aws:PrincipalTag/Team}"
      }
    }
  }]
}
JSON
```

⭐ One policy that scales to any number of teams. A principal tagged `Team=payments` can control instances tagged `Team=payments`, and nothing else. No policy edit is needed when a team is added.

---

## 🔬 Exercise 4: OIDC — Stop Storing Cloud Keys

Long-lived access keys in CI are the most commonly leaked cloud credential. OIDC removes them entirely.

### Step 1: Create the Identity Provider

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 2>/dev/null \
  || echo "(provider already exists — fine)"

aws iam list-open-id-connect-providers
```

### Step 2: The Trust Policy Is the Security Boundary

```bash
cat > github-trust.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::$ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:myorg/myrepo:ref:refs/heads/main"
      }
    }
  }]
}
JSON

aws iam create-role --role-name github-actions-deploy \
  --assume-role-policy-document file://github-trust.json \
  --max-session-duration 3600 \
  --description "Assumed by GitHub Actions via OIDC — no stored credentials" >/dev/null

aws iam put-role-policy --role-name github-actions-deploy \
  --policy-name deploy-s3 --policy-document file://policy-correct.json
```

### Step 3: The `sub` Claim Is Everything

```bash
aws iam get-role --role-name github-actions-deploy \
  --query 'Role.AssumeRolePolicyDocument.Statement[0].Condition' --output json
```

| `sub` pattern | Who can assume the role |
|---------------|------------------------|
| `repo:myorg/myrepo:ref:refs/heads/main` | ⭐ Only the `main` branch of that one repo |
| `repo:myorg/myrepo:environment:production` | Only jobs using the `production` environment (which can require approval) |
| `repo:myorg/myrepo:pull_request` | ⚠️ Any PR — including from a fork. Almost never what you want |
| `repo:myorg/*` | Any repo in the org. Too broad for a deploy role |
| `repo:*` | ⚠️⚠️ **Any repo on GitHub.** A catastrophic misconfiguration that does occur |

```yaml
# The workflow side — note the total absence of credentials
permissions:
  id-token: write          # ⭐ required to request the OIDC token
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy
      aws-region: us-east-1
      role-session-name: gha-${{ github.run_id }}
```

> ⭐ **Audit every OIDC trust policy for a `StringLike` on `sub` that's too permissive.** Using `StringLike` with a value that has no wildcard is fine; using it with `repo:myorg/*` means any repo in the org — including a new one someone creates today — can assume a production role.

---

## 🔬 Exercise 5: Audit the Account

### Step 1: The Credential Report

```bash
aws iam generate-credential-report >/dev/null
sleep 5
aws iam get-credential-report --query Content --output text | base64 -d > credential-report.csv
column -t -s, credential-report.csv | head -20
```

Columns to act on:

| Column | Look for |
|--------|----------|
| `password_enabled` + `mfa_active` | ⭐ A console user **without MFA** |
| `access_key_1_last_used_date` | `N/A` on a key that's months old — delete it |
| `access_key_1_last_rotated` | Anything over 90 days |
| `password_last_used` | Users who never log in — delete the account |

```bash
python3 - <<'PY'
import csv, datetime
rows = list(csv.DictReader(open("credential-report.csv")))
now = datetime.datetime.now(datetime.timezone.utc)

def age(s):
    if not s or s in ("N/A", "not_supported"):
        return None
    return (now - datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))).days

print("── console users without MFA ──")
for r in rows:
    if r["password_enabled"] == "true" and r["mfa_active"] == "false":
        print("  ⚠️ ", r["user"])

print("── access keys older than 90 days ──")
for r in rows:
    for n in ("1", "2"):
        if r[f"access_key_{n}_active"] == "true":
            a = age(r[f"access_key_{n}_last_rotated"])
            if a and a > 90:
                print(f"  ⚠️  {r['user']} key {n}: {a} days old")

print("── active keys never used ──")
for r in rows:
    for n in ("1", "2"):
        if r[f"access_key_{n}_active"] == "true" and r[f"access_key_{n}_last_used_date"] == "N/A":
            print(f"  ⚠️  {r['user']} key {n}: never used — delete it")
PY
```

### Step 2: Find Over-Broad Policies

```bash
# ⭐ Customer-managed policies granting Action:* on Resource:*
for arn in $(aws iam list-policies --scope Local --only-attached \
             --query 'Policies[].Arn' --output text); do
  ver=$(aws iam get-policy --policy-arn "$arn" --query 'Policy.DefaultVersionId' --output text)
  doc=$(aws iam get-policy-version --policy-arn "$arn" --version-id "$ver" \
        --query 'PolicyVersion.Document' --output json)
  echo "$doc" | grep -q '"\*"' && echo "  ⚠️  wildcard in: $arn"
done

# Who has AdministratorAccess?
aws iam list-entities-for-policy --policy-arn arn:aws:iam::aws:policy/AdministratorAccess \
  --query '{Users:PolicyUsers[].UserName,Roles:PolicyRoles[].RoleName,Groups:PolicyGroups[].GroupName}'

# Roles nobody has used in 90 days
aws iam list-roles --query 'Roles[?!starts_with(RoleName, `AWSServiceRole`)].RoleName' --output text \
  | tr '\t' '\n' | while read -r r; do
      last=$(aws iam get-role --role-name "$r" --query 'Role.RoleLastUsed.LastUsedDate' --output text 2>/dev/null)
      [ "$last" = "None" ] && echo "  ⚠️  never used: $r"
    done
```

### Step 3: Right-Size From Real Usage

```bash
# ⭐ Access Advisor: which services has this role ACTUALLY used?
JOB=$(aws iam generate-service-last-accessed-details --arn "$ROLE_ARN" \
      --query JobId --output text)
sleep 8
aws iam get-service-last-accessed-details --job-id "$JOB" \
  --query 'ServicesLastAccessed[?TotalAuthenticatedEntities>`0`].{Service:ServiceName,Last:LastAuthenticated}' \
  --output table
```

> ⭐ **This is how you shrink a policy safely.** Grant broadly, let it run for two weeks, then use Access Advisor and CloudTrail to see what was genuinely used — and remove the rest. Guessing produces either an outage or an over-broad policy; measuring produces neither.

---

## 🧨 Break It: Four IAM Failures

### Scenario 1: The Wildcard That Grants Everything

**Break it:**

```bash
cat > policy-wildcard.json <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ItWasFasterThanDebugging",
    "Effect": "Allow",
    "Action": "s3:*",
    "Resource": "*"
  }]
}
JSON
aws iam put-role-policy --role-name iam-lab-app \
  --policy-name wildcard-oops --policy-document file://policy-wildcard.json

aws iam simulate-principal-policy --policy-source-arn "$ROLE_ARN" \
  --action-names s3:DeleteBucket s3:PutBucketPolicy s3:GetObject \
  --resource-arns "arn:aws:s3:::some-other-production-bucket" \
  --query 'EvaluationResults[].{Action:EvalActionName,Decision:EvalDecision}' --output table
```

**Symptom:** `allowed` for everything, on **every bucket in the account** — including production buckets this role has nothing to do with. `s3:*` includes `DeleteBucket`, `PutBucketPolicy` (which can make a bucket public), and `PutBucketAcl`.

**Investigate:**

```bash
aws iam get-role-policy --role-name iam-lab-app --policy-name wildcard-oops \
  --query PolicyDocument --output json

# What did s3:* actually just grant? ~100 actions.
aws iam simulate-principal-policy --policy-source-arn "$ROLE_ARN" \
  --action-names s3:PutBucketPolicy s3:PutBucketAcl s3:DeleteBucketPolicy \
  --resource-arns "arn:aws:s3:::$BUCKET" \
  --query 'EvaluationResults[].{A:EvalActionName,D:EvalDecision}' --output table
```

**Root cause:** Someone hit `AccessDenied`, replaced the action list with `s3:*` to unblock themselves, and never came back. It always works, which is why it survives.

**Fix — and a guard so it can't happen again:**

```bash
aws iam delete-role-policy --role-name iam-lab-app --policy-name wildcard-oops

# A permission boundary caps what the role can EVER do, regardless of its policies
cat > boundary.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::$BUCKET", "arn:aws:s3:::$BUCKET/*"]
    },
    {
      "Sid": "NeverAllowBucketAdministration",
      "Effect": "Deny",
      "Action": ["s3:DeleteBucket", "s3:PutBucketPolicy", "s3:PutBucketAcl", "iam:*"],
      "Resource": "*"
    }
  ]
}
JSON
BOUNDARY=$(aws iam create-policy --policy-name iam-lab-boundary \
  --policy-document file://boundary.json --query 'Policy.Arn' --output text 2>/dev/null \
  || echo "arn:aws:iam::$ACCOUNT_ID:policy/iam-lab-boundary")
aws iam put-role-permissions-boundary --role-name iam-lab-app --permissions-boundary "$BOUNDARY"

# Re-attach the wildcard and watch the boundary stop it
aws iam put-role-policy --role-name iam-lab-app \
  --policy-name wildcard-oops --policy-document file://policy-wildcard.json
aws iam simulate-principal-policy --policy-source-arn "$ROLE_ARN" \
  --action-names s3:DeleteBucket --resource-arns "arn:aws:s3:::$BUCKET" \
  --query 'EvaluationResults[0].EvalDecision' --output text
#   ⭐ explicitDeny — the boundary wins over the identity policy
aws iam delete-role-policy --role-name iam-lab-app --policy-name wildcard-oops
```

---

### Scenario 2: `iam:PassRole` — the Escalation Nobody Notices

**Break it:**

```bash
cat > policy-passrole.json <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["ec2:RunInstances", "ec2:Describe*"], "Resource": "*" },
    { "Effect": "Allow", "Action": "iam:PassRole", "Resource": "*" }
  ]
}
JSON
aws iam put-role-policy --role-name iam-lab-app \
  --policy-name passrole-oops --policy-document file://policy-passrole.json

aws iam simulate-principal-policy --policy-source-arn "$ROLE_ARN" \
  --action-names iam:CreateUser iam:AttachUserPolicy s3:DeleteBucket \
  --resource-arns "*" \
  --query 'EvaluationResults[].{A:EvalActionName,D:EvalDecision}' --output table
```

**Symptom:** The simulation says the role **cannot** create IAM users or delete buckets. It looks tightly scoped. In reality, this policy is **equivalent to administrator access**:

1. `ec2:RunInstances` + `iam:PassRole` on `*` means it can launch an instance
2. …with **any role in the account** attached, including an admin role
3. It then has admin credentials, via the instance metadata service

**Investigate:**

```bash
# Which roles could be passed? Any of them.
aws iam list-roles --query 'Roles[?!starts_with(RoleName,`AWSServiceRole`)].RoleName' --output table | head

# Account-wide audit for this pattern
for r in $(aws iam list-roles --query 'Roles[].RoleName' --output text | tr '\t' '\n' | head -40); do
  for p in $(aws iam list-role-policies --role-name "$r" --query 'PolicyNames[]' --output text 2>/dev/null); do
    doc=$(aws iam get-role-policy --role-name "$r" --policy-name "$p" --query PolicyDocument --output json 2>/dev/null)
    echo "$doc" | grep -q 'PassRole' && echo "$doc" | grep -q '"Resource": *"\*"' \
      && echo "  ⚠️  unconstrained PassRole: role=$r policy=$p"
  done
done
```

**Root cause:** `iam:PassRole` looks administrative but harmless — it doesn't *do* anything by itself. Combined with any service that accepts a role (`ec2:RunInstances`, `lambda:CreateFunction`, `ecs:RunTask`, `glue:CreateJob`, `cloudformation:CreateStack`), it becomes "assume any role in the account".

**Fix — always constrain which roles may be passed, and to which service:**

```bash
aws iam delete-role-policy --role-name iam-lab-app --policy-name passrole-oops

cat > policy-passrole-safe.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["ec2:RunInstances", "ec2:Describe*"], "Resource": "*" },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::$ACCOUNT_ID:role/app-instance-role",
      "Condition": {
        "StringEquals": { "iam:PassedToService": "ec2.amazonaws.com" }
      }
    }
  ]
}
JSON
python3 -m json.tool policy-passrole-safe.json >/dev/null && echo "✅ scoped PassRole"
```

> ⭐ **Escalation primitives to treat as near-admin**, none of which `simulate` will warn you about: `iam:PassRole` · `iam:CreatePolicyVersion` · `iam:AttachRolePolicy` · `iam:PutRolePolicy` · `iam:UpdateAssumeRolePolicy` · `sts:AssumeRole` on `*` · `lambda:CreateFunction` + `PassRole` · `cloudformation:CreateStack` + `PassRole` · `ssm:SendCommand` on an admin instance.

---

### Scenario 3: The Trust Policy That Trusts Everyone

**Break it:**

```bash
cat > trust-wide.json <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "*" },
    "Action": "sts:AssumeRole"
  }]
}
JSON
aws iam update-assume-role-policy --role-name iam-lab-app \
  --policy-document file://trust-wide.json
aws iam get-role --role-name iam-lab-app --query 'Role.AssumeRolePolicyDocument' --output json
```

**Symptom:** `"Principal": {"AWS": "*"}` means **any AWS account on Earth** can assume this role, if they know its ARN. Role ARNs are not secret — they appear in logs, error messages, screenshots, and Stack Overflow questions. This is a genuine, exploited-in-the-wild misconfiguration.

**Investigate:**

```bash
# ⭐ Audit every role's trust policy for a wildcard or an external account
for r in $(aws iam list-roles --query 'Roles[?!starts_with(RoleName,`AWSServiceRole`)].RoleName' --output text | tr '\t' '\n'); do
  doc=$(aws iam get-role --role-name "$r" --query 'Role.AssumeRolePolicyDocument' --output json 2>/dev/null)
  echo "$doc" | grep -q '"AWS": *"\*"' && echo "  🚨 WILDCARD TRUST: $r"
  echo "$doc" | grep -oE 'arn:aws:iam::[0-9]{12}:root' | grep -v "$ACCOUNT_ID" \
    | while read -r ext; do echo "  ⚠️  external account trusted by $r: $ext"; done
done

# IAM Access Analyzer finds this automatically — enable it
aws accessanalyzer list-analyzers --query 'analyzers[].{Name:name,Status:status}' --output table 2>/dev/null \
  || echo "  ⚠️  no Access Analyzer configured — create one"
```

**Root cause:** Two paths. Someone was setting up cross-account access and used `*` to get it working. Or a tutorial said to. Either way it survives because nothing breaks.

**Fix:**

```bash
aws iam update-assume-role-policy --role-name iam-lab-app --policy-document file://trust-policy.json

# Cross-account access done correctly: name the account AND require an external ID
cat > trust-crossaccount.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::210987654321:root" },
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": { "sts:ExternalId": "a-secret-shared-with-that-partner-only" },
      "Bool": { "aws:MultiFactorAuthPresent": "true" }
    }
  }]
}
JSON

# Enable Access Analyzer so this is caught automatically next time
aws accessanalyzer create-analyzer --analyzer-name account-analyzer --type ACCOUNT >/dev/null 2>&1 \
  && echo "✅ Access Analyzer enabled" || echo "(already exists)"
```

> 💡 The **external ID** exists specifically to prevent the "confused deputy" problem: without it, if a third-party SaaS vendor trusts account X to assume roles on behalf of customers, any of their customers could assume *your* role by guessing its ARN.

---

### Scenario 4: Denied, and You Can't Tell Why

**Break it:**

```bash
# Add a Deny that overlaps an existing Allow
cat > policy-shadow-deny.json <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "BlanketDenyOnATag",
    "Effect": "Deny",
    "Action": "s3:*",
    "Resource": "*",
    "Condition": {
      "StringNotEquals": { "aws:ResourceTag/Environment": "dev" }
    }
  }]
}
JSON
aws iam put-role-policy --role-name iam-lab-app \
  --policy-name shadow-deny --policy-document file://policy-shadow-deny.json

CREDS=$(aws sts assume-role --role-arn "$ROLE_ARN" --role-session-name debug \
  --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' --output text)
read -r AK SK ST <<<"$CREDS"
AWS_ACCESS_KEY_ID=$AK AWS_SECRET_ACCESS_KEY=$SK AWS_SESSION_TOKEN=$ST \
  aws s3 cp /tmp/data.json "s3://$BUCKET/app/x.json" 2>&1 | tail -2
```

**Symptom:** `AccessDenied`. The role has an explicit `Allow` for exactly this action and resource. Nothing in the error says which policy denied it, or why.

**Investigate — the ordered method:**

```bash
# 1. ⭐ Simulate: this DOES tell you which statement matched
aws iam simulate-principal-policy --policy-source-arn "$ROLE_ARN" \
  --action-names s3:PutObject --resource-arns "arn:aws:s3:::$BUCKET/app/x.json" \
  --query 'EvaluationResults[0].{Decision:EvalDecision,MatchedStatements:MatchedStatements[].SourcePolicyId}' \
  --output json

# 2. List every policy in play
aws iam list-role-policies --role-name iam-lab-app
aws iam list-attached-role-policies --role-name iam-lab-app
aws iam get-role --role-name iam-lab-app --query 'Role.PermissionsBoundary'

# 3. Check the resource-based policy too — a bucket policy can deny independently
aws s3api get-bucket-policy --bucket "$BUCKET" --query Policy --output text 2>/dev/null | python3 -m json.tool 2>/dev/null \
  || echo "  (no bucket policy)"

# 4. And SCPs, if this account is in an Organization
aws organizations describe-organization >/dev/null 2>&1 \
  && echo "  ⚠️  in an Organization — an SCP could be denying this" \
  || echo "  (standalone account, no SCPs)"

# 5. CloudTrail records the denied call
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=PutObject \
  --max-results 3 --query 'Events[].CloudTrailEvent' --output text 2>/dev/null \
  | python3 -c 'import sys,json;[print(json.loads(l).get("errorCode","-"), json.loads(l).get("errorMessage","")[:90]) for l in sys.stdin if l.strip()]' 2>/dev/null
```

**Root cause:** IAM evaluates in a fixed order, and **an explicit Deny anywhere wins**:

```
1. Explicit Deny — in ANY policy → DENIED, full stop
2. SCP (Organizations)          → must allow
3. Resource-based policy        → can allow across accounts
4. Identity-based policy        → must allow
5. Permissions boundary         → must allow
6. Session policy               → must allow
Otherwise → implicit deny
```

**Fix:**

```bash
aws iam delete-role-policy --role-name iam-lab-app --policy-name shadow-deny
AWS_ACCESS_KEY_ID=$AK AWS_SECRET_ACCESS_KEY=$SK AWS_SESSION_TOKEN=$ST \
  aws s3 cp /tmp/data.json "s3://$BUCKET/app/x.json" && echo "✅ works again"
```

> ⭐ **The debugging order for any `AccessDenied`**: `simulate-principal-policy` first (it names the matched statement), then enumerate identity policies → boundary → resource policy → SCP. Guessing costs hours; the simulation costs seconds.

---

### Summary

| Failure | Why it survives | Detection |
|---------|----------------|-----------|
| `Action: "*"` / `Resource: "*"` | It makes the error go away | Audit for wildcards; permission boundaries as a cap |
| Unconstrained `iam:PassRole` | Looks harmless; `simulate` won't flag it | Grep policies for `PassRole` + `Resource: *` |
| `Principal: {"AWS": "*"}` in a trust policy | Nothing breaks | IAM Access Analyzer; audit every trust policy |
| Over-broad OIDC `sub` | Works, so nobody re-reads it | Check every `StringLike` on `sub` for a wildcard |
| Mysterious `AccessDenied` | The error names nothing | `simulate-principal-policy` names the matched statement |

**The IAM checklist:**

- [ ] Roles, not users. Instance profiles for EC2, IRSA for EKS, OIDC for CI
- [ ] No long-lived access keys — and any that exist are rotated and monitored
- [ ] MFA on every console user, enforced by policy condition
- [ ] `Resource: "*"` justified in a comment, or removed
- [ ] `iam:PassRole` always scoped to specific roles **and** `iam:PassedToService`
- [ ] Permission boundaries on any role a non-admin can modify
- [ ] IAM Access Analyzer enabled, findings triaged
- [ ] Credential report reviewed monthly
- [ ] Policies right-sized from Access Advisor and CloudTrail, not from guesses
- [ ] `simulate-principal-policy` assertions in CI for your critical negative cases

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
aws iam delete-role-policy --role-name iam-lab-app --policy-name app-s3-access 2>/dev/null
aws iam delete-role-policy --role-name iam-lab-app --policy-name conditional-access 2>/dev/null
aws iam delete-role-policy --role-name iam-lab-app --policy-name wildcard-oops 2>/dev/null
aws iam delete-role-policy --role-name iam-lab-app --policy-name passrole-oops 2>/dev/null
aws iam delete-role-policy --role-name iam-lab-app --policy-name shadow-deny 2>/dev/null
aws iam delete-role-permissions-boundary --role-name iam-lab-app 2>/dev/null
aws iam delete-role --role-name iam-lab-app 2>/dev/null

aws iam delete-role-policy --role-name github-actions-deploy --policy-name deploy-s3 2>/dev/null
aws iam delete-role --role-name github-actions-deploy 2>/dev/null

aws iam delete-policy --policy-arn "arn:aws:iam::$ACCOUNT_ID:policy/iam-lab-boundary" 2>/dev/null

aws s3 rb "s3://$BUCKET" --force 2>/dev/null
cd .. && rm -rf iam-lab

# Verify
aws iam list-roles --query 'Roles[?starts_with(RoleName,`iam-lab`) || starts_with(RoleName,`github-actions-deploy`)].RoleName' --output text
aws s3 ls | grep iam-lab || echo "✅ clean"
```

> 💡 The OIDC provider is shared infrastructure — leave it if you'll use OIDC again, or remove it with
> `aws iam delete-open-id-connect-provider --open-id-connect-provider-arn arn:aws:iam::$ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com`

---

## ✅ Validation

- [ ] Name the five policy elements and what each controls
- [ ] Explain why `s3:ListBucket` and `s3:GetObject` need different ARNs
- [ ] Use `simulate-principal-policy` to test a policy without performing the action
- [ ] Distinguish `allowed`, `implicitDeny`, and `explicitDeny`
- [ ] Write conditions for TLS, source IP, MFA, and resource tags
- [ ] Explain ABAC and why it scales better than listing resources
- [ ] Set up an OIDC trust policy and explain what the `sub` claim constrains
- [ ] Explain why unconstrained `iam:PassRole` is equivalent to admin
- [ ] State the full IAM evaluation order and what always wins
- [ ] Run a credential report and act on three findings

---

## 📝 What to Commit

- Every policy JSON, with a comment on what each condition buys you
- `simulate-principal-policy` output for both allowed and denied cases
- The OIDC trust policy, with the `sub` pattern explained
- Your credential-report audit script and its output
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: AWS Fundamentals](./lab-01-aws-fundamentals.md) | [Back to Module README](../README.md) | [Next Lab: FinOps Cost Review →](./lab-03-finops-cost-review.md)
