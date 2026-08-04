# Lab 02: Configuration and Health — ConfigMaps, Secrets, and Probes

## 🎯 Objective

Separate configuration from code the way Kubernetes intends, and make your workloads honestly report their own health. By the end you'll know exactly which probe gates traffic, which one restarts a container, why a config change sometimes needs a restart and sometimes doesn't, and how to debug a pod stuck at `0/1 Running`.

---

## 📋 Prerequisites

- Completed [Lab 01: Kubernetes Basics](./lab-01-kubernetes-basics.md)
- A running cluster (`minikube start --driver=docker`) and `kubectl` configured
- Familiarity with `kubectl describe` and reading the Events section

```bash
kubectl config current-context      # ⭐ confirm you are on minikube, not something real
kubectl get nodes
```

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Manifests for a ConfigMap, a Secret, and a Deployment that consumes both
- Output proving a pod stayed out of the Service endpoints until it was actually ready
- A record of the difference between an env-var config change and a volume-mounted one
- Your `failure-notes.md` from the Break It section
- Cleanup confirmation

---

## 📂 Lab Files

Every file this lab creates also exists as a real, CI-validated file in
[`../code/lab-02/`](../code/lab-02/).

```bash
# Option A — type them out yourself (recommended the first time; that's the learning)
# Option B — start from the reference copies
cp -r /path/to/the-devops-handbook/12-kubernetes/code/lab-02/. .
```

See [`../code/README.md`](../code/README.md).

---

## 🔬 Exercise 1: Configuration as Data

### Step 1: Set Up

```bash
mkdir -p k8s-config-lab && cd k8s-config-lab
kubectl create namespace configlab
kubectl config set-context --current --namespace=configlab
```

### Step 2: A ConfigMap Three Ways

There are three ways to create a ConfigMap, and each produces a different shape.

```bash
# (a) From literals — keys you type
kubectl create configmap app-settings \
  --from-literal=LOG_LEVEL=info \
  --from-literal=MAX_CONNECTIONS=100 \
  --from-literal=FEATURE_DARK_MODE=true

# (b) From a file — the FILENAME becomes the key, the CONTENT becomes the value
cat > app.properties <<'EOF'
server.port=8080
server.timeout=30s
cache.enabled=true
EOF
kubectl create configmap app-properties --from-file=app.properties

# (c) From an env-style file — each LINE becomes a key
cat > app.env <<'EOF'
DATABASE_HOST=postgres.configlab.svc.cluster.local
DATABASE_PORT=5432
EOF
kubectl create configmap app-env --from-env-file=app.env

kubectl get cm
kubectl get cm app-settings -o yaml
kubectl get cm app-properties -o yaml   # ⭐ note: ONE key, whose value is the whole file
kubectl get cm app-env -o yaml          # ⭐ note: TWO keys
```

**✅ Checkpoint:** You can explain why `--from-file` and `--from-env-file` produce different key structures from the same input.

### Step 3: Secrets Are Not Encrypted

```bash
kubectl create secret generic db-credentials \
  --from-literal=username=appuser \
  --from-literal=password='S3cr3t-P@ss'

kubectl get secret db-credentials -o yaml
# The values are base64. That is ENCODING, not encryption.

# ⭐ Anyone with `get secret` RBAC can read this in one command:
kubectl get secret db-credentials -o jsonpath='{.data.password}' | base64 -d; echo

# All keys at once
kubectl get secret db-credentials \
  -o go-template='{{range $k,$v := .data}}{{$k}}={{$v | base64decode}}{{"\n"}}{{end}}'
```

> ⚠️ **Kubernetes Secrets are base64-encoded, not encrypted.** They are stored in etcd, and by default that storage is plaintext too. What makes a Secret meaningfully different from a ConfigMap is that it is *treated* differently: not printed in `describe` output, mountable as `tmpfs`, and gated by separate RBAC. For production you need **encryption at rest** on the API server plus an external store (External Secrets Operator, Sealed Secrets, Vault) so plaintext never enters git.

