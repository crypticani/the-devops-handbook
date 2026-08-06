# Lab 05: RBAC and Pod Security

## 🎯 Objective

Lock down a cluster the way a real one is locked down. You'll create ServiceAccounts and bind least-privilege Roles, test permissions from *another identity's* point of view, enforce Pod Security Standards at the namespace level, and audit an existing cluster for the privileges nobody meant to grant.

---

## 📋 Prerequisites

- Completed [Lab 04: Scaling and Resource Tuning](./lab-04-scaling-and-resources.md)
- A running cluster with cluster-admin access

```bash
kubectl config current-context          # ⭐ minikube, not anything real
kubectl auth can-i '*' '*' --all-namespaces    # should print: yes
```

---

## 📦 Deliverables and Evidence

- A ServiceAccount with a least-privilege Role, and `kubectl auth can-i --as=` output proving the boundary
- A namespace enforcing the `restricted` Pod Security Standard, with a rejected pod as evidence
- A hardened Deployment that passes `restricted` enforcement
- Your cluster audit output: who is cluster-admin, which pods are privileged, which run as root
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-05/`](../code/lab-05/).

```bash
cp -r /path/to/the-devops-handbook/12-kubernetes/code/lab-05/. .
```

---

## 🔬 Exercise 1: RBAC Fundamentals

### Step 1: Set Up

```bash
mkdir -p k8s-rbac-lab && cd k8s-rbac-lab
kubectl create namespace rbaclab
kubectl config set-context --current --namespace=rbaclab
```

### Step 2: The Four Objects

RBAC has exactly four object types, and the whole model follows from how they combine.

| Object | Scope | Says |
|--------|-------|------|
| **Role** | One namespace | *what* may be done |
| **ClusterRole** | Whole cluster | *what* may be done |
| **RoleBinding** | One namespace | *who* may do it, **here** |
| **ClusterRoleBinding** | Whole cluster | *who* may do it, **everywhere** |

```bash
cat > rbac.yml <<'YAML'
apiVersion: v1
kind: ServiceAccount
metadata: {name: app-reader}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: {name: pod-reader}
rules:
  - apiGroups: [""]                      # "" is the core API group
    resources: ["pods", "pods/log"]      # ⭐ reading logs is a SEPARATE resource
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata: {name: app-reader-pods}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pod-reader
subjects:
  - kind: ServiceAccount
    name: app-reader
    namespace: rbaclab
YAML
kubectl apply -f rbac.yml
```

### Step 3: Test From the Other Identity's Point of View

This is the single most useful RBAC command, and most people never learn it.

```bash
SA=system:serviceaccount:rbaclab:app-reader

kubectl auth can-i list pods        --as="$SA"                    # yes
kubectl auth can-i get  pods/log    --as="$SA"                    # yes
kubectl auth can-i get  configmaps  --as="$SA"                    # yes
kubectl auth can-i create pods      --as="$SA"                    # no  ⭐
kubectl auth can-i delete pods      --as="$SA"                    # no
kubectl auth can-i get secrets      --as="$SA"                    # no  ⭐
kubectl auth can-i list pods        --as="$SA" -n default         # no  ⭐ Role is namespaced

# The whole permission set for that identity
kubectl auth can-i --list --as="$SA"
```

> ⭐ **`kubectl auth can-i --as=<identity>`** answers "what can *they* do?" without impersonating a human or reading YAML. Use it in CI to assert that a service account still can't reach your secrets after someone edits a Role.

### Step 4: Prove It From Inside a Pod

```bash
cat > reader-pod.yml <<'YAML'
apiVersion: v1
kind: Pod
metadata: {name: reader}
spec:
  serviceAccountName: app-reader
  containers:
    - name: kubectl
      image: bitnami/kubectl:latest
      command: ["sleep", "3600"]
      resources:
        requests: {cpu: 25m, memory: 32Mi}
        limits:   {memory: 128Mi}
YAML
kubectl apply -f reader-pod.yml
kubectl wait --for=condition=Ready pod/reader --timeout=90s

