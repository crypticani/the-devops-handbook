# Lab 03: Supply Chain Security

## 🎯 Objective

Answer three questions about the software you ship: **what is actually in it**, **did we really build it**, and **can anything else get deployed**. You'll generate an SBOM, sign an image and verify the signature, pin dependencies so a build is reproducible, and set up an admission policy that refuses unsigned images — closing the loop from build to runtime.

This closes the biggest gap in Lab 01: scanning tells you about *known* vulnerabilities in *recognised* packages. Supply chain security is about knowing what you have in the first place.

---

## 📋 Prerequisites

- Completed [Lab 01: Security Scanning](./lab-01-security-scanning.md) and [Lab 02: Secrets Management](./lab-02-secrets-management.md)
- Docker with BuildKit
- A local registry (started below) — no external account needed

```bash
docker --version && docker buildx version
```

---

## 📦 Deliverables and Evidence

- An SBOM for an image you built, and the count of components the CVE scanner *couldn't* see
- A signed image, a successful verification, and a **failed** verification on a tampered image
- A build pinned by digest, demonstrated to be reproducible
- An admission policy rejecting an unsigned image
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-03/`](../code/lab-03/).

```bash
cp -r /path/to/the-devops-handbook/13-security-basics/code/lab-03/. .
```

---

## 🔬 Exercise 1: What Is Actually In Your Image?

### Step 1: Set Up

```bash
mkdir -p supply-chain-lab && cd supply-chain-lab

# A local registry, so nothing leaves your machine
docker run -d -p 5000:5000 --name registry --restart=unless-stopped registry:2 >/dev/null
sleep 3
curl -s http://localhost:5000/v2/_catalog
```

### Step 2: Build Something Realistically Messy

```bash
mkdir -p app
cat > app/requirements.txt <<'EOF'
flask==3.0.0
requests==2.31.0
pyyaml==6.0.1
EOF

cat > app/main.py <<'EOF'
from flask import Flask
app = Flask(__name__)

@app.get("/health")
def health():
    return {"status": "ok"}
EOF

cat > Dockerfile <<'EOF'
FROM python:3.12-slim
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# A vendored binary — the way real applications actually acquire dependencies
RUN mkdir -p /app/vendor && \
    echo "#!/bin/sh" > /app/vendor/legacy-tool && \
    echo "echo 'legacy-tool v1.2.3'" >> /app/vendor/legacy-tool && \
    chmod +x /app/vendor/legacy-tool
COPY app/ .
RUN useradd -r -u 10001 appuser && chown -R appuser /app
USER 10001
CMD ["python", "main.py"]
EOF

docker build -q -t localhost:5000/demo-app:v1 .
docker push -q localhost:5000/demo-app:v1
```

### Step 3: Generate an SBOM

```bash
# syft
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /tmp
sudo install /tmp/syft /usr/local/bin/ 2>/dev/null || export PATH="/tmp:$PATH"
syft version

syft localhost:5000/demo-app:v1 -o table | head -25
syft localhost:5000/demo-app:v1 -o spdx-json > sbom.spdx.json
syft localhost:5000/demo-app:v1 -o cyclonedx-json > sbom.cdx.json
```

### Step 4: Compare the SBOM With What the Scanner Sees

```bash
TOTAL=$(jq '[.packages[]] | length' sbom.spdx.json)
echo "SBOM components: $TOTAL"

jq -r '[.packages[].externalRefs[]?.referenceLocator] | map(select(startswith("pkg:")))
       | map(split("/")[0] | sub("pkg:";"")) | group_by(.) | map({(.[0]): length}) | add' sbom.spdx.json

# What the CVE scanner examined
trivy image --format json localhost:5000/demo-app:v1 2>/dev/null \
  | jq '[.Results[].Packages[]?] | length' 2>/dev/null

