# Lab 04: Azure — Bicep Templates and Storage, Without a Subscription

## 🎯 Objective

Work with real Azure tooling on a second cloud: author a Bicep template, gate it in CI with a linter that fails the build, compile it to the ARM JSON that Azure actually receives, and then operate Blob Storage through the genuine `az` CLI against Microsoft's official emulator.

Everything here runs offline and costs nothing. `bicep build` and `bicep lint` never contact Azure, and **Azurite** is the storage emulator Microsoft's own tooling is tested against — the same APIs, the same CLI, the same SDKs. What you cannot do without a subscription is deploy, so this lab covers the two things that surround a deployment and catch most mistakes: the template review before it, and the resource operations after it.

---

## 📋 Prerequisites

- Read [§11 Azure — The Same Concepts, Different Nouns](../README.md#11-azure--the-same-concepts-different-nouns)
- Completed [Lab 02: IAM and Least Privilege](./lab-02-iam-least-privilege.md) — the access model here is the contrast to that one
- Docker and Docker Compose, ~1.5 GB free
- No Azure account, no credit card, no subscription

```bash
docker --version && docker compose version
```

---

## 📦 Deliverables and Evidence

- A linter failure that stops the build, and the fix that clears it
- The compiled ARM JSON, with the parameter and resource blocks Azure would receive
- The three insecure settings the default linter does **not** catch, and how you found them
- A blob you uploaded and listed through the real `az storage` commands
- A container you exposed anonymously, the HTTP 200 that proves it, and the 403 after locking it down
- The same object fetched with a SAS token instead — 200 without public access
- `azure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-04/`](../code/lab-04/).

```bash
cp -r /path/to/the-devops-handbook/09-cloud-fundamentals/code/lab-04/. .
chmod +x check-template.sh
docker compose up -d azurite
```

`main.bicep` ships **deliberately imperfect** — finding what is wrong with it is the lab.

---

## 🔬 Exercise 1: The Template Gate

### Step 1: What Bicep Is

Bicep is a DSL that compiles to an ARM template. ARM JSON is what Azure's Resource Manager accepts; nobody enjoys writing it, so Microsoft wrote a language that produces it. The mapping to what you already know:

| Concept | AWS | Azure |
|---------|-----|-------|
| Native IaC format | CloudFormation YAML/JSON | ARM JSON |
| Friendlier authoring layer | CDK (compiles to CFN) | **Bicep** (compiles to ARM) |
| Third-party alternative | Terraform (`aws` provider) | Terraform (`azurerm` provider) |
| Preview before applying | `aws cloudformation create-change-set` | `az deployment group what-if` |

Read `main.bicep` before running anything. It declares a storage account, a blob service, and a container — roughly forty lines that would be two hundred in ARM JSON.

### Step 2: Run the Gate

```bash
./check-template.sh
```

```text
══ Linting main.bicep
/work/main.bicep(21,7) : Error no-unused-params: Parameter "retentionDays" is declared but never used.
  ❌ lint failed — fix the errors above, or decide the rule is wrong and edit bicepconfig.json
```

The script exits `1`, which is the entire point: in CI this stops the pipeline. Look at `bicepconfig.json` to see why that particular finding is fatal:

```json
"no-unused-params": { "level": "error" },
"use-recent-api-versions": { "level": "warning" }
```

⭐ **Bicep's default linter runs at `warning` for almost everything, and warnings do not fail anything.** A rule only becomes a gate when you raise it to `error` in `bicepconfig.json` — a file you write, commit, and argue about in review. "We have linting" and "linting can block a merge" are different claims, and only the second one changes what ships.

### Step 3: Fix It

`retentionDays` is declared and never used — dead configuration that reviewers assume is doing something. Rather than deleting it, give it the job its name implies:

```bicep
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: retentionDays        // ⭐ soft delete: recover a blob deleted by mistake
    }
  }
}
```

```bash
./check-template.sh
```

```text
══ Linting main.bicep
  ✅ lint clean

══ Compiling main.bicep → main.json
  ✅ compiled — this ARM JSON is what Azure would actually receive
```

### Step 4: Read What It Compiled To

```bash
head -40 main.json
python3 -c "import json;d=json.load(open('main.json'));print(list(d['parameters']), len(d['resources']))"
```

The `templateHash` in the metadata is worth noticing: Azure uses it to tell whether a deployment is a genuine change. And `main.json` is a build artefact — it belongs in `.gitignore`, exactly like a compiled binary. Committing both is how the two drift apart.

---

## 🔬 Exercise 2: Operating Storage for Real

Azurite speaks the actual Blob API, so every command below is the one you would run against a real account — only the endpoint in the connection string differs.

```bash
docker compose run --rm cli 'az storage container create -n uploads -o table'
echo "invoice-2026-08" > invoice.txt
docker compose run --rm cli 'az storage blob upload -c uploads -f /work/invoice.txt -n invoices/aug.txt --overwrite -o none'
docker compose run --rm cli 'az storage blob list -c uploads -o table'
```

