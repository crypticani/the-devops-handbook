# Lab 01: Bash Scripting for DevOps

## 🎯 Objective

Write production-grade Bash scripts for real DevOps tasks — deployment, health checking, log rotation, and system monitoring.

---

## 📋 Prerequisites

- Bash shell (Linux/WSL2/macOS)
- ShellCheck installed: `sudo apt install -y shellcheck` on Debian/Ubuntu or `sudo dnf install -y ShellCheck` on RHEL-compatible systems

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Commands you ran and the important output you used for validation
- Any files, scripts, configs, manifests, or workflows you created
- A short failure note describing one thing that broke, how you diagnosed it, and how you fixed it
- Cleanup commands or confirmation that no long-running resources remain

Treat the validation section as the minimum proof that the lab worked.

---

## 📂 Lab Files

Every file this lab creates also exists as a real, CI-validated file in
[`../code/lab-01/`](../code/lab-01/) (2 files).

```bash
# Option A — type them out yourself (recommended the first time; that's the learning)
# Option B — start from the reference copies
cp -r /path/to/the-devops-handbook/04-scripting/code/lab-01/. .
```

Use Option B when you're comparing against a known-good version, or when something
won't start and you need to rule out a typo. See [`../code/README.md`](../code/README.md).

---

## 🔬 Exercise 1: Build a Deployment Script

### The Script

```bash
mkdir -p ~/devops-labs/module-04/scripts
cd ~/devops-labs/module-04/scripts

cat > deploy.sh << 'DEPLOY'
#!/bin/bash
set -euo pipefail

#
# Deployment Script
# Usage: ./deploy.sh -a <app_name> -v <version> -e <environment>
#

# ═══════════════════════════════════════
# Configuration
# ═══════════════════════════════════════
readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly LOG_FILE="/tmp/deploy_$(date +%Y%m%d_%H%M%S).log"
readonly LOCK_FILE="/tmp/deploy.lock"

# ═══════════════════════════════════════
# Logging Functions
# ═══════════════════════════════════════
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$1] $2" | tee -a "${LOG_FILE}"; }
info()  { log "INFO"  "$1"; }
warn()  { log "WARN"  "$1"; }
error() { log "ERROR" "$1" >&2; }

# ═══════════════════════════════════════
# Cleanup
# ═══════════════════════════════════════
cleanup() {
    local exit_code=$?
    rm -f "${LOCK_FILE}"
    if [ ${exit_code} -ne 0 ]; then
        error "Deployment FAILED! Check log: ${LOG_FILE}"
    fi
}
trap cleanup EXIT

# ═══════════════════════════════════════
# Usage
# ═══════════════════════════════════════
usage() {
    cat << EOF
Usage: $(basename "$0") -a APP -v VERSION -e ENV [OPTIONS]

Required:
    -a, --app          Application name
    -v, --version      Version to deploy
    -e, --env          Environment (staging|production)

Options:
    -d, --dry-run      Show what would happen
    -h, --help         Show this help
EOF
    exit 1
}

# ═══════════════════════════════════════
# Parse Arguments
# ═══════════════════════════════════════
APP=""
VERSION=""
ENV=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -a|--app)     APP="$2"; shift 2 ;;
        -v|--version) VERSION="$2"; shift 2 ;;
        -e|--env)     ENV="$2"; shift 2 ;;
        -d|--dry-run) DRY_RUN=true; shift ;;
        -h|--help)    usage ;;
        *)            error "Unknown option: $1"; usage ;;
    esac
done

# Validate
[[ -z "${APP}" ]] && { error "App name required"; usage; }
[[ -z "${VERSION}" ]] && { error "Version required"; usage; }
[[ -z "${ENV}" ]] && { error "Environment required"; usage; }
[[ "${ENV}" != "staging" && "${ENV}" != "production" ]] && { error "Invalid environment: ${ENV}"; usage; }

# ═══════════════════════════════════════
# Lock Check
# ═══════════════════════════════════════
if [ -f "${LOCK_FILE}" ]; then
    error "Another deployment is in progress!"
    exit 1
fi
echo $$ > "${LOCK_FILE}"

# ═══════════════════════════════════════
# Deployment Steps
# ═══════════════════════════════════════
info "═══════════════════════════════════════"
info "Deploying ${APP}:${VERSION} → ${ENV}"
info "═══════════════════════════════════════"

# Step 1: Pre-flight checks
info "Step 1: Running pre-flight checks..."
if [ "${DRY_RUN}" = true ]; then
    info "[DRY RUN] Would check disk space, service status, etc."
else
    disk_usage=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
    if [ "${disk_usage}" -gt 90 ]; then
        error "Disk usage is ${disk_usage}% — too high for deployment!"
        exit 1
    fi
    info "Disk usage: ${disk_usage}% ✅"
fi

# Step 2: Backup current version
info "Step 2: Creating backup..."
if [ "${DRY_RUN}" = true ]; then
    info "[DRY RUN] Would backup current version"
else
    info "Backup created ✅"
fi

# Step 3: Deploy
info "Step 3: Deploying ${APP}:${VERSION}..."
if [ "${DRY_RUN}" = true ]; then
    info "[DRY RUN] Would pull and start ${APP}:${VERSION}"
else
    sleep 2  # Simulate deployment
    info "Application deployed ✅"
fi

# Step 4: Health check
info "Step 4: Running health check..."
if [ "${DRY_RUN}" = true ]; then
    info "[DRY RUN] Would check http://localhost:8080/health"
else
    info "Health check passed ✅"
fi

# Summary
info "═══════════════════════════════════════"
info "✅ Deployment complete!"
info "   App:         ${APP}"
info "   Version:     ${VERSION}"
info "   Environment: ${ENV}"
info "   Log:         ${LOG_FILE}"
info "═══════════════════════════════════════"
DEPLOY

chmod +x deploy.sh

# Run it
./deploy.sh --app web-server --version v2.1.0 --env staging
echo ""
./deploy.sh --app web-server --version v2.1.0 --env production --dry-run
```