kubectl exec reader -- kubectl get pods                 # ✅ allowed
kubectl exec reader -- kubectl get secrets 2>&1 | tail -2   # ❌ Forbidden
kubectl exec reader -- kubectl delete pod reader 2>&1 | tail -2  # ❌ Forbidden
```

The token is mounted automatically at `/var/run/secrets/kubernetes.io/serviceaccount/`:

```bash
kubectl exec reader -- ls -l /var/run/secrets/kubernetes.io/serviceaccount/
kubectl exec reader -- cat /var/run/secrets/kubernetes.io/serviceaccount/namespace; echo
```

### Step 5: Turn the Token Off When It Isn't Needed

**Most pods never call the Kubernetes API**, yet by default every one of them gets a mounted credential.

```bash
cat > no-token.yml <<'YAML'
apiVersion: v1
kind: Pod
metadata: {name: no-token}
spec:
  automountServiceAccountToken: false      # ⭐ set this by default
  containers:
    - name: app
      image: nginx:1.27-alpine
      resources:
        requests: {cpu: 25m, memory: 32Mi}
        limits:   {memory: 64Mi}
YAML
kubectl apply -f no-token.yml
kubectl wait --for=condition=Ready pod/no-token --timeout=60s
kubectl exec no-token -- ls /var/run/secrets/kubernetes.io/ 2>&1 | tail -1   # not there ✅
```

You can also disable it per-ServiceAccount:

```bash
kubectl patch serviceaccount default -p '{"automountServiceAccountToken": false}'
```

> ⭐ **Why this matters**: an attacker who achieves remote code execution in any pod immediately gets that pod's API token. If it's the `default` ServiceAccount with no bindings, that's nearly harmless. If someone bound `default` to `cluster-admin` for convenience, an RCE in your image-resizing sidecar is a full cluster compromise. Turning off the mount removes the credential from the blast radius entirely.

---

## 🔬 Exercise 2: Scoping Permissions Properly

### Step 1: Reuse the Built-in ClusterRoles

Kubernetes ships four you should know before writing your own:

```bash
kubectl get clusterrole view edit admin cluster-admin
kubectl describe clusterrole view | head -25
```

| ClusterRole | Grants |
|-------------|--------|
| `view` | Read most things — ⭐ **but not Secrets** |
| `edit` | `view` + create/update/delete most objects; **cannot** change RBAC |
| `admin` | `edit` + manage Roles and RoleBindings **within a namespace** |
| `cluster-admin` | Everything, everywhere. Grant to almost nobody |

The important trick: bind a **ClusterRole** with a **RoleBinding** to grant it in **one namespace only**.

```bash
cat > scoped.yml <<'YAML'
apiVersion: v1
kind: ServiceAccount
metadata: {name: team-dev}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata: {name: team-dev-edit}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole            # ⭐ a CLUSTER role...
  name: edit
subjects:
  - kind: ServiceAccount
    name: team-dev
    namespace: rbaclab
YAML
kubectl apply -f scoped.yml     # ...bound by a namespaced RoleBinding

DEV=system:serviceaccount:rbaclab:team-dev
kubectl auth can-i create deployments --as="$DEV"                 # yes
kubectl auth can-i create deployments --as="$DEV" -n kube-system  # no ⭐
kubectl auth can-i create rolebindings --as="$DEV"                # no ⭐ edit can't escalate
kubectl auth can-i get secrets        --as="$DEV"                 # yes — 'edit' includes secrets
```

### Step 2: Narrow to Specific Objects

```bash
cat > narrow.yml <<'YAML'
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: {name: restart-one-deployment}
rules:
  # Listing has to be broad — you can't restrict `list` by name
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch"]
  # But mutation can be pinned to ONE object
  - apiGroups: ["apps"]
    resources: ["deployments"]
    resourceNames: ["payments-api"]        # ⭐ this deployment and no other
    verbs: ["patch", "update"]
  - apiGroups: ["apps"]
    resources: ["deployments/scale"]        # ⭐ subresources are separate
    resourceNames: ["payments-api"]
    verbs: ["update", "patch"]
YAML
kubectl apply -f narrow.yml

kubectl create serviceaccount deployer
kubectl create rolebinding deployer-restart --role=restart-one-deployment --serviceaccount=rbaclab:deployer