# ⭐ The vendored binary — in the image, in no package database
docker run --rm localhost:5000/demo-app:v1 /app/vendor/legacy-tool
grep -c 'legacy-tool' sbom.spdx.json || echo "  ⚠️  the vendored binary is NOT in the SBOM either"
```

**✅ Checkpoint:** You now have a concrete number for what the tooling can and can't see. `legacy-tool` runs inside the container and appears in neither the SBOM nor the scan — because neither can identify a shell script someone dropped in.

| Format | Use for |
|--------|---------|
| **SPDX** | Compliance, licence reporting, US federal (EO 14028) |
| **CycloneDX** | ⭐ Security tooling, VEX, dependency-track |
| **syft-json** | Richest detail; syft-specific |

### Step 5: Why an SBOM Is Worth Keeping

The value isn't at build time — it's the day a new CVE drops.

```bash
# Scan the SBOM instead of re-pulling and re-analysing every image
trivy sbom sbom.cdx.json 2>/dev/null | head -20

# ⭐ "Is log4j anywhere in our estate?" — answerable in seconds across thousands of images
jq -r '.packages[] | select(.name | test("flask|requests"; "i")) | "\(.name) \(.versionInfo)"' sbom.spdx.json
```

> ⭐ **The Log4Shell test.** In December 2021 the question that mattered was "which of our services ship log4j, and which version?" Organisations with SBOMs answered in minutes. Organisations without spent weeks. Generate an SBOM per build, store it beside the image, and that question becomes a `jq` query.

---

## 🔬 Exercise 2: Signing and Verification

An SBOM says what's inside. A signature says **who built it** and that **nobody changed it since**.

### Step 1: Install cosign

```bash
curl -sLo /tmp/cosign https://github.com/sigstore/cosign/releases/download/v2.4.0/cosign-linux-amd64
sudo install /tmp/cosign /usr/local/bin/cosign
cosign version | head -3
```

### Step 2: Sign With a Key Pair

```bash
COSIGN_PASSWORD="" cosign generate-key-pair
ls -l cosign.key cosign.pub

DIGEST=$(docker inspect localhost:5000/demo-app:v1 --format '{{index .RepoDigests 0}}' 2>/dev/null \
         || crane digest localhost:5000/demo-app:v1 2>/dev/null)
echo "signing: $DIGEST"

COSIGN_PASSWORD="" cosign sign --key cosign.key --yes --allow-insecure-registry \
  localhost:5000/demo-app:v1
```

### Step 3: Verify

```bash
cosign verify --key cosign.pub --allow-insecure-registry localhost:5000/demo-app:v1 2>&1 | tail -12
```

```
Verification for localhost:5000/demo-app:v1 --
The following checks were performed:
  - The cosign claims were validated
  - The signatures were verified against the specified public key
```

### Step 4: Watch Verification Fail

```bash
# Build a DIFFERENT image and push it to the same tag — a registry compromise, or a
# careless overwrite by another pipeline
cat > Dockerfile.evil <<'EOF'
FROM python:3.12-slim
RUN echo "malicious payload" > /tmp/pwned
CMD ["sleep", "3600"]
EOF
docker build -q -t localhost:5000/demo-app:v1 -f Dockerfile.evil .
docker push -q localhost:5000/demo-app:v1

cosign verify --key cosign.pub --allow-insecure-registry localhost:5000/demo-app:v1 2>&1 | tail -4
#   ⭐ "no matching signatures" — the tag now points at an unsigned image
```

**✅ Checkpoint:** Signature verification is what makes a **tag** trustworthy. Without it, a mutable tag means whoever can push to the registry decides what runs in production.

```bash
# Rebuild and re-sign the real one
docker build -q -t localhost:5000/demo-app:v1 . && docker push -q localhost:5000/demo-app:v1
COSIGN_PASSWORD="" cosign sign --key cosign.key --yes --allow-insecure-registry localhost:5000/demo-app:v1
```

### Step 5: Keyless Signing

Managing a private key reintroduces the problem from Lab 02. Keyless signing removes it.

```bash
# In CI, with OIDC available, no key exists at all:
#   cosign sign --yes ghcr.io/myorg/app@sha256:...
#
# The identity comes from the CI OIDC token; the signature and a short-lived
# certificate go to the public Rekor transparency log.
#
# Verification asserts WHO signed it:
#   cosign verify \
#     --certificate-identity-regexp 'https://github.com/myorg/.*' \
#     --certificate-oidc-issuer https://token.actions.githubusercontent.com \
#     ghcr.io/myorg/app@sha256:...
```

| | Key-based | Keyless (Sigstore) |
|---|-----------|-------------------|
| Private key to protect | ⚠️ Yes | ⭐ None |
| Identity proven | "whoever holds the key" | ⭐ "this repo, this workflow, this ref" |
| Revocation | Rotate the key, re-sign everything | Certificate expires in minutes |
| Audit trail | Whatever you build | ⭐ Public Rekor transparency log |
| Works offline | Yes | Needs Fulcio/Rekor |

### Step 6: Attach the SBOM as an Attestation

```bash
COSIGN_PASSWORD="" cosign attest --key cosign.key --yes --allow-insecure-registry \
  --predicate sbom.spdx.json --type spdxjson localhost:5000/demo-app:v1

