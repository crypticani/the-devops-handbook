# Module 13: Security Basics — Lab Code

Scanner targets, secret-delivery examples, and supply-chain artifacts.

These are the real files from this module's labs, validated in CI.

> ⚠️ **Much of this is intentionally insecure.** `lab-01` contains hardcoded credentials, a
> world-open security group, a public S3 bucket and a privileged root pod. `lab-02` contains
> Dockerfiles that deliberately bake secrets into image layers. They exist so your scanners
> have something to find. **Never copy them into a real project.**

---

## Contents

### `lab-01/`

An insecure and a hardened Dockerfile, a file with planted secrets, and misconfigured
Terraform and Kubernetes manifests — all deliberately wrong, for scanner practice.

```
lab-01/
├── .gitignore
├── Dockerfile.bad
├── Dockerfile.good
├── config.py
├── main.tf
├── pod.yml
├── secret-test/config.py
├── secret-test/gitignore
├── secret-test/iac-scan/main.tf
└── secret-test/iac-scan/pod.yml
```

### `lab-02/`

The four secret-delivery mechanisms, side by side, plus the Vault + Postgres stack.

```
lab-02/
├── Dockerfile.baked
├── Dockerfile.buildkit
├── compose.yaml
└── rotation-drill.md
```

`Dockerfile.baked` is the ❌ counter-example — it bakes a token into `ENV` and `ARG`, both of
which survive in the image. `Dockerfile.buildkit` is the ✅ version using
`--mount=type=secret`. Compare them with `docker history`.

### `lab-03/`

A demo app, a pinned build, a signature-verification gate, and a Kyverno admission policy.

```
lab-03/
├── Dockerfile
├── Dockerfile.evil
├── Dockerfile.pinned.example
├── app/main.py
├── app/requirements.txt
├── kyverno-verify-images.yaml
└── verify-before-deploy.sh
```

`Dockerfile.evil` exists only to demonstrate a tag being repointed — it is what an image
substitution looks like. `Dockerfile.pinned.example` needs a real base-image digest
substituted before use.

---

## Using these files

```bash
mkdir -p ~/devops-labs/13-security && cd ~/devops-labs/13-security
cp -r /path/to/the-devops-handbook/13-security-basics/code/lab-03/. .

# Lab 03 needs a real digest for the pinned build
docker pull python:3.12-slim
DIGEST=$(docker inspect python:3.12-slim --format '{{index .RepoDigests 0}}' | cut -d@ -f2)
sed "s|sha256:REPLACE-WITH-THE-REAL-DIGEST|$DIGEST|" Dockerfile.pinned.example > Dockerfile.pinned
```

---

<div align="center">

[← Module 13 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
