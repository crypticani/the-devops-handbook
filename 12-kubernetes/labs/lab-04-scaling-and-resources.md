# Lab 04: Scaling and Resource Tuning

## 🎯 Objective

Get resource requests and limits right — and learn what each kind of "wrong" looks like from the outside. You'll trigger a real OOMKill, cause CPU throttling and measure it, drive a HorizontalPodAutoscaler with load, and see how a PodDisruptionBudget protects you during a node drain.

This is the module's highest-value lab for real operations: most Kubernetes production incidents that aren't networking are resource misconfiguration.

---

## 📋 Prerequisites

- Completed [Lab 03: Services, Ingress, and Network Policy](./lab-03-networking-and-ingress.md)
- A cluster with metrics-server:

```bash
kubectl config current-context
minikube addons enable metrics-server
kubectl -n kube-system rollout status deploy/metrics-server --timeout=180s
sleep 30                       # give it a scrape cycle
kubectl top nodes              # must return numbers, not an error
```

---

## 📦 Deliverables and Evidence

- Manifests for a workload with tuned requests and limits, an HPA, and a PDB
- Evidence of an OOMKill: exit code 137, `OOMKilled` reason, and the pod's restart count
- A measured CPU throttling ratio, before and after raising the limit
- `kubectl get hpa` output showing a scale-up and scale-down cycle
- A node drain that respected the PDB
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-04/`](../code/lab-04/).

```bash
cp -r /path/to/the-devops-handbook/12-kubernetes/code/lab-04/. .
```

---

## 🔬 Exercise 1: Requests vs Limits

### Step 1: Set Up

```bash
mkdir -p k8s-resources-lab && cd k8s-resources-lab
kubectl create namespace reslab
kubectl config set-context --current --namespace=reslab
```

### Step 2: Understand What Each Field Does

They control **two completely different things**, and conflating them causes most resource incidents.

| | `requests` | `limits` |
|---|-----------|----------|
| **Used by** | The **scheduler** | The **kernel** (cgroups) |
| **Means** | "Reserve this much for me" | "Never let me exceed this" |
| **Too low** | Scheduled onto a crowded node; starved under contention | Throttled (CPU) or **OOMKilled** (memory) |
| **Too high** | Wasted capacity; pod may not schedule at all | Node overcommit; the node itself can OOM |
| **Enforced how?** | Only at scheduling time | Continuously, by the kernel |

```bash
# What the scheduler currently sees
kubectl describe node minikube | grep -A 8 "Allocated resources"
kubectl get node minikube -o jsonpath='{.status.allocatable}' | python3 -m json.tool
```

### Step 3: Watch the Scheduler Use Requests

```bash
ALLOC_CPU=$(kubectl get node minikube -o jsonpath='{.status.allocatable.cpu}')
echo "allocatable CPU: $ALLOC_CPU"

cat > greedy.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: greedy}
spec:
  replicas: 5
  selector: {matchLabels: {app: greedy}}
  template:
    metadata: {labels: {app: greedy}}
    spec:
      containers:
        - name: app
          image: registry.k8s.io/pause:3.9     # does nothing, uses nothing
          resources:
            requests: {cpu: "1500m"}           # ⭐ RESERVES 1.5 cores each
YAML
kubectl apply -f greedy.yml
sleep 8
kubectl get pods -l app=greedy
```

**Symptom:** Some pods are `Pending`. They use **zero** CPU — `pause` does nothing at all — but the scheduler reserved 1.5 cores for each and ran out.

```bash
kubectl describe pod -l app=greedy | grep -A4 Events | grep -i insufficient | head -3
#   0/1 nodes are available: 1 Insufficient cpu.

kubectl describe node minikube | grep -A 8 "Allocated resources"
```

> ⭐ **Requests are a reservation, not a measurement.** A cluster can be "full" at 15% actual utilisation if requests are set too high. This is the single biggest source of cloud waste in Kubernetes — and `kubectl top` will show you an idle cluster while pods refuse to schedule.

```bash
kubectl delete -f greedy.yml
```

### Step 4: The Three QoS Classes

```bash
cat > qos.yml <<'YAML'
apiVersion: v1
kind: Pod
metadata: {name: qos-guaranteed}
spec:
  containers:
    - name: app
      image: registry.k8s.io/pause:3.9
      resources:                      # ⭐ limits == requests, for BOTH cpu and memory
        requests: {cpu: 100m, memory: 64Mi}
        limits:   {cpu: 100m, memory: 64Mi}
