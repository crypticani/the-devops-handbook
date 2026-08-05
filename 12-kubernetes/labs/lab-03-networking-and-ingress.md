# Lab 03: Services, Ingress, and Network Policy

## 🎯 Objective

Understand how a packet actually reaches a pod. You'll work through every Service type, put an Ingress in front of several services, use cluster DNS the way applications do, lock traffic down with NetworkPolicy, and — most valuably — learn the two-command triage that splits any "I can't reach my service" problem in half.

---

## 📋 Prerequisites

- Completed [Lab 02: Configuration and Health](./lab-02-configuration-and-health.md)
- A running cluster with the Ingress addon:

```bash
kubectl config current-context
minikube addons enable ingress
kubectl -n ingress-nginx rollout status deploy/ingress-nginx-controller --timeout=180s
```

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Manifests for two backend services, an Ingress routing between them, and a NetworkPolicy
- `kubectl get endpoints` output before and after fixing a selector mismatch
- Evidence of host- and path-based routing working through a single Ingress
- Proof that a default-deny NetworkPolicy blocked traffic, and that an explicit allow rule restored it
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies of every file are in [`../code/lab-03/`](../code/lab-03/).

```bash
cp -r /path/to/the-devops-handbook/12-kubernetes/code/lab-03/. .
```

---

## 🔬 Exercise 1: Two Backends and a ClusterIP

### Step 1: Set Up

```bash
mkdir -p k8s-net-lab && cd k8s-net-lab
kubectl create namespace netlab
kubectl config set-context --current --namespace=netlab
```

### Step 2: Deploy Two Distinguishable Services

```bash
cat > backends.yml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata: {name: api-content}
data:
  index.html: "API service — v1\n"
---
apiVersion: v1
kind: ConfigMap
metadata: {name: web-content}
data:
  index.html: "WEB service — v1\n"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  labels: {app: api, tier: backend}
spec:
  replicas: 2
  selector: {matchLabels: {app: api}}
  template:
    metadata: {labels: {app: api, tier: backend}}
    spec:
      containers:
        - name: nginx
          image: nginx:1.27-alpine
          ports: [{containerPort: 80, name: http}]
          volumeMounts: [{name: content, mountPath: /usr/share/nginx/html}]
          readinessProbe:
            httpGet: {path: /, port: http}
            periodSeconds: 3
          resources:
            requests: {cpu: 25m, memory: 32Mi}
            limits:   {memory: 64Mi}
      volumes:
        - {name: content, configMap: {name: api-content}}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  labels: {app: web, tier: frontend}
spec:
  replicas: 2
  selector: {matchLabels: {app: web}}
  template:
    metadata: {labels: {app: web, tier: frontend}}
    spec:
      containers:
        - name: nginx
          image: nginx:1.27-alpine
          ports: [{containerPort: 80, name: http}]
          volumeMounts: [{name: content, mountPath: /usr/share/nginx/html}]
          readinessProbe:
            httpGet: {path: /, port: http}
            periodSeconds: 3
          resources:
            requests: {cpu: 25m, memory: 32Mi}
            limits:   {memory: 64Mi}
      volumes:
        - {name: content, configMap: {name: web-content}}
---
apiVersion: v1
kind: Service
metadata: {name: api}
spec:
  selector: {app: api}            # ⭐ matches POD labels, nothing else
  ports: [{name: http, port: 8080, targetPort: http}]
---
apiVersion: v1
kind: Service
metadata: {name: web}
spec:
  selector: {app: web}
  ports: [{name: http, port: 80, targetPort: http}]
YAML

kubectl apply -f backends.yml
kubectl rollout status deploy/api && kubectl rollout status deploy/web
```

### Step 3: The Two Commands That Matter

```bash
kubectl get svc
kubectl get endpoints            # ⭐ THE most useful networking command in Kubernetes
```

You should see both services with two pod IPs each:

```
NAME   ENDPOINTS                       AGE
api    10.244.0.12:80,10.244.0.13:80   30s
web    10.244.0.14:80,10.244.0.15:80   30s
```

> ⭐ **Learn this reflex now.** `kubectl get endpoints <svc>` splits every service-connectivity problem in half:
>
> - **Empty (`<none>`)** → the problem is *above* the Service: label selector mismatch, pods not Ready, or wrong namespace
> - **Populated** → the problem is *below* it: ports, the app's bind address, DNS, NetworkPolicy, or Ingress
>
> One command, half the search space gone. On newer clusters `kubectl get endpointslices` shows the same thing with more detail.

### Step 4: Note the Port Triplet

```bash
kubectl get svc api -o jsonpath='{.spec.ports[0]}' | python3 -m json.tool
```

Three different numbers, and mixing them up is a classic bug:

| Field | Meaning |
|-------|---------|
| `port` | The port **the Service** listens on — what clients connect to (`api:8080`) |
| `targetPort` | The port **on the pod** traffic is forwarded to (here, the named port `http` → 80) |
| `containerPort` | **Documentation only.** Kubernetes does not enforce it; what matters is what the process actually binds |

Using a **named** `targetPort` (`http`) rather than a number means you can change the container's port in one place.

---

## 🔬 Exercise 2: Cluster DNS

### Step 1: Get a Toolbox Pod

```bash
kubectl run netshoot --rm -it --restart=Never --image=nicolaka/netshoot -- bash
```

Everything in this step runs **inside** that pod:

```bash
# Same namespace — short name works
curl -s http://api:8080/
curl -s http://web/

# The fully-qualified name every short name expands to
curl -s http://api.netlab.svc.cluster.local:8080/

# What the resolver is actually doing
cat /etc/resolv.conf
#   nameserver 10.96.0.10
#   search netlab.svc.cluster.local svc.cluster.local cluster.local
#   options ndots:5

nslookup api
nslookup api.netlab.svc.cluster.local

# ⭐ Every Service also gets SRV records for its NAMED ports
nslookup -type=SRV _http._tcp.api.netlab.svc.cluster.local

# Reach a service in ANOTHER namespace — the short name will NOT work
nslookup kubernetes.default.svc.cluster.local
curl -sk https://kubernetes.default.svc.cluster.local/version | head -5

exit
```

**The DNS naming scheme:**

```
<service>.<namespace>.svc.cluster.local
   api    .  netlab  . svc.cluster.local
```

| From | Use |
|------|-----|
| Same namespace | `api` |
| Different namespace | `api.netlab` |
| Anywhere, unambiguous | `api.netlab.svc.cluster.local` |
| A specific pod of a StatefulSet | `pod-0.headless-svc.netlab.svc.cluster.local` |

> 💡 `options ndots:5` means any name with fewer than 5 dots is tried against every entry in `search` **first**. Looking up `api` costs one query; looking up `google.com` (1 dot) costs four failed queries before the real one. On a DNS-heavy service this is a measurable latency cost — the fix is a trailing dot (`google.com.`) or a per-pod `dnsConfig` with a lower `ndots`.

---

## 🔬 Exercise 3: Service Types

### Step 1: ClusterIP → NodePort → LoadBalancer

The types **stack** — each builds on the previous one.

```bash
# ClusterIP (what you already have) — internal only
kubectl get svc web

# NodePort — opens a port on EVERY node
kubectl patch svc web -p '{"spec":{"type":"NodePort"}}'
kubectl get svc web
NODEPORT=$(kubectl get svc web -o jsonpath='{.spec.ports[0].nodePort}')
echo "node port: $NODEPORT"
curl -s "http://$(minikube ip):$NODEPORT/"

# LoadBalancer — asks the cloud for an external IP.
# On minikube this stays <pending> until you run `minikube tunnel`.
kubectl patch svc web -p '{"spec":{"type":"LoadBalancer"}}'
kubectl get svc web
# EXTERNAL-IP: <pending>   ← on a real cloud this becomes an ALB/NLB. Each one COSTS MONEY.

kubectl patch svc web -p '{"spec":{"type":"ClusterIP","ports":[{"name":"http","port":80,"targetPort":"http","nodePort":null}]}}'
```