cosign verify-attestation --key cosign.pub --allow-insecure-registry \
  --type spdxjson localhost:5000/demo-app:v1 2>&1 | tail -3
```

> ⭐ An **attestation** is a signed statement *about* an artifact. Beyond the SBOM you can attest the scan results, the test results, the build provenance (SLSA), and a manual approval. Admission control can then require them: *"only run images that have a signed SBOM, a scan with no CRITICALs, and a provenance statement naming our CI."*

---

## 🔬 Exercise 3: Pinning and Reproducibility

### Step 1: See Why Tags Aren't Enough

```bash
docker pull -q python:3.12-slim
docker inspect python:3.12-slim --format '{{index .RepoDigests 0}}'
```

The tag `3.12-slim` points at a different image today than it did last month. Every rebuild silently picks up a new base — usually good (security patches), occasionally a breaking change you didn't ask for, and at worst a compromised upstream.

### Step 2: Pin by Digest

```bash
BASE_DIGEST=$(docker inspect python:3.12-slim --format '{{index .RepoDigests 0}}' | cut -d@ -f2)
echo "pinning to: $BASE_DIGEST"

cat > Dockerfile.pinned <<EOF
# ⭐ Immutable: this digest can never point at different content
FROM python:3.12-slim@$BASE_DIGEST
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt 2>/dev/null \
 || pip install --no-cache-dir -r requirements.txt
COPY app/ .
RUN useradd -r -u 10001 appuser && chown -R appuser /app
USER 10001
CMD ["python", "main.py"]
EOF

docker build -q -t localhost:5000/demo-app:pinned -f Dockerfile.pinned .
```

### Step 3: Pin Dependencies Too

A pinned base image with unpinned Python packages is only half-pinned.

```bash
pip install --quiet pip-tools 2>/dev/null || python3 -m pip install --quiet --user pip-tools 2>/dev/null

cat > app/requirements.in <<'EOF'
flask
requests
pyyaml
EOF

# ⭐ Generates every transitive dependency with a SHA256 hash
pip-compile --generate-hashes --quiet --output-file app/requirements.lock app/requirements.in 2>/dev/null \
  && head -20 app/requirements.lock \
  || echo "(pip-tools unavailable — the pattern is what matters)"
```

```
# requirements.lock (generated)
flask==3.0.3 \
    --hash=sha256:34e815dfaa43340d1d15a5c3a02b8476004037eb4840b34910c6e21679d288f3 \
    --hash=sha256:...
```

With `--require-hashes`, pip refuses any package whose content doesn't match — so a compromised PyPI mirror or a hijacked package version cannot substitute different code.

| Ecosystem | Lockfile | Hash verification |
|-----------|----------|-------------------|
| Python | `requirements.lock` (pip-tools), `poetry.lock`, `uv.lock` | `--require-hashes` |
| Node | `package-lock.json`, `pnpm-lock.yaml` | `npm ci` ⭐ (not `npm install`) |
| Go | `go.sum` | ⭐ Automatic, plus the checksum database |
| Rust | `Cargo.lock` | Automatic |
| Terraform | `.terraform.lock.hcl` | Automatic |
| Docker base | `FROM image@sha256:...` | Automatic |
| GH Actions | `uses: org/action@<full-sha>` | ⭐ Tags are mutable — pin the SHA |

### Step 4: Prove Reproducibility

```bash
docker build -q -t localhost:5000/demo-app:build1 -f Dockerfile.pinned . >/dev/null
docker build -q --no-cache -t localhost:5000/demo-app:build2 -f Dockerfile.pinned . >/dev/null

