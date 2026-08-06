# Module 12: Kubernetes — Cheat Sheet

> kubectl by verb, jsonpath recipes, debugging one-liners, and Helm. Concepts live in the [module README](./README.md).
> Cross-module daily commands: **[QUICK-REFERENCE.md](../QUICK-REFERENCE.md)**

**Jump to:** [Setup](#setup--context) · [Get](#get--list) · [Describe & events](#describe--events) · [Logs](#logs) · [Exec & debug](#exec--debug) · [Apply & edit](#apply-edit-delete) · [Rollouts](#rollouts--scaling) · [Resources](#resources--autoscaling) · [Config & secrets](#configmaps--secrets) · [Networking](#networking) · [Storage](#storage) · [RBAC](#rbac) · [jsonpath](#jsonpath--custom-columns) · [Debugging](#debugging-recipes) · [Helm](#helm) · [Manifests](#manifest-templates) · [Errors](#error-decoder)

---

## Setup & Context

```bash
kubectl version --client
kubectl cluster-info
kubectl config get-contexts                      # ⭐ which clusters do I have?
kubectl config current-context                   # ⭐ WHICH CLUSTER AM I ON RIGHT NOW
kubectl config use-context prod
kubectl config set-context --current --namespace=production    # ⭐ stop typing -n
kubectl config view --minify                     # current context only
kubectl api-resources                            # every resource type + short name
kubectl api-resources --namespaced=false         # cluster-scoped resources
kubectl api-versions
kubectl explain deployment.spec.template.spec.containers    # ⭐ built-in field docs
kubectl explain pod.spec --recursive | less
```

```bash
# Shell setup — do this once, save hours
alias k=kubectl
source <(kubectl completion bash)     # or zsh
complete -o default -F __start_kubectl k
export KUBE_EDITOR=vim

# kubectx / kubens — switch context and namespace instantly
kubectx prod
kubens production
```

> ⚠️ **Put the current context in your shell prompt.** `kubectl delete` in the wrong cluster is the Kubernetes equivalent of `rm -rf /`. Tools: `kube-ps1`, `starship`, or a plain `PS1` with `kubectl config current-context`.

---

## Get / List

```bash
kubectl get pods
kubectl get pods -A                              # ⭐ all namespaces
kubectl get pods -n kube-system
kubectl get pods -o wide                         # ⭐ + node, pod IP, nominated node
kubectl get pods -w                              # watch for changes
kubectl get pods --show-labels
kubectl get pods -l app=api,tier=backend         # label selector (AND)
kubectl get pods -l 'env in (staging,prod)'
kubectl get pods -l '!canary'                    # label absent
kubectl get pods --field-selector status.phase=Running
kubectl get pods --field-selector spec.nodeName=node-1
kubectl get pods --sort-by=.status.containerStatuses[0].restartCount   # ⭐ worst first
kubectl get pods --sort-by=.metadata.creationTimestamp
kubectl get pods -o yaml                         # full manifest
kubectl get pods -o json | jq '.items[].metadata.name'
kubectl get all                                  # common resources in this namespace
kubectl get all -A -o wide

kubectl get deploy,svc,ing                       # multiple types at once
kubectl get nodes -o wide
kubectl get ns
kubectl get events --sort-by=.lastTimestamp      # ⭐⭐ the most underused command
kubectl get events -A --sort-by=.lastTimestamp --field-selector type=Warning
kubectl get endpoints myservice                  # ⭐ does the Service match any pods?
kubectl get endpointslices -l kubernetes.io/service-name=myservice
```

**Short names:** `po` pods · `deploy` deployments · `rs` replicasets · `svc` services · `ing` ingresses · `ns` namespaces · `no` nodes · `cm` configmaps · `pv`/`pvc` volumes · `sa` serviceaccounts · `sts` statefulsets · `ds` daemonsets · `hpa` · `netpol` · `crd`

---

## Describe & Events

```bash
kubectl describe pod mypod                  # ⭐ scroll to the EVENTS section at the bottom
kubectl describe deploy myapp
kubectl describe node node-1                # ⭐ allocated resources, conditions, taints
kubectl describe svc myservice
kubectl describe pvc mydata

# Events for one object
kubectl get events --field-selector involvedObject.name=mypod --sort-by=.lastTimestamp

# Cluster-wide warnings in the last period
kubectl get events -A --field-selector type=Warning --sort-by=.lastTimestamp | tail -30
```

> 💡 **`describe` before `logs`.** Logs tell you what the application said; events tell you whether the application ever started. Scheduling failures, image pull errors, volume mount failures, and probe failures all appear **only** in events.

---

## Logs

```bash
kubectl logs mypod
kubectl logs mypod -c mycontainer                # multi-container pod
kubectl logs mypod --previous                    # ⭐⭐ the CRASHED container's logs
kubectl logs mypod -f                            # follow
kubectl logs mypod --tail=100
kubectl logs mypod --since=15m
kubectl logs mypod --since-time=2026-08-04T09:00:00Z
kubectl logs mypod --timestamps

kubectl logs -l app=api --all-containers --prefix --tail=50    # ⭐ all pods of an app
kubectl logs deploy/myapp                        # one pod from the deployment
kubectl logs deploy/myapp --all-pods -f          # (1.31+) every pod
kubectl logs job/mybatch
kubectl logs -n kube-system -l k8s-app=kube-dns  # CoreDNS

# Multi-pod tailing with colour
stern api                                        # stern is worth installing
stern -n prod 'api-.*' --since 10m
```

---

## Exec & Debug

```bash
kubectl exec -it mypod -- bash
kubectl exec -it mypod -c sidecar -- sh
kubectl exec mypod -- env
kubectl exec mypod -- cat /etc/config/app.yaml
kubectl exec mypod -- ps aux

# ⭐ Ephemeral debug container — for distroless/scratch images with no shell
kubectl debug -it mypod --image=nicolaka/netshoot --target=mycontainer
kubectl debug -it mypod --image=busybox --target=app -- sh

# Copy the pod with a different entrypoint — for CrashLoopBackOff
kubectl debug mypod -it --copy-to=mypod-debug --container=app -- sh
kubectl debug mypod -it --copy-to=mypod-debug --set-image=app=busybox -- sh

# Debug a NODE (privileged pod with the host filesystem at /host)
kubectl debug node/node-1 -it --image=ubuntu

# Throwaway pods
kubectl run tmp --rm -it --image=nicolaka/netshoot -- bash      # ⭐ network toolbox
kubectl run tmp --rm -it --image=busybox --restart=Never -- sh
kubectl run curl --rm -it --image=curlimages/curl -- sh

kubectl cp mypod:/var/log/app.log ./app.log
kubectl cp ./config.yaml mypod:/tmp/config.yaml
kubectl port-forward pod/mypod 8080:80           # ⭐ reach a pod from your laptop
kubectl port-forward svc/myservice 5432:5432
kubectl port-forward deploy/myapp 8080:8080
kubectl attach -it mypod
kubectl proxy --port=8001                        # local proxy to the API server
```

---

## Apply, Edit, Delete

```bash
kubectl apply -f deployment.yml
kubectl apply -f ./manifests/                    # a whole directory
kubectl apply -k ./overlays/prod                 # kustomize
kubectl apply -f https://example.com/manifest.yml
kubectl apply -f d.yml --dry-run=server          # ⭐ validate against the real API + webhooks
kubectl apply -f d.yml --dry-run=client -o yaml  # render without sending
kubectl diff -f deployment.yml                   # ⭐⭐ what WOULD change — always run this first

kubectl create deployment nginx --image=nginx:1.25
kubectl create ns staging
kubectl create cm app-config --from-file=./config/ --dry-run=client -o yaml > cm.yaml
kubectl create secret generic db --from-literal=password=s3cr3t
kubectl create job manual-run --from=cronjob/nightly

kubectl edit deploy myapp                        # opens $KUBE_EDITOR, applies on save
kubectl patch deploy myapp -p '{"spec":{"replicas":5}}'
kubectl patch deploy myapp --type=json \
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/image","value":"myapp:v2"}]'
kubectl set image deploy/myapp app=myapp:v2      # ⭐ the standard deploy command
kubectl set env deploy/myapp LOG_LEVEL=debug
kubectl set resources deploy/myapp -c=app --limits=memory=1Gi
kubectl label pod mypod env=prod --overwrite
kubectl annotate deploy myapp kubernetes.io/change-cause="deploy v2"

kubectl delete pod mypod
kubectl delete -f deployment.yml
kubectl delete pods -l app=api
kubectl delete pod mypod --grace-period=0 --force    # ⚠️ last resort — can orphan resources
kubectl delete all -l app=myapp -n staging           # ⚠️ 'all' is not literally everything
```

> 💡 **`kubectl diff -f` before `kubectl apply -f`** is the Kubernetes equivalent of `terraform plan`. It's the single easiest habit to adopt and it catches a surprising number of mistakes.

---

## Rollouts & Scaling

```bash
kubectl rollout status deploy/myapp --timeout=5m     # ⭐ blocks until ready or fails
kubectl rollout history deploy/myapp
kubectl rollout history deploy/myapp --revision=3
kubectl rollout undo deploy/myapp                    # ⭐ back one revision
kubectl rollout undo deploy/myapp --to-revision=3
kubectl rollout restart deploy/myapp                 # ⭐ rolling restart, no image change
kubectl rollout pause deploy/myapp                   # batch several changes
kubectl rollout resume deploy/myapp

kubectl scale deploy/myapp --replicas=5
kubectl scale deploy/myapp --replicas=0              # stop without deleting
kubectl scale --replicas=3 -f deployment.yml
kubectl scale deploy/myapp --current-replicas=3 --replicas=5   # safe conditional scale
```

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 0        # ⭐ never drop below the desired count
    maxSurge: 1              # one extra pod at a time
minReadySeconds: 10          # a pod must stay ready this long before continuing
progressDeadlineSeconds: 600 # mark the rollout failed after this
revisionHistoryLimit: 10
```

> 💡 A rollout with `maxUnavailable: 0` plus a correct **readiness probe** is genuine zero-downtime. Without the readiness probe, Kubernetes will happily route traffic to a pod that hasn't finished starting.

---

## Resources & Autoscaling

```bash
kubectl top nodes                                # requires metrics-server
kubectl top pods -A --sort-by=memory             # ⭐
kubectl top pods --containers
kubectl describe node node-1 | grep -A 8 "Allocated resources"    # ⭐ real utilisation
kubectl get pods -A -o custom-columns=\
'NS:.metadata.namespace,POD:.metadata.name,CPU_REQ:.spec.containers[*].resources.requests.cpu,MEM_REQ:.spec.containers[*].resources.requests.memory'

kubectl autoscale deploy myapp --min=2 --max=10 --cpu-percent=70
kubectl get hpa
kubectl describe hpa myapp                       # ⭐ why isn't it scaling?

kubectl cordon node-1                            # stop new pods landing here
kubectl drain node-1 --ignore-daemonsets --delete-emptydir-data    # ⭐ evacuate for maintenance
kubectl uncordon node-1
kubectl taint node node-1 key=value:NoSchedule
kubectl taint node node-1 key-                   # remove (trailing dash)
```

```yaml
resources:
  requests:              # ⭐ what the SCHEDULER reserves
    cpu: "100m"
    memory: "128Mi"
  limits:                # ⭐ the ceiling the kernel enforces
    cpu: "500m"          # exceeded → THROTTLED (slow)
    memory: "512Mi"      # exceeded → OOMKILLED (dead)
```

| | Too low | Too high |
|---|---------|----------|
| **CPU request** | Pod is starved under contention | Wastes capacity, blocks scheduling |
| **CPU limit** | Throttling — mysterious latency ⭐ | (Often better to omit CPU limits entirely) |
| **Memory request** | Node overcommits, evictions | Wastes capacity |
| **Memory limit** | **OOMKilled**, exit 137 | Node OOM risk affects neighbours |

```yaml
# Pod Disruption Budget — protects you during node drains
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: {name: myapp}
spec:
  minAvailable: 2        # or: maxUnavailable: 1
  selector: {matchLabels: {app: myapp}}
```

---

## ConfigMaps & Secrets

```bash
kubectl create cm app-config --from-literal=LOG_LEVEL=info --from-literal=PORT=8080
kubectl create cm app-config --from-file=./config/app.yaml
kubectl create cm app-config --from-env-file=.env
kubectl get cm app-config -o yaml
kubectl describe cm app-config

kubectl create secret generic db-creds \
  --from-literal=username=app --from-literal=password='s3cr3t'
kubectl create secret generic tls-key --from-file=./tls.key
kubectl create secret docker-registry ghcr \
  --docker-server=ghcr.io --docker-username=USER --docker-password="$TOKEN"
kubectl create secret tls my-tls --cert=cert.pem --key=key.pem

# ⭐ Read a secret value
kubectl get secret db-creds -o jsonpath='{.data.password}' | base64 -d; echo
kubectl get secret db-creds -o go-template='{{range $k,$v := .data}}{{$k}}={{$v|base64decode}}{{"\n"}}{{end}}'

# Update in place
kubectl create cm app-config --from-file=./config/ --dry-run=client -o yaml \
  | kubectl apply -f -
```

```yaml
envFrom:
  - configMapRef: {name: app-config}
  - secretRef:    {name: db-creds}
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef: {name: db-creds, key: password}
  - name: POD_NAME
    valueFrom:
      fieldRef: {fieldPath: metadata.name}       # ⭐ downward API
volumes:
  - name: config
    configMap:
      name: app-config
      items: [{key: app.yaml, path: app.yaml}]
```

> ⚠️ **Kubernetes Secrets are base64-encoded, not encrypted.** Anyone with `get secret` RBAC, or read access to etcd, can read them. For production: enable **encryption at rest** in the API server, restrict RBAC tightly, and use **External Secrets Operator** or **Sealed Secrets** so plaintext never enters git.
>
> Also: a pod using a ConfigMap via `env` does **not** pick up changes — you must restart it (`kubectl rollout restart`). ConfigMaps mounted as **volumes** do update, eventually, if the app re-reads the file.

---

## Networking

```bash
kubectl get svc
kubectl get svc -o wide
kubectl get endpoints myservice                  # ⭐ empty = selector/readiness problem
kubectl get ing
kubectl describe ing myingress
kubectl get netpol

kubectl expose deploy myapp --port=80 --target-port=8080 --name=myapp-svc
kubectl expose deploy myapp --type=LoadBalancer --port=80

# DNS test from inside the cluster
kubectl run tmp --rm -it --image=nicolaka/netshoot -- \
  nslookup myservice.mynamespace.svc.cluster.local
kubectl run tmp --rm -it --image=nicolaka/netshoot -- \
  curl -sv http://myservice.mynamespace:8080/health
```

**Service DNS**: `<service>.<namespace>.svc.cluster.local`
Same namespace: `myservice`. Cross-namespace: `myservice.othernamespace`.

```yaml
# Default-deny NetworkPolicy — the right starting point for any namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: default-deny-ingress}
spec:
  podSelector: {}
  policyTypes: [Ingress]
---
# Then allow specifically
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: allow-api-to-db}
spec:
  podSelector: {matchLabels: {app: db}}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector: {matchLabels: {app: api}}
      ports:
        - {protocol: TCP, port: 5432}
