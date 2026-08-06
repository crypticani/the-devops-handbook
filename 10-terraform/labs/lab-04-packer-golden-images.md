# Lab 04: Packer and Golden Images

## 🎯 Objective

Bake an image, verify it before it is allowed to exist, and hand it to Terraform by digest — the immutable-infrastructure loop, end to end, on your laptop for free.

Then break the four things that make golden images dangerous rather than useful: an unpinned base, a baked secret, a build that succeeds while producing a broken image, and a mutable tag that makes rollback impossible.

---

## 📋 Prerequisites

- Read [§9 Packer — Building Golden Images](../README.md#9-packer--building-golden-images)
- Completed [Lab 03: Modules and Environments](./lab-03-modules-and-environments.md)
- Docker running, and Packer + Terraform installed

```bash
docker version --format 'docker {{.Server.Version}}'
packer version
terraform version
```

> ⭐ This lab uses Packer's **Docker builder**, so it costs nothing and needs no cloud account. Every concept maps one-to-one onto `amazon-ebs`: same sources → provisioners → post-processors shape, same reproducibility problems, same fixes. The AMI version of this config is in §9.

---

## 📦 Deliverables and Evidence

- A built image, with the `verify` provisioner output showing what it checked
- `manifest.json`, and the digest Terraform actually ran
- Two builds of the same tag producing different digests, and the same two builds pinned by digest producing identical ones
- A baked secret, found with `docker history`, and the verify step that catches it
- A build that "succeeded" while producing a broken image, and the one-word fix
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-04/`](../code/lab-04/).

```bash
cp -r /path/to/the-devops-handbook/10-terraform/code/lab-04/. .
```

```text
packer/base.pkr.hcl         the build: source → provisioners → post-processors
packer/scripts/install.sh   what gets baked in (packages, agent, non-root user)
packer/scripts/verify.sh    ⭐ the gate between "commands ran" and "fit to deploy"
terraform/main.tf           the consumer: resolves the tag to a digest and runs it
```

---

## 🔬 Exercise 1: Bake, Verify, Consume

### Step 1: Build

```bash
cd packer
packer init .
packer fmt -check .            # ⭐ CI should enforce this, exactly like terraform fmt
packer validate -var image_version=v1 .
packer build -var image_version=v1 -var git_commit="$(git rev-parse --short HEAD)" .
```

```text
==> app-base.docker.base: Provisioning with shell script: scripts/install.sh
    app-base.docker.base: + apt-get install -y --no-install-recommends curl ca-certificates procps
==> app-base.docker.base: Provisioning with shell script: scripts/verify.sh
    app-base.docker.base: verify: OK — agent, user, ownership, cleanliness, no baked credentials
==> app-base.docker.base: Committing the container
    app-base.docker.base: Image ID: sha256:8880a63a4570...
==> app-base.docker.base: Running post-processor:  (type docker-tag)
    app-base.docker.base (docker-tag): Repository: app-base:v1
Build 'app-base.docker.base' finished after 2 minutes 48 seconds.
```

Three minutes, once — and then every instance starts ready. That is the trade: build-time cost paid once, boot-time cost removed from every launch.

### Step 2: Look at What You Built

```bash
cat manifest.json | python3 -m json.tool | head -20
docker image inspect app-base:v1 --format '{{.Config.User}} {{.Config.Entrypoint}}'
docker image inspect app-base:v1 --format '{{json .Config.Labels}}' | python3 -m json.tool
docker run --rm app-base:v1 whoami            # ⭐ non-root, without any service remembering to
docker run --rm app-base:v1 metrics-agent
```

```text
appuser
metrics-agent 1.4.0
```

The `org.opencontainers.image.revision` label is the one to notice: any running container traces back to the commit that built it. Without that, "which build is this?" during an incident is guesswork.

### Step 3: Hand It to Terraform

```bash
cd ../terraform
terraform init
terraform apply -auto-approve -var image_version=v1
```

```text
Outputs:

image_digest = "app-base@sha256:8880a63a457014c3d5b3f49b5cd4e17f30a559b874d37e4f9e96a62cab93ab12"
running = ["app-0", "app-1"]
```

Read `main.tf` and notice the interface between the two tools: the data source resolves the *tag* to a *digest* once, and every container is pinned to that digest. A rebuild of `v1` halfway through an apply therefore cannot give you a mixed fleet — which is exactly what happens when resources reference the tag directly.

```bash
docker exec app-0 whoami                     # appuser — the baked default survived
docker inspect app-0 --format '{{.Config.Labels}}' | tr ',' '\n' | grep base-version
```

### Step 4: The Guardrail

```bash
terraform plan -var image_version=latest
```

```text
Error: Invalid value for variable

  Refusing a mutable tag. Pass the version Packer stamped (e.g. the git SHA).
```

That validation block is not style policing. A mutable tag makes rollback *impossible*, because the version you would roll back to has already been overwritten — scenario 4.

---

## 🧨 Break It: Four Golden Image Failures

### Scenario 1: The Unpinned Base

**Break it.** The config defaults to `python:3.12-slim` — a tag, which is a moving pointer. Simulate what happens when upstream publishes a new one:

```bash
cd ../packer
packer build -var image_version=v2 .                 # a second build, same config
docker images app-base --format '{{.Tag}}  {{.ID}}  {{.CreatedAt}}'
docker image inspect app-base:v1 app-base:v2 --format '{{.Id}}'
```

**Symptom.** Two builds of an *identical configuration*, two different image IDs. Now pull a moved base and rebuild:

```bash
docker pull python:3.12-slim                          # in reality: upstream moved it
docker image inspect python:3.12-slim --format '{{index .RepoDigests 0}}'
```

Nothing warns you. The build succeeds, the tag is applied, and the image contains a different Python patch level, different OpenSSL, different everything the base maintainer changed. The scan you ran last week was of a different artefact.

**Root cause.** `image = "python:3.12-slim"` asks for "whatever that name means at build time". Reproducibility requires content addressing, not names.

**Fix.** Resolve the digest and pin it — and note you never invent this value, you read it:

```bash
docker pull python:3.12-slim
BASE=$(docker image inspect python:3.12-slim --format '{{index .RepoDigests 0}}')
echo "$BASE"                                          # python@sha256:...
packer build -var base_image="$BASE" -var image_version=v3 .
python3 -c "import json;print(json.load(open('manifest.json'))['builds'][-1]['custom_data'])"
```

The digest is now recorded in `manifest.json` alongside the git commit, so the build is reproducible and auditable. Updating the base becomes a deliberate commit that changes one string — which is the point of immutable infrastructure, not a bureaucratic inconvenience.

### Scenario 2: The Baked Secret

**Break it.** Pass a credential the way people do when they need private-repo access at build time:

```bash
docker run --rm -e API_TOKEN=super-secret-value app-base:v1 env | grep API_TOKEN   # runtime, fine
# Now bake one in — this is the mistake:
cat > /tmp/leak.pkr.hcl <<'EOF'
source "docker" "leak" {
  image  = "app-base:v1"
  commit = true
  changes = ["ENV API_TOKEN=super-secret-value"]
}
build {
  sources = ["source.docker.leak"]
  post-processor "docker-tag" {
    repository = "app-base"
    tags       = ["leaked"]
  }
}
EOF
packer build /tmp/leak.pkr.hcl
```

**Symptom.** The image works perfectly. The application starts, tests pass, nothing anywhere reports a problem:

```bash
docker image inspect app-base:leaked --format '{{json .Config.Env}}' | tr ',' '\n' | grep -i token
docker history --no-trunc app-base:leaked | grep -i token | head -2
```

```text
"API_TOKEN=super-secret-value"
```

**Root cause.** Anything in the image's environment, layers, or history is readable by anyone who can pull the image — and unlike a leaked file, you cannot delete it in a later layer, because the layer is still there. An image is a distribution mechanism; treat everything in it as published.

**Fix.** Two layers of defence, and you already have both:

1. **Runtime injection.** Secrets come from the environment at run time, or a secret manager, or a mounted file (Module 13 §2). Build-time credentials that are genuinely needed use `--secret` mounts that never land in a layer.
2. **The verify step catches it.** Look at `verify.sh` — it fails the build if the environment contains anything matching `secret|password|token|api_key`. Prove it:

```bash
sed -i 's|"USER appuser",|"USER appuser",\n    "ENV API_TOKEN=oops",|' base.pkr.hcl
packer build -var image_version=v4 . 2>&1 | grep -E 'VERIFY FAILED|Build .* errored'
git checkout base.pkr.hcl 2>/dev/null || sed -i '/ENV API_TOKEN=oops/d' base.pkr.hcl
docker rmi app-base:leaked
```

```text
    app-base.docker.base: VERIFY FAILED: a credential is present in the image environment
==> Wait completed after ... Build 'app-base.docker.base' errored
```

### Scenario 3: The Build That Succeeded and the Image That Is Broken

**Break it.** Remove the `-e` from the provisioner's shell — the default behaviour of many inline provisioners, and the single most dangerous line in this file:

```bash
sed -i 's|execute_command = "/bin/sh -euxc .{{ .Path }}."|execute_command = "/bin/sh -uxc \x27{{ .Path }}\x27"|' base.pkr.hcl
grep execute_command base.pkr.hcl
# and make one step fail the way a flaky mirror does
sed -i 's|apt-get install -y --no-install-recommends curl ca-certificates procps|apt-get install -y --no-install-recommends curl ca-certificates procps nonexistent-package-xyz|' scripts/install.sh
packer build -var image_version=v5 . 2>&1 | tail -6
```

**Symptom.** With `-e` gone, the failing `apt-get` prints an error, the script keeps going, and the script's *last* command determines the exit status — so the build reports success. Except the verify provisioner is still there, and it catches what the install step lost:

```text
    app-base.docker.base: VERIFY FAILED: monitoring agent missing
```

Now imagine the verify provisioner is not there — which is how most Packer configs in the wild look. You would have published `app-base:v5`, rolled it out to a fleet, and discovered on the next incident that no instance is reporting metrics.

**Root cause.** Two separate defects, and you need both fixes:

- A shell without `-e` turns "a step failed" into "the last step passed".
- A build with no verification proves only that commands exited, never that the artefact is correct.

**Fix.**

```bash
sed -i 's|nonexistent-package-xyz||' scripts/install.sh
sed -i 's|execute_command = "/bin/sh -uxc .{{ .Path }}."|execute_command = "/bin/sh -euxc \x27{{ .Path }}\x27"|' base.pkr.hcl
grep -n 'execute_command' base.pkr.hcl
packer build -var image_version=v5 . 2>&1 | grep -E 'verify: OK|finished'
```

> ⭐ This is the same lesson as `set -euo pipefail` in Module 04, with higher stakes: the artefact of a silent failure here is not a bad log line, it is a machine image you deploy to every instance.

### Scenario 4: The Mutable Tag and the Impossible Rollback

**Break it.** Publish twice to the same tag — the natural thing to do when the tag is `stable`, `prod`, or `latest`:

```bash
packer build -var image_version=rolling . >/dev/null 2>&1
docker image inspect app-base:rolling --format 'first  {{.Id}}'
packer build -var image_version=rolling -var base_image=python:3.12 . >/dev/null 2>&1
docker image inspect app-base:rolling --format 'second {{.Id}}'
```

**Symptom.** The tag now points at something else, and the previous image has no name at all:

```bash
docker images --filter dangling=true --format '{{.ID}}  {{.CreatedAt}}' | head -3
```

Your deployment record says "we deployed `app-base:rolling`". That sentence no longer identifies anything. If the second build is bad, the rollback target is an untagged digest you would have to find in `docker images` — assuming nobody has pruned it, which in a real registry with a lifecycle policy they have.

**Investigate.**

```bash
cd ../terraform
terraform plan -var image_version=rolling      # ⭐ a diff appeared without any code change
```

**Root cause.** A tag is a mutable pointer and a digest is content. Referencing tags in infrastructure means your infrastructure's meaning changes when someone else builds — which also breaks `terraform plan` as a review tool, because the plan is no longer a function of the code.

**Fix.** The pattern the reference code already implements:

- Immutable version per build (git SHA, or a monotonic version), never reused
- Terraform resolves tag → digest **once**, and resources reference the digest
- The `image_version != "latest"` validation as a backstop
- In a real registry, turn on tag immutability (ECR: `imageTagMutability = "IMMUTABLE"`) so the platform enforces it rather than your discipline

```bash
terraform destroy -auto-approve -var image_version=v1 2>/dev/null
```

### Summary

| Failure | How you detect it | How you prevent it |
|---------|------------------|--------------------|
| Unpinned base | Identical config, different digests between builds | Resolve and pin the base digest; record it in `manifest.json` |
| Baked secret | `docker history --no-trunc` / `Config.Env` contains a credential | Runtime injection; a verify step that fails the build |
| Build succeeds, image broken | Nothing — unless you verify. A missing agent found weeks later | `sh -e` in every provisioner, plus a verify provisioner that asserts the promises |
| Mutable tag | `terraform plan` shows a diff with no code change; dangling images | Immutable per-build versions, digest references, registry-enforced immutability |

⭐ **The theme of this lab**: an image is a *published artefact*. Everything in it is distributed, everything about it should be reproducible from the config, and its correctness has to be asserted at build time — because by the time it is wrong, it is wrong on every instance at once. Golden images are what make immutable infrastructure practical; a golden image you cannot reproduce is just a snowflake with a version number.

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
cd terraform && terraform destroy -auto-approve -var image_version=v1 2>/dev/null; cd ..
docker rmi $(docker images 'app-base' -q) 2>/dev/null || true
docker image prune -f
rm -f packer/manifest.json
rm -rf terraform/.terraform terraform/terraform.tfstate*
docker system df                # ⭐ confirm the space actually came back
```

---

## ✅ Validation

- [ ] Explain what belongs in a golden image and what must stay out of one
- [ ] Explain why boot time matters under autoscaling, and what a package repository outage does to configure-at-boot
- [ ] Build an image, and describe every provisioner in your config
- [ ] Explain why the verify provisioner exists when the install step already exited zero
- [ ] Pin a base image by digest, and say where you got the digest from
- [ ] Find a baked secret with `docker history`, and explain why deleting it in a later layer does not help
- [ ] Explain how a missing `-e` produces a successful build of a broken image
- [ ] Explain why Terraform should reference a digest rather than a tag, and what breaks otherwise
- [ ] Describe the AMI equivalent of everything you just did

---

## 📝 What to Commit

- `packer/base.pkr.hcl`, both scripts, `terraform/main.tf`
- Build output including the verify step, and `manifest.json`
- Two digests for the same tag, and identical digests after pinning
- The `docker history` output showing a baked secret, and the verify failure that caught it
- The `terraform plan` diff caused by a moved tag
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: Modules and Environments](./lab-03-modules-and-environments.md) | [Back to Module README](../README.md) | [Module 11: Ansible →](../../11-ansible/)