### Step 4: Declarative Versions

Everything above was imperative, which is fine for exploring. Real work is declarative:

```bash
cat > config.yml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-settings
data:
  LOG_LEVEL: "info"
  MAX_CONNECTIONS: "100"
  FEATURE_DARK_MODE: "true"
  # A whole file as one key — the | preserves newlines
  app.properties: |
    server.port=8080
    server.timeout=30s
    cache.enabled=true
---
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
stringData:              # ⭐ stringData takes PLAIN text; Kubernetes encodes it for you
  username: appuser
  password: S3cr3t-P@ss
YAML

kubectl apply -f config.yml
kubectl describe cm app-settings
kubectl describe secret db-credentials    # ⭐ values are hidden, unlike a ConfigMap
```

> 💡 Use `stringData` when writing Secrets by hand — you write plain text and Kubernetes base64-encodes it. `data` requires you to encode it yourself, which is an easy place to make a silent mistake.

---

## 🔬 Exercise 2: Consuming Configuration

### Step 1: Every Injection Method in One Pod

```bash
cat > deployment.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: config-demo
  labels: {app: config-demo}
spec:
  replicas: 2
  selector:
    matchLabels: {app: config-demo}
  template:
    metadata:
      labels: {app: config-demo}
    spec:
      containers:
        - name: app
          image: nginx:1.27-alpine
          ports:
            - {containerPort: 80, name: http}

          # (1) Every key in a ConfigMap/Secret becomes an env var
          envFrom:
            - configMapRef: {name: app-settings}
            - secretRef:    {name: db-credentials}

          env:
            # (2) One specific key, optionally renamed
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef: {name: db-credentials, key: password}
            # (3) The downward API — pod metadata as env vars
            - name: POD_NAME
              valueFrom:
                fieldRef: {fieldPath: metadata.name}
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef: {fieldPath: metadata.namespace}
            - name: NODE_NAME
              valueFrom:
                fieldRef: {fieldPath: spec.nodeName}
            - name: MEMORY_LIMIT
              valueFrom:
                resourceFieldRef: {containerName: app, resource: limits.memory}

          # (4) Mounted as files
          volumeMounts:
            - {name: config-volume, mountPath: /etc/app,     readOnly: true}
            - {name: secret-volume, mountPath: /etc/secrets, readOnly: true}

          resources:
            requests: {cpu: 50m,  memory: 64Mi}
            limits:   {memory: 128Mi}

      volumes:
        - name: config-volume
          configMap:
            name: app-settings
            items:
              - {key: app.properties, path: application.properties}
        - name: secret-volume
          secret:
            secretName: db-credentials
            defaultMode: 0400        # ⭐ read-only, owner only
YAML

kubectl apply -f deployment.yml
kubectl rollout status deploy/config-demo
```

### Step 2: Verify Each Method

```bash
POD=$(kubectl get pod -l app=config-demo -o jsonpath='{.items[0].metadata.name}')

echo "── env vars from envFrom ──"
kubectl exec "$POD" -- printenv | grep -E 'LOG_LEVEL|MAX_CONNECTIONS|FEATURE_DARK_MODE|username|password'

echo "── the renamed secret key ──"
kubectl exec "$POD" -- printenv DB_PASSWORD

echo "── downward API ──"
kubectl exec "$POD" -- printenv | grep -E 'POD_NAME|POD_NAMESPACE|NODE_NAME|MEMORY_LIMIT'

echo "── mounted config file ──"
kubectl exec "$POD" -- cat /etc/app/application.properties

echo "── mounted secret ──"
kubectl exec "$POD" -- ls -l /etc/secrets/
kubectl exec "$POD" -- cat /etc/secrets/username; echo
```

**✅ Checkpoint:** All four injection methods work, and you can see the same underlying data arriving through each.

### Step 3: The Update Behaviour That Surprises Everyone

This is the most practically important thing in the lab.