# The layer that matters — the dependency install
docker history --no-trunc --format '{{.Size}}\t{{.CreatedBy}}' localhost:5000/demo-app:build1 | grep pip | head -1
docker history --no-trunc --format '{{.Size}}\t{{.CreatedBy}}' localhost:5000/demo-app:build2 | grep pip | head -1
```

> 💡 Byte-identical image digests require more work (timestamps, file ordering, `SOURCE_DATE_EPOCH`), which is what the *reproducible builds* movement is about. **Dependency reproducibility** — the same inputs producing the same package versions — is achievable today with lockfiles and digests, and it's where the security value is.

---

## 🔬 Exercise 4: Enforce It at Deploy Time

Signing is worthless if nothing checks the signature.

### Step 1: The Verification Gate as a Script

```bash
cat > verify-before-deploy.sh <<'SH'
#!/usr/bin/env bash
# Run before every deploy. Exits non-zero if the image is not trustworthy.
set -uo pipefail

IMAGE="${1:?usage: verify-before-deploy.sh <image>}"
PUBKEY="${COSIGN_PUBKEY:-cosign.pub}"
FAIL=0

echo "── 1. signature ──"
if cosign verify --key "$PUBKEY" --allow-insecure-registry "$IMAGE" >/dev/null 2>&1; then
  echo "  ✅ signed and verified"
else
  echo "  ❌ NOT signed by our key"; FAIL=1
fi

echo "── 2. SBOM attestation ──"
if cosign verify-attestation --key "$PUBKEY" --allow-insecure-registry \
     --type spdxjson "$IMAGE" >/dev/null 2>&1; then
  echo "  ✅ SBOM attestation present"
else
  echo "  ⚠️  no SBOM attestation"; FAIL=1
fi

echo "── 3. vulnerabilities ──"
if trivy image --quiet --severity CRITICAL --exit-code 1 --ignore-unfixed "$IMAGE" >/dev/null 2>&1; then
  echo "  ✅ no fixable CRITICALs"
else
  echo "  ❌ fixable CRITICAL vulnerabilities present"; FAIL=1
fi

echo "── 4. pinned by digest ──"
if [[ "$IMAGE" == *"@sha256:"* ]]; then
  echo "  ✅ digest-pinned"
else
  echo "  ⚠️  deploying a mutable TAG — the content can change under you"
fi

exit $FAIL
SH
chmod +x verify-before-deploy.sh

./verify-before-deploy.sh localhost:5000/demo-app:v1; echo "exit=$?"
./verify-before-deploy.sh localhost:5000/demo-app:pinned; echo "exit=$?"    # unsigned → fails
```

**✅ Checkpoint:** `demo-app:v1` passes, `demo-app:pinned` fails because it was never signed. That's a gate you can put in front of any deploy.

### Step 2: Admission Control in Kubernetes

A script protects your pipeline. Admission control protects the **cluster** — including from anyone who bypasses the pipeline.

```bash
cat > kyverno-verify-images.yaml <<'YAML'
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
spec:
  validationFailureAction: Enforce        # Audit first, then Enforce
  background: false
  rules:
    - name: require-signature
      match:
        any:
          - resources:
              kinds: [Pod]
              namespaces: ["production", "staging"]
      verifyImages:
        - imageReferences: ["ghcr.io/myorg/*"]
          mutateDigest: true              # ⭐ rewrites the tag to the verified digest
          required: true
          attestors:
            - entries:
                - keyless:
                    subject: "https://github.com/myorg/*"
                    issuer: "https://token.actions.githubusercontent.com"

    - name: require-sbom-attestation
      match:
        any:
          - resources:
              kinds: [Pod]
              namespaces: ["production"]
      verifyImages:
        - imageReferences: ["ghcr.io/myorg/*"]
          attestations:
            - predicateType: https://spdx.dev/Document
              attestors:
                - entries:
                    - keyless:
                        subject: "https://github.com/myorg/*"
                        issuer: "https://token.actions.githubusercontent.com"

    - name: no-latest-tag
      match:
        any:
          - resources:
              kinds: [Pod]
      validate:
        message: "Deploy an immutable digest, not a mutable tag."
        pattern:
          spec:
            containers:
              - image: "*@sha256:*"