### Step 2: A Headless Service

```bash
cat > headless.yml <<'YAML'
apiVersion: v1
kind: Service
metadata: {name: api-headless}
spec:
  clusterIP: None          # ⭐ headless — no virtual IP, no load balancing
  selector: {app: api}
  ports: [{name: http, port: 8080, targetPort: http}]
YAML
kubectl apply -f headless.yml

kubectl run netshoot --rm -it --restart=Never --image=nicolaka/netshoot -- \
  sh -c 'echo "--- normal service (one virtual IP) ---"; nslookup api;
         echo "--- headless (every pod IP) ---";        nslookup api-headless'
```

**✅ Checkpoint:** A normal Service resolves to **one** virtual IP. A headless Service resolves to **every pod IP**, letting the client do its own load balancing or address individual pods. This is what StatefulSets use for stable per-pod DNS names.

### Step 3: ExternalName

```bash
cat > external.yml <<'YAML'
apiVersion: v1
kind: Service
metadata: {name: external-db}
spec:
  type: ExternalName
  externalName: db.production.example.com   # a CNAME, nothing more
YAML
kubectl apply -f external.yml
kubectl run netshoot --rm -it --restart=Never --image=nicolaka/netshoot -- nslookup external-db
```

Useful for pointing an in-cluster name at something outside the cluster, so application config stays identical across environments.

| Type | Reachable from | Cost | Use for |
|------|----------------|------|---------|
| **ClusterIP** | Inside the cluster | Free | Service-to-service. **The right answer 90% of the time** |
| **Headless** | Inside; resolves to pod IPs | Free | StatefulSets, client-side load balancing |
| **NodePort** | Any node IP, ports 30000–32767 | Free | Local clusters, bare metal behind your own LB |
| **LoadBalancer** | Internet | 💸 One cloud LB **per Service** | A single non-HTTP service exposed directly |
| **ExternalName** | DNS CNAME only | Free | Pointing at an external host |

---

## 🔬 Exercise 4: Ingress

One load balancer in front of many services — the reason you don't give every microservice `type: LoadBalancer`.

### Step 1: Host and Path Routing

```bash
cat > ingress.yml <<'YAML'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: apps
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  ingressClassName: nginx
  rules:
    # ── Path-based routing on one host ──
    - host: apps.local
      http:
        paths:
          - path: /api(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service:
                name: api
                port: {number: 8080}
          - path: /()(.*)
            pathType: ImplementationSpecific
            backend:
              service:
                name: web
                port: {number: 80}
    # ── Host-based routing ──
    - host: api.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api
                port: {number: 8080}
YAML

kubectl apply -f ingress.yml
kubectl get ingress
kubectl describe ingress apps | tail -20
```

### Step 2: Test It

```bash
IP=$(minikube ip); echo "cluster ip: $IP"

# Use --resolve so the Host header is correct without editing /etc/hosts
curl -s --resolve "apps.local:80:$IP" http://apps.local/api/     # → API service — v1
curl -s --resolve "apps.local:80:$IP" http://apps.local/          # → WEB service — v1
curl -s --resolve "api.local:80:$IP"  http://api.local/           # → API service — v1

# Wrong Host header → no rule matches → the controller's default backend
curl -s --resolve "nope.local:80:$IP" http://nope.local/ -o /dev/null -w '%{http_code}\n'   # 404
```

**✅ Checkpoint:** One IP, one load balancer, three routing rules, two backend services.

### Step 3: pathType Matters

| `pathType` | Behaviour |
|------------|-----------|
| `Exact` | Matches the path **exactly**. `/api` does not match `/api/` |
| `Prefix` | Matches on **path segments**. `/api` matches `/api` and `/api/v1`, but **not** `/apifoo` |
| `ImplementationSpecific` | Up to the controller — ingress-nginx treats it as a **regex** |