```bash
# Change ONE value
kubectl patch cm app-settings --type merge -p '{"data":{"LOG_LEVEL":"debug","app.properties":"server.port=8080\nserver.timeout=60s\ncache.enabled=false\n"}}'

echo "── immediately after the change ──"
kubectl exec "$POD" -- printenv LOG_LEVEL          # still "info"  ❌
kubectl exec "$POD" -- cat /etc/app/application.properties   # still the old file

echo "── wait for the kubelet sync period (up to ~60s) ──"
sleep 75

kubectl exec "$POD" -- printenv LOG_LEVEL          # STILL "info"  ❌ env vars NEVER update
kubectl exec "$POD" -- cat /etc/app/application.properties   # ✅ the new content
```

| Injection method | Updates without a restart? |
|------------------|---------------------------|
| `env` / `envFrom` | ❌ **Never.** The value is fixed when the container starts |
| Volume mount | ✅ Yes, within ~1 minute (kubelet sync period) |
| Volume mount with `subPath` | ❌ **No.** A `subPath` mount is not updated — a very common trap |
| Secret as `tmpfs` volume | ✅ Same as ConfigMap volumes |

```bash
# To pick up an env-var change, you must restart:
kubectl rollout restart deploy/config-demo
kubectl rollout status deploy/config-demo
POD=$(kubectl get pod -l app=config-demo -o jsonpath='{.items[0].metadata.name}')
kubectl exec "$POD" -- printenv LOG_LEVEL          # ✅ "debug"
```

> ⭐ **The production pattern**: annotate the pod template with a **hash of the config**, so any config change automatically changes the pod spec and triggers a rollout:
> ```yaml
> template:
>   metadata:
>     annotations:
>       checksum/config: "<sha256 of the ConfigMap contents>"
> ```
> Helm does this with `{{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}`. Kustomize does it automatically with `configMapGenerator`, which appends a content hash to the ConfigMap *name*. Without one of these, config changes silently don't apply and you spend an afternoon wondering why.

---

## 🔬 Exercise 3: Probes — Three Jobs, Three Probes

### Step 1: Understand What Each One Controls

| Probe | Fails → | Answers |
|-------|---------|---------|
| **startupProbe** | Kill and restart the container | "Have I finished booting?" Disables the other two until it passes |
| **readinessProbe** | Remove the pod from Service endpoints — **no restart** | "Can I serve traffic *right now*?" |
| **livenessProbe** | **Restart the container** | "Am I deadlocked and unrecoverable?" |

### Step 2: Deploy an App With All Three

```bash
cat > probes-demo.yml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: probe-content
data:
  # /healthz always returns 200. /ready we will toggle by hand.
  default.conf: |
    server {
      listen 80;
      location / {
        return 200 "serving\n";
        add_header Content-Type text/plain;
      }
      location /healthz {
        return 200 "alive\n";
        add_header Content-Type text/plain;
      }
      location /ready {
        # Serves the file if it exists, 503 if it doesn't
        root /var/ready;
        try_files /ready.txt =503;
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: probes-demo
  labels: {app: probes-demo}
spec:
  replicas: 3
  selector:
    matchLabels: {app: probes-demo}
  template:
    metadata:
      labels: {app: probes-demo}
    spec:
      containers:
        - name: web
          image: nginx:1.27-alpine
          ports: [{containerPort: 80, name: http}]
          command: ["/bin/sh", "-c"]
          args:
            - |
              mkdir -p /var/ready
              # Simulate a slow start: not ready for the first 15 seconds
              (sleep 15 && echo ok > /var/ready/ready.txt) &
              exec nginx -g 'daemon off;'

          startupProbe:                # ⭐ gives the app up to 60s to boot
            httpGet: {path: /healthz, port: http}
            periodSeconds: 2
            failureThreshold: 30

          readinessProbe:              # ⭐ gates TRAFFIC
            httpGet: {path: /ready, port: http}
            periodSeconds: 3
            failureThreshold: 2
            successThreshold: 1

          livenessProbe:               # ⭐ gates RESTART — cheap, no dependencies
            httpGet: {path: /healthz, port: http}
            periodSeconds: 10
            failureThreshold: 3

          volumeMounts:
            - {name: conf, mountPath: /etc/nginx/conf.d}
          resources:
            requests: {cpu: 50m, memory: 32Mi}
            limits:   {memory: 96Mi}
      volumes:
        - name: conf
          configMap: {name: probe-content}
---
apiVersion: v1
kind: Service
metadata:
  name: probes-demo
spec:
  selector: {app: probes-demo}
  ports: [{port: 80, targetPort: http}]
YAML

kubectl apply -f probes-demo.yml
```

