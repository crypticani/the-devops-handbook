# Lab 02: Secrets Management

## 🎯 Objective

Stop putting secrets where they can be read. You'll compare the four ways a secret reaches a running application, encrypt secrets safely enough to commit them to git, issue **dynamic credentials that expire on their own**, and practise the rotation drill — because the fix for a leaked secret is always rotation, never cleanup.

---

## 📋 Prerequisites

- Completed [Lab 01: Security Scanning](./lab-01-security-scanning.md)
- Docker and Docker Compose
- `age` and `sops` (installed in Exercise 3), `jq`

```bash
docker --version && docker compose version
command -v jq >/dev/null || echo "install jq first"
```

> 💰 **Cost**: everything here runs locally in containers. No cloud resources.

---

## 📦 Deliverables and Evidence

- A comparison table of the four delivery mechanisms, with the leak path you found for each
- A SOPS-encrypted file you would be comfortable committing, plus proof of what's readable in it
- Vault issuing a database credential that expires, with the expiry demonstrated
- A completed rotation drill with timings
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-02/`](../code/lab-02/).

```bash
cp -r /path/to/the-devops-handbook/13-security-basics/code/lab-02/. .
```

---

## 🔬 Exercise 1: Where Secrets Leak

Four ways to get a secret into a container. Each leaks somewhere different.

### Step 1: Set Up

```bash
mkdir -p secrets-lab && cd secrets-lab
```

### Step 2: Baked Into the Image — the Worst Option

```bash
cat > Dockerfile.baked <<'EOF'
FROM alpine:3.20
ENV API_TOKEN=sk-live-baked-into-the-image-forever
ARG BUILD_SECRET=arg-secrets-are-also-visible
RUN echo "using $BUILD_SECRET during build" > /tmp/build.log
CMD ["sleep", "3600"]
EOF

docker build -q -t leak-baked:v1 -f Dockerfile.baked .
```

**Where it leaks — three independent places:**

```bash
# 1. Image metadata, readable by anyone who can pull the image
docker inspect leak-baked:v1 --format '{{range .Config.Env}}{{println .}}{{end}}'

# 2. ⭐ Build history — ARG values too, even though they aren't in the final env
docker history --no-trunc leak-baked:v1 | grep -i secret

# 3. The image layers themselves. Deleting a file in a later layer does NOT remove it.
docker save leak-baked:v1 | tar -t 2>/dev/null | head -5
```

> ⚠️ **`ARG` is not a secret mechanism.** It doesn't appear in the final environment, which makes people think it's safe — but `docker history` prints it. So does anyone who pulls the image from your registry.

### Step 3: Environment Variables — Better, Still Leaky

```bash
docker run -d --name leak-env -e API_TOKEN='sk-live-from-env' alpine:3.20 sleep 3600

# Leak 1: inspect
docker inspect leak-env --format '{{range .Config.Env}}{{println .}}{{end}}' | grep API_TOKEN

# Leak 2: ⭐ /proc — any process in the container can read another's environment
docker exec leak-env sh -c 'cat /proc/1/environ | tr "\0" "\n" | grep API_TOKEN'

# Leak 3: child processes inherit it, and often log it
docker exec leak-env sh -c 'env | grep API_TOKEN'

# Leak 4: crash dumps, error reporters, and `docker inspect` in support tickets
```

### Step 4: A Mounted File — Better Again

```bash
mkdir -p secrets && echo -n 'sk-live-from-file' > secrets/api_token
chmod 600 secrets/api_token

docker run -d --name leak-file \
  -v "$PWD/secrets/api_token:/run/secrets/api_token:ro" \
  alpine:3.20 sleep 3600

docker exec leak-file cat /run/secrets/api_token; echo
docker inspect leak-file --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -c API_TOKEN || echo "  ✅ not in the environment"
docker exec leak-file sh -c 'cat /proc/1/environ | tr "\0" "\n" | grep -c API_TOKEN' || echo "  ✅ not in /proc"