```bash
# Prove Prefix is segment-based, not string-based
kubectl patch ingress apps --type json -p '[{"op":"replace","path":"/spec/rules/1/http/paths/0/pathType","value":"Prefix"},{"op":"replace","path":"/spec/rules/1/http/paths/0/path","value":"/api"}]'
sleep 3
curl -s --resolve "api.local:80:$IP" http://api.local/api/v1 -o /dev/null -w 'segment match: %{http_code}\n'
curl -s --resolve "api.local:80:$IP" http://api.local/apifoo -o /dev/null -w 'string match:  %{http_code}\n'   # 404 ⭐
```

### Step 4: TLS

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt -subj "/CN=apps.local" \
  -addext "subjectAltName=DNS:apps.local" 2>/dev/null

kubectl create secret tls apps-tls --cert=tls.crt --key=tls.key

kubectl patch ingress apps --type json -p '[{"op":"add","path":"/spec/tls","value":[{"hosts":["apps.local"],"secretName":"apps-tls"}]}]'
sleep 5

curl -sk --resolve "apps.local:443:$IP" https://apps.local/api/
echo | openssl s_client -connect "$IP:443" -servername apps.local 2>/dev/null | openssl x509 -noout -subject -dates
```

**✅ Checkpoint:** TLS terminates at the Ingress. Traffic from the Ingress to your pods is plain HTTP — which is exactly why you also need NetworkPolicy.

---

## 🔬 Exercise 5: NetworkPolicy

> ⚠️ NetworkPolicy is enforced by the **CNI plugin**, not by Kubernetes itself. minikube's default CNI ignores it silently. Enable a CNI that enforces:
>
> ```bash
> minikube start --cni=calico        # a fresh cluster, or:
> kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/calico.yaml
> kubectl -n kube-system rollout status ds/calico-node --timeout=300s
> ```
>
> If you skip this, the policies below will apply cleanly and do **nothing** — which is itself worth seeing once.

### Step 1: Confirm Everything Is Open by Default

```bash
kubectl run client --rm -it --restart=Never --image=nicolaka/netshoot --labels="app=client" -- \
  sh -c 'curl -s -m3 http://api:8080/ && curl -s -m3 http://web/'
```

Both succeed. **A pod with no NetworkPolicy accepts traffic from anywhere in the cluster.**

### Step 2: Default Deny

```bash
cat > netpol.yml <<'YAML'
# ⭐ Start here in every namespace: deny all ingress, then allow explicitly
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: default-deny-ingress}
spec:
  podSelector: {}          # every pod in this namespace
  policyTypes: [Ingress]
YAML
kubectl apply -f netpol.yml

kubectl run client --rm -it --restart=Never --image=nicolaka/netshoot --labels="app=client" -- \
  sh -c 'curl -s -m3 http://api:8080/ || echo "❌ api BLOCKED"'
```

Also notice the Ingress controller can no longer reach your services:

```bash
curl -s --resolve "apps.local:80:$(minikube ip)" http://apps.local/api/ -o /dev/null -w '%{http_code}\n'   # 503
```

### Step 3: Allow What You Actually Need

```bash
cat >> netpol.yml <<'YAML'
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: allow-client-to-api}
spec:
  podSelector: {matchLabels: {app: api}}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector: {matchLabels: {app: client}}
      ports:
        - {protocol: TCP, port: 80}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: allow-ingress-controller}
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels: {kubernetes.io/metadata.name: ingress-nginx}
      ports:
        - {protocol: TCP, port: 80}
YAML
kubectl apply -f netpol.yml

kubectl run client --rm -it --restart=Never --image=nicolaka/netshoot --labels="app=client" -- \
  sh -c 'echo "api:"; curl -s -m3 http://api:8080/ || echo "BLOCKED";
         echo "web:"; curl -s -m3 http://web/     || echo "BLOCKED (expected — no rule)"'