### Step 3: Watch Readiness Gate the Traffic

Open a second terminal and watch:

```bash
# Terminal 2
watch -n1 'kubectl get pods -l app=probes-demo; echo; kubectl get endpoints probes-demo'
```

In terminal 1:

```bash
kubectl get pods -l app=probes-demo -w
```

**What you should observe, in order:**

1. Pods appear as `0/1 Running` — the container is up, but **not ready**
2. `kubectl get endpoints probes-demo` shows **no addresses**
3. After ~15 seconds the readiness probe starts passing
4. Pods flip to `1/1 Running` and their IPs appear in the endpoints list

```bash
kubectl get endpoints probes-demo -o jsonpath='{.subsets[*].addresses[*].ip}'; echo
```

**✅ Checkpoint:** You watched a pod be *running but deliberately excluded from the Service* until it was genuinely ready. That gap is what makes zero-downtime deploys possible.

### Step 4: Break Readiness on One Pod

```bash
POD=$(kubectl get pod -l app=probes-demo -o jsonpath='{.items[0].metadata.name}')

# Remove the readiness marker — this pod stops being ready
kubectl exec "$POD" -- rm /var/ready/ready.txt

sleep 12
kubectl get pods -l app=probes-demo
# ⭐ That pod is now 0/1. It is NOT restarted — readiness never restarts anything.

kubectl get endpoints probes-demo
# ⭐ Only 2 IPs now. Traffic is being routed away from the unhealthy pod, automatically.

kubectl describe pod "$POD" | grep -A3 'Readiness probe failed'

# Restore it
kubectl exec "$POD" -- sh -c 'echo ok > /var/ready/ready.txt'
sleep 8
kubectl get pods -l app=probes-demo    # back to 1/1
```

**✅ Checkpoint:** A failing readiness probe removes a pod from load balancing without killing it — the pod gets a chance to recover, and users never see the error.

### Step 5: Prove Liveness Restarts

```bash
POD=$(kubectl get pod -l app=probes-demo -o jsonpath='{.items[0].metadata.name}')
kubectl get pod "$POD" -o jsonpath='{.status.containerStatuses[0].restartCount}'; echo

# Kill nginx inside the container — /healthz stops answering
kubectl exec "$POD" -- sh -c 'nginx -s stop' 2>/dev/null || true

# livenessProbe: periodSeconds 10 × failureThreshold 3 ≈ 30s to detect
sleep 45
kubectl get pod "$POD"
kubectl get pod "$POD" -o jsonpath='{.status.containerStatuses[0].restartCount}'; echo   # ⭐ now 1
kubectl describe pod "$POD" | grep -A5 Events | head -12
```

**✅ Checkpoint:** `RESTARTS` incremented and the Events show `Liveness probe failed ... Container web failed liveness probe, will be restarted`. Note the **pod** was not recreated — its name and IP are unchanged. Only the container inside it restarted.

---

## 🧨 Break It: Four Configuration and Health Failures

### Scenario 1: The Missing Key

**Break it:**

```bash
cat > missing-key.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: missing-key}
spec:
  replicas: 1
  selector: {matchLabels: {app: missing-key}}
  template:
    metadata: {labels: {app: missing-key}}
    spec:
      containers:
        - name: app
          image: nginx:1.27-alpine
          env:
            - name: API_TOKEN
              valueFrom:
                secretKeyRef: {name: db-credentials, key: api_token}   # ❌ no such key
YAML
kubectl apply -f missing-key.yml
sleep 5
kubectl get pods -l app=missing-key
```