### Validate with ShellCheck

```bash
shellcheck deploy.sh
# Should report 0 errors if written correctly
# ShellCheck catches: unquoted variables, missing set -e, useless cats, etc.
```

---

## 🔬 Exercise 2: Build a Service Health Monitor

```bash
cat > health_monitor.sh << 'HEALTHMON'
#!/bin/bash
set -euo pipefail

# Monitor multiple services and report status

SERVICES=(
    "http://localhost:80|Nginx"
    "http://localhost:8080|Application"
)

check_http() {
    local url="$1"
    local name="$2"

    local start_time=$(date +%s%N)
    local status_code
    status_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 --max-time 5 "${url}" 2>/dev/null || echo "000")
    local end_time=$(date +%s%N)
    local duration=$(( (end_time - start_time) / 1000000 ))

    if [ "${status_code}" = "200" ]; then
        echo "✅ ${name}: UP (HTTP ${status_code}, ${duration}ms)"
        return 0
    else
        echo "❌ ${name}: DOWN (HTTP ${status_code}, ${duration}ms)"
        return 1
    fi
}

echo "═══════════════════════════════════════"
echo "  Service Health Check — $(date)"
echo "═══════════════════════════════════════"

failures=0
for service_entry in "${SERVICES[@]}"; do
    IFS='|' read -r url name <<< "${service_entry}"
    check_http "${url}" "${name}" || failures=$((failures + 1))
done

echo "───────────────────────────────────────"
if [ ${failures} -gt 0 ]; then
    echo "⚠️  ${failures} service(s) are DOWN"
    exit 1
else
    echo "✅ All services are healthy"
fi
HEALTHMON

chmod +x health_monitor.sh
./health_monitor.sh
```

---

## 🧨 Break It: Four Ways a "Working" Script Fails in Production

Every one of these scripts passes a happy-path test. Each scenario below is a real failure mode that only appears later — usually at 3am, inside cron or CI.