# But: it IS on the host disk, and the mount path is visible
docker inspect leak-file --format '{{range .Mounts}}{{.Source}} → {{.Destination}}{{end}}'
```

### Step 5: tmpfs — Never Touches Disk

```bash
docker run -d --name leak-tmpfs \
  --tmpfs /run/secrets:rw,noexec,nosuid,size=1m \
  alpine:3.20 sh -c 'echo -n "sk-live-in-ram" > /run/secrets/api_token; sleep 3600'

docker exec leak-tmpfs cat /run/secrets/api_token; echo
docker exec leak-tmpfs mount | grep /run/secrets     # ⭐ tmpfs — RAM only
```

### Step 6: Score Them

```bash
docker rm -f leak-env leak-file leak-tmpfs >/dev/null 2>&1
```

| Mechanism | In the image? | In `inspect`? | In `/proc`? | On host disk? | Verdict |
|-----------|--------------|--------------|-------------|--------------|---------|
| `ENV` in Dockerfile | ⚠️ **Yes, forever** | Yes | Yes | Yes | ❌ Never |
| `ARG` in Dockerfile | ⚠️ **In `docker history`** | No | No | Yes | ❌ Never |
| `-e` at runtime | No | ⚠️ **Yes** | ⚠️ **Yes** | No | 🟡 Acceptable with care |
| Mounted file | No | Path only | ✅ No | ⚠️ Yes | 🟢 Good |
| **tmpfs / secret manager** | No | Path only | ✅ No | ✅ **No** | ⭐ Best |

> ⭐ **The ranking that matters in practice**: image > environment > file > tmpfs, worst to best. But the mechanism is secondary. A **short-lived, automatically-rotated** credential delivered via environment variable is safer than a **permanent** one delivered via tmpfs. Lifetime beats delivery.

---

## 🔬 Exercise 2: BuildKit Secrets

You often need a credential *during* a build — a private package registry token — without it entering the image.

```bash
cat > .npmrc <<'EOF'
//registry.npmjs.org/:_authToken=npm_SECRET_TOKEN_VALUE
EOF

cat > Dockerfile.buildkit <<'EOF'
# syntax=docker/dockerfile:1
FROM alpine:3.20
# ⭐ The secret is mounted for THIS RUN only. It is never a layer.
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    echo "token starts with: $(head -c 20 /root/.npmrc)" > /build-evidence.txt
CMD ["cat", "/build-evidence.txt"]
EOF

DOCKER_BUILDKIT=1 docker build -q --secret id=npmrc,src=.npmrc -t buildkit-safe:v1 -f Dockerfile.buildkit .

# The build USED it...
docker run --rm buildkit-safe:v1

# ...and it is nowhere in the image
docker history --no-trunc buildkit-safe:v1 | grep -c 'npm_SECRET' || echo "  ✅ not in history"
docker save buildkit-safe:v1 | tar -xO 2>/dev/null | strings 2>/dev/null | grep -c 'npm_SECRET_TOKEN_VALUE' || echo "  ✅ not in any layer"
```

**✅ Checkpoint:** The build read the token, and the token is not in `history` or any layer. Compare that with `Dockerfile.baked` from Exercise 1.

```bash
rm -f .npmrc
```

Other BuildKit mount types worth knowing:

```dockerfile
RUN --mount=type=secret,id=aws,target=/root/.aws/credentials ...
RUN --mount=type=ssh git clone git@github.com:org/private.git     # forwards your agent
RUN --mount=type=cache,target=/root/.npm npm ci                    # not a secret, but the same idea
```

---

## 🔬 Exercise 3: SOPS — Encrypted Secrets in Git

The GitOps problem: you want configuration in version control, but configuration contains secrets.

### Step 1: Install

```bash
# age — modern, simple encryption
curl -sL https://github.com/FiloSottile/age/releases/download/v1.2.0/age-v1.2.0-linux-amd64.tar.gz \
  | tar xz -C /tmp && sudo install /tmp/age/age /tmp/age/age-keygen /usr/local/bin/

# sops
curl -sLo /tmp/sops https://github.com/getsops/sops/releases/download/v3.9.0/sops-v3.9.0.linux.amd64
sudo install /tmp/sops /usr/local/bin/sops