curl -s --resolve "apps.local:80:$(minikube ip)" http://apps.local/api/     # ✅ works again
```

**✅ Checkpoint:** `client` reaches `api` but not `web`. The Ingress controller reaches both. Everything else is denied.

**Key NetworkPolicy rules:**

| Rule | Detail |
|------|--------|
| Policies are **additive** | Traffic is allowed if **any** policy allows it. There is no "deny" rule |
| A pod with **no** policy | Accepts everything |
| A pod with **any** policy | Denies everything except what that policy allows |
| `podSelector` vs `namespaceSelector` | Selects within this namespace vs. selects whole namespaces. Both in **one** `from:` entry means AND; as two entries it means OR |
| Egress is separate | `policyTypes: [Egress]` — remember to allow DNS to `kube-system` port 53 or everything breaks |
| Enforcement is the CNI's job | Calico, Cilium, Weave enforce. Flannel and minikube's default do not |

---

## 🧨 Break It: Four Networking Failures

### Scenario 1: The Selector Typo

**Break it:**

```bash
kubectl patch svc api -p '{"spec":{"selector":{"app":"api-service"}}}'   # ❌ no pod has this label
sleep 3
kubectl get endpoints api
```

**Symptom:** `ENDPOINTS: <none>`. Every request gets connection refused or a 503 from the Ingress. `kubectl get pods` shows everything `1/1 Running` and perfectly healthy, which is what makes this confusing.

**Investigate:**

```bash
kubectl get endpoints api                                       # ⭐ <none> — problem is ABOVE the Service
kubectl get svc api -o jsonpath='{.spec.selector}'; echo        # {"app":"api-service"}
kubectl get pods -l app=api --show-labels                       # app=api,tier=backend
# The two do not match.
```

**Root cause:** A Service is bound to pods **only** by label selector. There is no validation — Kubernetes will happily create a Service whose selector matches nothing, and report no error.

**Fix:**

```bash
kubectl patch svc api -p '{"spec":{"selector":{"app":"api"}}}'
kubectl get endpoints api                                       # ✅ two IPs
```

> ⭐ Empty endpoints has exactly three causes: **(1)** selector doesn't match pod labels, **(2)** pods exist but are **not Ready** — unready pods are excluded by design, **(3)** wrong namespace. Check them in that order.

---

### Scenario 2: The App Bound to Localhost

**Break it:**

```bash
cat > localhost-trap.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: localhost-trap}
spec:
  replicas: 1
  selector: {matchLabels: {app: localhost-trap}}
  template:
    metadata: {labels: {app: localhost-trap}}
    spec:
      containers:
        - name: app
          image: python:3.12-alpine
          command: ["python3","-m","http.server","8000","--bind","127.0.0.1"]   # ❌
          ports: [{containerPort: 8000}]
---
apiVersion: v1
kind: Service
metadata: {name: localhost-trap}
spec:
  selector: {app: localhost-trap}
  ports: [{port: 8000, targetPort: 8000}]
YAML
kubectl apply -f localhost-trap.yml
kubectl rollout status deploy/localhost-trap

kubectl get endpoints localhost-trap        # ⭐ endpoints ARE populated
kubectl run t --rm -it --restart=Never --image=nicolaka/netshoot -- \
  curl -s -m3 http://localhost-trap:8000/ || echo "❌ connection refused"
```

**Symptom:** Endpoints are populated, the pod is `1/1 Running`, and connections are still refused. Endpoints being healthy tells you the problem is *below* the Service — so you look at ports and binding.

**Investigate:**

```bash
POD=$(kubectl get pod -l app=localhost-trap -o jsonpath='{.items[0].metadata.name}')

# From INSIDE the pod, localhost works:
kubectl exec "$POD" -- python3 -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/').status)"