DEP=system:serviceaccount:rbaclab:deployer
kubectl auth can-i patch deployments/payments-api --as="$DEP"   # yes
kubectl auth can-i patch deployments/other-app    --as="$DEP"   # no  ⭐
kubectl auth can-i delete deployments             --as="$DEP"   # no
```

> 💡 `resourceNames` works for `get`, `patch`, `update`, and `delete` — but **not** for `list`, `watch`, or `create`, because the name isn't known at request time. That's why the Role above splits read and write into separate rules.

### Step 3: Subresources Are Separate Permissions

A frequent source of "I gave them access and it still doesn't work":

| You want them to | You must grant |
|------------------|----------------|
| Read pod logs | `pods/log` — **not** covered by `pods` |
| `kubectl exec` into a pod | `pods/exec` (`create` verb) |
| `kubectl port-forward` | `pods/portforward` (`create`) |
| Scale a Deployment | `deployments/scale` |
| Evict a pod (drain) | `pods/eviction` (`create`) |
| Read a pod's status only | `pods/status` |

```bash
kubectl auth can-i create pods/exec --as="$DEV"
kubectl auth can-i get pods/log     --as=system:serviceaccount:rbaclab:app-reader
```

---

## 🔬 Exercise 3: Pod Security Standards

RBAC controls *who can act*. Pod Security Standards control *what a pod may be*.

### Step 1: The Three Levels

| Level | Allows |
|-------|--------|
| `privileged` | Everything. No restrictions at all |
| `baseline` | Blocks the well-known escapes: privileged containers, host namespaces, hostPath, most capabilities |
| `restricted` | ⭐ Baseline **plus** enforced non-root, no privilege escalation, `RuntimeDefault` seccomp, all capabilities dropped |

Each level has three independent modes: `enforce` (reject), `audit` (log), `warn` (message to the user).

### Step 2: Enforce `restricted`

```bash
kubectl label namespace rbaclab \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted --overwrite

kubectl get namespace rbaclab --show-labels
```

### Step 3: Watch It Reject a Normal Pod

```bash
kubectl run plain-nginx --image=nginx:1.27-alpine 2>&1 | tail -8
```

**Symptom:**

```
Error from server (Forbidden): pods "plain-nginx" is forbidden:
violates PodSecurity "restricted:latest":
  allowPrivilegeEscalation != false,
  unrestricted capabilities,
  runAsNonRoot != true,
  seccompProfile
```

⭐ The error names **every** violation at once, which makes it a genuinely useful checklist rather than a guessing game.

### Step 4: Write a Compliant Pod

```bash
cat > hardened.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hardened
  labels: {app: hardened}
spec:
  replicas: 2
  selector: {matchLabels: {app: hardened}}
  template:
    metadata: {labels: {app: hardened}}
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        seccompProfile: {type: RuntimeDefault}
      containers:
        - name: web
          image: nginxinc/nginx-unprivileged:1.27-alpine   # ⭐ listens on 8080 as non-root
          ports: [{containerPort: 8080, name: http}]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: {drop: ["ALL"]}
          volumeMounts:
            - {name: cache, mountPath: /var/cache/nginx}
            - {name: run,   mountPath: /var/run}
            - {name: tmp,   mountPath: /tmp}
          resources:
            requests: {cpu: 25m, memory: 32Mi}
            limits:   {memory: 64Mi}
          readinessProbe:
            httpGet: {path: /, port: http}
            periodSeconds: 5
      volumes:
        - {name: cache, emptyDir: {}}
        - {name: run,   emptyDir: {}}
        - {name: tmp,   emptyDir: {}}