YAML
python3 -c "import yaml,sys; list(yaml.safe_load_all(open('kyverno-verify-images.yaml'))); print('✅ valid policy YAML')"
```

> ⭐ **`mutateDigest: true` is the subtle, important one.** Kyverno resolves the tag to the digest it verified and rewrites the pod spec. Without it there's a time-of-check-to-time-of-use gap: you verify `:v1`, and by the time the kubelet pulls, `:v1` points somewhere else.

### Step 3: The Full Pipeline

```yaml
# .github/workflows/secure-build.yml
permissions:
  contents: read
  packages: write
  id-token: write          # ⭐ keyless signing needs this

steps:
  - uses: actions/checkout@v4

  - name: Secret scan (full history)
    uses: gitleaks/gitleaks-action@v2

  - name: Dependency + IaC + secret scan of the source
    run: trivy fs --scanners vuln,secret,misconfig --exit-code 1 --severity HIGH,CRITICAL .

  - name: SAST
    run: semgrep --config=auto --error .

  - id: build
    uses: docker/build-push-action@v6
    with:
      push: true
      tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
      provenance: true          # ⭐ SLSA build provenance
      sbom: true

  # ⭐ Everything below operates on the DIGEST, never the tag
  - name: Scan the built image
    run: trivy image --exit-code 1 --severity CRITICAL --ignore-unfixed
         ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}

  - name: Generate SBOM
    run: syft ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }} -o spdx-json > sbom.json

  - uses: sigstore/cosign-installer@v3
  - name: Sign and attest — keyless
    run: |
      IMG=ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}
      cosign sign --yes "$IMG"
      cosign attest --yes --predicate sbom.json --type spdxjson "$IMG"

  - name: Deploy the verified digest
    run: kubectl set image deploy/app app=ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}
```

| Control | What it stops |
|---------|--------------|
| Secret scan | Credentials reaching the remote |
| Dependency scan | Known-vulnerable libraries |
| SAST | Your own code's flaws |
| Image scan **on the digest** | Vulnerabilities in what you actually built |
| SBOM | Not knowing what you shipped when the next CVE lands |
| Provenance | "Which commit and workflow produced this?" |
| Signature | A registry compromise, or a tag overwrite |
| Admission control | Anything that bypassed all of the above |

---

## 🧨 Break It: Four Supply Chain Failures

### Scenario 1: The Mutable Tag

**Break it:**

```bash
cd supply-chain-lab
docker build -q -t localhost:5000/svc:v1.0.0 . && docker push -q localhost:5000/svc:v1.0.0
GOOD=$(crane digest localhost:5000/svc:v1.0.0 2>/dev/null || \
       docker inspect localhost:5000/svc:v1.0.0 --format '{{index .RepoDigests 0}}' | cut -d@ -f2)
echo "released digest: $GOOD"

# A release tag is supposed to be immutable. Nothing enforces that.
docker build -q -t localhost:5000/svc:v1.0.0 -f Dockerfile.evil . && docker push -q localhost:5000/svc:v1.0.0
NOW=$(crane digest localhost:5000/svc:v1.0.0 2>/dev/null || \
      docker inspect localhost:5000/svc:v1.0.0 --format '{{index .RepoDigests 0}}' | cut -d@ -f2)