# From another pod, using the pod IP directly, it does not:
PODIP=$(kubectl get pod "$POD" -o jsonpath='{.status.podIP}')
kubectl run t --rm -it --restart=Never --image=nicolaka/netshoot -- curl -s -m3 "http://$PODIP:8000/" || echo "❌ refused"

kubectl exec "$POD" -- sh -c 'netstat -tlnp 2>/dev/null || ss -tlnp'   # ⭐ 127.0.0.1:8000, not 0.0.0.0:8000
```

**Root cause:** Each pod has its own network namespace. `127.0.0.1` inside the container means *that container* — nothing outside it can connect, including kube-proxy. This is the same rule as Docker (Module 05), one layer up.

**Fix:**

```bash
kubectl patch deploy localhost-trap --type json -p \
 '[{"op":"replace","path":"/spec/template/spec/containers/0/command",
    "value":["python3","-m","http.server","8000","--bind","0.0.0.0"]}]'
kubectl rollout status deploy/localhost-trap
kubectl run t --rm -it --restart=Never --image=nicolaka/netshoot -- curl -s -m3 http://localhost-trap:8000/ | head -3
kubectl delete -f localhost-trap.yml
```

---

### Scenario 3: The Cross-Namespace Name That Doesn't Resolve

**Break it:**

```bash
kubectl create namespace other
kubectl -n other run consumer --rm -it --restart=Never --image=nicolaka/netshoot -- \
  sh -c 'curl -s -m3 http://api:8080/ || echo "❌ could not resolve api"'
```

**Symptom:** `Could not resolve host: api` — from a pod in a different namespace, even though the Service exists and is healthy.

**Investigate:**

```bash
kubectl -n other run t --rm -it --restart=Never --image=nicolaka/netshoot -- sh -c '
  cat /etc/resolv.conf
  echo "--- short name ---";  nslookup api          || true
  echo "--- with namespace ---"; nslookup api.netlab
  echo "--- FQDN ---";        nslookup api.netlab.svc.cluster.local'
```

**Root cause:** The `search` list in `/etc/resolv.conf` is built from the **pod's own namespace**. A pod in `other` searches `other.svc.cluster.local` first — `api` doesn't exist there.

**Fix — always use the namespace-qualified name for cross-namespace calls:**

```bash
kubectl -n other run consumer --rm -it --restart=Never --image=nicolaka/netshoot -- \
  curl -s -m3 http://api.netlab:8080/
```

```bash
kubectl delete namespace other
```

> 💡 Two related traps. **(1)** A NetworkPolicy in `netlab` selecting `podSelector` only will block the other namespace even after DNS works — you need a `namespaceSelector`. **(2)** Hardcoding the FQDN suffix `svc.cluster.local` breaks on clusters configured with a different cluster domain; `api.netlab` is the portable form.

---

### Scenario 4: The NetworkPolicy That Broke DNS

The single most common NetworkPolicy mistake.

**Break it:**

```bash
cat > deny-egress.yml <<'YAML'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: default-deny-egress}
spec:
  podSelector: {}
  policyTypes: [Egress]      # ❌ denies ALL outbound — including DNS
YAML
kubectl apply -f deny-egress.yml

kubectl run client --rm -it --restart=Never --image=nicolaka/netshoot --labels="app=client" -- \
  sh -c 'time curl -s -m5 http://api:8080/ || echo "❌ failed"'
```

**Symptom:** Everything times out rather than failing fast, and the error is a **DNS** error, not a connection error — which sends people looking at CoreDNS instead of at the policy they just applied.

**Investigate:**

```bash
kubectl run t --rm -it --restart=Never --image=nicolaka/netshoot --labels="app=client" -- sh -c '
  echo "--- can we resolve? ---";  nslookup api 2>&1 | head -5
  echo "--- can we reach a pod IP directly? ---"
  curl -s -m3 http://'"$(kubectl get endpoints api -o jsonpath='{.subsets[0].addresses[0].ip}')"':80/ || echo "also blocked"'