```

---

## Storage

```bash
kubectl get pv
kubectl get pvc
kubectl get sc                                   # storage classes
kubectl describe pvc mydata                      # ⭐ why is it Pending?
kubectl get pvc -A --sort-by=.spec.resources.requests.storage
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata: {name: mydata}
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: gp3
  resources: {requests: {storage: 20Gi}}
```

| Access mode | Meaning |
|-------------|---------|
| `ReadWriteOnce` (RWO) | One **node** can mount it read-write — the normal case for block storage |
| `ReadOnlyMany` (ROX) | Many nodes, read-only |
| `ReadWriteMany` (RWX) | Many nodes read-write — needs NFS/EFS/CephFS, not EBS |
| `ReadWriteOncePod` | Exactly one **pod** |

> 💡 A `Pending` PVC is almost always one of: no default StorageClass, a StorageClass that provisions in a different AZ than the pod's node, or requesting `ReadWriteMany` from a driver that only does `ReadWriteOnce`. `kubectl describe pvc` says which.

---

## RBAC

```bash
kubectl auth can-i create deployments                       # ⭐ can I?
kubectl auth can-i delete pods --namespace prod
kubectl auth can-i '*' '*' --all-namespaces                 # am I cluster-admin?
kubectl auth can-i list secrets --as=system:serviceaccount:default:myapp    # ⭐ can THEY?
kubectl auth whoami                                          # (1.28+)