### Scenario 1: The Stale Lock File

**Break it:**

```bash
cd ~/devops-labs/module-04/scripts

# Simulate a deployment that was killed mid-run (power loss, OOM, Ctrl-C on a
# machine where the trap didn't fire — e.g. SIGKILL)
echo 99999 > /tmp/deploy.lock

./deploy.sh -a myapp -v 1.0.0 -e staging
```

**Symptom:** `Another deployment is in progress!` — forever. No deployment can ever run again.

**Investigate:**

```bash
cat /tmp/deploy.lock                 # 99999 — is that PID alive?
ps -p "$(cat /tmp/deploy.lock)" || echo "PID is dead — the lock is STALE"
```

**Root cause:** The lock is a plain file with no liveness check. `trap cleanup EXIT` removes it on a normal exit and on SIGTERM, but **SIGKILL cannot be trapped** — the file survives the process that owned it.

**Fix — validate the lock holder, or use a kernel-backed lock:**

```bash
# Option A: check that the recorded PID is still alive
if [ -f "${LOCK_FILE}" ]; then
    lock_pid=$(cat "${LOCK_FILE}" 2>/dev/null || echo "")
    if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
        error "Deployment already running (PID ${lock_pid})"; exit 1
    else
        warn "Removing stale lock from dead PID ${lock_pid:-unknown}"
        rm -f "${LOCK_FILE}"
    fi
fi

# Option B — better: let the kernel hold the lock. It is released
# automatically when the process dies, however it dies.
exec 200>/var/lock/deploy.lock
flock -n 200 || die "another deployment is already running"
```

```bash
rm -f /tmp/deploy.lock          # clean up before continuing
```

---

### Scenario 2: `set -e` Doesn't Catch What You Think

**Break it:**

```bash
cat > trap-test.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

check_disk() {
    df / | awk 'NR==2 {print $5}' | tr -d '%'
}

# Looks safe. Isn't.
usage=$(check_disk)
if [ "$usage" -gt 90 ]; then echo "too full"; fi

# Now the trap: a failing command inside an if-condition
if grep -q "nonexistent-pattern" /etc/hostname; then
    echo "found"
fi
echo "STILL RUNNING — set -e did not stop us"

# And the real killer:
result=$(false | wc -l)      # pipefail? the ASSIGNMENT masks the exit status
echo "STILL RUNNING after a failed pipeline: result=$result"
EOF
chmod +x trap-test.sh && ./trap-test.sh
```

**Symptom:** The script keeps going after commands that failed. In a deploy script, this means step 4 runs even though step 3 never succeeded — you ship a half-applied change and the script exits 0.

**Investigate:**

```bash
bash -x ./trap-test.sh 2>&1 | tail -20      # watch each command and its result
```

**Root cause:** `set -e` is deliberately suppressed in three places: inside `if`/`while` conditions, on the left of `&&`/`||`, and for any command whose status is being *tested*. Separately, `local x=$(cmd)` and `x=$(cmd)` where the assignment is the whole statement can mask the inner exit status.

**Fix — check explicitly where correctness matters:**

```bash
# Separate declaration from assignment so the status isn't swallowed
local usage
usage=$(check_disk) || die "could not read disk usage"

# Check a pipeline's stages when it matters
cmd1 | cmd2 | cmd3
[[ "${PIPESTATUS[*]}" == "0 0 0" ]] || die "pipeline failed: ${PIPESTATUS[*]}"
```

---

### Scenario 3: It Works in Your Shell, Not in Cron

**Break it:**

```bash
# Simulate cron's environment: no PATH, no profile, no HOME assumptions
env -i /bin/bash --noprofile --norc ~/devops-labs/module-04/scripts/health_monitor.sh
```

**Symptom:** `curl: command not found`, or the script exits instantly with no output at all.

**Investigate:**

```bash
env -i /bin/bash --noprofile --norc -c 'echo "PATH=[$PATH]"'
# PATH=[/usr/bin:/bin]  — or empty. Your ~/.bashrc additions are gone.

command -v curl                      # /usr/bin/curl — fine in YOUR shell
```