```text
Name              Blob Type    Blob Tier    Length    Content Type    Last Modified
----------------  -----------  -----------  --------  --------------  -------------------------
invoices/aug.txt  BlockBlob    Hot          20        text/plain      2026-08-12T03:13:15+00:00
```

⭐ **`invoices/` is not a folder.** Blob Storage is flat, exactly like S3: the slash is part of the name, and "directories" are a prefix filter the tooling renders as a tree. Listing ten million blobs to find one prefix is why naming schemes matter more here than on a filesystem.

**The connection string** in `docker-compose.yml` is the well-known Azurite development credential — published in Microsoft's docs, identical on every machine on earth. It is safe here precisely because it grants access to nothing real, and it is a perfect illustration of what a connection string *is*: a bearer credential, the whole account, in one line of text. Which is Break It scenario 4.

---

## 🧨 Break It: Four Azure Failures

### Scenario 1: The Warning Nobody Reads

**Break it.** Lower the rule you just satisfied back to a warning:

```bash
sed -i 's/"no-unused-params": { "level": "error" }/"no-unused-params": { "level": "warning" }/' bicepconfig.json
```

Then re-introduce an unused parameter — add `param unusedThing string = 'x'` anywhere in `main.bicep`:

```bash
./check-template.sh
```

**Symptom.** The finding is still printed. The script still passes. The pipeline still deploys.

```text
WARNING: /work/main.bicep(4,7) : Warning no-unused-params: Parameter "unusedThing" is declared but never used.
  ✅ lint clean
```

**Root cause.** A warning in a CI log is a message nobody sees. Pipeline output scrolls past, and after the tenth benign warning the team stops reading all of them — including the eleventh, which was not benign. This is the same dynamic as an alert that fires daily and gets ignored.

**Fix.** Put it back, and adopt the rule of thumb: **every finding is either an error or deleted**. If a rule is not worth failing a build over, turn it off explicitly and write down why — a rule at `warning` forever is a decision nobody made.

```bash
git checkout bicepconfig.json 2>/dev/null || sed -i 's/"no-unused-params": { "level": "warning" }/"no-unused-params": { "level": "error" }/' bicepconfig.json
```

### Scenario 2: The Linter Is Not a Security Scanner

**Break it.** Nothing to break — the flaws are already in `main.bicep` and both the linter and the compiler are perfectly happy with them:

```bash
grep -n -A4 "properties: {" main.bicep | head -12
```

```text
    supportsHttpsTrafficOnly: false
    minimumTlsVersion: 'TLS1_0'
    allowBlobPublicAccess: true
```

**Symptom.** `./check-template.sh` says `✅ lint clean`. That template would deploy an account that accepts **unencrypted HTTP**, negotiates **TLS 1.0**, and permits **anonymous public containers**.

**Root cause.** The Bicep linter checks *Bicep* — unused parameters, interpolation style, API version age. It has no opinion about whether your configuration is safe, because that is a different tool's job. Every ecosystem has this seam: `terraform validate` will not tell you a security group is open to the world either.

**Fix.** Set the three properties correctly:

```bicep
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
```

Then add the layer that would have caught them for you. In order of strength:

| Layer | What it does | Where it runs |
|-------|--------------|---------------|
| **IaC security scanner** (Checkov, PSRule for Azure, tfsec) | Rules about *configuration*, not syntax | CI, on the PR |
| **Azure Policy** | Refuses non-compliant resources at deployment time | The platform — cannot be bypassed by a pipeline |
| **Defender for Cloud** | Finds what already exists and is wrong | Continuously, after the fact |