---
apiVersion: v1
kind: Pod
metadata: {name: qos-burstable}
spec:
  containers:
    - name: app
      image: registry.k8s.io/pause:3.9
      resources:
        requests: {cpu: 50m, memory: 32Mi}
        limits:   {memory: 128Mi}     # requests < limits
---
apiVersion: v1
kind: Pod
metadata: {name: qos-besteffort}
spec:
  containers:
    - name: app
      image: registry.k8s.io/pause:3.9   # ⭐ no resources block at all
YAML
kubectl apply -f qos.yml
sleep 5
kubectl get pods -o custom-columns='NAME:.metadata.name,QOS:.status.qosClass'
```

| QoS class | When | Eviction order under node pressure |
|-----------|------|-----------------------------------|
| **Guaranteed** | `limits == requests` for **every** resource in **every** container | Evicted **last** |
| **Burstable** | Requests set, limits higher or absent | Evicted second |
| **BestEffort** | No requests or limits at all | ⭐ Evicted **first** |

> 💡 When a node runs out of memory, the kubelet evicts pods in QoS order, and within a class it evicts whichever most exceeds its request. **A pod with no resources block is first in the queue to die.** That alone is reason enough to set requests on everything.

```bash
kubectl delete -f qos.yml
```

---

## 🔬 Exercise 2: Trigger a Real OOMKill

### Step 1: Deploy Something That Will Exceed Its Limit

```bash
cat > memory-hog.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: memory-hog}
spec:
  replicas: 1
  selector: {matchLabels: {app: memory-hog}}
  template:
    metadata: {labels: {app: memory-hog}}
    spec:
      containers:
        - name: hog
          image: python:3.12-alpine
          command: ["python3","-u","-c"]
          args:
            - |
              import time
              chunks = []
              mb = 0
              while True:
                  chunks.append(bytearray(10 * 1024 * 1024))   # 10 MiB
                  mb += 10
                  print(f"allocated {mb} MiB", flush=True)
                  time.sleep(0.4)
          resources:
            requests: {cpu: 50m, memory: 32Mi}
            limits:   {memory: 128Mi}      # ⭐ the ceiling it will hit
YAML
kubectl apply -f memory-hog.yml
kubectl rollout status deploy/memory-hog
```

### Step 2: Watch It Die

```bash
POD=$(kubectl get pod -l app=memory-hog -o jsonpath='{.items[0].metadata.name}')
kubectl logs -f "$POD" &
LOGPID=$!
sleep 25
kill $LOGPID 2>/dev/null

kubectl get pod "$POD"
```

The log stops abruptly somewhere past 120 MiB. There is **no error message and no stack trace** — the kernel killed the process instantly.

### Step 3: Prove It Was an OOMKill

```bash
# ⭐ The definitive check
kubectl get pod "$POD" -o jsonpath='{.status.containerStatuses[0].lastState.terminated}' | python3 -m json.tool
#   "exitCode": 137,
#   "reason": "OOMKilled"

kubectl get pod "$POD" -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}'; echo
kubectl get pod "$POD" -o jsonpath='{.status.containerStatuses[0].restartCount}'; echo
kubectl describe pod "$POD" | grep -iE 'oom|last state|exit code|reason' | head
```

| Signal | Meaning |
|--------|---------|
| Exit code **137** | `128 + 9` — killed by SIGKILL |
| `reason: OOMKilled` | The kernel's cgroup OOM killer, specifically |
| Restart count climbing | It will keep dying; expect `CrashLoopBackOff` shortly |
| **No application logs** | SIGKILL is uncatchable — the app cannot log its own death |

> ⭐ **This is why OOM is hard to debug.** The application produces no error, so people search the app logs, find nothing, and conclude "it just disappeared". The evidence lives only in the pod's `lastState`, and only until the pod object is deleted. **`exit code 137` means "check the memory limit" — commit that to memory.**

### Step 4: Fix It Two Ways

```bash
# (a) Raise the limit — correct if the app legitimately needs the memory
kubectl set resources deploy/memory-hog -c=hog --limits=memory=512Mi
kubectl rollout status deploy/memory-hog
sleep 30
kubectl get pods -l app=memory-hog          # survives longer, but this app leaks forever