kubectl get roles,rolebindings -A
kubectl get clusterroles,clusterrolebindings
kubectl describe clusterrole view
kubectl get sa

kubectl create sa myapp
kubectl create role pod-reader --verb=get,list,watch --resource=pods
kubectl create rolebinding myapp-pods --role=pod-reader --serviceaccount=default:myapp
kubectl create clusterrolebinding admin-alice --clusterrole=cluster-admin --user=alice
```

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: {namespace: prod, name: app-reader}
rules:
  - apiGroups: [""]
    resources: [pods, configmaps]
    verbs: [get, list, watch]
  - apiGroups: ["apps"]
    resources: [deployments]
    resourceNames: [myapp]        # ⭐ scope to specific objects
    verbs: [get, patch]
```

| | Namespaced | Cluster-wide |
|---|-----------|--------------|
| Permissions | `Role` | `ClusterRole` |
| Grant | `RoleBinding` | `ClusterRoleBinding` |

A `RoleBinding` can reference a `ClusterRole` — that grants those permissions **within one namespace**, which is the usual way to reuse the built-in `view`/`edit`/`admin` roles.

---

## jsonpath & Custom Columns

```bash
kubectl get pods -o jsonpath='{.items[*].metadata.name}'
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'
kubectl get pods -o jsonpath='{.items[*].spec.containers[*].image}' | tr ' ' '\n' | sort -u
kubectl get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}'
kubectl get pod mypod -o jsonpath='{.status.containerStatuses[0].restartCount}'
kubectl get pod mypod -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}'   # ⭐ OOMKilled?
kubectl get svc mysvc -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
kubectl get secret s -o jsonpath='{.data.password}' | base64 -d

kubectl get pods -o custom-columns=\
'NAME:.metadata.name,STATUS:.status.phase,NODE:.spec.nodeName,RESTARTS:.status.containerStatuses[0].restartCount,IMAGE:.spec.containers[0].image'

kubectl get pods -A -o custom-columns=\
'NS:.metadata.namespace,POD:.metadata.name,MEM_LIM:.spec.containers[*].resources.limits.memory'

# Everything running in the cluster, deduplicated
kubectl get pods -A -o jsonpath='{range .items[*]}{range .spec.containers[*]}{.image}{"\n"}{end}{end}' | sort -u
```