YAML
kubectl apply -f hardened.yml
kubectl rollout status deploy/hardened --timeout=120s
kubectl get pods -l app=hardened
```

**✅ Checkpoint:** It passes `restricted` enforcement and runs.

Verify each control actually took effect:

```bash
POD=$(kubectl get pod -l app=hardened -o jsonpath='{.items[0].metadata.name}')
kubectl exec "$POD" -- id                                   # uid=10001, not 0
kubectl exec "$POD" -- touch /etc/test 2>&1 | tail -1       # Read-only file system ✅
kubectl exec "$POD" -- touch /tmp/ok && echo "tmpfs writable ✅"
kubectl exec "$POD" -- ls /var/run/secrets/ 2>&1 | tail -1  # no API token ✅
```

> 💡 `readOnlyRootFilesystem: true` is the control that breaks most images, because almost everything writes *somewhere*. The fix is always the same: find the paths it needs (`/tmp`, `/var/run`, a cache dir) and mount an `emptyDir` at each. That's why this manifest has three of them.

### Step 5: Use `warn` Before `enforce`

Turning on `enforce` in a live namespace breaks every non-compliant workload instantly. Roll it out in stages:

```bash
kubectl create namespace staging-psa
# Stage 1 — observe only. Nothing is rejected; violations are logged and warned.
kubectl label namespace staging-psa \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/audit=restricted --overwrite

kubectl -n staging-psa run plain --image=nginx:1.27-alpine 2>&1 | head -5
#   Warning: would violate ... but the pod IS created

kubectl -n staging-psa get pods

# Stage 2 — once the warnings are gone, flip enforce on.
kubectl label namespace staging-psa pod-security.kubernetes.io/enforce=restricted --overwrite

kubectl delete namespace staging-psa
```

---

## 🧨 Break It: Four Security Failures

### Scenario 1: The Convenience Binding That Owns the Cluster

**Break it:**

```bash
# The single most common real-world Kubernetes misconfiguration
kubectl create clusterrolebinding oops-admin \
  --clusterrole=cluster-admin \
  --serviceaccount=rbaclab:default

kubectl auth can-i '*' '*' --as=system:serviceaccount:rbaclab:default --all-namespaces
```

**Symptom:** `yes`. Every pod in `rbaclab` that uses the `default` ServiceAccount — which is every pod that doesn't specify one — now has full cluster admin, mounted as a token inside the container.

**Investigate — demonstrate the actual impact:**

```bash
kubectl run pwn --image=bitnami/kubectl:latest --restart=Never -- sleep 3600
kubectl wait --for=condition=Ready pod/pwn --timeout=90s

kubectl exec pwn -- kubectl get secrets -A --no-headers 2>/dev/null | head -5   # ⭐ every secret in the cluster
kubectl exec pwn -- kubectl get nodes
kubectl exec pwn -- kubectl auth can-i delete nodes
```

An RCE in **any** container in that namespace is now a total cluster compromise.

**Investigate the audit query you should run everywhere:**

```bash
# ⭐ Who is cluster-admin?
kubectl get clusterrolebindings -o json | python3 -c '
import json,sys
for i in json.load(sys.stdin)["items"]:
    if i["roleRef"]["name"] == "cluster-admin":
        subs = ", ".join(f"{s[\"kind\"]}/{s.get(\"namespace\",\"-\")}/{s[\"name\"]}" for s in i.get("subjects") or [])
        print(f"{i[\"metadata\"][\"name\"]}: {subs}")'

# Any binding at all to a 'default' ServiceAccount is a smell
kubectl get rolebindings,clusterrolebindings -A -o wide | grep -i 'default' | head
```

**Root cause:** Someone hit `Forbidden`, and `cluster-admin` made it go away. It always does — that's the problem.

**Fix:**

```bash
kubectl delete clusterrolebinding oops-admin
kubectl delete pod pwn --force --grace-period=0 2>/dev/null

# Grant the narrowest thing that works, to a DEDICATED ServiceAccount:
kubectl create serviceaccount ci-deployer
kubectl create rolebinding ci-deployer-edit --clusterrole=edit --serviceaccount=rbaclab:ci-deployer
kubectl auth can-i --list --as=system:serviceaccount:rbaclab:ci-deployer | head
```

| Rule | Why |
|------|-----|
| Never bind anything to the `default` ServiceAccount | Every unspecified pod inherits it |
| Never grant `cluster-admin` to a workload | Workloads need a handful of verbs, not all of them |
| Set `automountServiceAccountToken: false` by default | Removes the credential from the blast radius |
| Audit `cluster-admin` bindings on a schedule | They accumulate |

---

### Scenario 2: The Escalation Path Hidden in `create pods`

**Break it:**

```bash
kubectl create serviceaccount pod-creator
kubectl create role pod-maker --verb=create,get,list --resource=pods
kubectl create rolebinding pod-maker-b --role=pod-maker --serviceaccount=rbaclab:pod-creator