sops --version && age --version
```

### Step 2: Generate a Key

```bash
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt 2>/dev/null || echo "(key already exists)"
chmod 600 ~/.config/sops/age/keys.txt

export SOPS_AGE_RECIPIENT=$(grep 'public key' ~/.config/sops/age/keys.txt | awk '{print $NF}')
echo "public key: $SOPS_AGE_RECIPIENT"
```

> ⚠️ `~/.config/sops/age/keys.txt` holds the **private** key. It never goes in git. In production the equivalent is a KMS key, and access to it is the real access control.

### Step 3: Configure and Encrypt

```bash
cat > .sops.yaml <<EOF
creation_rules:
  - path_regex: secrets/.*\.ya?ml$
    age: $SOPS_AGE_RECIPIENT
  - path_regex: .*\.enc\.ya?ml$
    age: $SOPS_AGE_RECIPIENT
    # ⭐ Encrypt only the values of keys matching this pattern
    encrypted_regex: '^(password|token|secret|key|.*_KEY|.*_SECRET)$'
EOF

mkdir -p secrets
cat > secrets/app.yaml <<'EOF'
environment: production
replicas: 3
database:
  host: db.internal
  port: 5432
  username: appuser
  password: SuperSecret-Prod-2026
api:
  endpoint: https://api.example.com
  token: sk-live-abc123def456
EOF

sops -e -i secrets/app.yaml
cat secrets/app.yaml
```

### Step 4: See What Is and Isn't Hidden

```bash
grep -E 'environment|replicas|host|port|username' secrets/app.yaml     # ⭐ still readable
grep -E 'password|token' secrets/app.yaml                              # ENC[AES256_GCM,...]
```

**✅ Checkpoint:** Structure and non-sensitive values stay in plaintext, so the file **diffs meaningfully in a PR**. Only the secret values are encrypted. That's the property that makes SOPS usable in review — an all-or-nothing encrypted blob produces useless diffs.

### Step 5: Use It

```bash
sops -d secrets/app.yaml                                    # decrypt to stdout
sops -d --extract '["database"]["password"]' secrets/app.yaml; echo
sops secrets/app.yaml                                       # edit decrypted in $EDITOR, re-encrypt on save

# In an app or entrypoint
sops exec-env secrets/app.yaml 'echo "password is: $database_password"' 2>/dev/null \
  || sops -d --output-type json secrets/app.yaml | jq -r '.database.password'
```

### Step 6: Prove It's Safe to Commit

```bash
git init -q 2>/dev/null
git add .sops.yaml secrets/app.yaml && git commit -qm "add encrypted app secrets"

# A scanner finds nothing, because there is nothing to find
gitleaks detect --source . --no-banner 2>/dev/null && echo "  ✅ gitleaks: clean"
git show HEAD:secrets/app.yaml | grep -E 'password|token'
```

> 💡 SOPS supports `age`, AWS KMS, GCP KMS, Azure Key Vault, and PGP — and **multiple recipients at once**, which is how a team shares access. Adding a colleague is `sops updatekeys secrets/app.yaml` after adding their key to `.sops.yaml`. Revoking someone means removing their key **and rotating the secret**, because they could have decrypted it already.

---

## 🔬 Exercise 4: Vault and Dynamic Credentials

The strongest pattern: the credential doesn't exist until it's needed, and expires on its own.

### Step 1: Run Vault and Postgres

```bash
cat > compose.yaml <<'YAML'
services:
  vault:
    image: hashicorp/vault:1.17
    cap_add: [IPC_LOCK]
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: root-token-dev-only
      VAULT_DEV_LISTEN_ADDRESS: 0.0.0.0:8200
    ports: ["8200:8200"]

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: bootstrap-only
      POSTGRES_DB: appdb
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 10
YAML