kubectl get networkpolicy
kubectl describe networkpolicy default-deny-egress
```

**Root cause:** A blanket egress deny blocks UDP/TCP port 53 to CoreDNS in `kube-system`. Name resolution fails before any connection is attempted. Because DNS clients retry with a timeout, this presents as *slowness* first and failure second.

**Fix — every default-deny-egress policy needs a DNS exception:**

```bash
cat > allow-dns.yml <<'YAML'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: allow-dns-egress}
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels: {kubernetes.io/metadata.name: kube-system}
          podSelector:
            matchLabels: {k8s-app: kube-dns}
      ports:
        - {protocol: UDP, port: 53}
        - {protocol: TCP, port: 53}      # ⭐ TCP too — large responses fall back to it
    # then allow the traffic you actually want
    - to:
        - podSelector: {matchLabels: {app: api}}
      ports:
        - {protocol: TCP, port: 80}
YAML
kubectl apply -f allow-dns.yml

kubectl run client --rm -it --restart=Never --image=nicolaka/netshoot --labels="app=client" -- \
  curl -s -m5 http://api:8080/
```

```bash
kubectl delete -f deny-egress.yml -f allow-dns.yml
```

---

### The Triage Flow

```
Can't reach a service?
│
├─ kubectl get endpoints <svc>          ⭐ ALWAYS FIRST
│  │
│  ├─ <none>  → the problem is ABOVE the Service
│  │            • selector ≠ pod labels  (kubectl get pods --show-labels)
│  │            • pods exist but are NOT Ready
│  │            • wrong namespace
│  │
│  └─ has IPs → the problem is BELOW the Service
│               • targetPort ≠ the port the process binds
│               • app bound to 127.0.0.1 instead of 0.0.0.0   (ss -tlnp in the pod)
│               • curl the POD IP directly to isolate
│               • DNS: nslookup from a netshoot pod
│               • NetworkPolicy: kubectl get networkpolicy
│               • Ingress: describe it, then read the controller logs
```

| Failure | Endpoints | Distinguishing signal |
|---------|-----------|----------------------|
| Selector mismatch | `<none>` | Pods healthy, labels differ |
| Pods not Ready | `<none>` | `kubectl get pods` shows `0/1` |
| Wrong `targetPort` | populated | Connection refused from everywhere including the pod IP |
| Bound to localhost | populated | Works via `exec` + localhost, fails via pod IP |
| Cross-namespace name | n/a | **DNS** error, not a connection error |
| NetworkPolicy | populated | Timeout, not refusal; `get networkpolicy` is non-empty |
| Ingress rule | populated | Service works internally; only external access fails |

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
kubectl delete namespace netlab other --ignore-not-found
kubectl config set-context --current --namespace=default
cd .. && rm -rf k8s-net-lab
```

---

## ✅ Validation

- [ ] Explain the difference between `port`, `targetPort`, and `containerPort`
- [ ] Use `kubectl get endpoints` as the first triage step and say what each result rules out
- [ ] Resolve a Service by short name, namespaced name, and FQDN, and explain when each works
- [ ] Describe what `ndots:5` does and why it costs extra DNS queries
- [ ] Compare ClusterIP, headless, NodePort, LoadBalancer, and ExternalName, including cost
- [ ] Route two services through one Ingress by both path and host
- [ ] Explain the difference between `Exact`, `Prefix`, and `ImplementationSpecific` path types
- [ ] Terminate TLS at the Ingress with a Secret
- [ ] Write a default-deny NetworkPolicy plus explicit allow rules
- [ ] Explain why a default-deny **egress** policy must allow DNS

---

## 📝 What to Commit

- `backends.yml`, `ingress.yml`, `netpol.yml`
- `kubectl get endpoints` output before and after the selector fix
- curl output proving path- and host-based routing
- Before/after evidence for the NetworkPolicy
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: Configuration and Health](./lab-02-configuration-and-health.md) | [Back to Module README](../README.md) | [Next Lab: Scaling and Resource Tuning →](./lab-04-scaling-and-resources.md)
