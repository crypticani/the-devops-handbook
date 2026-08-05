# Module 12: Kubernetes — Lab Code

Kubernetes manifests for every lab in this module — pods and Services through resource tuning,
RBAC, and GitOps.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

---

## Contents

### `lab-01/`

Deployment with probes and resource limits, a Service, and a pod wired to a ConfigMap and Secret.

```
lab-01/
├── configured-pod.yml
├── deployment.yml
└── service.yml
```

### `lab-02/`

Configuration separated from code, and workloads that report their own health: a ConfigMap in both
file and env forms, a Deployment consuming them, and a probe demonstration.

```
lab-02/
├── app.env
├── app.properties
├── config.yml
├── deployment.yml
└── probes-demo.yml
```

### `lab-03/`

How a packet reaches a pod: two backends behind Services, a headless Service, an ExternalName
Service, an Ingress, and a NetworkPolicy.

```
lab-03/
├── backends.yml
├── external.yml
├── headless.yml
├── ingress.yml
└── netpol.yml
```

### `lab-04/`

Requests, limits, and the shapes of "wrong": a CPU-throttled pod, a memory hog that gets
OOMKilled, a greedy pod, the three QoS classes, an HPA target, and a PodDisruptionBudget.

```
lab-04/
├── cpu-throttle.yml
├── greedy.yml
├── hpa-demo.yml
├── memory-hog.yml
├── pdb-demo.yml
├── pdb.yml
└── qos.yml
```

### `lab-05/`

Least-privilege RBAC and Pod Security Standards: Roles and bindings, a narrowed Role, a pod
with its ServiceAccount token disabled, and a Deployment that passes `restricted` enforcement.

```
lab-05/
├── hardened.yml
├── narrow.yml
├── no-token.yml
├── rbac.yml
├── reader-pod.yml
└── scoped.yml
```

### `lab-06/`

GitOps with Argo CD. `manifests/` is what lives in **your** GitOps repository — Argo CD applies
it, you never do. The `Application` objects go to the cluster instead.

```
lab-06/
├── application-public.yml          # Argo CD's public example repo — works with no setup
├── application.yml.example         # your repo, manual sync
├── application-auto.yml.example    # your repo, automated: prune + selfHeal
└── manifests/
    ├── deployment.yml
    └── service.yml
```

The two `.example` files need your GitHub username substituted — copy each to the real filename
and edit it.

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/12-kubernetes && cd ~/devops-labs/12-kubernetes
cp -r /path/to/the-devops-handbook/12-kubernetes/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 12 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