**Handy `jq` combinations:**

```bash
kubectl get pods -o json | jq -r '.items[] | select(.status.phase!="Running") | .metadata.name'
kubectl get pods -A -o json | jq -r '.items[] | select(.spec.containers[].resources.limits == null)
  | "\(.metadata.namespace)/\(.metadata.name)"'          # ⭐ pods with no limits
kubectl get nodes -o json | jq -r '.items[] | "\(.metadata.name) \(.status.allocatable.memory)"'
```

---

## Debugging Recipes

```bash
# ─── Pod won't start ───
kubectl get pods                                       # 1. read STATUS
kubectl describe pod mypod                             # 2. ⭐ scroll to Events
kubectl logs mypod --previous                          # 3. ⭐ the crashed container
kubectl get events --sort-by=.lastTimestamp | tail -30 # 4. cluster-level causes
kubectl get pod mypod -o yaml | less                   # 5. the full resolved spec

# Was it OOMKilled?
kubectl get pod mypod -o jsonpath='{.status.containerStatuses[*].lastState.terminated.reason}'

# ─── Service unreachable ───
kubectl get endpoints myservice                        # ⭐ FIRST. Empty = labels/readiness
kubectl get pods -l app=myapp --show-labels            # do labels match the selector?
kubectl get svc myservice -o jsonpath='{.spec.selector}'
kubectl run tmp --rm -it --image=nicolaka/netshoot -- curl -sv http://myservice:80
kubectl run tmp --rm -it --image=nicolaka/netshoot -- nslookup myservice
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --tail=50

# ─── Node problems ───
kubectl get nodes
kubectl describe node node-1 | grep -A 10 Conditions   # ⭐ DiskPressure? MemoryPressure?
kubectl describe node node-1 | grep -A 8 "Allocated resources"
kubectl get pods -A --field-selector spec.nodeName=node-1

# ─── Everything is Pending ───
kubectl describe pod mypod | grep -A 5 Events          # "0/3 nodes are available: ..."
kubectl get nodes -o custom-columns='NAME:.metadata.name,TAINTS:.spec.taints'
kubectl top nodes
kubectl get resourcequota -A
kubectl get limitrange -A

# ─── Resource forensics ───
kubectl get pods -A --sort-by=.status.containerStatuses[0].restartCount | tail -20
kubectl top pods -A --sort-by=memory | head -20
kubectl get pods -A -o json | jq -r '.items[] |
  select(.status.containerStatuses[]?.lastState.terminated.reason=="OOMKilled") |
  "\(.metadata.namespace)/\(.metadata.name)"'          # ⭐ everything recently OOMKilled
```