# (b) The real fix for a leak is in the application. Meanwhile, cap the blast radius:
kubectl set resources deploy/memory-hog -c=hog --limits=memory=128Mi --requests=memory=128Mi
kubectl get pods -l app=memory-hog -o custom-columns='NAME:.metadata.name,QOS:.status.qosClass'
#   Guaranteed — it dies, but it never destabilises the node or its neighbours
```

> 💡 An OOMKill is not always a bug in your app. Setting a limit **below** what the app needs at peak causes exactly the same symptom. Before raising the limit, look at `kubectl top pod` over a real workload and check whether the memory curve plateaus (correct sizing needed) or climbs forever (a leak).

```bash
kubectl delete -f memory-hog.yml
```

---

## 🔬 Exercise 3: CPU Throttling — The Silent Latency Killer

Memory limits kill you loudly. CPU limits slow you down silently.

### Step 1: Deploy a CPU-Bound Workload With a Tight Limit

```bash
cat > cpu-throttle.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: cpu-throttle}
spec:
  replicas: 1
  selector: {matchLabels: {app: cpu-throttle}}
  template:
    metadata: {labels: {app: cpu-throttle}}
    spec:
      containers:
        - name: burner
          image: python:3.12-alpine
          command: ["python3","-u","-c"]
          args:
            - |
              import time
              while True:
                  t0 = time.time()
                  x = 0
                  for _ in range(3_000_000):
                      x += 1
                  print(f"work unit took {time.time()-t0:.3f}s", flush=True)
          resources:
            requests: {cpu: 50m,  memory: 32Mi}
            limits:   {cpu: 100m, memory: 64Mi}    # ⭐ 10% of one core
YAML
kubectl apply -f cpu-throttle.yml
kubectl rollout status deploy/cpu-throttle
sleep 20

POD=$(kubectl get pod -l app=cpu-throttle -o jsonpath='{.items[0].metadata.name}')
kubectl logs "$POD" --tail=5
```

**Symptom:** Each work unit takes several seconds. The pod is healthy — `1/1 Running`, zero restarts, no events, no errors anywhere. It is simply **slow**, and nothing in Kubernetes says why.

### Step 2: Measure the Throttling

```bash
kubectl top pod "$POD"
#   CPU hovers at ~100m — pinned exactly at the limit. That's the tell.

# ⭐ The cgroup counters — the direct evidence
kubectl exec "$POD" -- sh -c '
  echo "--- cgroup v2 ---"
  cat /sys/fs/cgroup/cpu.stat 2>/dev/null
  echo "--- cgroup v1 ---"
  cat /sys/fs/cgroup/cpu/cpu.stat 2>/dev/null'
```

Look at these three numbers:

| Field | Meaning |
|-------|---------|
| `nr_periods` | How many 100 ms scheduling windows have elapsed |
| `nr_throttled` | How many of those the container was **stopped** in |
| `throttled_usec` / `throttled_time` | Total time spent frozen, waiting for its next quota |

```bash
kubectl exec "$POD" -- sh -c '
  P=$(awk "/nr_periods/{print \$2}" /sys/fs/cgroup/cpu.stat 2>/dev/null)
  T=$(awk "/nr_throttled/{print \$2}" /sys/fs/cgroup/cpu.stat 2>/dev/null)
  [ -n "$P" ] && [ "$P" -gt 0 ] && echo "throttled ratio: $(( T * 100 / P ))%"'
```

The Prometheus equivalent (Module 07):

```promql
rate(container_cpu_cfs_throttled_periods_total[5m])
  / rate(container_cpu_cfs_periods_total[5m])
