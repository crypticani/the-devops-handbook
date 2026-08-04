# Module 13: Security Basics — Cheat Sheet

> Scanning tools, secret management, hardening commands, and audit one-liners. Concepts live in the [module README](./README.md).
> Cross-module daily commands: **[QUICK-REFERENCE.md](../QUICK-REFERENCE.md)**

**Jump to:** [Scanning](#scanning-toolbox) · [Secrets in git](#secrets-in-git) · [Secret managers](#secret-managers) · [SSH & TLS](#ssh--tls) · [Linux hardening](#linux-hardening) · [Container security](#container-security) · [Kubernetes security](#kubernetes-security) · [Cloud audit](#cloud-audit-one-liners) · [CI/CD security](#cicd-security) · [Vulnerability triage](#vulnerability-triage) · [Incident response](#incident-response)

---

## Scanning Toolbox

| Tool | Scans | Typical use |
|------|-------|-------------|
| **trivy** | Images, filesystems, git repos, IaC, K8s, SBOMs | ⭐ The one tool to start with — covers most of the list below |
| **grype** | Images, filesystems | Alternative CVE scanner; good second opinion |
| **syft** | Anything | SBOM generation |
| **gitleaks** | Git history + working tree | ⭐ Secret detection |
| **trufflehog** | Git, S3, filesystems | Secret detection **with live verification** |
| **hadolint** | Dockerfiles | Lint + best practices |
| **dockle** | Images | CIS-style image audit |
| **checkov** | Terraform, CFN, K8s, Helm, Dockerfile | Policy-as-code |
| **tfsec** | Terraform | (Now folded into Trivy) |
| **kube-bench** | Kubernetes nodes | CIS Kubernetes Benchmark |
| **kubescape** | Cluster + manifests | NSA/CISA + MITRE frameworks |
| **polaris** | K8s workloads | Best-practice checks |
| **semgrep** | Source code | ⭐ SAST with custom rules |
| **bandit** | Python | SAST |
| **npm audit` / `pip-audit` / `cargo audit** | Dependencies | SCA per ecosystem |
| **OWASP ZAP** | Running web apps | DAST |
| **lynis** | Linux hosts | System hardening audit |
| **prowler** / **scoutsuite** | AWS/Azure/GCP | Cloud posture assessment |
| **cosign** | Images | Signing and verification |

```bash
# ─── Trivy: one tool, many targets ───
trivy image myapp:v1
trivy image --severity HIGH,CRITICAL --exit-code 1 myapp:v1      # ⭐ CI gate
trivy image --ignore-unfixed myapp:v1                            # only actionable findings
trivy image --scanners vuln,secret,misconfig myapp:v1
trivy fs .                                                       # source tree
trivy fs --scanners secret .                                     # secrets only
trivy config .                                                   # ⭐ Terraform/K8s/Dockerfile misconfig
trivy repo https://github.com/org/repo
trivy k8s --report summary cluster                               # live cluster
trivy sbom sbom.json
trivy image --format cyclonedx --output sbom.json myapp:v1
trivy image --format sarif --output trivy.sarif myapp:v1         # upload to GitHub Security

# .trivyignore — accept a risk explicitly, with a reason and a date
cat > .trivyignore <<'EOF'
# CVE-2023-1234: only exploitable via the CLI parser we don't use.
# Accepted by @alice 2026-08-04, re-review 2026-11-04.
CVE-2023-1234
EOF

# ─── Others ───
grype myapp:v1 --fail-on high
syft myapp:v1 -o spdx-json > sbom.json
hadolint Dockerfile
dockle myapp:v1
checkov -d . --framework terraform --compact
semgrep --config=auto .
semgrep --config=p/security-audit --sarif -o semgrep.sarif .
lynis audit system
```

---

## Secrets in Git

```bash
# ─── Detect ───
gitleaks detect --source . --verbose                    # ⭐ scans full history
gitleaks detect --source . --report-format sarif --report-path gitleaks.sarif
gitleaks protect --staged                               # pre-commit: staged changes only
trufflehog git file://. --only-verified                 # ⭐ confirms the key actually works
trufflehog github --repo=https://github.com/org/repo

# Manual grep for the obvious patterns
git log -p --all | grep -nE 'AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{36}'
git rev-list --all --objects | git cat-file --batch-check='%(objecttype) %(objectname) %(rest)' \
  | awk '$1=="blob"' | sort -k3 | grep -iE '\.(env|pem|key|p12|pfx)$'
```

```bash
# ─── Prevent ───
pip install pre-commit
cat > .pre-commit-config.yaml <<'YAML'
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks: [{id: gitleaks}]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: detect-private-key
      - id: detect-aws-credentials
      - id: check-added-large-files
  - repo: https://github.com/antonbabenko/pre-commit-terraform
    rev: v1.88.0
    hooks: [{id: terraform_fmt}, {id: terraform_tflint}, {id: terrascan}]
YAML
pre-commit install && pre-commit run --all-files
```

### Remediation — the order matters

```
1. ROTATE the credential.  ⭐ Do this FIRST, before anything else.
   Assume it is compromised the moment it was pushed. Bots scan
   public GitHub within seconds of a commit landing.

2. REVOKE the old value at the provider and check its usage logs
   (CloudTrail, audit log) for anything you didn't do.

3. PURGE it from history — cleanup, not remediation:
      pip install git-filter-repo
      git filter-repo --path secrets.env --invert-paths
      # or replace the literal string everywhere:
      printf 'AKIAIOSFODNN7EXAMPLE==>REDACTED\n' > replacements.txt
      git filter-repo --replace-text replacements.txt

4. FORCE-PUSH and have every collaborator re-clone.
   Ask GitHub Support to purge cached views and fork references.

5. PREVENT recurrence: pre-commit hook + CI scan + push protection.
```

> ⚠️ **Rewriting history does not un-leak a secret.** Forks, clones, CI caches, and GitHub's own cached views may still hold it. Rotation is the only real fix; history rewriting is hygiene.

---

## Secret Managers

| Approach | Good | Bad |
|----------|------|-----|
| Env var from CI secret store | Simple, universal | Visible in `/proc`, process listings, crash dumps |
| Mounted file (tmpfs) | Not in the environment; rotatable | Needs a delivery mechanism |
| Vault / cloud secret manager with **dynamic** credentials | ⭐ Short-lived, audited, revocable | Operational complexity |
| Sealed Secrets / SOPS in git | GitOps-friendly, encrypted at rest | Still a long-lived secret, just encrypted |
| Hardcoded in code or image | — | Never. This is the thing we're preventing |

```bash
# ─── HashiCorp Vault ───
export VAULT_ADDR=https://vault.example.com
vault login -method=oidc
vault kv put secret/myapp/prod db_password='s3cr3t' api_key='...'
vault kv get secret/myapp/prod
vault kv get -field=db_password secret/myapp/prod        # ⭐ scriptable
vault kv get -format=json secret/myapp/prod | jq -r .data.data.db_password
vault kv metadata get secret/myapp/prod                  # version history
vault kv rollback -version=3 secret/myapp/prod
vault kv delete secret/myapp/prod

# ⭐ Dynamic database credentials — expire automatically
vault read database/creds/readonly
vault lease revoke -prefix database/creds/

vault policy write app-read - <<'EOF'
path "secret/data/myapp/*" { capabilities = ["read"] }
EOF
vault auth enable kubernetes
vault write auth/kubernetes/role/myapp \
  bound_service_account_names=myapp \
  bound_service_account_namespaces=prod \
  policies=app-read ttl=1h

# ─── AWS Secrets Manager / SSM ───
aws secretsmanager create-secret --name prod/db --secret-string '{"password":"s3cr3t"}'
aws secretsmanager get-secret-value --secret-id prod/db --query SecretString --output text | jq -r .password
aws secretsmanager rotate-secret --secret-id prod/db --rotation-lambda-arn arn:...
aws ssm put-parameter --name /prod/db/password --value 's3cr3t' --type SecureString --overwrite
aws ssm get-parameter --name /prod/db/password --with-decryption --query Parameter.Value --output text
aws ssm get-parameters-by-path --path /prod/ --recursive --with-decryption

# ─── SOPS — encrypted secrets in git ───
sops -e -i secrets.yaml               # encrypt in place (values only, keys stay readable)
sops -d secrets.yaml                  # decrypt to stdout
sops secrets.yaml                     # edit decrypted in $EDITOR
# .sops.yaml
#   creation_rules:
#     - path_regex: secrets/.*\.yaml$
#       kms: arn:aws:kms:us-east-1:123:key/abc

# ─── Sealed Secrets (Kubernetes) ───
kubectl create secret generic db --from-literal=password=s3cr3t --dry-run=client -o yaml \
  | kubeseal --format yaml > sealed-db.yaml     # ⭐ safe to commit
kubectl apply -f sealed-db.yaml
```

**Rules:**
- Rotate on a schedule **and** on every departure or suspected exposure
- Prefer **short-lived, dynamically issued** credentials over long-lived static ones
- Scope every credential to the narrowest resource and action set that works
- Never log a secret — `no_log`, `sensitive`, `::add-mask::`, `set +x`
- Audit access: who read which secret, when

---

## SSH & TLS

```bash
# ─── Keys ───
ssh-keygen -t ed25519 -C "alice@example.com"          # ⭐ ed25519, not RSA
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/prod_key       # more KDF rounds
ssh-keygen -l -f ~/.ssh/id_ed25519.pub                # fingerprint
ssh-keygen -p -f ~/.ssh/id_ed25519                    # change the passphrase
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@host
ssh-add -l && ssh-add -D                              # list / clear the agent

# ─── Server hardening: /etc/ssh/sshd_config ───
# PermitRootLogin no
# PasswordAuthentication no
# PubkeyAuthentication yes
# ChallengeResponseAuthentication no
# X11Forwarding no
# MaxAuthTries 3
# ClientAliveInterval 300
# ClientAliveCountMax 2
# AllowUsers deploy admin
# AllowGroups ssh-users
# Protocol 2
sudo sshd -t                                          # ⭐ TEST before reloading
sudo systemctl reload sshd
# ⚠️ Keep your current session open until a NEW one is verified

# ─── Audit ───
sudo lastb | head -20                                 # failed logins
sudo grep 'Failed password' /var/log/auth.log | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn
sudo fail2ban-client status sshd
ss -tnp state established '( dport = :22 or sport = :22 )'
```

```bash
# ─── TLS certificates ───
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -dates
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
openssl s_client -connect example.com:443 -showcerts </dev/null     # full chain
openssl x509 -in cert.pem -noout -text
nmap --script ssl-enum-ciphers -p 443 example.com     # supported protocols/ciphers
testssl.sh https://example.com                        # ⭐ thorough TLS audit

# Do cert and key match?
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa  -noout -modulus -in key.pem  | openssl md5

# Expiry monitoring across a fleet
for h in api.example.com app.example.com; do
  exp=$(echo | openssl s_client -connect "$h:443" -servername "$h" 2>/dev/null \
        | openssl x509 -noout -enddate | cut -d= -f2)
  printf '%-28s %s\n' "$h" "$exp"
done

# Let's Encrypt
certbot certificates
certbot renew --dry-run                               # ⭐ test renewal before it matters
```

**Security headers to serve:**

```nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
server_tokens off;
```

```bash
curl -sI https://example.com | grep -iE 'strict-transport|x-frame|x-content-type|content-security'
```

---

## Linux Hardening

```bash
# ─── Users, sudo, and access ───
awk -F: '($3 == 0) {print $1}' /etc/passwd            # ⭐ every UID-0 account (should be root only)
awk -F: '($2 == "") {print $1}' /etc/shadow           # accounts with NO password
sudo -l -U deploy                                     # what can this user run?
grep -rE 'NOPASSWD|ALL=\(ALL\)' /etc/sudoers /etc/sudoers.d/
getent group sudo docker wheel                        # who has privileged group membership
lastlog | awk '$2 != "**Never" '                      # who has actually logged in
find / -xdev -type f -perm -4000 -ls 2>/dev/null      # ⭐ SUID binaries
find / -xdev -type f -perm -2000 -ls 2>/dev/null      # SGID binaries
find / -xdev \( -perm -0002 \) -type f -ls 2>/dev/null # world-writable files
find /home -name '.ssh' -type d -exec ls -ld {} \;    # SSH dir permissions

# ─── Services and network exposure ───
ss -tlnp                                              # ⭐ what is listening, and why?
systemctl list-units --type=service --state=running
systemctl list-unit-files --state=enabled
sudo ufw status verbose  ||  sudo firewall-cmd --list-all

# ─── Updates ───
apt list --upgradable 2>/dev/null | grep -i security
sudo unattended-upgrade --dry-run -d
sudo dnf updateinfo list security
sudo dnf needs-restarting -r
sudo needrestart                                      # which services need a restart after updates

# ─── Integrity and audit ───
sudo aide --check                                     # file integrity
sudo debsums -c                                       # changed package files (Debian)
rpm -Va | head -30                                    # changed package files (RHEL)
sudo auditctl -l                                      # audit rules
sudo ausearch -m avc -ts recent                       # ⭐ SELinux denials
sudo aureport --summary
getenforce && sudo sestatus                           # SELinux state
sudo aa-status                                        # AppArmor state

# ─── Kernel hardening: /etc/sysctl.d/99-hardening.conf ───
# net.ipv4.conf.all.rp_filter = 1
# net.ipv4.conf.all.accept_redirects = 0
# net.ipv4.conf.all.accept_source_route = 0
# net.ipv4.tcp_syncookies = 1
# net.ipv4.icmp_echo_ignore_broadcasts = 1
# kernel.randomize_va_space = 2
# kernel.dmesg_restrict = 1
# fs.protected_hardlinks = 1
# fs.protected_symlinks = 1
sudo sysctl --system

sudo lynis audit system                               # ⭐ comprehensive hardening report
```

---

## Container Security

```bash
trivy image --severity HIGH,CRITICAL --exit-code 1 myapp:v1
hadolint Dockerfile
dockle myapp:v1
docker scout cves myapp:v1

# Runtime posture
docker inspect myapp --format '{{.Config.User}}'                    # ⭐ empty == root
docker inspect myapp --format '{{.HostConfig.Privileged}}'
docker inspect myapp --format '{{.HostConfig.ReadonlyRootfs}}'
docker inspect myapp --format '{{.HostConfig.CapAdd}} {{.HostConfig.CapDrop}}'
docker inspect myapp --format '{{range .Mounts}}{{.Source}}→{{.Destination}} {{end}}'

# ⭐ Audit: which containers run as root or are privileged?
docker ps -q | xargs -r docker inspect \
  --format '{{.Name}} user={{.Config.User}} privileged={{.HostConfig.Privileged}}'

# ⭐ Audit: anything mounting the Docker socket? (= root on the host)
docker ps -q | xargs -r docker inspect \
  --format '{{.Name}} {{range .Mounts}}{{.Source}} {{end}}' | grep docker.sock
```

**Hardened run:**

```bash
docker run -d \
  --user 10001:10001 \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop ALL --cap-add NET_BIND_SERVICE \
  --security-opt no-new-privileges:true \
  --security-opt seccomp=default.json \
  --memory 512m --cpus 1 --pids-limit 200 \
  --network appnet \
  myapp:v1
```

**Signing and verification:**

```bash
cosign generate-key-pair
cosign sign --key cosign.key ghcr.io/org/app:v1
cosign verify --key cosign.pub ghcr.io/org/app:v1
cosign sign --yes ghcr.io/org/app:v1                          # ⭐ keyless, via OIDC
cosign attest --predicate sbom.json --type spdxjson ghcr.io/org/app:v1
```

**Image checklist:** non-root `USER` · minimal base (`distroless`/`slim`/`scratch`) · multi-stage build · pinned base by digest · no secrets in any layer · `.dockerignore` present · scanned in CI with a **failing** gate · SBOM generated · image signed.

---

## Kubernetes Security

```bash
kube-bench run --targets master,node                  # CIS benchmark
kubescape scan framework nsa
kubescape scan framework mitre
polaris audit --audit-path ./manifests
trivy k8s --report summary cluster

# ─── RBAC audit ───
kubectl auth can-i --list                                              # my permissions
kubectl auth can-i --list --as=system:serviceaccount:default:myapp     # ⭐ theirs
kubectl get clusterrolebindings -o json | jq -r '.items[] |
  select(.roleRef.name=="cluster-admin") |
  "\(.metadata.name): \(.subjects // [] | map(.kind+"/"+.name) | join(", "))"'   # ⭐ who is cluster-admin
kubectl get rolebindings,clusterrolebindings -A -o wide | grep -i default    # default SA bindings

# ─── Workload posture ───
# Privileged containers
kubectl get pods -A -o json | jq -r '.items[] |
  select(.spec.containers[]?.securityContext?.privileged==true) |
  "\(.metadata.namespace)/\(.metadata.name)"'

# Containers that may run as root
kubectl get pods -A -o json | jq -r '.items[] |
  select((.spec.securityContext?.runAsNonRoot // false) != true) |
  "\(.metadata.namespace)/\(.metadata.name)"'

# Host namespace / hostPath usage  ⭐ container escape risk
kubectl get pods -A -o json | jq -r '.items[] |
  select(.spec.hostNetwork==true or .spec.hostPID==true or .spec.hostIPC==true) |
  "\(.metadata.namespace)/\(.metadata.name)"'
kubectl get pods -A -o json | jq -r '.items[] |
  select(.spec.volumes[]?.hostPath) | "\(.metadata.namespace)/\(.metadata.name)"'

# No resource limits — a noisy-neighbour and DoS risk
kubectl get pods -A -o json | jq -r '.items[] |
  select(.spec.containers[].resources.limits == null) |
  "\(.metadata.namespace)/\(.metadata.name)"'

# Namespaces with NO NetworkPolicy at all
comm -23 <(kubectl get ns -o name | cut -d/ -f2 | sort) \
         <(kubectl get netpol -A -o jsonpath='{.items[*].metadata.namespace}' | tr ' ' '\n' | sort -u)
```

```yaml
# Pod Security Standards — enforce at the namespace level
apiVersion: v1
kind: Namespace
metadata:
  name: prod
  labels:
    pod-security.kubernetes.io/enforce: restricted     # ⭐ privileged | baseline | restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

```yaml
# Secure workload defaults
spec:
  automountServiceAccountToken: false      # ⭐ unless the pod calls the K8s API
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    fsGroup: 10001
    seccompProfile: {type: RuntimeDefault}
  containers:
    - securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        privileged: false
        capabilities: {drop: [ALL]}
```

**Kubernetes checklist:** RBAC least privilege (no blanket `cluster-admin`) · Pod Security Standards `restricted` · default-deny NetworkPolicies · Secrets encrypted at rest + external secret store · `automountServiceAccountToken: false` by default · resource limits everywhere · admission control (Kyverno/OPA Gatekeeper) enforcing signed, scanned images · API server audit logging on · private API endpoint · node auto-upgrades.

---

## Cloud Audit One-Liners

```bash
# ─── IAM ───
aws sts get-caller-identity
aws iam generate-credential-report >/dev/null && aws iam get-credential-report \
  --query Content --output text | base64 -d | column -t -s,      # ⭐ stale keys, no MFA
aws iam list-users --query 'Users[?PasswordLastUsed<=`2025-08-01`].UserName'
aws iam list-policies --scope Local --query 'Policies[].PolicyName'
aws iam simulate-principal-policy --policy-source-arn arn:...:role/App \
  --action-names s3:DeleteBucket                                  # ⭐ can it do the scary thing?

# ─── Network exposure ───
aws ec2 describe-security-groups --query \
 'SecurityGroups[?IpPermissions[?contains(IpRanges[].CidrIp, `0.0.0.0/0`)]].{ID:GroupId,Name:GroupName}' \
 --output table                                                   # ⭐ open to the internet
aws ec2 describe-instances --query \
 'Reservations[].Instances[?PublicIpAddress!=null].[InstanceId,PublicIpAddress]' --output table
aws rds describe-db-instances --query \
 'DBInstances[?PubliclyAccessible==`true`].DBInstanceIdentifier'   # ⭐ public databases

# ─── Storage ───
for b in $(aws s3api list-buckets --query 'Buckets[].Name' --output text); do
  pab=$(aws s3api get-public-access-block --bucket "$b" 2>/dev/null \
        --query 'PublicAccessBlockConfiguration.BlockPublicAcls' --output text || echo "NONE")
  enc=$(aws s3api get-bucket-encryption --bucket "$b" >/dev/null 2>&1 && echo yes || echo "NO")
  printf '%-40s public_block=%-6s encrypted=%s\n' "$b" "$pab" "$enc"
done

# ─── Logging and detection ───
aws cloudtrail describe-trails --query 'trailList[].{Name:Name,Multi:IsMultiRegionTrail,Logging:HomeRegion}'
aws guardduty list-detectors
aws securityhub get-findings --filters '{"SeverityLabel":[{"Value":"CRITICAL","Comparison":"EQUALS"}]}' \
  --max-results 20 --query 'Findings[].Title'
aws configservice describe-compliance-by-config-rule --compliance-types NON_COMPLIANT

# ─── Full posture assessment ───
prowler aws --severity critical high
scoutsuite aws
```

---

## CI/CD Security

**Pipeline gates, in order (cheapest first):**

```yaml
1. Secret scan        gitleaks protect --staged        # pre-commit, then CI on full history
2. Dependency scan    trivy fs --scanners vuln .       # or npm audit / pip-audit
3. SAST               semgrep --config=auto .
4. IaC scan           trivy config .  /  checkov -d .
5. Build              docker build (multi-stage, non-root, pinned base)
6. Image scan         trivy image --exit-code 1 --severity HIGH,CRITICAL
7. SBOM               syft -o spdx-json > sbom.json
8. Sign               cosign sign --yes $IMAGE
9. Deploy             admission control verifies the signature
10. DAST              OWASP ZAP against staging
```

**Supply-chain hardening:**

| Control | Command / setting |
|---------|-------------------|
| Pin third-party actions to a **SHA** | `uses: org/action@a1b2c3d...` — tags are mutable |
| Least-privilege `GITHUB_TOKEN` | `permissions: {contents: read}` at the workflow root |
| **OIDC** instead of static cloud keys | `id-token: write` + `role-to-assume` |
| Never run untrusted PR code with secrets | Avoid `pull_request_target` with a PR-ref checkout |
| Pin base images by digest | `FROM node:20-slim@sha256:...` |
| Commit lockfiles | `package-lock.json`, `.terraform.lock.hcl`, `poetry.lock` |
| Sign commits and images | `git commit -S`, `cosign sign` |
| Enable branch protection | Required reviews + required status checks |
| Enable GitHub push protection | Blocks secret pushes at the server |
| Restrict self-hosted runners | Never on public-repo PRs |

```bash
# Verify a signed image at deploy time
cosign verify --certificate-identity-regexp 'https://github.com/myorg/.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/myorg/app:v1
```

---

## Vulnerability Triage

Not every CVE matters. Triage in this order:

```
1. IS IT REACHABLE?
   Is the vulnerable package actually loaded and called by your code path?
   A CVE in a dev dependency that never ships is not a production risk.

2. IS IT EXPOSED?
   Internet-facing, or behind three layers of internal network?
   Does exploitation require authentication you already enforce?

3. WHAT IS THE IMPACT?
   RCE / auth bypass / data exposure → drop everything.
   DoS on an internal batch job → schedule it.

4. IS THERE A FIX?
   `--ignore-unfixed` filters out the ones you can't action today.
   No fix + reachable + exposed → mitigate (WAF rule, config change, disable the feature).

5. RECORD THE DECISION.
   Accepted risks go in .trivyignore with a REASON, an OWNER, and a REVIEW DATE.
   An ignore file with no expiry is how a critical CVE lives for three years.
```

| CVSS | Internet-facing | Internal only |
|------|-----------------|---------------|
| **Critical (9.0+)** | Patch within 24h | Patch within 7 days |
| **High (7.0–8.9)** | Patch within 7 days | Patch within 30 days |
| **Medium (4.0–6.9)** | Next release cycle | Next release cycle |
| **Low (<4.0)** | Batch with routine updates | Batch with routine updates |

```bash
# Where is this package actually coming from?
trivy image --format json myapp:v1 | jq -r '.Results[].Vulnerabilities[]?
  | select(.Severity=="CRITICAL") | "\(.PkgName) \(.InstalledVersion) → \(.FixedVersion // "no fix") \(.VulnerabilityID)"'
npm ls vulnerable-package
pip show vulnerable-package
```

---

## Incident Response

```
1. DETECT     — alert, anomaly, report. Note the time.
2. CONTAIN    — stop the bleeding before you investigate.
3. PRESERVE   — snapshot before you change anything. Evidence first.
4. ERADICATE  — remove the access, patch the hole.
5. RECOVER    — restore service from a known-good state.
6. LEARN      — blameless postmortem with dated action items.
```

```bash
# ─── CONTAIN ───
aws iam update-access-key --user-name compromised --access-key-id AKIA... --status Inactive
aws iam attach-user-policy --user-name compromised --policy-arn arn:aws:iam::aws:policy/AWSDenyAll
kubectl scale deploy/compromised --replicas=0
kubectl label pod suspicious quarantine=true --overwrite     # then a NetworkPolicy isolates it
aws ec2 modify-instance-attribute --instance-id i-0abc --groups sg-quarantine
sudo ufw deny from <attacker-ip>

# ─── PRESERVE (before you touch anything) ───
aws ec2 create-snapshot --volume-id vol-0abc --description "IR-2026-08-04 evidence"
docker commit suspicious-container evidence:incident-01
kubectl cp suspicious-pod:/var/log ./evidence/logs
sudo dd if=/dev/mem of=/mnt/evidence/memory.dump bs=1M       # memory capture
sudo tar czf /mnt/evidence/logs.tgz /var/log
sha256sum /mnt/evidence/* > /mnt/evidence/MANIFEST.sha256    # ⭐ chain of custody

# ─── INVESTIGATE ───
sudo last -20 && sudo lastb -20
sudo grep -E 'Accepted|Failed' /var/log/auth.log | tail -50
sudo journalctl --since "2 hours ago" -p warning
ps auxf                                                       # unexpected process tree
ss -tnp                                                       # unexpected outbound connections
sudo find / -xdev -mtime -1 -type f -ls 2>/dev/null | head -50   # ⭐ recently modified files
sudo find / -xdev -type f -perm -4000 -newer /etc/hostname -ls 2>/dev/null   # new SUID binaries
crontab -l && sudo ls -la /etc/cron.*/ /var/spool/cron/

aws cloudtrail lookup-events --lookup-attributes \
  AttributeKey=Username,AttributeValue=compromised --max-results 50
kubectl get events -A --sort-by=.lastTimestamp | tail -50
```

**Postmortem template:**

```markdown
# Incident: <short title>

**Date**: 2026-08-04 · **Duration**: 09:12–10:47 UTC (95 min)
**Severity**: SEV-2 · **Author**: <name>

## Impact
Who was affected, how many, for how long, and in what way.

## Timeline (UTC)
| Time | Event |
|------|-------|
| 09:12 | First 5xx errors; alert fired |
| 09:18 | On-call acknowledged |
| 09:31 | Root cause identified |
| 09:44 | Mitigation applied |
| 10:47 | Fully recovered |

## Root Cause
The technical chain of events. Systems, not people.

## What Went Well
## What Went Poorly
## Where We Got Lucky

## Action Items
| Action | Owner | Due | Ticket |
|--------|-------|-----|--------|
| Add alert on X | @alice | 2026-08-11 | OPS-482 |
```

> 💡 **Blameless means systems-focused, not consequence-free.** "Alice deleted the database" is not a root cause. "A single command could delete production with no confirmation, no backup verification, and no audit trail" is — and it produces action items that actually prevent recurrence.

---

<div align="center">

[← Module 13 README](./README.md) · [Resources](./resources.md) · [Labs](./labs/) · [Handbook Quick Reference](../QUICK-REFERENCE.md)

</div>