---

## Helm

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm search repo nginx
helm search hub prometheus
helm show values bitnami/nginx > values.yaml         # ⭐ see every configurable option
helm show chart bitnami/nginx
helm show readme bitnami/nginx

helm install myrelease bitnami/nginx
helm install myrelease bitnami/nginx -f values.yaml --namespace prod --create-namespace
helm install myrelease ./mychart --set replicaCount=3 --set image.tag=v2
helm install myrelease ./mychart --dry-run --debug   # ⭐ render without installing
helm install myrelease ./mychart --wait --timeout 5m --atomic   # ⭐ auto-rollback on failure

helm upgrade myrelease bitnami/nginx -f values.yaml
helm upgrade --install myrelease ./mychart -f values.yaml       # ⭐ idempotent — use in CI
helm upgrade myrelease ./mychart --reuse-values --set image.tag=v3

helm list / helm list -A / helm list --all           # includes failed releases
helm status myrelease
helm history myrelease                               # ⭐ revision list
helm rollback myrelease 3
helm uninstall myrelease --keep-history
helm get values myrelease                            # ⭐ what values are actually in use
helm get values myrelease --all                      # including chart defaults
helm get manifest myrelease                          # the rendered YAML that was applied
helm get notes myrelease

helm template myrelease ./mychart -f values.yaml     # ⭐ render locally, no cluster needed
helm template . | kubectl apply --dry-run=server -f -
helm lint ./mychart
helm diff upgrade myrelease ./mychart                # plugin: helm-diff ⭐ install this
helm dependency update ./mychart
helm package ./mychart
helm create mychart
```

```
mychart/
├── Chart.yaml          # name, version, appVersion, dependencies
├── values.yaml         # default values
├── values.schema.json  # ⭐ validates user-supplied values
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── _helpers.tpl    # named template definitions
│   └── NOTES.txt       # post-install message
└── charts/             # vendored subcharts
```

```yaml
# Template essentials
{{ .Values.image.tag | default .Chart.AppVersion }}
{{ .Release.Name }} {{ .Release.Namespace }} {{ .Chart.Name }} {{ .Chart.Version }}
{{ include "mychart.fullname" . }}
{{- if .Values.ingress.enabled }} ... {{- end }}
{{- range .Values.env }}
  - name: {{ .name }}
    value: {{ .value | quote }}
{{- end }}
{{- with .Values.nodeSelector }}
nodeSelector: {{ toYaml . | nindent 8 }}
{{- end }}
checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
#   ⭐ that annotation forces a rollout whenever the ConfigMap changes
{{ required "image.repository is required" .Values.image.repository }}
{{ .Values.password | b64enc }}
```

---

## GitOps (Argo CD)

```bash
argocd login localhost:8080 --username admin --insecure     # port-forwarded, self-signed cert
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d                # the install-time admin password
argocd account update-password                               # ⭐ then delete that Secret