echo "digest now:      $NOW"
[ "$GOOD" != "$NOW" ] && echo "  🚨 v1.0.0 now points at DIFFERENT content"
```

**Symptom:** `v1.0.0` is a different image than the one you tested, reviewed, and released. Every node that pulls it from now on runs something else — and your manifests, your changelog and your audit trail all still say `v1.0.0`.

**Investigate:**

```bash
curl -s http://localhost:5000/v2/svc/tags/list | jq
docker run --rm localhost:5000/svc:v1.0.0 cat /tmp/pwned 2>/dev/null && echo "  🚨 running the substituted image"
```

**Root cause:** Tags are mutable pointers. Anyone with push access — a compromised CI token, a mistaken pipeline, a malicious insider — can repoint one, and nothing about the reference changes.

**Fix:**

```bash
# 1. Deploy digests, not tags
echo "deploy: localhost:5000/svc@$GOOD"

# 2. Enable registry tag immutability
#    ECR:  aws ecr put-image-tag-mutability --repository-name svc --image-tag-mutability IMMUTABLE
#    GHCR/Harbor/Artifactory: immutable tag rules in the repo settings

# 3. Sign, and verify at admission — a substituted image has no valid signature
```

```yaml
# ⭐ In Kubernetes, always:
image: ghcr.io/myorg/svc@sha256:abc123...
# never:
image: ghcr.io/myorg/svc:v1.0.0
```

> ⭐ Tags are for humans. **Digests are for machines.** Let CI resolve the tag to a digest once, then carry the digest through scanning, signing, and deployment. Everything downstream is then referring to the same bytes.

---

### Scenario 2: Typosquatting

**Break it:**

```bash
cat > requirements-typo.txt <<'EOF'
flask==3.0.0
requsts==2.31.0
python-dateutil==2.8.2
EOF
grep -n 'requsts' requirements-typo.txt
```

**Symptom:** `requsts` (missing the `e`) is a plausible typo. On a public index, names one edit away from popular packages get registered by attackers. `pip install` finds it, installs it, and runs its `setup.py` — **arbitrary code execution during the build**, before any scanner sees the image.

**Investigate:**

```bash
# Compare declared dependencies against what you actually intended
python3 - <<'PY'
POPULAR = {"requests","flask","django","numpy","pandas","urllib3","boto3","pyyaml","cryptography"}
def dist(a, b):
    if abs(len(a)-len(b)) > 2: return 9
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j]+1, cur[j-1]+1, prev[j-1] + (ca != cb)))
        prev = cur
    return prev[-1]

for line in open("requirements-typo.txt"):
    name = line.split("==")[0].strip()
    if not name or name in POPULAR: continue
    for p in POPULAR:
        if 0 < dist(name, p) <= 2:
            print(f"  ⚠️  '{name}' is {dist(name,p)} edit(s) from '{p}' — typosquat?")
PY
```

**Root cause:** Public package indexes allow anyone to register any unclaimed name. Related attacks: **dependency confusion** (an attacker publishes your *internal* package name publicly at a higher version, and your resolver prefers it), and **maintainer compromise** of a legitimate package.

**Fix:**

```bash
rm -f requirements-typo.txt
```

| Control | Stops |
|---------|-------|
| ⭐ **Lockfile with hashes** | Any substitution, including a hijacked version of the *right* package |
| ⭐ **Private registry/proxy** (Artifactory, Nexus, CodeArtifact) | Uncurated public packages entering at all |
| Explicit index pinning (`--index-url`, `.npmrc` scopes) | Dependency confusion |
| `pip install --require-hashes` / `npm ci` | Anything not in the lockfile |
| `--ignore-scripts` (npm) | Install-time code execution |
| Dependency review in PRs | A new dependency arriving unnoticed |
| SBOM diff between releases | ⭐ "What changed in our dependency tree?" |

```bash
# ⭐ Diff SBOMs between two versions — the single best signal that something changed
# syft app:v1 -o json > v1.json && syft app:v2 -o json > v2.json
# diff <(jq -r '.artifacts[].name' v1.json | sort) <(jq -r '.artifacts[].name' v2.json | sort)
```

---

### Scenario 3: The GitHub Action Pinned to a Tag

**Break it:**

```bash
mkdir -p .github/workflows
cat > .github/workflows/risky.yml <<'YAML'
name: Risky
on: [push]
permissions:
  contents: write
  id-token: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4                    # ⚠️ mutable tag
      - uses: some-community/setup-tool@v1           # ⚠️ mutable tag, third party
      - uses: another/deploy-action@main             # ⚠️⚠️ a BRANCH
        env:
          AWS_ROLE: ${{ secrets.AWS_DEPLOY_ROLE }}
