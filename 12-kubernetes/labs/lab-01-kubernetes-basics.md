# Lab 01: Kubernetes Basics — Deploy, Scale, and Update with minikube

## 🎯 Objective

Set up a local Kubernetes cluster, deploy applications, expose them with Services, scale horizontally, perform rolling updates and rollbacks — the core K8s workflows you'll use daily.

---

## 📋 Prerequisites

- Docker installed
- minikube installed (`minikube version`)
- kubectl installed (`kubectl version --client`)
- Completed Module 05 (Docker) and Module 11 (Ansible)

### Install minikube and kubectl (if needed)

```bash
# minikube (Linux)
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# kubectl (Linux)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl
```

---

## 🔬 Exercise 1: Start a Cluster and Deploy

### Step 1: Start minikube

```bash
minikube start --driver=docker

# Verify
kubectl cluster-info
kubectl get nodes
```

### Step 2: Create a Deployment

```bash
mkdir -p k8s-lab && cd k8s-lab

cat > deployment.yml << 'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
        - name: nginx
          image: nginx:1.25
          ports:
            - containerPort: 80
          resources:
            requests:
              memory: "64Mi"
              cpu: "50m"
            limits:
              memory: "128Mi"
              cpu: "100m"
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 3
            periodSeconds: 5
YAML

kubectl apply -f deployment.yml
```

### Step 3: Verify

```bash
# Watch pods come up
kubectl get pods -w

# Check deployment
kubectl get deployments

# Detailed info
kubectl describe deployment web-app

# Check events
kubectl get events --sort-by='.lastTimestamp'
```

**✅ Checkpoint:** 3 pods running with STATUS = Running and READY = 1/1.

---

## 🔬 Exercise 2: Expose with a Service

```bash
cat > service.yml << 'YAML'
apiVersion: v1
kind: Service
metadata:
  name: web-app
spec:
  selector:
    app: web-app
  type: NodePort
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30080
YAML

kubectl apply -f service.yml

# Access the service
minikube service web-app --url
# Visit the URL in your browser — you should see the Nginx welcome page

# Or use port-forward
kubectl port-forward service/web-app 8080:80 &
curl http://localhost:8080
```

**✅ Checkpoint:** Nginx welcome page accessible from your browser.

---

## 🔬 Exercise 3: Scale and Observe

```bash
# Scale up
kubectl scale deployment web-app --replicas=5
kubectl get pods -w

# Scale down
kubectl scale deployment web-app --replicas=2
kubectl get pods -w

# Check which nodes the pods are on
kubectl get pods -o wide

# Check resource usage
kubectl top pods    # (requires metrics-server: minikube addons enable metrics-server)
```

**✅ Checkpoint:** Scaling up creates new pods, scaling down terminates extras.

---

## 🔬 Exercise 4: Rolling Update and Rollback

### Step 1: Update the Image

```bash
# Update to a new version
kubectl set image deployment/web-app nginx=nginx:1.26

# Watch the rollout
kubectl rollout status deployment/web-app

# Check rollout history
kubectl rollout history deployment/web-app

# Verify new version
kubectl get pods -o jsonpath='{.items[*].spec.containers[0].image}'
```

### Step 2: Rollback

```bash
# Deploy a broken image
kubectl set image deployment/web-app nginx=nginx:nonexistent

# Watch it fail
kubectl get pods
# You'll see ImagePullBackOff errors

# Rollback!
kubectl rollout undo deployment/web-app

# Verify rollback
kubectl rollout status deployment/web-app
kubectl get pods
```

**✅ Checkpoint:** You deployed a bad image, saw it fail, and rolled back successfully.

---

## 🔬 Exercise 5: ConfigMaps and Secrets

```bash
# Create a ConfigMap
kubectl create configmap app-config \
  --from-literal=APP_ENV=production \
  --from-literal=LOG_LEVEL=info

# Create a Secret
kubectl create secret generic db-creds \
  --from-literal=DB_USER=admin \
  --from-literal=DB_PASS=s3cret123

# Deploy a pod that uses them
cat > configured-pod.yml << 'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: configured-app
spec:
  containers:
    - name: app
      image: busybox
      command: ["sh", "-c", "env | sort && sleep 3600"]
      envFrom:
        - configMapRef:
            name: app-config
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
YAML

kubectl apply -f configured-pod.yml

# Verify environment variables
kubectl logs configured-app | grep -E "APP_ENV|LOG_LEVEL|DB_USER|DB_PASS"
```

**✅ Checkpoint:** Pod has environment variables from both ConfigMap and Secret.

---

## 🧨 Break It: Debug Scenarios

### Scenario 1: Wrong Image

```bash
kubectl set image deployment/web-app nginx=nginx:doesnotexist
# Check: kubectl get pods → ImagePullBackOff
# Fix: kubectl rollout undo deployment/web-app
```

### Scenario 2: Resource Limits Too Low

```bash
kubectl set resources deployment/web-app --limits=memory=1Mi
# Check: kubectl get pods → OOMKilled
# Fix: kubectl set resources deployment/web-app --limits=memory=128Mi
```

### Scenario 3: Labels Don't Match

```bash
# Create a service with wrong selector
cat > broken-svc.yml << 'YAML'
apiVersion: v1
kind: Service
metadata:
  name: broken
spec:
  selector:
    app: wrong-label
  ports:
    - port: 80
YAML
kubectl apply -f broken-svc.yml
kubectl get endpoints broken
# Endpoints: <none> — no pods match!
```

---

## 🧹 Cleanup

```bash
kubectl delete -f .
cd .. && rm -rf k8s-lab
minikube stop    # or: minikube delete
```

---

## ✅ Validation

- [ ] Start a minikube cluster and verify with kubectl
- [ ] Create a Deployment with 3 replicas and health probes
- [ ] Expose it with a NodePort Service and access from browser
- [ ] Scale up and down, observe pod lifecycle
- [ ] Perform a rolling update and verify new image version
- [ ] Rollback a broken deployment
- [ ] Use ConfigMaps and Secrets as environment variables
- [ ] Debug ImagePullBackOff, OOMKilled, and selector mismatch issues
- [ ] Explain the difference between Deployment and Pod

---

[← Back to Module README](../README.md)