argocd app list
argocd app get web                                           # ⭐ Sync Status + Health Status
argocd app get web --refresh                                 # compare against Git NOW, don't wait
argocd app get web -o json | jq '.spec.syncPolicy'           # is prune/selfHeal actually on?
argocd app diff web                                          # ⭐ what differs from Git, before syncing
argocd app resources web                                     # what Argo CD believes it manages
argocd app manifests web                                     # the rendered YAML it would apply

argocd app sync web
argocd app sync web --dry-run                                # ⭐ read this before enabling prune
argocd app sync web --prune
argocd app history web
argocd app rollback web 3                                    # ⚠️ out-of-band — next sync undoes it

argocd app set web --sync-policy automated --auto-prune=true --self-heal=true
argocd app set web --revision main                           # ⭐ which revision it actually tracks
argocd app set web --sync-policy none                        # back to manual

argocd app logs web --follow                                 # app pod logs, via Argo CD
argocd app wait web --health --timeout 300                   # ⭐ use this in a pipeline
kubectl -n argocd logs deploy/argocd-repo-server             # Git clone / render failures
kubectl -n argocd logs statefulset/argocd-application-controller   # sync + reconcile failures
kubectl get applications -n argocd -o wide                   # no CLI? the CRD is right there
```

| Status pair | Means |
|-------------|-------|
| `Synced` + `Healthy` | Working as intended |
| `Synced` + `Degraded` | ⭐ The cluster matches Git and **Git is wrong** — re-syncing cannot fix it. Revert |
| `OutOfSync` + `Healthy` | Something is running that Git doesn't describe — drift, or a pending change |
| `OutOfSync` + `Degraded` | A failed sync, usually a bad manifest — check the app's conditions |
| `Missing` | Git describes it, nothing applied it yet |

| Field | Default | Why it bites |
|-------|---------|--------------|
| `syncPolicy.automated` | absent | No automation at all — Argo CD is a diff tool until you set it |
| `automated.selfHeal` | `false` | ⭐ Cluster-side drift is reported, never reverted |
| `automated.prune` | `false` | ⭐ Deleting a manifest from Git deletes nothing. `Synced` stays green |
| `targetRevision` | — | `HEAD`/a stale branch tracks the wrong thing while looking perfectly synced |
| `ignoreDifferences` | absent | Without it, `selfHeal` fights the HPA over `spec.replicas` forever |

---

## Service Mesh

Only after limits, probes, and NetworkPolicies are right — a mesh on shaky basics adds a second
place for bugs to hide.

```bash
# Istio
istioctl install --set profile=demo          # ⚠️ never `demo` in production
kubectl label namespace app istio-injection=enabled    # injection is per NAMESPACE
istioctl analyze -n app                      # ⭐ finds misconfiguration before it bites
istioctl proxy-status                        # are sidecars in sync with the control plane
istioctl proxy-config routes deploy/checkout # what this proxy actually believes
istioctl proxy-config secret deploy/checkout # mTLS certs the sidecar holds