⭐ **Only the middle one actually prevents anything.** A scanner can be skipped with `--skip-check`, and a finding after deployment is a cleanup task. Azure Policy is the equivalent of an AWS SCP: it makes the bad state unrepresentable rather than merely discouraged — the same distinction as [§7's explicit deny](../README.md#7-identity--access-management-iam).

### Scenario 3: Anonymous Access, and How Fast It Is Real

**Break it.** Turn on public access for the container, exactly as `allowBlobPublicAccess: true` permits:

```bash
docker compose run --rm cli 'az storage container set-permission -n uploads --public-access blob -o none'
docker compose run --rm cli 'az storage container show-permission -n uploads -o json'
```

**Symptom.** No credential is needed any more. Fetch the blob with nothing but a URL:

```bash
docker compose run --rm cli 'curl -s -o /dev/null -w "%{http_code}\n" \
  http://azurite:10000/devstoreaccount1/uploads/invoices/aug.txt'
```

```text
200
```

**Root cause.** Two settings had to agree: the account allowed public containers, and the container was set to public. That is the Azure version of the S3 bucket policy story from §11's mistakes list, and the outcome is identical — an object readable by anyone who guesses or is told the URL, with no log entry that says "a stranger read this".

**Fix, and the thing to do instead.**

```bash
docker compose run --rm cli 'az storage container set-permission -n uploads --public-access off -o none'
docker compose run --rm cli 'curl -s -o /dev/null -w "after lockdown: %{http_code}\n" \
  http://azurite:10000/devstoreaccount1/uploads/invoices/aug.txt'
```

```text
after lockdown: 403
```

Now serve the same object to a specific person, for a limited time, without making it public — a **SAS token**, Azure's equivalent of an S3 presigned URL:

```bash
docker compose run --rm cli 'S=$(az storage blob generate-sas -c uploads -n invoices/aug.txt \
  --permissions r --expiry 2026-12-31T00:00Z -o tsv); \
  curl -s -o /dev/null -w "with SAS: %{http_code}\n" \
  "http://azurite:10000/devstoreaccount1/uploads/invoices/aug.txt?$S"'
```

```text
with SAS: 200
```

⭐ **That is the pattern for every "users need to download their file" requirement**: private container, short-lived signed URL, generated by your application after it has checked who is asking. Public containers are for things you would put on a billboard.

### Scenario 4: The Connection String Is the Whole Account

**Break it.** Look at what the credential in `docker-compose.yml` actually grants:

```bash
docker compose run --rm cli 'az storage container list -o table && az storage container delete -n uploads --yes -o none && az storage container list -o table'
```

**Symptom.** One environment variable read every container, then deleted one. No second factor, no per-operation authorisation, no expiry.

**Root cause.** A storage connection string embeds the **account key**, which is root on that storage account. It cannot be scoped to one container, it cannot be limited to read, and it does not expire. Anyone who obtains it — from a log line, a stack trace, a `.env` committed by accident, an image layer — has everything until someone notices and rotates.

**Fix.** Ranked, and the ranking matters:

| Approach | Blast radius | When to use it |
|----------|--------------|----------------|
| **Managed identity + RBAC** ⭐ | One role, one scope, no secret exists at all | The default for anything running *in* Azure |
| **Entra ID service principal** | Scoped role, credential rotates | Pipelines outside Azure — pair with OIDC so no secret is stored |
| **SAS token** | One container or blob, one permission, an expiry | Handing access to a client or a partner |
| **Account key** | The entire account, forever | Emulators, and local development. That is the list |

⭐ **Managed identity is the single biggest practical difference from AWS day-to-day**, and it is the same idea as an EC2 instance profile taken further: the resource *is* the identity, so there is no key to leak, rotate, or accidentally print. If a design has a storage key in it, ask what stops that key from being managed identity instead — usually nothing but habit.

Recreate what you deleted, and confirm the account key really did have that power:

```bash
docker compose run --rm cli 'az storage container create -n uploads -o table'
```

### Summary

| Failure | How you detect it | How you prevent it |
|---------|------------------|--------------------|
| Findings that never block | Everything is a warning and the build is always green | Every rule is `error` or removed; decide deliberately |
| Insecure but valid template | Lint and build both pass; the resource is still wrong | An IaC security scanner in CI, and **Azure Policy** at the platform |
| Anonymous public access | `show-permission` returns anything but `off` | `allowBlobPublicAccess: false` on the account; SAS for sharing |
| Account key sprawl | A connection string in env vars, CI, or a `.env` | Managed identity; SAS where an external party needs access |

⭐ **The theme of this lab**: the tools tell you about *syntax*, and the mistakes that hurt are about *configuration and identity*. The Bicep linter, the compiler, and a green pipeline all agreed the template was fine while it enabled TLS 1.0 and anonymous reads. Knowing which tool checks which layer — and which layer can be enforced rather than advised — is the difference between security in a document and security in the platform.

**Write this up** in `azure-notes.md`.

---

## 🧹 Cleanup

```bash
docker compose down -v
rm -f main.json invoice.txt
docker image rm mcr.microsoft.com/azure-storage/azurite mcr.microsoft.com/azure-cli 2>/dev/null || true
```

---

## ✅ Validation

- [ ] Explain what Bicep compiles to, and why that intermediate format exists
- [ ] Make a linter rule block a build, and say why `warning` does not
- [ ] Name three insecure settings a Bicep linter will happily accept
- [ ] Explain which layer — scanner, policy, or posture tool — actually prevents a bad deployment
- [ ] Expose a blob anonymously, then lock it down, and prove both with an HTTP status
- [ ] Produce a SAS token and say what it is scoped to
- [ ] Explain what an account key grants, and the three better options in order
- [ ] Map resource group, subscription, Entra ID and managed identity to their AWS equivalents

---

## 📝 What to Commit

- `main.bicep` (fixed), `bicepconfig.json`, `docker-compose.yml`, `check-template.sh`
- The failing lint output and the passing run after your fix
- The three security findings the linter missed, and how you'd catch them in CI
- Your 200 / 403 / 200-with-SAS sequence
- `azure-notes.md` covering all four scenarios

> ⚠️ Do **not** commit `main.json` — it is a build artefact. Add it to `.gitignore` along with anything else `bicep build` produces.

---

[← Previous Lab: FinOps Cost Review](./lab-03-finops-cost-review.md) | [Back to Module README](../README.md) | [Module 10: Terraform →](../../10-terraform/)