```

**Anything sustained above ~5% means the limit is too low.**

### Step 3: Raise the Limit and Re-measure

```bash
kubectl set resources deploy/cpu-throttle -c=burner --limits=cpu=1000m
kubectl rollout status deploy/cpu-throttle
sleep 25
POD=$(kubectl get pod -l app=cpu-throttle -o jsonpath='{.items[0].metadata.name}')
kubectl logs "$POD" --tail=5      # ⭐ work units now complete far faster
kubectl exec "$POD" -- cat /sys/fs/cgroup/cpu.stat 2>/dev/null | head -3
```

> ⭐ **Why many teams set CPU *requests* but no CPU *limit*.** CPU is compressible — under contention the scheduler shares it proportionally to requests, so a pod without a limit degrades gracefully instead of being frozen. A CPU limit converts "slower when the node is busy" into "artificially slow **all the time**, even on an idle node". Memory is different: it is not compressible, so a memory limit is essential to stop one pod taking down the node.
>
> The common production stance: **always set memory requests and limits; set CPU requests, and set CPU limits only where you need hard multi-tenant isolation.**

```bash
kubectl delete -f cpu-throttle.yml
```

---

## 🔬 Exercise 4: Horizontal Pod Autoscaler

### Step 1: Deploy a Scalable Workload

```bash
cat > hpa-demo.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: hpa-demo}
spec:
  replicas: 1
  selector: {matchLabels: {app: hpa-demo}}
  template:
    metadata: {labels: {app: hpa-demo}}
    spec:
      containers:
        - name: app
          image: registry.k8s.io/hpa-example      # burns CPU on every request
          ports: [{containerPort: 80}]
          resources:
            requests: {cpu: 100m, memory: 64Mi}   # ⭐ HPA percentages are relative to REQUESTS
            limits:   {cpu: 500m, memory: 128Mi}
---
apiVersion: v1
kind: Service
metadata: {name: hpa-demo}
spec:
  selector: {app: hpa-demo}
  ports: [{port: 80}]
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: {name: hpa-demo}
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: hpa-demo}
  minReplicas: 1
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: {type: Utilization, averageUtilization: 50}   # 50% of the 100m REQUEST
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0      # react immediately
      policies: [{type: Percent, value: 100, periodSeconds: 15}]
    scaleDown:
      stabilizationWindowSeconds: 120    # ⭐ wait 2 min before shrinking — avoids flapping
      policies: [{type: Percent, value: 50, periodSeconds: 60}]
YAML
kubectl apply -f hpa-demo.yml
kubectl rollout status deploy/hpa-demo
sleep 45
kubectl get hpa hpa-demo
```

> ⚠️ If `TARGETS` shows `<unknown>`, metrics-server isn't reporting yet. Wait another 30s, then check `kubectl top pod`. If `top` fails, the HPA can never work — fix metrics-server first.

### Step 2: Generate Load

In a second terminal:

```bash
kubectl run load-generator --rm -it --restart=Never --image=busybox:1.36 -- \
  /bin/sh -c "while true; do wget -q -O- http://hpa-demo.reslab.svc.cluster.local; done"