docker compose up -d
sleep 12
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=root-token-dev-only
alias vault='docker compose exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN=root-token-dev-only vault vault'
vault status | head -6
```

> ⚠️ **Dev mode only.** It runs unsealed, in memory, with a fixed root token. A real Vault is sealed on start, needs unseal keys or auto-unseal, and root tokens are generated then revoked.

### Step 2: Static Secrets (KV v2)

```bash
vault kv put secret/myapp/prod db_password='S3cr3t' api_key='sk-live-xyz'
vault kv get secret/myapp/prod
vault kv get -field=db_password secret/myapp/prod        # ⭐ scriptable

vault kv put secret/myapp/prod db_password='RotatedPassword' api_key='sk-live-xyz'
vault kv metadata get secret/myapp/prod | head -12       # ⭐ versioned automatically
vault kv get -version=1 -field=db_password secret/myapp/prod
vault kv rollback -version=1 secret/myapp/prod
```

### Step 3: Dynamic Database Credentials

This is the part worth the setup.

```bash
vault secrets enable database

vault write database/config/appdb \
  plugin_name=postgresql-database-plugin \
  allowed_roles="readonly,readwrite" \
  connection_url="postgresql://{{username}}:{{password}}@postgres:5432/appdb?sslmode=disable" \
  username="postgres" \
  password="bootstrap-only"

vault write database/roles/readonly \
  db_name=appdb \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
                       GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
  default_ttl="2m" \
  max_ttl="10m"
```

```bash
# ⭐ Generate a credential that did not exist a second ago
vault read database/creds/readonly
```

```
Key                Value
---                -----
lease_id           database/creds/readonly/xY9...
lease_duration     2m
lease_renewable    true
password           A1a-8kZq...
username           v-root-readonly-xK2p8...
```

### Step 4: Watch It Expire

```bash
CREDS=$(vault read -format=json database/creds/readonly)
DBUSER=$(echo "$CREDS" | jq -r .data.username)
DBPASS=$(echo "$CREDS" | jq -r .data.password)
LEASE=$(echo "$CREDS" | jq -r .lease_id)
echo "issued: $DBUSER"

# It works now
docker compose exec -e PGPASSWORD="$DBPASS" postgres \
  psql -U "$DBUSER" -d appdb -c 'SELECT current_user, now();'

# The role really exists in Postgres
docker compose exec -e PGPASSWORD=bootstrap-only postgres \
  psql -U postgres -d appdb -c "\du" | grep -c "$DBUSER"

# Revoke early, or wait 2 minutes for the TTL
vault lease revoke "$LEASE"
sleep 3

docker compose exec -e PGPASSWORD="$DBPASS" postgres \
  psql -U "$DBUSER" -d appdb -c 'SELECT 1;' 2>&1 | tail -2
#   ⭐ authentication failed — the role no longer exists

docker compose exec -e PGPASSWORD=bootstrap-only postgres \
  psql -U postgres -d appdb -c "\du" | grep -c "$DBUSER" || echo "  ✅ role removed from Postgres"
```

**✅ Checkpoint:** Vault created a real Postgres role, handed you the credential, and **deleted the role** when the lease ended. A credential that leaks from a log or a crash dump is worthless two minutes later.

| | Static secret | Dynamic secret |
|---|--------------|----------------|
| Exists before it's requested | Yes | ⭐ **No** |
| Shared between consumers | Usually | Never — one per request |
| Rotation | Manual, coordinated, scary | ⭐ Automatic, continuous |
| Value of a leaked copy | Full, until someone notices | Expires in minutes |
| Attribution after an incident | "someone with the app password" | ⭐ The exact lease and requester |

### Step 5: Policies and App Auth

```bash
vault policy write myapp-read - <<'EOF'
path "secret/data/myapp/*"      { capabilities = ["read"] }
path "database/creds/readonly"  { capabilities = ["read"] }
EOF

vault auth enable approle
vault write auth/approle/role/myapp \
  token_policies="myapp-read" token_ttl=20m token_max_ttl=1h secret_id_ttl=10m

ROLE_ID=$(vault read -field=role_id auth/approle/role/myapp/role-id)
SECRET_ID=$(vault write -f -field=secret_id auth/approle/role/myapp/secret-id)
APP_TOKEN=$(vault write -field=token auth/approle/login role_id="$ROLE_ID" secret_id="$SECRET_ID")

