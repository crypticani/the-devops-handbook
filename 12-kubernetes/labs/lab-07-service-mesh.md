# Lab 07: Service Mesh with Linkerd

## 🎯 Objective

Get mTLS, per-hop golden metrics, and identity-based authorization across two services **without changing either application** — then measure what that actually cost you, and find the four ways a mesh gives you less than you think it does.

You'll use Linkerd because a small team can genuinely operate it. Everything here has an Istio equivalent; the failure modes are identical.

---

## 📋 Prerequisites

- Read [§10 Service Mesh — When You Actually Need One](../README.md#10-service-mesh--when-you-actually-need-one)
- Completed [Lab 05: RBAC and Pod Security](./lab-05-rbac-and-security.md) and [Lab 06: GitOps with Argo CD](./lab-06-gitops-argocd.md)
- A cluster with **4 GB of memory free** — the control plane plus sidecars is not free, which is part of the lesson

```bash
kubectl config current-context          # ⭐ minikube, not anything real
minikube start --memory=4096 --cpus=2   # if you need a bigger one
kubectl top nodes
```

> ⚠️ Do not install a mesh in a cluster you care about while learning. The control plane is a new failure domain for *all* service-to-service traffic.

---

## 📦 Deliverables and Evidence

- `linkerd check` passing, and the trust anchor's expiry date written down
- `linkerd viz edges` showing the web → api edge as secured
- Golden metrics per service from `linkerd viz stat`, with no application change
- Your measured **cost**: pod memory before and after injection, and the control plane's footprint
- An authorization policy that allows one identity and denies everything else, with both outcomes shown
- `failure-notes.md` covering all four scenarios

---

## 📂 Lab Files

Reference copies are in [`../code/lab-07/`](../code/lab-07/).

```bash
cp -r /path/to/the-devops-handbook/12-kubernetes/code/lab-07/. .
```

```text
apps.yml       web → api, with their own ServiceAccounts. Knows nothing about a mesh
policy.yml     Server + MeshTLSAuthentication + AuthorizationPolicy (identity-based authz)
unmeshed.yml   a workload OUTSIDE the mesh, to answer the question people forget to ask
```

---

## 🔬 Exercise 1: Before and After

### Step 1: Deploy Without the Mesh

```bash
kubectl apply -f apps.yml
kubectl -n meshlab rollout status deploy/api deploy/web
kubectl -n meshlab get pods
```

```text
NAME                   READY   STATUS    RESTARTS   AGE
api-6d8f9c7b4-2xk9m    1/1     Running   0          25s
api-6d8f9c7b4-vn4tq    1/1     Running   0          25s
web-7f9d8c5b6-p8lqz    1/1     Running   0          25s
```

`1/1` — one container per pod. Record the baseline you are about to change:

```bash
kubectl -n meshlab top pods
kubectl -n meshlab logs deploy/web --tail=3      # 200s, so traffic is flowing
```

Two facts about this state worth naming, because they are what the mesh is for: the traffic between web and api is **plaintext** on the network, and neither service reports anything about the other. You have no idea what web's success rate against api is unless one of them was instrumented to tell you.

### Step 2: Install Linkerd

```bash
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh
export PATH="$HOME/.linkerd2/bin:$PATH"
linkerd version --client

# ⭐ The best preflight of any mesh. Run it before installing anything.
linkerd check --pre

linkerd install --crds | kubectl apply -f -
linkerd install | kubectl apply -f -
linkerd check                      # takes a minute; every line is a real assertion
linkerd viz install | kubectl apply -f -
linkerd check
```

Two things to record now, while it is fresh:

```bash
# The control plane's footprint — this is a cost you carry forever
kubectl -n linkerd top pods
kubectl -n linkerd get deploy

# ⭐ The trust anchor's expiry. Write this date down somewhere a human will see it.
linkerd check --output short 2>&1 | grep -A2 'trust anchors'
```

> ⚠️ **The single most common Linkerd outage is a trust anchor that expired.** The default anchor is valid for one year; when it lapses, every mTLS handshake in the cluster fails at once, and the fix under pressure is a certificate rotation nobody has rehearsed. Put the expiry in a calendar and an alert the day you install.

### Step 3: Mesh the Namespace

```bash
kubectl annotate namespace meshlab linkerd.io/inject=enabled
kubectl -n meshlab get pods                 # ⭐ still 1/1 — nothing has changed yet
```

The annotation only affects pods **created after** it. Existing pods are untouched, which is scenario 1. Restart them:

```bash
kubectl -n meshlab rollout restart deploy/api deploy/web
kubectl -n meshlab rollout status deploy/api deploy/web
kubectl -n meshlab get pods
```

```text
NAME                   READY   STATUS    RESTARTS   AGE
api-8c7d6f5b9-4kx2n    2/2     Running   0          40s
api-8c7d6f5b9-9wm7p    2/2     Running   0          38s
web-5b6c8d9f7-r2vqx    2/2     Running   0          40s
```

`2/2`. The second container is the proxy, and no manifest mentioned it.

### Step 4: What You Just Got, For Free

```bash
# mTLS, verified — every edge should say SECURED ✓
linkerd viz edges deploy -n meshlab
```

```text
SRC   DST   SRC_NS    DST_NS    SECURED
web   api   meshlab   meshlab   √
```

```bash
# Golden metrics per service, with no instrumentation in either app
linkerd viz stat deploy -n meshlab
```

```text
NAME   MESHED   SUCCESS      RPS   LATENCY_P50   LATENCY_P95   LATENCY_P99
api       2/2   100.00%   1.0rps           1ms           2ms           2ms
web       1/1   100.00%   1.0rps           1ms           2ms           2ms
```

```bash
# Live requests, without touching the application
linkerd viz tap deploy/web -n meshlab | head -5
```

```text
req id=0:1 proxy=out src=10.244.0.28:47238 dst=10.244.0.31:80 tls=true :method=GET :path=/
```

`tls=true` on traffic between two services that have no TLS code in them. That is the argument for a mesh, and you just made it in four commands.

### Step 5: Now Measure the Bill

```bash
kubectl -n meshlab top pods
```

```text
NAME                   CPU(cores)   MEMORY(bytes)
api-8c7d6f5b9-4kx2n    4m           38Mi
web-5b6c8d9f7-r2vqx    3m           31Mi
```

Compare with your Step 1 baseline: roughly 20–30 MiB and a few millicores per pod, plus the control plane you measured in Step 2. On this three-pod lab that is noise. Do the arithmetic for 300 pods before you tell anyone a mesh is free:

```bash
kubectl get pods -A --no-headers | wc -l        # × ~25 MiB, if you mesh everything
```

> **💡 DevOps Impact**: this number is why ambient/sidecarless modes exist, and why "mesh only the namespaces that need it" is a legitimate architecture rather than a cop-out.

---

## 🔬 Exercise 2: Authorization by Identity

A NetworkPolicy can say *this pod may reach that port*. It cannot say *this workload's cryptographic identity may call this route*, because IPs are not identities. Watch the difference.

```bash
# Deploy a workload OUTSIDE the mesh, and confirm it can reach api today
kubectl apply -f unmeshed.yml
kubectl -n outside logs deploy/outsider --tail=3
```

```text
outsider -> api: 200
```

Anything in the cluster can call your API. Now add the policy:

```bash
kubectl apply -f policy.yml
kubectl -n meshlab describe server api-http | head -12
sleep 15
```

```bash
kubectl -n meshlab logs deploy/web --tail=3        # ⭐ web still works: it has the identity
kubectl -n outside logs deploy/outsider --tail=3   # the outsider does not
```

```text
200 200 200
outsider -> api: 000
```

Read `policy.yml` and note what made that work: the allowed identity is
`web.meshlab.serviceaccount.identity.linkerd.cluster.local` — derived from the **ServiceAccount**, proven by a certificate the proxy rotates hourly, and unforgeable by anything that lacks the key. An attacker who gets a shell in another pod inherits that pod's identity and nothing more.

Also note what `policy.yml` had to include: an explicit authorization for the **kubelet's probes**. Declaring a `Server` switches the port to default-deny, and the kubelet is not in the mesh and has no identity. That is scenario 2.

---

## 🧨 Break It: Four Ways the Mesh Gives You Less Than You Think

### Scenario 1: Annotated, Not Restarted

**Break it.** Add a new deployment to the meshed namespace using a manifest that predates injection, the way a Helm upgrade or a stale GitOps commit would:

```bash
kubectl -n meshlab create deployment legacy --image=curlimages/curl:8.8.0 \
  -- sh -c 'while true; do curl -s -o /dev/null http://api.meshlab.svc.cluster.local/; sleep 2; done'
kubectl -n meshlab get pods -l app=legacy
```

That one *is* injected — it was created after the annotation. Now the real version of the mistake:

```bash
kubectl annotate namespace outside linkerd.io/inject=enabled
kubectl -n outside get pods                      # ⭐ still 1/1. Nothing happened
kubectl -n outside logs deploy/outsider --tail=2
```

**Symptom.** The namespace says it is meshed. `kubectl get ns -o yaml` shows the annotation. And the pod has no proxy, no mTLS, and no policy enforcement — while every dashboard that counts *namespaces* reports 100% coverage.

**Investigate.**

```bash
# The only trustworthy source is the pods themselves
linkerd viz stat deploy -n outside               # MESHED shows 0/1
kubectl -n outside get pods -o json | \
  python3 -c "import json,sys; [print(p['metadata']['name'], len(p['spec']['containers']),'containers')
              for p in json.load(sys.stdin)['items']]"
```

**Root cause.** Injection happens through an admission webhook at **pod creation**. Annotating a namespace changes what happens to future pods and does nothing to existing ones.

**Fix.**

```bash
kubectl -n outside rollout restart deploy/outsider
kubectl -n outside get pods                      # 2/2
linkerd viz stat deploy -n outside               # MESHED 1/1
```

> ⭐ Report mesh coverage by **pod**, never by namespace, and alert on unmeshed pods in namespaces that are supposed to be meshed. "We annotated the namespaces" is a claim about intent; `MESHED 1/1` is a claim about reality.

### Scenario 2: Default Deny Catches Your Own Probes

**Break it.** Remove the probe authorization — exactly what you get if you write the `Server` and the workload policy and stop there:

```bash
kubectl -n meshlab delete authorizationpolicy api-allow-probes
kubectl -n meshlab delete httproute api-probes
kubectl -n meshlab get pods -w                   # watch for 60 seconds
```

**Symptom.**

```text
api-8c7d6f5b9-4kx2n   2/2   Running   0     5m
api-8c7d6f5b9-4kx2n   1/2   Running   1     6m     ← restarted
api-8c7d6f5b9-4kx2n   2/2   Running   1     6m
```

Healthy pods restarting on a loop. `web` is still getting 200s, so the *application* is fine — and the pods are being killed anyway.

**Investigate.**

```bash
kubectl -n meshlab describe pod -l app=api | grep -A5 'Liveness\|Events'
kubectl -n meshlab logs -l app=api -c linkerd-proxy --tail=20 | grep -i unauthorized
```

```text
Liveness probe failed: HTTP probe failed with statuscode: 403
... unauthorized request denied
```

**Root cause.** A `Server` makes its port default-deny for everything, and the kubelet that runs your probes is not a mesh workload — it has an IP, not an identity. So the mesh correctly denies it, the probe fails, and Kubernetes restarts a working pod.

**Fix.** Restore the probe authorization, which is why `policy.yml` ships one:

```bash
kubectl apply -f policy.yml
sleep 20
kubectl -n meshlab get pods -l app=api           # stable, no new restarts
```

> ⭐ Every mesh has this trap in some form. When you turn on default-deny, enumerate the *non-application* clients of every port first: probes, Prometheus scrapes, admission webhooks, the ingress controller, backup jobs. Each one needs an explicit allow, and each one is a 3 a.m. surprise if you forget it.

### Scenario 3: The Mesh Only Sees the Mesh

**Break it.** You now believe api is protected: policy allows only web's identity. Test that belief from a workload with **host networking**, which any privileged pod can request:

```bash
kubectl -n meshlab delete deployment legacy --ignore-not-found
API_POD_IP=$(kubectl -n meshlab get pod -l app=api -o jsonpath='{.items[0].status.podIP}')
kubectl -n outside rollout undo deploy/outsider 2>/dev/null || true
kubectl -n outside patch deploy outsider -p \
  '{"spec":{"template":{"metadata":{"annotations":{"linkerd.io/inject":"disabled"}}}}}'
kubectl -n outside rollout status deploy/outsider
kubectl -n outside exec deploy/outsider -- \
  curl -s -o /dev/null -w 'direct to pod IP: %{http_code}\n' -m 5 "http://$API_POD_IP:80/"
```

**Symptom.** Depending on how your policy is written and whether the proxy intercepts that path, you will see either `200` — policy bypassed entirely — or `000`. Either result is the lesson:

```bash
linkerd viz edges deploy -n meshlab      # ⭐ the outsider's traffic does not appear AT ALL
linkerd viz stat deploy -n meshlab       # api's RPS does not include it
```

Traffic that never entered the mesh is invisible to every mesh view. Your "100% mTLS" dashboard is a statement about meshed traffic, and it says nothing about unmeshed traffic — which is precisely where an attacker will be.

**Root cause.** A mesh is not a network boundary; it is a set of cooperating proxies. Enforcement depends on the *client* being meshed too. Anything that can talk to a pod IP directly, run in host network namespace, or opt out of injection is outside the model.

**Fix.** Defence in depth — the mesh is one layer, not the layer:

```bash
# NetworkPolicy still does the L3/L4 job the mesh cannot: it doesn't care about identity,
# and it doesn't care whether the client is meshed
cat <<'EOF' | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-from-meshlab-only
  namespace: meshlab
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: meshlab
EOF
sleep 5
kubectl -n outside exec deploy/outsider -- \
  curl -s -o /dev/null -w 'after netpol: %{http_code}\n' -m 5 "http://$API_POD_IP:80/" || true
```

Plus Pod Security admission to stop pods requesting host networking in the first place (Lab 05), and mesh coverage measured per pod so an unmeshed workload is visible.

### Scenario 4: The Control Plane Is a Deploy-Time SPOF

**Break it.** Take out the injector, which is what a bad upgrade, an evicted pod, or a full node does for you:

```bash
kubectl -n linkerd scale deploy/linkerd-proxy-injector --replicas=0
kubectl -n meshlab logs deploy/web --tail=3      # ⭐ existing traffic is FINE
kubectl -n meshlab rollout restart deploy/api
kubectl -n meshlab get pods -l app=api
```

**Symptom.** Two very different outcomes depending on the webhook's failure policy, and you need to know which one you have:

```text
# Either — pods cannot be created at all:
Error creating: Internal error occurred: failed calling webhook
  "linkerd-proxy-injector.linkerd.io": ... connection refused

# Or, with failurePolicy: Ignore — pods come up 1/1, UNMESHED, and nothing complains
```

Meanwhile the existing pods keep serving perfectly: proxies already have their config and certificates, so the data plane survives a control plane outage. It is *changes* that break.

**Investigate.**

```bash
kubectl get mutatingwebhookconfiguration linkerd-proxy-injector-webhook-config \
  -o jsonpath='{.webhooks[0].failurePolicy}{"\n"}'
kubectl -n meshlab describe rs -l app=api | grep -A3 Events
linkerd check                                     # tells you exactly what is unhealthy
```

**Root cause.** A mesh adds a component that sits in the path of every pod creation and every certificate issuance. That is a genuinely new failure domain, and it fails at deploy time rather than at request time — which is why teams discover it during an incident, when they are trying to deploy the fix.

**Fix.**

```bash
kubectl -n linkerd scale deploy/linkerd-proxy-injector --replicas=1
linkerd check
kubectl -n meshlab rollout restart deploy/api
kubectl -n meshlab get pods -l app=api            # 2/2 again
```

Operationally: run the control plane with multiple replicas and a PodDisruptionBudget, alert on `linkerd check` failing (it is scriptable and returns a non-zero exit), monitor certificate expiry, and rehearse the upgrade path. Treat it like the API server, because for your service traffic it now is one.

### Summary

| Failure | How you detect it | How you prevent it |
|---------|------------------|--------------------|
| Annotated, not restarted | `MESHED 0/1` in `linkerd viz stat`; pods still `1/1` | Measure coverage per pod, not per namespace; alert on unmeshed pods in meshed namespaces |
| Default deny kills probes | Healthy pods restarting; `403` in probe events, `unauthorized` in proxy logs | Enumerate every non-application client before enabling default-deny — probes, scrapes, webhooks, ingress |
| Unmeshed traffic invisible | Traffic that does not appear in `viz edges` or `stat` at all | Defence in depth: NetworkPolicy for L3/L4, Pod Security to block host network, coverage monitoring |
| Control plane outage | New pods fail to create, or come up unmeshed; existing traffic unaffected | HA control plane + PDB, alert on `linkerd check`, monitor cert expiry, rehearse upgrades |

⭐ **The theme of this lab**: a mesh delivers exactly what it promised — mTLS, metrics, and identity-based policy with no application changes, in about ten commands. What it also delivers is a second control plane, a proxy in every pod, a new class of "is it the app or the proxy?" debugging, and a false sense of coverage the moment one workload is not meshed. Under about ten services, an Ingress plus NetworkPolicies plus a retry library gets you most of the value for none of that. Above it, with a real mTLS requirement, this is the trade — and now you have made it with your hands rather than from a diagram.

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
kubectl delete -f policy.yml --ignore-not-found
kubectl delete networkpolicy api-from-meshlab-only -n meshlab --ignore-not-found
kubectl delete -f unmeshed.yml --ignore-not-found
kubectl delete -f apps.yml --ignore-not-found

linkerd viz uninstall | kubectl delete -f - --ignore-not-found
linkerd uninstall | kubectl delete -f - --ignore-not-found
kubectl get ns | grep -E 'linkerd|meshlab|outside'    # should be empty

# Or, since this was a throwaway cluster:
minikube delete
```

---

## ✅ Validation

- [ ] Explain what a mesh gives you that a NetworkPolicy cannot, and vice versa
- [ ] Install Linkerd and interpret `linkerd check`
- [ ] Prove mTLS between two services that contain no TLS code
- [ ] Read golden metrics per hop and say why they needed no instrumentation
- [ ] State the per-pod cost you measured, and extrapolate it to 300 pods
- [ ] Write an authorization policy scoped to one workload identity, and explain where the identity comes from
- [ ] Explain why declaring a `Server` breaks probes, and list the other non-application clients you must authorize
- [ ] Explain why unmeshed traffic is invisible to the mesh, and what still covers it
- [ ] Explain what survives a control plane outage and what does not
- [ ] Say when you would *not* use a mesh, and what you would do instead

---

## 📝 What to Commit

- `apps.yml`, `policy.yml`, `unmeshed.yml`
- `linkerd check` output, and the trust anchor expiry date
- `viz edges` showing SECURED, and `viz tap` showing `tls=true`
- Your before/after memory measurements and the 300-pod extrapolation
- The probe-failure events from scenario 2, and the webhook error from scenario 4
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: GitOps with Argo CD](./lab-06-gitops-argocd.md) | [Back to Module README](../README.md) | [Module 13: Security Basics →](../../13-security-basics/)
