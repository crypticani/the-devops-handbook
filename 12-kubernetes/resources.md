# Module 12: Kubernetes — Resources

---

## 📖 Essential Reading

| Resource | Type | Difficulty | Notes |
|----------|------|------------|-------|
| [Kubernetes Documentation](https://kubernetes.io/docs/home/) | Documentation | Beginner | Official docs — start with "Learn Kubernetes Basics" |
| [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/) | Reference | All | **Bookmark this** — essential kubectl commands |
| [Kubernetes Patterns (Ibryam & Huß)](https://www.oreilly.com/library/view/kubernetes-patterns-2nd/9781098131678/) | Book | Intermediate | Reusable design patterns for K8s |
| [Kubernetes Up & Running (Hightower et al.)](https://www.oreilly.com/library/view/kubernetes-up-and/9781098110192/) | Book | Intermediate | Comprehensive K8s guide |
| [Kubernetes the Hard Way (Kelsey Hightower)](https://github.com/kelseyhightower/kubernetes-the-hard-way) | Tutorial | Advanced | Build a cluster from scratch — deep understanding |

---

## 🎥 Videos & Courses

| Resource | Type | Duration | Notes |
|----------|------|----------|-------|
| [Kubernetes Course (TechWorld with Nana)](https://www.youtube.com/watch?v=X48VuDVv0do) | Video | 4 hours | Best beginner K8s walkthrough |
| [Kubernetes in 100 Seconds (Fireship)](https://www.youtube.com/watch?v=PziYflu8cB8) | Video | 2 min | Quick conceptual overview |
| [Kubernetes Networking (Nana)](https://www.youtube.com/watch?v=5cNrTU6o3Fw) | Video | 30 min | Services, Ingress, DNS explained |
| [Helm Explained (TechWorld with Nana)](https://www.youtube.com/watch?v=-ykwb1d0DXU) | Video | 30 min | Helm charts and practical usage |
| [K8s Debugging (Learnk8s)](https://learnk8s.io/troubleshooting-deployments) | Article | 20 min | Visual debugging flowchart — print this! |

---

## 🧰 Tools & References

| Resource | Type | Notes |
|----------|------|-------|
| [minikube](https://minikube.sigs.k8s.io/) | Tool | Local single-node K8s cluster for learning |
| [kind](https://kind.sigs.k8s.io/) | Tool | K8s in Docker — lightweight local clusters |
| [k9s](https://k9scli.io/) | Tool | Terminal UI for Kubernetes — essential for productivity |
| [Lens](https://k8slens.dev/) | Tool | Desktop GUI for Kubernetes cluster management |
| [Helm](https://helm.sh/) | Tool | Package manager for Kubernetes |
| [Artifact Hub](https://artifacthub.io/) | Registry | Find Helm charts, operators, and K8s packages |
| [K8s Debugging Flowchart](https://learnk8s.io/troubleshooting-deployments) | Reference | Visual guide to debugging deployments |
| [kubectx + kubens](https://github.com/ahmetb/kubectx) | Tool | Switch between clusters and namespaces quickly |

---

## 🎯 Recommended Practice Path

1. **Week 1**: Install minikube. Deploy nginx as a Deployment with 3 replicas. Create a Service. Practice kubectl commands. Scale up/down. Do a rolling update and rollback.
2. **Week 2**: Deploy a multi-service app (frontend + backend + database). Use ConfigMaps and Secrets. Add health probes. Install Helm and deploy a chart from Artifact Hub.
3. **Week 3**: Set up an Ingress controller. Configure HPA for auto-scaling. Practice the debugging flowchart on intentionally broken deployments. Deploy your own Helm chart.