YAML
python3 -c "import yaml;yaml.safe_load(open('.github/workflows/risky.yml'));print('valid YAML — and dangerous')"
```

**Symptom:** Nothing. It works. But `@v1` and `@main` are **mutable git refs**. Whoever controls that repository — the maintainer, or anyone who compromises their account — can change what runs inside your pipeline, with access to `secrets` and your OIDC identity. This is not hypothetical: it's how several real supply chain compromises worked.

**Investigate:**

```bash
grep -rn 'uses:' .github/workflows/ | grep -vE 'uses:.*@[0-9a-f]{40}' \
  || echo "  ✅ everything pinned to a full SHA"
```

**Root cause:** Every `uses:` is remote code execution in your CI, with your permissions. A tag is a pointer the *other* repository controls.

**Fix:**

```bash
cat > .github/workflows/safe.yml <<'YAML'
name: Safe
on: [push]
permissions:
  contents: read          # ⭐ least privilege by default
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write     # only where actually needed
    steps:
      # ⭐ Full commit SHA. The comment tracks the human-readable version.
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
      - uses: sigstore/cosign-installer@59acb6260d9c0ba8f4a2f9d9b48431a222b68e20 # v3.5.0
YAML
python3 -c "import yaml;yaml.safe_load(open('.github/workflows/safe.yml'));print('✅ pinned')"

# Automate it: `pin-github-action`, or Dependabot, which updates SHAs and keeps the comment
```

**And never interpolate untrusted input into a shell:**

```yaml
# ❌ The PR title is attacker-controlled and becomes shell code
- run: echo "Building ${{ github.event.pull_request.title }}"

# ✅ Pass through the environment, where it stays data
- run: echo "Building $TITLE"
  env:
    TITLE: ${{ github.event.pull_request.title }}
```

```bash
rm -rf .github
```

---

### Scenario 4: The SBOM Nobody Looks At

**Break it:**

```bash
# The compliance-checkbox version: generate it, upload it, never read it
syft localhost:5000/demo-app:v1 -o spdx-json > sbom-archived.json
ls -lh sbom-archived.json
echo "→ uploaded to the artifact store. Job done. ✅"
```

**Symptom:** A file exists. Six months later a critical CVE drops in a transitive dependency and the questions are: *which of our 200 services ship it?* *Which versions?* *Which are internet-facing?* Nobody has ever queried these files, there's no index, and each one is attached to a build number nobody can map to a running service.

**Investigate — the questions an SBOM must be able to answer:**

```bash
echo "── 1. Do we ship package X, and at what version? ──"
jq -r '.packages[] | select(.name=="requests") | "\(.name) \(.versionInfo)"' sbom.spdx.json

echo "── 2. What licences are we shipping? ──"
jq -r '[.packages[].licenseConcluded // "NOASSERTION"] | group_by(.) | map({(.[0]): length}) | add' sbom.spdx.json

echo "── 3. What changed between releases? ──"
echo "   diff <(jq -r '.packages[].name' old.json|sort) <(jq -r '.packages[].name' new.json|sort)"

echo "── 4. Which RUNNING services contain it? ──"
echo "   ⚠️  requires SBOMs linked to deployed digests, not to build numbers"
```

**Root cause:** Generating an SBOM is the easy 10%. The value is in **storage keyed by image digest**, **continuous re-scanning as new CVEs are published**, and a **link from digest to running workload**.

**Fix:**

```bash
# 1. ⭐ Attach the SBOM to the image itself, so it travels with the artifact
COSIGN_PASSWORD="" cosign attest --key cosign.key --yes --allow-insecure-registry \
  --predicate sbom.spdx.json --type spdxjson localhost:5000/demo-app:v1

