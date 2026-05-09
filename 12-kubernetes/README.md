# Module 12: Kubernetes

> *"Kubernetes doesn't make simple things simple. It makes impossible things possible." — Kelsey Hightower*

---

## 🎯 Why This Module Matters

You can containerize an app with Docker. But how do you run 50 containers across 10 servers, handle failures, scale on demand, and do zero-downtime deployments? **Kubernetes** — the industry-standard container orchestration platform.

**In real-world DevOps work**, you will:
- Deploy applications as Pods, Deployments, and Services
- Scale applications horizontally based on load
- Perform zero-downtime rolling updates and rollbacks
- Configure networking, storage, and secrets
- Debug failing pods and cluster issues
- Manage Kubernetes with Helm charts

---

## 📚 Table of Contents

1. [Why Kubernetes?](#1-why-kubernetes)
2. [Architecture](#2-architecture)
3. [Core Objects](#3-core-objects)
4. [kubectl — The Essential Tool](#4-kubectl--the-essential-tool)
5. [Deployments and Scaling](#5-deployments-and-scaling)
6. [Services and Networking](#6-services-and-networking)
7. [ConfigMaps and Secrets](#7-configmaps-and-secrets)
8. [Storage](#8-storage)
9. [Helm — Package Manager](#9-helm--package-manager)
10. [Common Mistakes and Anti-Patterns](#10-common-mistakes-and-anti-patterns)
11. [Debugging Mindset](#11-debugging-mindset)
12. [Interview Insights](#12-interview-insights)

---

## 1. Why Kubernetes?

### The Problem It Solves

```
WITHOUT ORCHESTRATION:
  "Container crashed at 3am" → You get paged, manually restart
  "Traffic spiked 10x" → You manually spin up more containers
  "New version deploy" → Stop old, start new → DOWNTIME
  "Server died" → All containers on that server are gone

WITH KUBERNETES:
  Container crashed → K8s auto-restarts it (self-healing)
  Traffic spiked → K8s auto-scales (HPA)
  New version → Rolling update (zero downtime)
  Server died → K8s reschedules containers to healthy nodes
```

### When to Use Kubernetes

```
USE K8S WHEN:
  ✅ Running multiple microservices
  ✅ Need auto-scaling and self-healing
  ✅ Multiple environments (dev, staging, prod)
  ✅ Team size > 5 engineers
  ✅ High availability is critical

DON'T USE K8S WHEN:
  ❌ Single monolithic app
  ❌ Small team (1-3 people)
  ❌ Simple deployment needs (use Docker Compose)
  ❌ You don't have the expertise to operate it
```

---

## 2. Architecture

### Cluster Components

```
┌─────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER                         │
│                                                              │
│  ┌─────────────── CONTROL PLANE ──────────────────────┐     │
│  │                                                     │     │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────┐ │     │
│  │  │API Server│  │  Scheduler   │  │  Controller  │ │     │
│  │  │          │  │              │  │  Manager     │ │     │
│  │  │ kubectl  │  │ "Where to   │  │ "Desired vs  │ │     │
│  │  │ talks to │  │  place pods" │  │  actual state"│ │     │
│  │  │ this     │  │              │  │              │ │     │
│  │  └──────────┘  └──────────────┘  └──────────────┘ │     │
│  │  ┌──────────┐                                     │     │
│  │  │  etcd    │  Key-value store (cluster state)    │     │
│  │  └──────────┘                                     │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌──── WORKER NODE 1 ─────┐  ┌──── WORKER NODE 2 ─────┐   │
│  │  ┌─────┐  ┌─────┐      │  │  ┌─────┐  ┌─────┐      │   │
│  │  │Pod A│  │Pod B│      │  │  │Pod C│  │Pod D│      │   │
│  │  └─────┘  └─────┘      │  │  └─────┘  └─────┘      │   │
│  │                         │  │                         │   │
│  │  ┌───────┐ ┌─────────┐ │  │  ┌───────┐ ┌─────────┐ │   │
│  │  │kubelet│ │kube-proxy│ │  │  │kubelet│ │kube-proxy│ │   │
│  │  └───────┘ └─────────┘ │  │  └───────┘ └─────────┘ │   │
│  └─────────────────────────┘  └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Component Roles

| Component | Role |
|-----------|------|
| **API Server** | Front door to the cluster. kubectl talks to this |
| **etcd** | Key-value database storing ALL cluster state |
| **Scheduler** | Decides which node to place a new pod on |
| **Controller Manager** | Ensures desired state = actual state (reconciliation loop) |
| **kubelet** | Agent on each node — manages pods on that node |
| **kube-proxy** | Networking — routes traffic to the right pods |

---

## 3. Core Objects

### Pod — Smallest Deployable Unit

```yaml
# pod.yml — You rarely create Pods directly (use Deployments)
apiVersion: v1
kind: Pod
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      ports:
        - containerPort: 80
      resources:
        requests:
          memory: "64Mi"
          cpu: "100m"
        limits:
          memory: "128Mi"
          cpu: "250m"
```

### Deployment — Manages Pods

```yaml
# deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web-app
spec:
  replicas: 3                          # Run 3 copies
  selector:
    matchLabels:
      app: web-app
  template:                            # Pod template
    metadata:
      labels:
        app: web-app
    spec:
      containers:
        - name: web
          image: nginx:1.25
          ports:
            - containerPort: 80
          resources:
            requests:
              memory: "64Mi"
              cpu: "100m"
            limits:
              memory: "128Mi"
              cpu: "250m"
          livenessProbe:               # Is the container alive?
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:              # Is it ready for traffic?
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 3
            periodSeconds: 5
```

### Service — Expose Pods to Network

```yaml
# service.yml
apiVersion: v1
kind: Service
metadata:
  name: web-app
spec:
  selector:
    app: web-app                       # Routes to pods with this label
  type: ClusterIP                      # Internal only (default)
  ports:
    - port: 80                         # Service port
      targetPort: 80                   # Container port
---
# NodePort — accessible from outside cluster
apiVersion: v1
kind: Service
metadata:
  name: web-app-external
spec:
  selector:
    app: web-app
  type: NodePort
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30080                  # Accessible at <NodeIP>:30080
---
# LoadBalancer — cloud provider creates an external LB
apiVersion: v1
kind: Service
metadata:
  name: web-app-lb
spec:
  selector:
    app: web-app
  type: LoadBalancer
  ports:
    - port: 80
      targetPort: 80
```

### Service Types

```
ClusterIP:     Internal only (service-to-service communication)
               web-app.default.svc.cluster.local:80
               
NodePort:      Exposes on each node's IP at a static port (30000-32767)
               <NodeIP>:30080
               
LoadBalancer:  Cloud LB → forwards to NodePort → to Pods
               External users → ALB → Pods

Ingress:       HTTP/HTTPS routing (paths, domains → services)
               example.com/api → api-service
               example.com/web → web-service
```

---

## 4. kubectl — The Essential Tool

### Must-Know Commands

```bash
# ─── VIEWING RESOURCES ───
kubectl get pods                        # List pods
kubectl get pods -o wide                # Show node, IP
kubectl get deployments                 # List deployments
kubectl get services                    # List services
kubectl get all                         # Everything in namespace
kubectl get nodes                       # List cluster nodes

# ─── DETAILED INFO ───
kubectl describe pod <name>             # Detailed pod info + events
kubectl describe deployment <name>      # Deployment details
kubectl logs <pod-name>                 # Container logs
kubectl logs <pod-name> -f              # Follow logs (tail)
kubectl logs <pod-name> --previous      # Logs from crashed container

# ─── CREATING / APPLYING ───
kubectl apply -f deployment.yml         # Create/update from file
kubectl apply -f ./k8s/                 # Apply all files in directory
kubectl delete -f deployment.yml        # Delete resources from file

# ─── SCALING ───
kubectl scale deployment web-app --replicas=5

# ─── UPDATES ───
kubectl set image deployment/web-app web=nginx:1.26
kubectl rollout status deployment/web-app
kubectl rollout undo deployment/web-app   # Rollback!
kubectl rollout history deployment/web-app

# ─── DEBUGGING ───
kubectl exec -it <pod-name> -- /bin/bash  # Shell into pod
kubectl port-forward <pod-name> 8080:80   # Local port forwarding
kubectl top pods                          # Resource usage
kubectl get events --sort-by='.lastTimestamp'
```

### Namespaces

```bash
# Namespaces isolate resources (like folders)
kubectl get namespaces
kubectl create namespace staging
kubectl get pods -n staging              # Pods in staging namespace
kubectl apply -f app.yml -n staging      # Deploy to staging

# Common namespaces:
#   default     — where your stuff goes if unspecified
#   kube-system — Kubernetes system components
#   kube-public — Publicly readable resources
```

---

## 5. Deployments and Scaling

### Rolling Update (Default)

```
Deployment update: nginx:1.25 → nginx:1.26

Step 1: [v1] [v1] [v1]           ← 3 pods running v1
Step 2: [v1] [v1] [v1] [v2]     ← New v2 pod created
Step 3: [v1] [v1] [v2] [v2]     ← Old v1 pod terminated
Step 4: [v1] [v2] [v2] [v2]     ← Continue rolling
Step 5: [v2] [v2] [v2]          ← All running v2

Zero downtime — at least some pods always running!
```

### Update Strategy Configuration

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1            # Max extra pods during update
      maxUnavailable: 0      # Don't kill old before new is ready
```

### Horizontal Pod Autoscaler (HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70    # Scale up when CPU > 70%
```

```bash
# Or create via CLI
kubectl autoscale deployment web-app --min=2 --max=10 --cpu-percent=70
```

---

## 6. Services and Networking

### Ingress — HTTP Routing

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-service
                port:
                  number: 80
```

### DNS Inside the Cluster

```
Every Service gets a DNS name:
  <service-name>.<namespace>.svc.cluster.local

  web-app.default.svc.cluster.local
  database.production.svc.cluster.local

  Short form (same namespace): web-app
  Cross-namespace: web-app.other-namespace
```

---

## 7. ConfigMaps and Secrets

### ConfigMap — Non-Sensitive Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_ENV: "production"
  LOG_LEVEL: "info"
  DATABASE_HOST: "db.default.svc.cluster.local"
  config.json: |
    {
      "feature_flags": {
        "new_ui": true
      }
    }
---
# Use in a Deployment
spec:
  containers:
    - name: app
      envFrom:
        - configMapRef:
            name: app-config        # All keys as env vars
      volumeMounts:
        - name: config-volume
          mountPath: /app/config
  volumes:
    - name: config-volume
      configMap:
        name: app-config
        items:
          - key: config.json
            path: config.json       # Mounted as file
```

### Secret — Sensitive Data

```bash
# Create from CLI
kubectl create secret generic db-creds \
  --from-literal=DB_USER=admin \
  --from-literal=DB_PASS=supersecret

# Create from YAML (values must be base64 encoded)
echo -n 'admin' | base64        # YWRtaW4=
echo -n 'supersecret' | base64  # c3VwZXJzZWNyZXQ=
```

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-creds
type: Opaque
data:
  DB_USER: YWRtaW4=              # base64 encoded
  DB_PASS: c3VwZXJzZWNyZXQ=
---
# Use in a Deployment
spec:
  containers:
    - name: app
      env:
        - name: DB_USER
          valueFrom:
            secretKeyRef:
              name: db-creds
              key: DB_USER
        - name: DB_PASS
          valueFrom:
            secretKeyRef:
              name: db-creds
              key: DB_PASS
```

> ⚠️ **Kubernetes Secrets are NOT encrypted by default** — they're base64 encoded (not encryption!). Enable encryption at rest or use external secret stores (Vault, AWS Secrets Manager).

---

## 8. Storage

### PersistentVolume and PersistentVolumeClaim

```yaml
# PVC — request storage
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: db-storage
spec:
  accessModes:
    - ReadWriteOnce               # One node can mount
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard      # Cloud provider manages provisioning
---
# Use in a Pod
spec:
  containers:
    - name: postgres
      image: postgres:15
      volumeMounts:
        - name: db-data
          mountPath: /var/lib/postgresql/data
  volumes:
    - name: db-data
      persistentVolumeClaim:
        claimName: db-storage
```

---

## 9. Helm — Package Manager

### Why Helm?

```
WITHOUT HELM:
  10 YAML files per app × 3 environments = 30 files to maintain
  Copy-paste, find-and-replace "staging" → "production" 😱

WITH HELM:
  1 chart (template) + values files per environment
  helm install myapp ./chart -f prod-values.yml
```

### Helm Basics

```bash
# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Add a chart repository
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Search for charts
helm search repo nginx

# Install a chart
helm install my-nginx bitnami/nginx

# List installed releases
helm list

# Upgrade with new values
helm upgrade my-nginx bitnami/nginx --set replicaCount=3

# Rollback
helm rollback my-nginx 1

# Uninstall
helm uninstall my-nginx
```

### Chart Structure

```
my-app/
├── Chart.yaml          # Chart metadata (name, version)
├── values.yaml         # Default configuration values
├── templates/
│   ├── deployment.yaml # Deployment template with {{ .Values.* }}
│   ├── service.yaml    # Service template
│   ├── ingress.yaml    # Ingress template
│   └── _helpers.tpl    # Template helper functions
└── charts/             # Sub-chart dependencies
```

---

## 10. Common Mistakes and Anti-Patterns

### ❌ No Resource Limits

```yaml
# BAD: Pod can consume unlimited resources → starves other pods
containers:
  - name: app
    image: myapp:latest

# GOOD: Set requests AND limits
containers:
  - name: app
    image: myapp:v1.2.3
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "500m"
```

### ❌ Using `latest` Tag

```yaml
# BAD: What version is "latest"? Different on every pull
image: myapp:latest

# GOOD: Pin to a specific version
image: myapp:v1.2.3
# or SHA: myapp@sha256:abc123...
```

### ❌ No Health Checks

```yaml
# BAD: K8s can't tell if app is healthy → sends traffic to broken pods

# GOOD: Liveness + Readiness probes
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 10
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
```

### ❌ Secrets in ConfigMaps

```
BAD:  Database password in a ConfigMap (visible to anyone)
GOOD: Use Kubernetes Secrets + external secret management (Vault)
```

---

## 11. Debugging Mindset

### K8s Debugging Framework

```
Pod not running?
│
├─ 1. kubectl get pods (check STATUS)
│     ├─ Pending     → No node has resources → kubectl describe pod
│     ├─ ImagePull   → Wrong image name/tag → check image reference
│     ├─ CrashLoop   → App crashing → kubectl logs <pod>
│     ├─ Error       → Container failed → kubectl logs <pod> --previous
│     └─ Running     → But not working → check service/ingress
│
├─ 2. kubectl describe pod <name>
│     └─ Events section shows WHY (scheduling, pulling, crashes)
│
├─ 3. kubectl logs <pod>
│     └─ Application-level errors
│
├─ 4. kubectl exec -it <pod> -- /bin/sh
│     └─ Debug from inside the container
│
└─ 5. kubectl get events --sort-by='.lastTimestamp'
      └─ Cluster-wide events timeline
```

### Service Not Reachable?

```
Can't reach my service?
│
├─ 1. Does the Pod exist? → kubectl get pods -l app=myapp
├─ 2. Is the Pod running? → kubectl describe pod
├─ 3. Do labels match?    → Pod labels must match Service selector
├─ 4. Right ports?        → targetPort must match containerPort
├─ 5. DNS working?        → kubectl exec test -- nslookup myservice
└─ 6. Endpoints exist?    → kubectl get endpoints myservice
```

### `kubectl debug` — Debugging Minimal and Distroless Images

`kubectl exec` only works if the container has a shell. Modern production images (distroless, scratch, Alpine-based) often have **no shell, no curl, no tools at all**. `kubectl debug` (GA since Kubernetes 1.25) solves this by attaching an **ephemeral debug container** to a running pod.

```bash
# Problem: Your production pod uses a distroless image — no shell inside
kubectl exec -it my-pod -- /bin/sh
# Error: OCI runtime exec failed: exec failed: unable to start container process

# Solution: Attach a debug container with tools to the running pod
kubectl debug -it my-pod --image=busybox:latest --target=my-container
# --image     = the debug image (busybox, nicolaka/netshoot, ubuntu)
# --target    = the container to share process namespace with (see its processes)
# You're now inside a debug container with tools, alongside your running app

# Inside the debug container, you can:
#   ps aux              → see processes in the target container
#   cat /proc/1/environ → read environment variables of the app process
#   wget localhost:8080  → test the app internally
#   nslookup myservice   → test DNS resolution

# For network debugging, use nicolaka/netshoot (has curl, dig, tcpdump, etc.)
kubectl debug -it my-pod --image=nicolaka/netshoot --target=my-container

# Debug a node (creates a privileged pod on the node)
kubectl debug node/my-node -it --image=ubuntu
# Useful for: checking node disk, checking kubelet logs, host networking

# Create a copy of the pod with a different command (for crash loops)
kubectl debug my-pod -it --copy-to=my-pod-debug --container=my-container -- /bin/sh
# This creates a copy of the pod where you can override the entrypoint
```

> 💡 **In production, `kubectl debug` is often the ONLY way to troubleshoot** distroless images (common in Go/Java microservices). Learn to reach for it when `exec` fails.

---

## 12. Interview Insights

**Q: Explain Kubernetes architecture.**
> A K8s cluster has a control plane and worker nodes. The control plane runs the API server (entry point), etcd (state store), scheduler (pod placement), and controller manager (reconciliation loops). Worker nodes run kubelet (manages pods), kube-proxy (networking), and the container runtime. Users interact via kubectl which talks to the API server.

**Q: What's the difference between a Pod and a Deployment?**
> A Pod is the smallest deployable unit — one or more containers that share networking and storage. A Deployment manages Pods — it ensures the desired number of replicas are running, handles rolling updates, and enables rollbacks. You almost never create Pods directly; you create Deployments.

**Q: How does Kubernetes handle a node failure?**
> When a node stops responding, the controller manager detects it via the kubelet heartbeat. After a timeout (default 5 minutes), pods on that node are marked for rescheduling. The scheduler places them on healthy nodes. If using Deployments, the replica count is maintained automatically. This is self-healing.

**Q: Explain the difference between ClusterIP, NodePort, and LoadBalancer.**
> ClusterIP is internal-only — services talk to each other within the cluster. NodePort exposes a service on every node's IP at a static port (30000-32767) — accessible from outside. LoadBalancer integrates with a cloud provider to create an external load balancer that routes to the service. In production, you typically use LoadBalancer or Ingress.

**Q: How do you do zero-downtime deployments in Kubernetes?**
> Use Deployments with RollingUpdate strategy. Set maxUnavailable to 0 so no old pods are killed until new ones are ready. Add readiness probes so traffic only goes to pods that are actually ready. K8s creates new pods, waits for readiness, then terminates old pods — users see no interruption.

**Q: What is a Helm chart?**
> Helm is a package manager for Kubernetes. A chart is a collection of templated YAML manifests with configurable values. Instead of maintaining separate YAML files for each environment, you have one chart with different values files (dev.yaml, prod.yaml). Helm also handles versioning, upgrades, and rollbacks of deployments.

---

## Practical Checkpoint

Before moving on, you should be able to:

- Deploy workloads with Deployments, Services, ConfigMaps, Secrets, probes, and resource limits.
- Use `kubectl get`, `describe`, `logs`, `events`, and rollout commands to debug failures.
- Perform a rolling update and rollback while preserving service availability.

Portfolio evidence to keep:

- Kubernetes manifests.
- Rollout and rollback command output.
- Debug notes for one failed pod, bad image, or readiness problem.

Suggested project: [Kubernetes Rollout and Rollback](./projects/project-01-rollout-rollback.md)

---

## ➡️ What's Next?

With Kubernetes mastered, you've completed the core production skills. Next, you'll consolidate security practices across the entire stack.

**[Module 13: Security Basics →](../13-security-basics/)**

---

<div align="center">

**Module 12 Complete** ✅

[← Back to Ansible](../11-ansible/) | [Next: Security Basics →](../13-security-basics/)

</div>