```

In the first terminal, watch:

```bash
kubectl get hpa hpa-demo -w
```

```
NAME       REFERENCE             TARGETS         MINPODS  MAXPODS  REPLICAS
hpa-demo   Deployment/hpa-demo   cpu: 0%/50%     1        10       1
hpa-demo   Deployment/hpa-demo   cpu: 247%/50%   1        10       1
hpa-demo   Deployment/hpa-demo   cpu: 247%/50%   1        10       4      ⭐ scaling up
hpa-demo   Deployment/hpa-demo   cpu: 118%/50%   1        10       8
hpa-demo   Deployment/hpa-demo   cpu:  52%/50%   1        10       8      ⭐ stabilised
```

**The maths:** desired replicas = `ceil(current_replicas × currentMetric / targetMetric)`. At 247% against a 50% target with 1 replica: `ceil(1 × 247/50) = 5`, capped by the scale-up policy.

```bash
kubectl describe hpa hpa-demo | tail -15    # the Events show every scaling decision and why
```

### Step 3: Watch It Scale Back Down

Stop the load generator (Ctrl-C), then:

```bash
kubectl get hpa hpa-demo -w
```

Scale-down is deliberately slow — the `stabilizationWindowSeconds: 120` means the HPA waits two minutes of low utilisation before shrinking, and then only by 50% per minute. Without that window an autoscaler oscillates: scale up, load drops, scale down, load returns, scale up.

```bash
kubectl delete -f hpa-demo.yml
```

**HPA gotchas:**

| Problem | Cause | Fix |
|---------|-------|-----|
| `TARGETS: <unknown>` | No metrics-server, or the pod has **no CPU request** | Install metrics-server; set requests — the percentage is meaningless without one |
| Never scales up | Target too high, or the metric isn't the bottleneck | Check `describe hpa` events; consider a custom metric |
| Flaps constantly | No stabilization window | Set `behavior.scaleDown.stabilizationWindowSeconds` |
| Scales but pods stay Pending | Cluster has no room | You also need a **Cluster Autoscaler**; HPA only creates pods |
| Fights with `kubectl scale` | Both control `replicas` | Remove `replicas` from the Deployment manifest once an HPA owns it |

---

## 🔬 Exercise 5: PodDisruptionBudget

### Step 1: Deploy Without Protection, Then Drain

```bash
cat > pdb-demo.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: pdb-demo}
spec:
  replicas: 3
  selector: {matchLabels: {app: pdb-demo}}
  template:
    metadata: {labels: {app: pdb-demo}}
    spec:
      containers:
        - name: app
          image: nginx:1.27-alpine
          resources:
            requests: {cpu: 25m, memory: 32Mi}
            limits:   {memory: 64Mi}
YAML
kubectl apply -f pdb-demo.yml
kubectl rollout status deploy/pdb-demo

# A single-node cluster can't demonstrate a real drain, but the API behaviour is identical.
kubectl get pods -l app=pdb-demo
```

### Step 2: Add a PDB and Test the Eviction API

```bash
cat > pdb.yml <<'YAML'
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: {name: pdb-demo}
spec:
  minAvailable: 2                    # ⭐ never fewer than 2 running
  selector: {matchLabels: {app: pdb-demo}}
YAML
kubectl apply -f pdb.yml
kubectl get pdb
#   NAME       MIN AVAILABLE   ALLOWED DISRUPTIONS
#   pdb-demo   2               1                    ⭐ exactly one may be evicted at a time
```

```bash
# Evict one pod — allowed
POD1=$(kubectl get pod -l app=pdb-demo -o jsonpath='{.items[0].metadata.name}')
kubectl get --raw "/api/v1/namespaces/reslab/pods/$POD1" >/dev/null && \
kubectl delete pod "$POD1" --wait=false

# Immediately scale to 2 and check the budget again
kubectl scale deploy/pdb-demo --replicas=2
sleep 10
kubectl get pdb
#   ALLOWED DISRUPTIONS: 0   ⭐ a drain would now BLOCK rather than take the service down
```

**✅ Checkpoint:** With `minAvailable: 2` and only 2 pods running, `ALLOWED DISRUPTIONS` is 0. A `kubectl drain` on that node would wait rather than proceed — which is exactly the protection you want during a rolling node upgrade.

```bash
kubectl scale deploy/pdb-demo --replicas=3
```

**PDB rules:**

| | |
|---|---|
| Protects against | **Voluntary** disruptions: `kubectl drain`, node upgrades, cluster autoscaler scale-down |
| Does **not** protect against | Node crashes, OOMKills, `kubectl delete pod` — those are involuntary |
| `minAvailable: 1` with `replicas: 1` | ⚠️ Blocks drains **forever**. Use `maxUnavailable: 1`, or run 2+ replicas |
| Use percentages for autoscaled apps | `minAvailable: 50%` scales with the deployment |

```bash
kubectl delete -f pdb.yml -f pdb-demo.yml
```

---

## 🧨 Break It: Four Resource Failures

### Scenario 1: The Pod That Can Never Be Scheduled

**Break it:**

```bash
cat > unschedulable.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: unschedulable}
spec:
  replicas: 1
  selector: {matchLabels: {app: unschedulable}}
  template:
    metadata: {labels: {app: unschedulable}}
    spec:
      containers:
        - name: app
          image: nginx:1.27-alpine
          resources:
            requests: {cpu: "64", memory: "256Gi"}     # ❌ larger than any node
