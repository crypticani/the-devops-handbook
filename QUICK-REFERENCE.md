<div align="center">

# ⚡ Quick Reference

### The commands a DevOps engineer actually types every day

*One page. Keep it open in a tab.*

</div>

---

Per-module deep references: [Linux](./01-linux/cheatsheet.md) · [Networking](./02-networking/cheatsheet.md) · [Git](./03-git/cheatsheet.md) · [Scripting](./04-scripting/cheatsheet.md) · [Docker](./05-containers-docker/cheatsheet.md) · [CI/CD](./06-ci-cd/cheatsheet.md) · [Observability](./07-observability/cheatsheet.md) · [Logging](./08-logging/cheatsheet.md) · [Cloud](./09-cloud-fundamentals/cheatsheet.md) · [Terraform](./10-terraform/cheatsheet.md) · [Ansible](./11-ansible/cheatsheet.md) · [Kubernetes](./12-kubernetes/cheatsheet.md) · [Security](./13-security-basics/cheatsheet.md)

**Jump to:** [The daily 50](#the-daily-50) · [Server triage](#60-second-server-triage) · [Cluster triage](#60-second-cluster-triage) · [Service down](#service-is-down) · [Exit codes](#exit-codes--signals) · [HTTP codes](#http-status-codes) · [Ports](#common-ports) · [File modes](#file-permissions) · [CIDR](#cidr-math) · [Cron](#cron-syntax) · [Time & size units](#time--size-units) · [Safety rules](#the-rules-that-prevent-outages)

---

## The Daily 50

The commands that make up most of the working day, grouped by what you're trying to do.

### Look around

```bash
pwd; ls -lah                        # where am I, what's here
df -h && df -i                      # disk space AND inodes
free -h                             # memory ("available" is the number that matters)
uptime                              # load average — compare against `nproc`
ps aux --sort=-%mem | head          # top memory consumers
ss -tlnp                            # what is listening, and which process owns it
journalctl -u SERVICE -n 50 --no-pager
systemctl status SERVICE
```

### Find things

```bash
grep -rn "pattern" .                # recursive, with line numbers
grep -rn --include="*.py" "pattern" .
find . -name "*.log" -mtime -1      # by name and age
find . -type f -size +100M          # big files
rg "pattern"                        # ripgrep — faster if installed
history | grep docker               # what did I run last time?
which CMD; type -a CMD              # what will actually run
```

### Git

```bash
git status -sb
git diff                            # unstaged
git diff --staged                   # what you're about to commit
git switch -c feature/x
git add -p                          # stage hunks interactively
git commit -m "feat: ..."
git push -u origin HEAD
git pull --rebase
git log --oneline --graph --decorate --all
git reflog                          # ⭐ your undo history for everything committed
git restore --staged FILE           # unstage
git revert SHA                      # undo a PUSHED commit safely
```

### Docker

```bash
docker ps -a                        # ⭐ -a shows the crashed ones too
docker logs -f --tail 100 NAME
docker exec -it NAME sh
docker compose up -d --build
docker compose logs -f SERVICE
docker compose down
docker system df                    # where the disk went
docker inspect -f '{{.State.ExitCode}} OOM={{.State.OOMKilled}}' NAME
```

### Kubernetes

```bash
kubectl config current-context      # ⭐ WHICH CLUSTER AM I ON
kubectl get pods -o wide
kubectl describe pod POD            # ⭐ read the Events section
kubectl logs POD --previous         # ⭐ the crashed container's output
kubectl get events --sort-by=.lastTimestamp | tail -30
kubectl get endpoints SVC           # ⭐ empty = label/readiness problem
kubectl exec -it POD -- sh
kubectl port-forward svc/SVC 8080:80
kubectl rollout status deploy/APP --timeout=5m
kubectl rollout undo deploy/APP     # ⭐ the 3am command
kubectl diff -f manifest.yml        # ⭐ before every apply
```

### Terraform

```bash
terraform fmt -recursive
terraform validate
terraform plan -out=tfplan          # ⭐ review, then apply THIS file
terraform apply tfplan
terraform state list
terraform state show ADDR
terraform output -raw NAME
```

### Network debugging

```bash
dig +short HOST                     # does the name resolve?
nc -zv HOST PORT                    # is the port open?
curl -sSf -o /dev/null -w '%{http_code} %{time_total}s\n' URL
curl -v URL                         # full request/response
ss -tnp | grep HOST
mtr -rwc 20 HOST                    # where are packets being lost?
```

---

## 60-Second Server Triage

Cheapest checks first. Each one narrows the search.

```bash
uptime                                          # 1. load vs `nproc`
free -h                                         # 2. memory + swap
df -h && df -i                                  # 3. disk AND inodes
dmesg -T | tail -30                             # 4. OOM kills, disk errors
systemctl list-units --state=failed             # 5. what's down
journalctl -p err --since "1 hour ago" -n 50    # 6. recent errors
ps aux --sort=-%cpu | head -10                  # 7. top CPU
ss -s && ss -tlnp                               # 8. sockets and listeners
iostat -xz 1 3                                  # 9. disk latency
```

| What you see | What it means |
|--------------|---------------|
| Load ≫ CPU count, but CPU% low | Blocked on **I/O**, not CPU — check `iostat`, `vmstat` `b` column |
| `available` memory low, swap active | Memory pressure — expect OOM kills (`dmesg \| grep -i oom`) |
| `df -h` fine, `df -i` at 100% | **Inode** exhaustion — millions of small files |
| Disk full, nothing large found | Deleted-but-open file — `lsof +L1`, restart the holder |
| High `%util` + high `await` | Disk is the bottleneck |
| Thousands of `TIME_WAIT` | Connection churn — enable keep-alive/pooling |
| Thousands of `CLOSE_WAIT` | **Application bug** — it isn't closing sockets |

---

## 60-Second Cluster Triage

```bash
kubectl config current-context                              # ⭐ right cluster?
kubectl get nodes                                           # any NotReady?
kubectl get pods -A | grep -vE 'Running|Completed'          # ⭐ everything unhealthy
kubectl get events -A --sort-by=.lastTimestamp | tail -40
kubectl top nodes && kubectl top pods -A --sort-by=memory | head
kubectl get pods -A --sort-by=.status.containerStatuses[0].restartCount | tail -15
kubectl describe node NODE | grep -A 10 Conditions          # DiskPressure? MemoryPressure?
```

```bash
# Everything recently OOMKilled
kubectl get pods -A -o json | jq -r '.items[] |
  select(.status.containerStatuses[]?.lastState.terminated.reason=="OOMKilled") |
  "\(.metadata.namespace)/\(.metadata.name)"'
```

---

## Service Is Down

Work bottom-up. Each rung eliminates a layer.

```bash
dig +short api.example.com                    # 1. DNS resolves?
ping -c 3 IP                                  # 2. host reachable? (ICMP may be blocked)
nc -zv IP 443                                 # 3. port open?
openssl s_client -connect IP:443 -servername api.example.com </dev/null   # 4. TLS ok?
curl -v https://api.example.com/health        # 5. what does the app say?
```

| Step 3 result | Meaning | Look at |
|---------------|---------|---------|
| **Connection refused** | A machine answered "nothing here" — routing and firewalls are fine | Service is down, or bound to `127.0.0.1` |
| **Connection timed out** | Nobody answered at all | Firewall, security group, NACL, route |
| **No route to host** | Local routing has no path | `ip route`, gateway, subnet |

> ⭐ **Refused vs timeout is the single highest-value distinction in network debugging.** One means "the packet arrived"; the other means "it didn't." Reading it correctly saves hours.

---

## Exit Codes & Signals

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Misuse of a builtin / bad arguments |
| `126` | Found but **not executable** — missing `chmod +x`, or CRLF line endings |
| `127` | **Command not found** — wrong path, or missing from a slim image |
| `128+N` | Killed by signal N |
| `130` | SIGINT — Ctrl-C |
| **`137`** | ⭐ SIGKILL — **almost always OOM** in a container |
| `139` | SIGSEGV — segmentation fault |
| `143` | SIGTERM — a normal graceful stop |
| `125` | Docker itself failed (bad `docker run` flags) |

| Signal | № | Effect |
|--------|---|--------|
| `SIGHUP` | 1 | Most daemons **reload config** |
| `SIGINT` | 2 | Ctrl-C, catchable |
| `SIGKILL` | 9 | Immediate, **uncatchable**, no cleanup |
| `SIGTERM` | 15 | Polite shutdown — **the default, always try first** |
| `SIGSTOP`/`SIGCONT` | 19/18 | Pause / resume |

---

## HTTP Status Codes

| Code | Meaning | What it tells you |
|------|---------|-------------------|
| 200 / 201 / 204 | OK / Created / No Content | Working |
| 301 / 308 | Permanent redirect | ⚠️ Browsers cache these — hard to undo |
| 302 / 307 | Temporary redirect | Safe to change later |
| 304 | Not Modified | Cache hit |
| 400 | Bad Request | Malformed client request |
| **401** | Unauthorized | ⭐ **Not authenticated** — "who are you?" |
| **403** | Forbidden | ⭐ **Authenticated, not allowed** — "I know who you are, and no" |
| 404 | Not Found | Wrong path, or the wrong vhost/ingress rule matched |
| 405 | Method Not Allowed | GET where POST was expected |
| 409 | Conflict | Concurrent modification |
| 413 | Payload Too Large | Raise the proxy body limit |
| 429 | Too Many Requests | Rate limited — check `Retry-After` |
| 500 | Internal Server Error | The app threw — read app logs |
| **502** | Bad Gateway | ⭐ Proxy **couldn't reach** the backend |
| 503 | Service Unavailable | Overloaded, or no healthy backends |
| **504** | Gateway Timeout | ⭐ Backend answered, but **too slowly** |

---

## Common Ports

| Port | Service | | Port | Service |
|------|---------|-|------|---------|
| 22 | SSH | | 5672 / 15672 | RabbitMQ / UI |
| 25 / 587 | SMTP / submission | | 6379 | Redis |
| 53 | DNS (UDP + TCP) | | 6443 | **Kubernetes API server** |
| 80 | HTTP | | 8080 | HTTP alt / app servers |
| 123 | NTP (UDP) | | 8443 | HTTPS alt |
| 443 | HTTPS | | 9090 | **Prometheus** |
| 2379–2380 | etcd | | 9093 | Alertmanager |
| 3000 | **Grafana** | | 9100 | node_exporter |
| 3100 | Loki | | 9115 | blackbox_exporter |
| 3306 | MySQL / MariaDB | | 9200 / 9300 | Elasticsearch |
| 5432 | **PostgreSQL** | | 10250 | kubelet API |
| 5601 | Kibana | | 27017 | MongoDB |

---

## File Permissions

| Octal | Symbolic | Use for |
|-------|----------|---------|
| `400` | `r--------` | Root-owned secrets |
| **`600`** | `rw-------` | ⭐ **SSH private keys**, `.env`, tokens |
| `640` | `rw-r-----` | Config containing secrets, readable by a service group |
| **`644`** | `rw-r--r--` | ⭐ Normal files, `authorized_keys` |
| **`700`** | `rwx------` | ⭐ `~/.ssh` |
| `750` | `rwxr-x---` | Service directories |
| **`755`** | `rwxr-xr-x` | ⭐ **Directories**, binaries, scripts |
| `777` | `rwxrwxrwx` | ❌ Never in production |

```
r = 4    w = 2    x = 1        ⇒  rwx = 7, rw- = 6, r-x = 5, r-- = 4
Special: setuid 4000 · setgid 2000 · sticky 1000
```

**SSH refuses to work unless:** `~/.ssh` is `700`, private keys are `600`, `authorized_keys` is `600`, and `~` is not group- or world-writable.

---

## CIDR Math

| CIDR | Mask | Total | Usable | AWS* |
|------|------|-------|--------|------|
| `/32` | 255.255.255.255 | 1 | 1 | 1 |
| `/28` | 255.255.255.240 | 16 | 14 | 11 |
| `/26` | 255.255.255.192 | 64 | 62 | 59 |
| `/24` | 255.255.255.0 | 256 | 254 | 251 |
| `/20` | 255.255.240.0 | 4,096 | 4,094 | 4,091 |
| `/16` | 255.255.0.0 | 65,536 | 65,534 | 65,531 |

\* AWS reserves 5 addresses per subnet, not 2.

**Formula:** host bits = `32 − prefix` → total = `2^host bits` → usable = total − 2.

**Private ranges:** `10.0.0.0/8` · `172.16.0.0/12` · `192.168.0.0/16`
**Also reserved:** `127.0.0.0/8` loopback · `169.254.0.0/16` link-local (**cloud metadata lives at `169.254.169.254`**)

---

## Cron Syntax

```
┌───── minute (0-59)
│ ┌─── hour (0-23)
│ │ ┌─ day of month (1-31)
│ │ │ ┌─ month (1-12)
│ │ │ │ ┌─ day of week (0-7, 0 and 7 both = Sunday)
│ │ │ │ │
* * * * *  command
```

| Expression | Runs |
|------------|------|
| `*/5 * * * *` | Every 5 minutes |
| `0 * * * *` | Hourly, on the hour |
| `30 2 * * *` | 02:30 daily |
| `0 3 * * 0` | 03:00 Sundays |
| `0 0 1 * *` | Midnight on the 1st |
| `0 9-17 * * 1-5` | Hourly, 9–5, weekdays |
| `@reboot` / `@daily` / `@hourly` | Shorthand |

> ⚠️ **Cron's environment is nearly empty.** Use absolute paths for every binary and file, redirect both streams (`>> /var/log/x.log 2>&1`), and prefer a **systemd timer** for anything important — you get logging, dependency ordering, and `systemctl list-timers` for free.

---

## Time & Size Units

| Availability | Downtime/year | Downtime/month | Downtime/week |
|--------------|---------------|----------------|---------------|
| 99% ("two nines") | 3.65 days | 7.2 hours | 1.68 hours |
| 99.9% ("three nines") | 8.77 hours | 43.8 min | 10.1 min |
| **99.95%** | 4.38 hours | 21.9 min | 5.04 min |
| **99.99% ("four nines")** | 52.6 min | 4.38 min | 1.01 min |
| 99.999% ("five nines") | 5.26 min | 26.3 s | 6.05 s |

| Binary | Decimal | Note |
|--------|---------|------|
| 1 KiB = 1,024 B | 1 KB = 1,000 B | Kubernetes uses `Ki`/`Mi`/`Gi` (binary) |
| 1 MiB = 1,048,576 B | 1 MB = 1,000,000 B | Cloud storage is usually billed decimal |
| 1 GiB = 1,073,741,824 B | 1 GB = 1,000,000,000 B | A "1 TB" disk shows as ~931 GiB |

**Kubernetes CPU**: `1000m` = 1 core · `500m` = half a core · `100m` = 10% of a core.

---

## The Rules That Prevent Outages

| Rule | Why |
|------|-----|
| ⭐ **`kubectl config current-context` before anything destructive** | The right command in the wrong cluster is the worst outage |
| ⭐ **`aws sts get-caller-identity` before anything destructive** | Same, for cloud accounts |
| ⭐ **`terraform plan -out=tfplan`, then apply *that file*** | Guarantees you shipped what was reviewed |
| ⭐ **`kubectl diff -f` before `kubectl apply -f`** | Terraform's plan step, for Kubernetes |
| **Allow SSH before enabling any firewall** | The classic self-lockout |
| **`sudo sshd -t` before reloading sshd**, and keep the old session open | Test the config with an escape hatch available |
| **`nginx -t` before reloading nginx** | Same idea |
| **Build once, promote the same artifact** | Rebuilding between environments means you tested something else |
| **`--force-with-lease`, never bare `--force`** | Refuses to clobber someone else's push |
| **Commit early — `reflog` can only recover commits** | Uncommitted work is genuinely unrecoverable |
| **Quote every shell variable: `"$var"`** | Unquoted variables word-split and glob |
| **`set -Eeuo pipefail` at the top of every script** | Turns silent failures into loud ones |
| **Set memory limits on every container** | Unbounded containers take the node down with them |
| **Readiness probes gate traffic; liveness probes gate restarts** | A liveness probe that checks a database turns a blip into a total outage |
| **Rotate a leaked secret *first*, purge history second** | It's compromised the second it's pushed |
| **Set a cloud billing alarm on day one** | Free-tier accounts still generate four-figure bills |
| **Put log retention on every log group** | CloudWatch's default is *forever* |

---

<div align="center">

**[← Back to the Handbook](./README.md)** · [Per-module cheat sheets](#-quick-reference) · [Practical Learning Guide](./PRACTICAL-LEARNING.md)

</div>