**Symptom:** `CreateContainerConfigError`. Not `CrashLoopBackOff`, not `ImagePullBackOff` — a status most people have never seen, so they don't know where to look.

**Investigate:**

```bash
kubectl describe pod -l app=missing-key | tail -12
#   Error: couldn't find key api_token in Secret configlab/db-credentials   ⭐ names it exactly

kubectl get secret db-credentials -o jsonpath='{.data}' | tr ',' '\n'
```

**Root cause:** The container cannot be *configured*, so it is never *created*. `kubectl logs` returns nothing useful because there has never been a running container to log.

**Fix — either add the key, or mark the reference optional:**

```yaml
env:
  - name: API_TOKEN
    valueFrom:
      secretKeyRef:
        name: db-credentials
        key: api_token
        optional: true          # ⭐ pod starts; the env var is simply absent
```

> 💡 `optional: true` is right for genuinely optional settings and wrong for required ones — a pod that starts without its database password will fail later, further from the cause. Prefer failing at creation for anything mandatory.

```bash
kubectl delete -f missing-key.yml
```

---

### Scenario 2: The Liveness Probe That Amplifies an Outage

This is the most damaging probe mistake, and it looks completely reasonable in review.

**Break it:**

```bash
cat > bad-liveness.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: bad-liveness}
spec:
  replicas: 3
  selector: {matchLabels: {app: bad-liveness}}
  template:
    metadata: {labels: {app: bad-liveness}}
    spec:
      containers:
        - name: web
          image: nginx:1.27-alpine
          ports: [{containerPort: 80}]
          # ❌ The liveness probe checks a DEPENDENCY that doesn't exist
          livenessProbe:
            exec:
              command: ["sh", "-c", "wget -q -T2 -O- http://database.configlab.svc.cluster.local:5432 || exit 1"]
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 2
YAML
kubectl apply -f bad-liveness.yml
sleep 60
kubectl get pods -l app=bad-liveness
```

**Symptom:** Every replica is in `CrashLoopBackOff` with a climbing restart count. The application itself is completely healthy — nginx is serving fine — but the "database" doesn't exist, so every pod kills itself, simultaneously, forever.

**Investigate:**

```bash
kubectl get pods -l app=bad-liveness -o custom-columns='NAME:.metadata.name,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount'
kubectl describe pod -l app=bad-liveness | grep -A3 'Liveness probe failed' | head

# Prove the app itself is fine:
POD=$(kubectl get pod -l app=bad-liveness -o jsonpath='{.items[0].metadata.name}')
kubectl exec "$POD" -- wget -qO- http://localhost/ 2>/dev/null | head -2
```

**Root cause:** The liveness probe checks something the container **cannot fix by restarting**. When a shared dependency has a blip, every replica fails liveness at the same moment, every replica restarts at the same moment, and a partial degradation becomes a total outage — caused entirely by the health check.

**Fix — the rule is absolute:**

```yaml
# ✅ LIVENESS: cheap, local, no dependencies. "Is my own process wedged?"
livenessProbe:
  httpGet: {path: /healthz, port: http}    # returns 200 if the process is responsive
  periodSeconds: 10
  failureThreshold: 3

# ✅ READINESS: may check dependencies. Failing removes it from traffic,
#    which is recoverable and correct — the pod rejoins when the dep returns.
readinessProbe:
  httpGet: {path: /ready, port: http}      # checks the DB connection pool
  periodSeconds: 5
  failureThreshold: 2
```

| Probe | May check a dependency? | Why |
|-------|------------------------|-----|
| **liveness** | ❌ **Never** | Restarting cannot fix someone else's outage; it turns a blip into a cascade |
| **readiness** | ✅ Yes | Removing from traffic is reversible and is the correct response |
| **startup** | ❌ No | Same reasoning as liveness |