YAML
kubectl apply -f unschedulable.yml
sleep 8
kubectl get pods -l app=unschedulable
```

**Symptom:** `Pending`, forever. No restarts, no logs, no crash — just nothing happening. `kubectl logs` returns `container "app" in pod ... is waiting to start`.

**Investigate:**

```bash
kubectl describe pod -l app=unschedulable | grep -A6 Events
#   0/1 nodes are available: 1 Insufficient cpu, 1 Insufficient memory.

kubectl get node minikube -o jsonpath='{.status.allocatable}' | python3 -m json.tool
kubectl describe node minikube | grep -A 8 "Allocated resources"
```

**Root cause:** The scheduler found no node that can satisfy the request. Note the message names *which* resource is short — read it carefully, because the same `Pending` status also covers taints, node selectors, affinity rules, and unbound PVCs.

**The `Pending` decision tree:**

| Event message contains | Cause | Fix |
|------------------------|-------|-----|
| `Insufficient cpu/memory` | Requests exceed available capacity | Lower requests, or add nodes |
| `had taint {...} that the pod didn't tolerate` | Node taints | Add a toleration |
| `didn't match Pod's node affinity/selector` | `nodeSelector`/affinity | Fix the labels or the rule |
| `pod has unbound immediate PersistentVolumeClaims` | Storage not provisioned | Check StorageClass and AZ |
| `didn't match pod topology spread constraints` | Spread rules can't be met | Relax to `ScheduleAnyway` |

```bash
kubectl set resources deploy/unschedulable -c=app --requests=cpu=50m,memory=64Mi
kubectl rollout status deploy/unschedulable
kubectl delete -f unschedulable.yml
```

---

### Scenario 2: The Node Everyone Blames Instead of the Limit

**Break it:**

```bash
cat > mystery-slow.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: mystery-slow}
spec:
  replicas: 2
  selector: {matchLabels: {app: mystery-slow}}
  template:
    metadata: {labels: {app: mystery-slow}}
    spec:
      containers:
        - name: app
          image: python:3.12-alpine
          command: ["python3","-u","-c"]
          args:
            - |
              import http.server, socketserver, time
              class H(http.server.BaseHTTPRequestHandler):
                  def do_GET(self):
                      t0=time.time(); x=0
                      for _ in range(2_000_000): x+=1
                      self.send_response(200); self.end_headers()
                      self.wfile.write(f"{time.time()-t0:.3f}s\n".encode())
                  def log_message(self,*a): pass
              socketserver.TCPServer(("",8000),H).serve_forever()
          ports: [{containerPort: 8000}]
          resources:
            requests: {cpu: 50m, memory: 64Mi}
            limits:   {cpu: 80m, memory: 128Mi}     # ❌ far too tight
---
apiVersion: v1
kind: Service
metadata: {name: mystery-slow}
spec:
  selector: {app: mystery-slow}
  ports: [{port: 8000}]
YAML
kubectl apply -f mystery-slow.yml
kubectl rollout status deploy/mystery-slow
sleep 10

kubectl run t --rm -it --restart=Never --image=nicolaka/netshoot -- \
  sh -c 'for i in 1 2 3; do curl -s -w " total=%{time_total}s\n" http://mystery-slow:8000/; done'
```

**Symptom:** Requests take seconds. Pods are `1/1 Running`, zero restarts, no events, nothing in the logs. The usual reaction is to blame the node, the network, or the application — and none of those is the cause.

**Investigate — the ordered checklist for "healthy but slow":**