PC=system:serviceaccount:rbaclab:pod-creator
kubectl auth can-i get secrets --as="$PC"        # no  — looks safe
kubectl auth can-i create pods  --as="$PC"       # yes — looks harmless
```

**Symptom:** By the `can-i` output, this identity cannot read Secrets. In reality it can read every Secret in the namespace, because it can **create a pod that mounts one**:

```bash
# Temporarily relax PSA so the escalation is demonstrable
kubectl label namespace rbaclab pod-security.kubernetes.io/enforce=baseline --overwrite

kubectl create secret generic sensitive --from-literal=api_key=REAL-SECRET-VALUE

cat > escalate.yml <<'YAML'
apiVersion: v1
kind: Pod
metadata: {name: escalate}
spec:
  containers:
    - name: reader
      image: busybox:1.36
      command: ["sh","-c","cat /secrets/api_key; sleep 60"]
      volumeMounts: [{name: s, mountPath: /secrets}]
      resources: {requests: {cpu: 25m, memory: 16Mi}, limits: {memory: 32Mi}}
  volumes:
    - name: s
      secret: {secretName: sensitive}
YAML
kubectl apply -f escalate.yml
sleep 10
kubectl logs escalate            # ⭐ REAL-SECRET-VALUE — read without any `get secrets` permission
```

**Investigate:**

```bash
kubectl auth can-i get secrets --as="$PC"     # still "no" — the check does not see this path
```

**Root cause:** `create pods` is an **implicit escalation primitive**. A pod spec can mount any Secret in the namespace, use any ServiceAccount in the namespace, set `hostPath` to read the node's filesystem, or run privileged. RBAC checks the *pod creation*, not what the pod then does.

**Fix — treat `create pods` as a privileged verb:**

```bash
# 1. Grant workload-shaped verbs on Deployments, not raw pod creation
kubectl create role deploy-manager --verb=get,list,watch,create,update,patch --resource=deployments

# 2. Enforce Pod Security Standards so a created pod can't be dangerous
kubectl label namespace rbaclab pod-security.kubernetes.io/enforce=restricted --overwrite

# 3. Use admission policy (Kyverno / OPA Gatekeeper) to restrict which
#    Secrets and ServiceAccounts a pod spec may reference.
```

```bash
kubectl delete pod escalate --force --grace-period=0 2>/dev/null
kubectl delete secret sensitive
```

> ⭐ **Verbs that are escalation primitives**, and should be treated as near-admin: `create pods` · `create pods/exec` · `create serviceaccounts/token` · `escalate` and `bind` on RBAC · `patch` on nodes · `create` on `persistentvolumes` (hostPath). `kubectl auth can-i` will not warn you about any of them.

---

### Scenario 3: `hostPath` — the Container Escape

**Break it:**

```bash
kubectl create namespace danger
# No PSA labels — the default is `privileged`, i.e. no restrictions at all
cat > escape.yml <<'YAML'
apiVersion: v1
kind: Pod
metadata: {name: escape, namespace: danger}
spec:
  containers:
    - name: shell
      image: busybox:1.36
      command: ["sleep","3600"]
      volumeMounts:
        - {name: host, mountPath: /host}     # ❌ the entire node filesystem
      resources: {requests: {cpu: 25m, memory: 16Mi}, limits: {memory: 32Mi}}
  volumes:
    - name: host
      hostPath: {path: /}
YAML
kubectl apply -f escape.yml
kubectl -n danger wait --for=condition=Ready pod/escape --timeout=90s

kubectl -n danger exec escape -- ls /host/etc/kubernetes/ 2>/dev/null | head
kubectl -n danger exec escape -- cat /host/etc/hostname
kubectl -n danger exec escape -- ls /host/var/lib/kubelet/pods 2>/dev/null | head -3
```

**Symptom:** From inside a container, you're reading the **node's** filesystem — including kubelet credentials, other pods' mounted Secrets, and (on a control-plane node) the etcd certificates. Container isolation is completely bypassed.

**Investigate — audit for it:**

```bash
# ⭐ Every pod in the cluster using hostPath
kubectl get pods -A -o json | python3 -c '
import json,sys
for p in json.load(sys.stdin)["items"]:
    for v in p["spec"].get("volumes") or []:
        if "hostPath" in v:
            print(f"{p[\"metadata\"][\"namespace\"]}/{p[\"metadata\"][\"name\"]}: {v[\"hostPath\"][\"path\"]}")'