# Linkerd — the best preflight of any mesh
linkerd check
linkerd viz stat deploy -n app               # success rate + p99 per deployment
linkerd viz tap deploy/checkout              # live requests, no app changes
linkerd viz edges deploy -n app              # who actually talks to whom
```

| Gives you | Instead of |
|-----------|-----------|
| mTLS everywhere, certs rotated hourly | Per-language TLS config and cert distribution you built |
| Retries, timeouts, circuit breaking as policy | A different client library per language |
| Traffic splitting by weight (real canaries) | Replica arithmetic across two Deployments |
| Golden metrics for every service pair | Instrumenting every service and hoping for consistency |
| L7 authorization by workload identity | NetworkPolicy at L3/L4 — IP and port only |

| Costs you | Roughly |
|-----------|---------|
| Memory + CPU per pod (sidecar) | ~50–100 MB each × every pod |
| Latency | Single-digit ms, on both sides of every call |
| A control plane | HA, upgraded, and able to break all service traffic when misconfigured |
| Debugging surface | "App or proxy?" — startup ordering, `PERMISSIVE` vs `STRICT`, sidecars outliving Jobs |

**Models**: sidecar (per pod, full L7, priciest) · ambient/sidecarless (per node for L4+mTLS,
L7 opt-in) · eBPF (Cilium — least latency, tied to your CNI).
**Under ~10 services**: Ingress + NetworkPolicies + a retry library. Skip the mesh.

---

## Manifest Templates

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  labels: {app: myapp}
spec:
  replicas: 3
  revisionHistoryLimit: 5
  selector:
    matchLabels: {app: myapp}          # ⚠️ immutable after creation
  strategy:
    type: RollingUpdate
    rollingUpdate: {maxUnavailable: 0, maxSurge: 1}
  template:
    metadata:
      labels: {app: myapp}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      serviceAccountName: myapp
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        fsGroup: 10001
        seccompProfile: {type: RuntimeDefault}
      topologySpreadConstraints:       # ⭐ spread across zones
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector: {matchLabels: {app: myapp}}
      containers:
        - name: app
          image: ghcr.io/org/myapp@sha256:abc...     # ⭐ digest, not a tag
          imagePullPolicy: IfNotPresent
          ports: [{containerPort: 8080, name: http}]
          envFrom:
            - configMapRef: {name: myapp-config}
            - secretRef:    {name: myapp-secrets}
          resources:
            requests: {cpu: 100m, memory: 128Mi}
            limits:   {memory: 512Mi}
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: {drop: [ALL]}
          startupProbe:                # ⭐ for slow starters — protects liveness
            httpGet: {path: /health, port: http}
            failureThreshold: 30
            periodSeconds: 5
          readinessProbe:              # ⭐ gates TRAFFIC
            httpGet: {path: /ready, port: http}
            periodSeconds: 5
            failureThreshold: 3
          livenessProbe:               # ⭐ gates RESTART — keep it simple and cheap
            httpGet: {path: /health, port: http}
            periodSeconds: 10
            failureThreshold: 3
          lifecycle:
            preStop:
              exec: {command: ["sh", "-c", "sleep 10"]}   # let the LB deregister first
          volumeMounts:
            - {name: tmp, mountPath: /tmp}
      volumes:
        - name: tmp
          emptyDir: {}
      terminationGracePeriodSeconds: 45
```