```bash
POD=$(kubectl get pod -l app=mystery-slow -o jsonpath='{.items[0].metadata.name}')

echo "── 1. is it pinned at its CPU limit? ──"
kubectl top pod "$POD"
kubectl get pod "$POD" -o jsonpath='{.spec.containers[0].resources}' | python3 -m json.tool

echo "── 2. throttling counters ──"
kubectl exec "$POD" -- cat /sys/fs/cgroup/cpu.stat 2>/dev/null | head -3

echo "── 3. is the NODE actually busy? ──"
kubectl top node

echo "── 4. any events at all? ──"
kubectl describe pod "$POD" | grep -A5 Events
```

`kubectl top node` shows the node is nearly idle while the pod is at exactly its limit. **That combination — busy pod, idle node — is the signature of CPU throttling.**

**Fix:**

```bash
kubectl set resources deploy/mystery-slow -c=app --limits=cpu=1000m --requests=cpu=200m
kubectl rollout status deploy/mystery-slow
sleep 10
kubectl run t --rm -it --restart=Never --image=nicolaka/netshoot -- \
  sh -c 'for i in 1 2 3; do curl -s -w " total=%{time_total}s\n" http://mystery-slow:8000/; done'

kubectl delete -f mystery-slow.yml
```

> ⭐ **Alert on throttling, not just on CPU usage.** A pod at 100% of a 100m limit shows as "0.1 cores" on a dashboard and looks perfectly fine. The throttling ratio is the only metric that reveals it.

---

### Scenario 3: The HPA That Does Nothing

**Break it:**

```bash
cat > hpa-broken.yml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: hpa-broken}
spec:
  replicas: 1
  selector: {matchLabels: {app: hpa-broken}}
  template:
    metadata: {labels: {app: hpa-broken}}
    spec:
      containers:
        - name: app
          image: registry.k8s.io/hpa-example
          ports: [{containerPort: 80}]
          # ❌ NO resources block at all
---
apiVersion: v1
kind: Service
metadata: {name: hpa-broken}
spec:
  selector: {app: hpa-broken}
  ports: [{port: 80}]
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: {name: hpa-broken}
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: hpa-broken}
  minReplicas: 1
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: {type: Utilization, averageUtilization: 50}
YAML
kubectl apply -f hpa-broken.yml
kubectl rollout status deploy/hpa-broken
sleep 60
kubectl get hpa hpa-broken
```

**Symptom:** `TARGETS: <unknown>/50%`. Load it as hard as you like — it will never scale.

**Investigate:**

```bash
kubectl describe hpa hpa-broken | tail -20
#   FailedGetResourceMetric: missing request for cpu

kubectl get deploy hpa-broken -o jsonpath='{.spec.template.spec.containers[0].resources}'; echo   # {}
kubectl top pod -l app=hpa-broken       # metrics-server DOES have data
```

**Root cause:** `averageUtilization: 50` means "50% **of the CPU request**". With no request, there is no denominator, so the HPA cannot compute a percentage and refuses to act. metrics-server is working fine — the maths is undefined.

**Fix:**

```bash
kubectl set resources deploy/hpa-broken -c=app --requests=cpu=100m,memory=64Mi
kubectl rollout status deploy/hpa-broken
sleep 60
kubectl get hpa hpa-broken       # ⭐ TARGETS now shows a real percentage
```

The alternative, if you genuinely don't want to set a request:

```yaml
metrics:
  - type: Resource
    resource:
      name: cpu
      target: {type: AverageValue, averageValue: 200m}   # absolute, needs no request
```

```bash
kubectl delete -f hpa-broken.yml
```

---

### Scenario 4: The PDB That Blocks Every Drain Forever

**Break it:**

```bash
kubectl create deployment singleton --image=nginx:1.27-alpine --replicas=1
kubectl rollout status deploy/singleton

cat > bad-pdb.yml <<'YAML'
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: {name: singleton}
spec:
  minAvailable: 1                    # ❌ with replicas: 1, this can NEVER be satisfied
  selector: {matchLabels: {app: singleton}}
YAML
kubectl apply -f bad-pdb.yml
sleep 5
kubectl get pdb singleton
```

**Symptom:**

```
NAME        MIN AVAILABLE   ALLOWED DISRUPTIONS
singleton   1               0
```