# Namespaces with no Pod Security Standard at all
kubectl get ns -o json | python3 -c '
import json,sys
for n in json.load(sys.stdin)["items"]:
    labels = n["metadata"].get("labels") or {}
    if not any(k.startswith("pod-security.kubernetes.io/enforce") for k in labels):
        print(f"⚠️  {n[\"metadata\"][\"name\"]}: no PSA enforcement")'
```

**Root cause:** A namespace with no `pod-security.kubernetes.io/enforce` label defaults to **`privileged`** — no restrictions. Creating a namespace is a normal operation, and nothing prompts you to label it.

**Fix:**

```bash
kubectl label namespace danger pod-security.kubernetes.io/enforce=baseline --overwrite
kubectl -n danger delete pod escape --force --grace-period=0
kubectl -n danger apply -f escape.yml 2>&1 | tail -4     # ⭐ now rejected: hostPath volumes
kubectl delete namespace danger
```

> ⭐ Label **every** namespace at creation. A cluster-wide default is available via `AdmissionConfiguration`, and Kyverno/Gatekeeper can enforce "no namespace without a PSA label" as policy. Some system components legitimately need `hostPath` — the CNI, CSI drivers, node exporters — which is exactly why those live in their own namespaces with their own, deliberate, exceptions.

---

### Scenario 4: The Secret Everyone Could Already Read

**Break it:**

```bash
kubectl create secret generic db-prod --from-literal=password='PROD-PASSWORD-9x2'

# Anyone with `view` on the namespace...
kubectl create serviceaccount viewer
kubectl create rolebinding viewer-b --clusterrole=view --serviceaccount=rbaclab:viewer
V=system:serviceaccount:rbaclab:viewer
kubectl auth can-i get secrets --as="$V"        # no ✅ — `view` deliberately excludes Secrets

# ...but `edit` does NOT exclude them
kubectl auth can-i get secrets --as=system:serviceaccount:rbaclab:team-dev   # yes ⭐
kubectl get secret db-prod -o jsonpath='{.data.password}' | base64 -d; echo
```

**Symptom:** Every engineer with `edit` on the namespace — which is the normal grant for a development team — can read every production credential stored there, in one command, with no audit trail beyond a generic API GET.

**Investigate:**

```bash
# Who can read Secrets in this namespace?
for sa in $(kubectl get sa -o jsonpath='{.items[*].metadata.name}'); do
  printf '%-16s %s\n' "$sa" "$(kubectl auth can-i get secrets --as="system:serviceaccount:rbaclab:$sa" 2>/dev/null)"
done

# Is encryption at rest even on? (On managed clusters, check the provider's docs.)
kubectl get secret db-prod -o yaml | head -6      # base64, not encryption
```

**Root cause:** Two compounding facts. **(1)** Secrets are base64-encoded, and stored in etcd in plaintext unless encryption at rest is explicitly configured. **(2)** The built-in `edit` ClusterRole includes Secrets, so the standard "give the team edit on their namespace" grant hands over every credential.

**Fix — in increasing order of strength:**

```bash
# 1. Use `view` + a narrow custom role instead of `edit` where possible
kubectl create role edit-no-secrets --verb=get,list,watch,create,update,patch,delete \
  --resource=deployments,services,configmaps,pods,jobs,cronjobs
```

```yaml
# 2. Enable encryption at rest on the API server (self-managed clusters)
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources: ["secrets"]
    providers:
      - aescbc: {keys: [{name: key1, secret: <base64 32-byte key>}]}
      - identity: {}