| Probe | Failure means | Use for |
|-------|---------------|---------|
| **startupProbe** | Kill and restart | Slow-starting apps; disables the other two until it passes |
| **readinessProbe** | Remove from Service endpoints ⭐ | "Can I serve traffic right now?" — may check dependencies |
| **livenessProbe** | **Restart the container** ⚠️ | "Am I deadlocked?" — must be cheap and must **not** check dependencies |

> ⚠️ **Never make a liveness probe check a database.** When the database has a hiccup, every replica fails liveness, every replica restarts simultaneously, and a small outage becomes a total one. Dependency checks belong in **readiness**.

---

## Error Decoder

| Status / message | Cause | Fix |
|------------------|-------|-----|
| `Pending` + `Insufficient cpu/memory` | No node has room | Lower requests, scale the cluster |
| `Pending` + `didn't match node selector` / `had taint` | Scheduling constraints | Fix `nodeSelector`/affinity, add a toleration |
| `Pending` + `pod has unbound PVC` | Storage not provisioned | `describe pvc`; check StorageClass and AZ |
| `ImagePullBackOff` / `ErrImagePull` | Bad image name/tag, or auth | Verify the tag; add `imagePullSecrets` |
| `CrashLoopBackOff` | Container keeps exiting | `logs --previous`; check exit code and OOM |
| `OOMKilled` (exit 137) | Exceeded the memory limit | Raise the limit or fix the leak |
| `CreateContainerConfigError` | Missing ConfigMap/Secret key | `describe pod` names the missing key |
| `Init:0/1` | An init container is blocking | `logs POD -c <init-container>` |
| `Running` but `READY 0/1` | ⭐ Readiness probe failing | `describe pod` → probe path, port, initialDelay |
| `Terminating` forever | Finalizer, or SIGTERM ignored | Check `.metadata.finalizers`; last resort `--force --grace-period=0` |
| `Evicted` | Node pressure (disk/memory) | `describe node` → Conditions; set requests properly |
| `Service has no endpoints` | Selector doesn't match, or pods unready | Compare `svc.spec.selector` with pod labels |
| `502/504` from Ingress | Backend unready, or wrong port | Check endpoints, `targetPort`, ingress-controller logs |
| `Error from server (Forbidden)` | RBAC | `kubectl auth can-i ...`; add a Role/RoleBinding |
| `The Deployment is invalid: spec.selector: field is immutable` | Changed the selector | Delete and recreate the Deployment |
| Config change had no effect | ConfigMap via `env` needs a restart | `kubectl rollout restart deploy/myapp` |
| CPU throttling, no errors | CPU **limit** too low | Raise or remove the CPU limit; check `container_cpu_cfs_throttled_periods_total` |

---

<div align="center">

[← Module 12 README](./README.md) · [Resources](./resources.md) · [Labs](./labs/) · [Handbook Quick Reference](../QUICK-REFERENCE.md)

</div>