```bash
kubectl delete -f bad-liveness.yml
```

---

### Scenario 3: The Slow Starter Killed by Its Own Liveness Probe

**Break it:**

```bash
cat > slow-start.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: slow-start}
spec:
  replicas: 1
  selector: {matchLabels: {app: slow-start}}
  template:
    metadata: {labels: {app: slow-start}}
    spec:
      containers:
        - name: web
          image: nginx:1.27-alpine
          ports: [{containerPort: 80}]
          command: ["/bin/sh","-c"]
          args: ["sleep 40; exec nginx -g 'daemon off;'"]   # 40s "JVM warm-up"
          # ❌ No startupProbe, and liveness starts checking almost immediately
          livenessProbe:
            httpGet: {path: /, port: 80}
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 3
YAML
kubectl apply -f slow-start.yml
sleep 90
kubectl get pods -l app=slow-start
```

**Symptom:** `CrashLoopBackOff`, restart count climbing. The application **never gets to finish starting** — liveness kills it at ~20 seconds, every time. It would work perfectly if it were left alone for 40.

**Investigate:**

```bash
kubectl describe pod -l app=slow-start | grep -A6 Events | head -12
#   Liveness probe failed: connection refused
#   Container web failed liveness probe, will be restarted

kubectl get pod -l app=slow-start -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}'; echo
```

**Root cause:** `initialDelaySeconds` is a guess. Tuning it for the worst case (a cold JVM on a loaded node) makes real failures take that long to detect. That trade-off is exactly what `startupProbe` exists to remove.

**Fix:**

```yaml
# ⭐ startupProbe suspends liveness and readiness until it passes.
#    Budget = failureThreshold × periodSeconds = 30 × 5 = 150s of grace.
startupProbe:
  httpGet: {path: /, port: 80}
  periodSeconds: 5
  failureThreshold: 30

# Now liveness can be aggressive, because it only runs on a started container
livenessProbe:
  httpGet: {path: /, port: 80}
  periodSeconds: 10
  failureThreshold: 3
```

```bash
kubectl patch deploy slow-start --type json -p '[
 {"op":"add","path":"/spec/template/spec/containers/0/startupProbe",
  "value":{"httpGet":{"path":"/","port":80},"periodSeconds":5,"failureThreshold":30}},
 {"op":"remove","path":"/spec/template/spec/containers/0/livenessProbe/initialDelaySeconds"}]'
kubectl rollout status deploy/slow-start --timeout=3m
kubectl get pods -l app=slow-start        # ⭐ 1/1 Running, 0 restarts
kubectl delete -f slow-start.yml
```

---

### Scenario 4: The subPath Mount That Never Updates

**Break it:**

```bash
cat > subpath-trap.yml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata: {name: sp-config}
data:
  app.conf: "version=1\n"
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: subpath-trap}
spec:
  replicas: 1
  selector: {matchLabels: {app: subpath-trap}}
  template:
    metadata: {labels: {app: subpath-trap}}
    spec:
      containers:
        - name: app
          image: nginx:1.27-alpine
          volumeMounts:
            # ❌ subPath is used to place ONE file into a directory that has other files.
            #    The cost: it is mounted ONCE and never updated.
            - name: cfg
              mountPath: /etc/nginx/app.conf
              subPath: app.conf
      volumes:
        - name: cfg
          configMap: {name: sp-config}
YAML
kubectl apply -f subpath-trap.yml
kubectl rollout status deploy/subpath-trap

POD=$(kubectl get pod -l app=subpath-trap -o jsonpath='{.items[0].metadata.name}')
kubectl exec "$POD" -- cat /etc/nginx/app.conf      # version=1

kubectl patch cm sp-config --type merge -p '{"data":{"app.conf":"version=2\n"}}'
sleep 90
kubectl exec "$POD" -- cat /etc/nginx/app.conf      # ⭐ STILL version=1, forever
```