`ALLOWED DISRUPTIONS: 0`, permanently. Any node drain — a security patch, a Kubernetes upgrade, a cluster autoscaler scale-down — will hang on this pod indefinitely. The cluster-upgrade job that silently stalls at 3am is usually this.

**Investigate:**

```bash
kubectl describe pdb singleton
kubectl get deploy singleton -o jsonpath='{.spec.replicas}'; echo
# minAvailable(1) == replicas(1)  → evicting the only pod would breach the budget

# Prove the eviction API refuses:
POD=$(kubectl get pod -l app=singleton -o jsonpath='{.items[0].metadata.name}')
kubectl drain minikube --ignore-daemonsets --delete-emptydir-data --dry-run=server 2>&1 | grep -i singleton | head -3
```

**Root cause:** `minAvailable` is an absolute floor. When it equals the replica count there is no slack, so no voluntary disruption is ever permitted.

**Fix — two options:**

```bash
# (a) Run more replicas (the right answer for anything that matters)
kubectl scale deploy/singleton --replicas=3
sleep 8
kubectl get pdb singleton              # ALLOWED DISRUPTIONS: 2

# (b) Or express the budget as maxUnavailable, which tolerates a single replica
kubectl delete pdb singleton
kubectl apply -f - <<'YAML'
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: {name: singleton}
spec:
  maxUnavailable: 1                    # ⭐ always allows exactly one eviction
  selector: {matchLabels: {app: singleton}}
YAML
kubectl get pdb singleton
```

```bash
kubectl delete pdb singleton; kubectl delete deploy singleton
```

---

### Summary

| Failure | Visible symptom | The command that proves it |
|---------|----------------|----------------------------|
| Requests too high | `Pending` on an idle cluster | `describe pod` → `Insufficient cpu` |
| Memory limit too low | Exit **137**, `CrashLoopBackOff`, **no app logs** | `.lastState.terminated.reason == OOMKilled` |
| CPU limit too low | Healthy but **slow**, no events at all | `cpu.stat` throttling ratio; pod at limit while node is idle |
| No resource requests | HPA `<unknown>`; **first to be evicted** | `describe hpa`; `.status.qosClass == BestEffort` |
| PDB too strict | Node drains hang forever | `kubectl get pdb` → `ALLOWED DISRUPTIONS: 0` |

> ⭐ **Two of these five are completely silent.** CPU throttling and BestEffort eviction risk produce no events, no errors, and no restarts — you only find them by looking at cgroup counters and QoS class. That's why resource tuning is monitored (Module 07), not just configured.

**A sane default for anything you deploy:**

```yaml
resources:
  requests:
    cpu: 100m          # measured from real load, not guessed
    memory: 128Mi      # measured at steady state, with headroom
  limits:
    memory: 256Mi      # ~2× the request — bounds the blast radius
    # cpu limit deliberately omitted — see Exercise 3
```

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
kubectl delete namespace reslab
kubectl config set-context --current --namespace=default
cd .. && rm -rf k8s-resources-lab
```

---

## ✅ Validation

- [ ] Explain what `requests` control versus what `limits` control, and who enforces each
- [ ] Show that a cluster can be "full" while nearly idle
- [ ] Identify a pod's QoS class and state its eviction priority
- [ ] Trigger an OOMKill and prove it from `lastState`, not from guesswork
- [ ] Measure a CPU throttling ratio from cgroup counters
- [ ] Explain why many teams set CPU requests but not CPU limits
- [ ] Drive an HPA through a full scale-up and scale-down cycle
- [ ] Explain why an HPA reports `<unknown>` without resource requests
- [ ] Write a PDB that protects availability without blocking drains forever

---

## 📝 What to Commit

- `memory-hog.yml`, `cpu-throttle.yml`, `hpa-demo.yml`, `pdb.yml`
- The `lastState.terminated` JSON showing `OOMKilled` and exit code 137
- Throttling ratio before and after raising the CPU limit
- `kubectl get hpa` output across a full scale cycle
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: Services, Ingress, and Network Policy](./lab-03-networking-and-ingress.md) | [Back to Module README](../README.md) | [Next Lab: RBAC and Pod Security →](./lab-05-rbac-and-security.md)