# The app's token can read what it needs...
docker compose exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN="$APP_TOKEN" vault \
  vault kv get -field=db_password secret/myapp/prod

# ...and nothing else
docker compose exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN="$APP_TOKEN" vault \
  vault kv get secret/otherapp/prod 2>&1 | tail -2
```

> 💡 In Kubernetes you'd use the **Kubernetes auth method** instead of AppRole — the pod's ServiceAccount token *is* its Vault identity, so there's no bootstrap secret at all. That closes the "secret-zero" problem: with AppRole you still have to deliver the `secret_id` somehow.

---

## 🔬 Exercise 5: The Rotation Drill

Rotation is a procedure, and an untested procedure doesn't work. Time yourself.

### Step 1: The Scenario

> A `git push` at 14:32 included `config/database.yml` containing the production Postgres password. The repository is public. It has been 6 minutes.

### Step 2: Run It

```bash
cat > rotation-drill.md <<'MD'
# Rotation Drill — Production DB Password

Start time: ____

## 1. ROTATE (target: < 15 min)   ⭐ FIRST. Always first.
- [ ] Generate a new credential
- [ ] Deploy it to every consumer (list them — this is where drills find gaps)
- [ ] Verify the application works on the new credential
- [ ] Revoke the old one
- [ ] Confirm the old one now FAILS

## 2. ASSESS (in parallel)
- [ ] When was it pushed? How long was it exposed?
- [ ] Was the repo public? Forked? Indexed?
- [ ] Check the audit log for use from unknown sources
- [ ] Any data accessed that shouldn't have been?

## 3. CLEAN UP (hygiene, not remediation)
- [ ] git filter-repo to purge from history
- [ ] Force-push; every collaborator re-clones
- [ ] Ask the host to purge cached views and fork references

## 4. PREVENT
- [ ] Pre-commit secret scan
- [ ] Server-side push protection
- [ ] Move this secret to a manager so the next one is dynamic

## Findings
- Consumers I forgot about: ____
- Time to rotate:           ____
- What made it slow:        ____
MD
```

### Step 3: Practise Against Vault

```bash
# The "leaked" credential
vault kv get -field=db_password secret/myapp/prod

# ── ROTATE ──
NEW_PASS=$(openssl rand -base64 24)
vault kv put secret/myapp/prod db_password="$NEW_PASS" api_key='sk-live-xyz'

# Consumers pick it up on their next read — no redeploy needed
vault kv get -field=db_password secret/myapp/prod

# ── VERIFY the old value is gone from the current version ──
vault kv get -version=1 -field=db_password secret/myapp/prod    # still in history…
vault kv metadata delete secret/myapp/prod                       # …destroy every version
vault kv get secret/myapp/prod 2>&1 | tail -1
```

**Time each phase.** The number that matters is **time-to-rotate**, and the thing drills reliably find is a consumer nobody remembered — a cron job, a BI tool, a partner integration.

> ⭐ **Rotation is the fix. History rewriting is cleanup.** A secret is compromised the moment it reaches a remote: bots scan public GitHub within seconds, and forks, clones, CI caches and cached web views all keep copies you cannot reach. An engineer who purges history and skips rotation has done the visible work and none of the useful work.

---

## 🧨 Break It: Four Secret-Management Failures

### Scenario 1: The Secret in the Log

**Break it:**

```bash
cat > leaky-app.sh <<'SH'
#!/usr/bin/env bash
set -x                                  # ❌ traces every command, with its arguments
DB_PASSWORD="${DB_PASSWORD:-fallback-secret}"
echo "connecting..."
curl -s -u "admin:$DB_PASSWORD" http://localhost:9999/health 2>/dev/null || true
SH
chmod +x leaky-app.sh
DB_PASSWORD='sk-live-REAL-SECRET' ./leaky-app.sh 2>&1 | tee app.log
grep -c 'sk-live-REAL-SECRET' app.log
```

**Symptom:** The password is in the log, in plaintext, twice. That log goes to your centralised logging stack (Module 08), gets indexed, replicated, retained for 90 days, and is readable by everyone with Kibana access.

**Investigate — where else does this happen:**

```bash
grep -rn 'set -x' . 2>/dev/null | head
ps auxww | grep -i 'password\|token' | grep -v grep | head    # ⭐ CLI args are world-readable via ps
docker compose logs 2>&1 | grep -ciE 'password|token|secret' || echo "  ✅ compose logs clean"
```

**Root cause:** Four common paths — `set -x`, passing secrets as command-line arguments (visible in `ps` to **every user on the host**), verbose HTTP client logging, and unhandled exceptions that dump the environment.

**Fix:**

```bash
cat > safe-app.sh <<'SH'
#!/usr/bin/env bash
set -Eeuo pipefail
: "${DB_PASSWORD:?DB_PASSWORD is required}"