```

```bash
# 3. ⭐ Best: don't store production secrets in etcd at all.
#    External Secrets Operator pulls from Vault / AWS Secrets Manager / GCP SM
#    and the cluster only ever holds a short-lived, auto-rotated copy.
#    Sealed Secrets lets you commit encrypted secrets to git safely.
```

```bash
kubectl delete secret db-prod
```

---

### Summary

| Failure | Why it's easy to miss | Detection |
|---------|----------------------|-----------|
| `cluster-admin` bound to `default` SA | It makes the error go away, and nothing complains | Audit ClusterRoleBindings for `cluster-admin` |
| `create pods` as an escalation path | `kubectl auth can-i get secrets` says **no** | Treat pod-creation verbs as privileged; enforce PSA |
| `hostPath` container escape | New namespaces default to `privileged` | Audit for `hostPath`; label every namespace |
| `edit` grants Secret access | It's the standard team grant | Enumerate who can `get secrets`; use an external secret store |

**The audit script to keep:**

```bash
#!/usr/bin/env bash
echo "── cluster-admin bindings ──"
kubectl get clusterrolebindings -o json | jq -r '.items[]
  | select(.roleRef.name=="cluster-admin")
  | "\(.metadata.name): \([.subjects[]? | "\(.kind)/\(.name)"] | join(", "))"'

echo "── namespaces without PSA enforcement ──"
kubectl get ns -o json | jq -r '.items[]
  | select((.metadata.labels // {}) | has("pod-security.kubernetes.io/enforce") | not)
  | .metadata.name'

echo "── privileged containers ──"
kubectl get pods -A -o json | jq -r '.items[]
  | select(.spec.containers[]?.securityContext?.privileged == true)
  | "\(.metadata.namespace)/\(.metadata.name)"'

echo "── hostPath volumes ──"
kubectl get pods -A -o json | jq -r '.items[]
  | select(.spec.volumes[]?.hostPath)
  | "\(.metadata.namespace)/\(.metadata.name)"'

echo "── host namespaces ──"
kubectl get pods -A -o json | jq -r '.items[]
  | select(.spec.hostNetwork==true or .spec.hostPID==true or .spec.hostIPC==true)
  | "\(.metadata.namespace)/\(.metadata.name)"'

echo "── pods that may run as root ──"
kubectl get pods -A -o json | jq -r '.items[]
  | select((.spec.securityContext.runAsNonRoot // false) != true)
  | "\(.metadata.namespace)/\(.metadata.name)"' | head -20
```

> ⭐ **The theme of this lab**: `kubectl auth can-i` tells you about *direct* permissions. It says nothing about permissions reachable by **creating an object that has permissions** — a pod that mounts a Secret, a pod that uses a privileged ServiceAccount, a pod that mounts the host filesystem. RBAC alone is not a security boundary. RBAC **plus** Pod Security Standards **plus** admission policy is.

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
kubectl delete namespace rbaclab danger staging-psa --ignore-not-found
kubectl delete clusterrolebinding oops-admin --ignore-not-found
kubectl config set-context --current --namespace=default
cd .. && rm -rf k8s-rbac-lab
```

---

## ✅ Validation

- [ ] Explain the four RBAC objects and how a RoleBinding + ClusterRole combination scopes to one namespace
- [ ] Use `kubectl auth can-i --as=` to test another identity's permissions
- [ ] Explain why `pods/log`, `pods/exec`, and `deployments/scale` need separate grants
- [ ] Disable `automountServiceAccountToken` and explain what risk it removes
- [ ] Name the three Pod Security Standard levels and the three modes
- [ ] Write a Deployment that passes `restricted` enforcement, including the emptyDir mounts a read-only root filesystem needs
- [ ] Roll PSA out with `warn` before `enforce`
- [ ] Explain how `create pods` allows reading Secrets without `get secrets`
- [ ] Run the cluster audit and interpret every section

---

## 📝 What to Commit

- `rbac.yml`, `narrow.yml`, `hardened.yml`
- `kubectl auth can-i --list --as=...` output for each ServiceAccount you created
- The PSA rejection message for a non-compliant pod, and proof the hardened one runs
- Your cluster audit output, with a note on anything it found
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: Scaling and Resource Tuning](./lab-04-scaling-and-resources.md) | [Back to Module README](../README.md) | [Next Lab: GitOps with Argo CD →](./lab-06-gitops-argocd.md)