**Root cause:** Cron runs with a nearly empty environment. Anything you rely on from `~/.bashrc`, `~/.profile`, a version manager (`nvm`, `pyenv`, `rbenv`), or a custom `PATH` does not exist.

**Fix:**

```bash
# At the top of the script
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# In the crontab, set the environment explicitly and capture BOTH streams
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
MAILTO=ops@example.com
*/5 * * * * /home/user/devops-labs/module-04/scripts/health_monitor.sh >> /var/log/health.log 2>&1
```

Re-test with `env -i` until it passes. That's the only honest cron test.

---

### Scenario 4: The Unquoted Variable

**Break it:**

```bash
mkdir -p /tmp/breaklab && cd /tmp/breaklab
touch "my report.txt" "notes.txt"

cat > cleanup.sh <<'EOF'
#!/usr/bin/env bash
TARGET_DIR="/tmp/breaklab"
FILE="my report.txt"

# Unquoted — bash word-splits on the space
for f in $(ls $TARGET_DIR); do
    echo "would process: $f"
done

echo "---"
rm -v $FILE 2>&1 || true
EOF
chmod +x cleanup.sh && ./cleanup.sh
```

**Symptom:** The loop prints `my`, `report.txt`, `notes.txt` — three items where there are two files. `rm` reports it cannot find `my` or `report.txt`.

**Investigate:**

```bash
bash -x ./cleanup.sh 2>&1 | grep '^+ rm'      # see the expansion the shell actually built
shellcheck cleanup.sh                          # SC2086, SC2045 — it tells you exactly this
```

**Root cause:** Unquoted expansion is split on `$IFS` (space, tab, newline by default) and then glob-expanded. A filename with a space becomes two arguments. Worse, an **unset** variable expands to nothing: `rm -rf $TARGET_DIR/` becomes `rm -rf /`.

**Fix:**

```bash
for f in "$TARGET_DIR"/*; do          # glob, don't parse ls
    [[ -e "$f" ]] || continue         # guard the no-match case
    echo "would process: $f"
done

rm -v -- "$FILE"                      # quote, and use -- to stop leading-dash names
rm -rf -- "${TARGET_DIR:?TARGET_DIR must be set}"   # ⭐ refuses to run if unset/empty
```

```bash
cd ~ && rm -rf /tmp/breaklab          # clean up
```

---

### Prevention Checklist

Run this against both of your scripts before you call them done:

```bash
cd ~/devops-labs/module-04/scripts
shellcheck deploy.sh health_monitor.sh          # must be clean
bash -n deploy.sh                                # syntax only
env -i /bin/bash --noprofile --norc ./health_monitor.sh   # cron simulation
```

| Failure mode | Guard |
|--------------|-------|
| Stale lock | `flock`, or verify the PID with `kill -0` |
| `set -e` gap | Separate declaration from assignment; check `PIPESTATUS` |
| Empty environment | Absolute paths, explicit `PATH`, test with `env -i` |
| Unquoted variable | Quote everything; `${VAR:?}` on anything you pass to `rm` |
| Silent failure | `set -Eeuo pipefail` **plus** `trap ... ERR` |

**Write this up** in `failure-notes.md` — one paragraph per scenario: symptom, how you found it, root cause, fix.

---

## ✅ Validation

- [ ] Deploy script runs without ShellCheck warnings
- [ ] Deploy script validates arguments and shows usage
- [ ] Deploy script uses a lock file to prevent concurrent runs
- [ ] Health monitor checks multiple services and reports status
- [ ] All scripts use `set -euo pipefail`
- [ ] All scripts include cleanup traps


## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- Deployment script with argument validation and locking
- Health monitor script with multi-service checks
- ShellCheck output showing clean results
- Notes on error handling patterns you used (traps, set -euo pipefail)

---

[← Back to Module README](../README.md) | [Next Lab: Python Automation →](./lab-02-python-automation.md)