# Disable tracing around anything that touches the secret
run_authenticated() {
  { set +x; } 2>/dev/null
  # ⭐ Pass via stdin or a file, NEVER as an argument — argv is public
  curl -s --config <(printf 'user = "admin:%s"\n' "$DB_PASSWORD") http://localhost:9999/health
  local rc=$?
  return $rc
}
run_authenticated || echo "request failed (no secret printed)"
SH
chmod +x safe-app.sh
```

| Path | Guard |
|------|-------|
| `set -x` | `{ set +x; } 2>/dev/null` around secret-handling code |
| CLI arguments | ⭐ stdin, a file, or an env var — never `argv` |
| Verbose HTTP logs | Redact `Authorization` headers before logging |
| Exception handlers | Never log the whole environment |
| CI output | `::add-mask::$VALUE` in Actions; `no_log: true` in Ansible; `sensitive` in Terraform |

```bash
rm -f app.log leaky-app.sh safe-app.sh
```

---

### Scenario 2: Kubernetes Secrets Are Not Encrypted

**Break it:**

```bash
# Simulate what a Kubernetes Secret actually is
echo -n 'SuperSecretProdPassword' | base64
echo 'U3VwZXJTZWNyZXRQcm9kUGFzc3dvcmQ=' | base64 -d; echo
```

**Symptom:** Base64 is **encoding, not encryption**. It exists so binary data survives YAML, not to protect anything. Anyone who can read the Secret object — or read etcd, or read a backup of etcd — has the plaintext.

**Investigate (on a real cluster):**

```bash
# Anyone with `get secret` RBAC:
#   kubectl get secret db -o jsonpath='{.data.password}' | base64 -d
#
# Who has it?
#   for sa in $(kubectl get sa -o name); do
#     echo "$sa $(kubectl auth can-i get secrets --as=system:serviceaccount:default:${sa#*/})"
#   done
#
# Is encryption at rest even on? (self-managed clusters)
#   ps aux | grep kube-apiserver | grep -o 'encryption-provider-config=[^ ]*'
```

**Root cause:** Two compounding facts. Secrets are stored in etcd **unencrypted by default**, and the built-in `edit` ClusterRole — the standard grant for a dev team — **includes** Secrets.

**Fix — in increasing order of strength:**

```yaml
# 1. Encryption at rest on the API server
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources: ["secrets"]
    providers:
      - aescbc: { keys: [{ name: key1, secret: <base64 32-byte key> }] }
      - identity: {}
```

```bash
# 2. Sealed Secrets — safe to commit, decryptable only by the cluster controller
#    kubectl create secret generic db --from-literal=password=x --dry-run=client -o yaml \
#      | kubeseal --format yaml > sealed-db.yaml     # ⭐ commit THIS

# 3. ⭐ External Secrets Operator — the plaintext never enters git OR etcd long-term
```

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata: { name: db-creds }
spec:
  refreshInterval: 1h                 # ⭐ picks up rotation automatically
  secretStoreRef: { name: vault-backend, kind: SecretStore }
  target: { name: db-creds }
  data:
    - secretKey: password
      remoteRef: { key: secret/myapp/prod, property: db_password }
```