**Symptom:** The ConfigMap shows `version=2`. The file in the pod says `version=1`. It will still say `version=1` tomorrow. Meanwhile a *non*-subPath mount would have updated within a minute — so the behaviour is inconsistent across your own manifests, which makes it maddening to debug.

**Investigate:**

```bash
kubectl get cm sp-config -o jsonpath='{.data.app\.conf}'      # version=2 — the source IS updated
kubectl exec "$POD" -- cat /etc/nginx/app.conf                # version=1 — the mount is not
kubectl get pod "$POD" -o jsonpath='{.spec.containers[0].volumeMounts}' | tr ',' '\n' | grep -i subpath
```

**Root cause:** A normal ConfigMap volume mount is a symlink farm the kubelet atomically re-points on update. A `subPath` mount bind-mounts a single file at container creation, bypassing that mechanism entirely. It is documented behaviour, and it catches nearly everyone once.

**Fix — pick one of three:**

```yaml
# (a) Mount the whole directory (no subPath) and use items: to control filenames
volumeMounts:
  - {name: cfg, mountPath: /etc/app, readOnly: true}
volumes:
  - name: cfg
    configMap:
      name: sp-config
      items: [{key: app.conf, path: app.conf}]

# (b) Keep subPath, but make config changes trigger a rollout
template:
  metadata:
    annotations:
      checksum/config: "<sha256 of the ConfigMap>"

# (c) Use Kustomize configMapGenerator — the ConfigMap NAME gets a content hash,
#     so any change is a new object and therefore a new pod spec.
```

```bash
kubectl delete -f subpath-trap.yml
```

---

### Summary

| Failure | Status you'd see | First command | Rule |
|---------|-----------------|---------------|------|
| Missing ConfigMap/Secret key | `CreateContainerConfigError` | `kubectl describe pod` | The event names the exact key |
| Liveness checks a dependency | All replicas `CrashLoopBackOff` at once | `kubectl describe` → probe events | **Liveness never checks dependencies** |
| Slow start killed by liveness | `CrashLoopBackOff`, restarts climbing | Restart count + probe events | Use `startupProbe`, not a big `initialDelaySeconds` |
| `subPath` config never updates | Silent — no error at all | Compare `kubectl get cm` with `kubectl exec cat` | Avoid `subPath`, or hash-annotate the pod template |
| Env-var config never updates | Silent | Same comparison | Env vars are fixed at container start. Restart to apply |

> ⭐ **The theme**: two of these four produce **no error output at all**. Config drift between what's in etcd and what's in the container is invisible unless you go and compare. Build the habit of `kubectl exec <pod> -- printenv` / `cat` to verify what the container *actually* received, rather than trusting what you applied.

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
kubectl delete namespace configlab
kubectl config set-context --current --namespace=default
cd .. && rm -rf k8s-config-lab
```

---

## ✅ Validation

You've completed this lab when you can:

- [ ] Create ConfigMaps from literals, files, and env-files, and explain the different key shapes
- [ ] Explain why a Secret is not encrypted, and what actually makes it different from a ConfigMap
- [ ] Inject configuration four ways: `envFrom`, `secretKeyRef`, downward API, and volume mount
- [ ] State which methods update live and which need a restart — and explain the `subPath` exception
- [ ] Describe what each of the three probes controls, and what happens when each one fails
- [ ] Watch a pod stay out of Service endpoints until readiness passes
- [ ] Explain why a liveness probe must never check a downstream dependency
- [ ] Diagnose `CreateContainerConfigError` from the Events section
- [ ] Use `startupProbe` to protect a slow-starting application

---

## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- `config.yml`, `deployment.yml`, and `probes-demo.yml`
- Output showing endpoints empty → populated as readiness passed
- Your notes on the env-var vs volume-mount update behaviour, with the commands that proved it
- `failure-notes.md` covering all four Break It scenarios

---

[← Previous Lab: Kubernetes Basics](./lab-01-kubernetes-basics.md) | [Back to Module README](../README.md) | [Next Lab: Services, Ingress and Network Policy →](./lab-03-networking-and-ingress.md)