# Anyone, anywhere, can now retrieve it from the digest alone
cosign download attestation --allow-insecure-registry localhost:5000/demo-app:v1 2>/dev/null \
  | jq -r '.payload' | base64 -d 2>/dev/null | jq '.predicate.name' 2>/dev/null | head -1
```

```bash
# 2. Continuous re-scan — the CVE that matters didn't exist when you built
#    trivy sbom sbom.spdx.json          # nightly, against today's database
#
# 3. An inventory that maps DIGEST → SBOM → running workload
#    kubectl get pods -A -o json | jq -r '.items[].status.containerStatuses[]?.imageID' | sort -u
#
# 4. Dependency-Track or a similar server ingests SBOMs and alerts you
#    when a new CVE affects something you already shipped.
```

> ⭐ **The test for whether your SBOM programme is real**: can you answer *"which running services contain package X at version Y?"* in under five minutes, without rebuilding anything? If not, you are generating files, not managing a supply chain.

---

### Summary

| Failure | Detection | Prevention |
|---------|-----------|------------|
| Mutable tag repointed | Digest changed for the same tag | Deploy digests; immutable tags; verify signatures |
| Typosquat / dependency confusion | Edit-distance check; SBOM diff | Lockfiles with hashes; private proxy; index pinning |
| Action pinned to a tag or branch | `grep uses:` for non-SHA refs | Full commit SHAs; least-privilege `permissions:` |
| SBOM nobody queries | Try to answer "who ships X?" | Attest to the digest; re-scan continuously; keep an inventory |

**The supply chain checklist:**

- [ ] Base images pinned by **digest**
- [ ] Dependencies in a lockfile with **hashes**; `npm ci` / `--require-hashes`
- [ ] Every GitHub Action pinned to a **full commit SHA**
- [ ] Workflow `permissions:` set explicitly, least privilege
- [ ] SBOM generated per build and **attested to the image digest**
- [ ] Images **signed**, ideally keyless via OIDC
- [ ] Build **provenance** (SLSA) attested
- [ ] Registry configured for **immutable tags**
- [ ] Deployments reference **digests**, never tags
- [ ] **Admission control** verifies signature and attestations before anything runs
- [ ] SBOMs re-scanned on a schedule against a current CVE database
- [ ] An inventory mapping running digests to SBOMs

> ⭐ **The three questions this lab answers** — *what is in it*, *did we build it*, *can anything else run* — are what "supply chain security" means in practice. Lab 01's scanners tell you about known problems in things they recognise. This lab is about the things they don't.

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
cd supply-chain-lab 2>/dev/null || true
docker rm -f registry 2>/dev/null
docker rmi -f localhost:5000/demo-app:v1 localhost:5000/demo-app:pinned \
  localhost:5000/demo-app:build1 localhost:5000/demo-app:build2 localhost:5000/svc:v1.0.0 2>/dev/null
cd .. && rm -rf supply-chain-lab
docker ps -a | grep registry || echo "✅ clean"
```

---

## ✅ Validation

- [ ] Generate an SBOM and state how many components the CVE scanner didn't examine
- [ ] Explain what SPDX and CycloneDX are each used for
- [ ] Sign an image, verify it, and make verification fail by substituting the tag
- [ ] Explain why keyless signing is stronger than a key pair
- [ ] Attach an SBOM as an attestation and retrieve it from the digest
- [ ] Pin a base image by digest and dependencies by hash
- [ ] Explain the difference between reproducible builds and reproducible dependencies
- [ ] Write an admission policy requiring a signature, and explain `mutateDigest`
- [ ] Explain why a GitHub Action pinned to `@v1` is remote code execution
- [ ] Answer "which running services contain package X?" and describe what infrastructure that needs

---

## 📝 What to Commit

- `sbom.spdx.json` and `sbom.cdx.json`, with your component-count analysis
- Terminal output showing verification succeeding, then failing after the tag was repointed
- `Dockerfile.pinned` and a hash-pinned lockfile
- `verify-before-deploy.sh` and `kyverno-verify-images.yaml`
- The secure pipeline workflow
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: Secrets Management](./lab-02-secrets-management.md) | [Back to Module README](../README.md) | [Module 14: System Design →](../../14-system-design-devops/)