> ⭐ Combine this with Vault's dynamic credentials and the Kubernetes Secret holds a value that expires on its own. That's the strongest commonly-available posture: nothing permanent in git, nothing permanent in etcd.

---

### Scenario 3: The Encrypted File Anyone Can Decrypt

**Break it:**

```bash
cd secrets-lab 2>/dev/null || cd .
# The private key committed alongside the encrypted file
cp ~/.config/sops/age/keys.txt ./age-key.txt
git add -f age-key.txt 2>/dev/null && git commit -qm "add key for CI" 2>/dev/null
ls -l age-key.txt secrets/app.yaml

SOPS_AGE_KEY_FILE=./age-key.txt sops -d secrets/app.yaml | grep password
```

**Symptom:** The encryption is intact and completely pointless — the decryption key is in the same repository. This happens because someone needed CI to decrypt and took the shortest path.

**Investigate:**

```bash
git log --all --diff-filter=A --name-only --pretty=format: 2>/dev/null \
  | sort -u | grep -iE '\.(key|pem|p12|pfx)$|keys?\.txt|age-key' | head
gitleaks detect --source . --no-banner 2>/dev/null || echo "  ⚠️ gitleaks flagged the private key"
```

**Root cause:** Encryption relocates the problem from "protect the secret" to "protect the key". If the key travels with the ciphertext, you've achieved nothing.

**Fix:**

```bash
git rm --cached age-key.txt -q 2>/dev/null
rm -f age-key.txt
cat >> .gitignore <<'EOF'
*.key
*.pem
age-key*.txt
keys.txt
EOF
git add .gitignore && git commit -qm "never commit private keys" 2>/dev/null
```

| Where the key lives | Verdict |
|---------------------|---------|
| Committed next to the ciphertext | ❌ Pointless |
| A CI secret variable | 🟡 Works, but it's a long-lived secret you must protect |
| **KMS** (AWS/GCP/Azure) | ⭐ The key never leaves the HSM; access is IAM-controlled and audited |
| **OIDC → KMS**, no stored key at all | ⭐⭐ CI proves its identity, then decrypts. Nothing to leak |

```yaml
# .sops.yaml with KMS — access control becomes an IAM question, and it's logged
creation_rules:
  - path_regex: secrets/.*\.yaml$
    kms: 'arn:aws:kms:us-east-1:123456789012:key/abcd-1234'
```

> ⭐ **The question to ask of any secrets scheme**: *"who can decrypt this, and how would I know if they did?"* With a committed key: everyone, and never. With KMS: whoever IAM allows, and every decrypt is in CloudTrail.

---

### Scenario 4: The Secret That Was Never Rotated

**Break it:**

```bash
cat > audit-secret-age.sh <<'SH'
#!/usr/bin/env bash
# How old is every secret you have?
echo "── Vault KV ──"
for p in myapp/prod; do
  created=$(vault kv metadata get -format=json "secret/$p" 2>/dev/null | jq -r '.data.created_time' 2>/dev/null)
  [ -n "$created" ] && [ "$created" != "null" ] && echo "  secret/$p  created: $created"
done
echo "── AWS access keys ──"
echo "  aws iam get-credential-report | ... (see Module 09 Lab 02)"
echo "── K8s Secrets ──"
echo "  kubectl get secrets -A -o json | jq -r '.items[] | \"\(.metadata.creationTimestamp) \(.metadata.namespace)/\(.metadata.name)\"' | sort"
SH
chmod +x audit-secret-age.sh && ./audit-secret-age.sh
```

**Symptom:** In most organisations, running this reveals credentials created years ago that have never changed — surviving multiple staff departures, laptop losses, and vendor breaches. Nobody knows who has copies.

**Investigate — the questions nobody can answer:**

```
For each long-lived secret:
  □ Who has ever had access to it?
  □ Has anyone who left the company had it?
  □ Is it in an old backup, a Slack message, a wiki page, a screenshot?
  □ How long would rotating it take, and what would break?
  □ ⭐ Would you know if someone else were using it right now?
```

**Root cause:** Rotation is manual, coordinated, and risky, so it gets deferred — and the longer it's deferred the riskier it feels, which defers it further.

**Fix — reduce the cost of rotation until it isn't a decision:**

| Approach | Rotation cost |
|----------|--------------|
| Password in a config file | Hours, coordinated, scary |
| Password in a secret manager | Minutes — consumers re-read |
| **Managed rotation** (AWS Secrets Manager + Lambda) | ⭐ Zero — scheduled, automatic |
| **Dynamic credentials** (Vault) | ⭐⭐ N/A — nothing lives long enough to rotate |

```bash
# AWS Secrets Manager: rotation as configuration
# aws secretsmanager rotate-secret --secret-id prod/db \
#   --rotation-lambda-arn arn:aws:lambda:... \
#   --rotation-rules AutomaticallyAfterDays=30

# Alert on staleness
# aws secretsmanager list-secrets \
#   --query 'SecretList[?LastRotatedDate==null].[Name,CreatedDate]' --output table
```

```bash
rm -f audit-secret-age.sh
```

---

### Summary

| Failure | Detection | Prevention |
|---------|-----------|------------|
| Secret in a log | `grep` your own logs for known values | `set +x`, never in `argv`, mask in CI |
| Base64 ≠ encryption | Anyone with `get secret` reads it | Encryption at rest + External Secrets |
| Key committed with ciphertext | Scan history for `*.key`, `keys.txt` | KMS, or OIDC → KMS |
| Never rotated | Audit creation dates | Managed rotation, or dynamic credentials |

**The decision table:**

| Situation | Use |
|-----------|-----|
| Secret needed during a **build** | ⭐ BuildKit `--mount=type=secret` |
| Config in git for **GitOps** | ⭐ SOPS + KMS, or Sealed Secrets |
| App needs a **database** credential | ⭐⭐ Vault dynamic secrets |
| App needs a **third-party API key** | Secret manager + scheduled rotation |
| **CI** needs cloud access | ⭐⭐ OIDC — no stored credential at all |
| Local development | `.env` in `.gitignore`, with fake values |

> ⭐ **The single question to judge any scheme by**: *how long is a leaked copy useful?* Forever → you have a problem, whatever the encryption. Fifteen minutes → the leak is an inconvenience.

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
cd secrets-lab 2>/dev/null || true
docker compose down -v 2>/dev/null
docker rm -f leak-baked leak-env leak-file leak-tmpfs 2>/dev/null
docker rmi leak-baked:v1 buildkit-safe:v1 2>/dev/null
cd .. && rm -rf secrets-lab

# Keep your age key if you'll use SOPS again, or:
# rm -f ~/.config/sops/age/keys.txt

docker ps -a | grep -E 'leak-|vault|postgres' || echo "✅ nothing left running"
```

---

## ✅ Validation

- [ ] Name the four delivery mechanisms and where each one leaks
- [ ] Explain why `ARG` is not a secret mechanism
- [ ] Use a BuildKit secret and prove it isn't in `docker history` or any layer
- [ ] Encrypt a file with SOPS so it still produces a readable PR diff
- [ ] Explain why `encrypted_regex` matters for reviewability
- [ ] Issue a dynamic database credential and demonstrate it expiring
- [ ] Compare static and dynamic secrets on rotation cost and leak value
- [ ] Explain why a Kubernetes Secret is not encrypted, and name two fixes
- [ ] Explain why a key committed beside its ciphertext defeats encryption
- [ ] State the rotation order and why rotation precedes history rewriting

---

## 📝 What to Commit

- The SOPS-encrypted `secrets/app.yaml` and `.sops.yaml` (⚠️ **never** the age key)
- Your Vault policy and database role definitions
- Terminal output showing a dynamic credential working, then failing after revocation
- Your completed `rotation-drill.md`, including the consumers you'd forgotten
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: Security Scanning](./lab-01-security-scanning.md) | [Back to Module README](../README.md) | [Next Lab: Supply Chain Security →](./lab-03-supply-chain-security.md)
