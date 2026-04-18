# Lab 01: Bash Scripting for DevOps

## 🎯 Objective

Write production-grade Bash scripts for real DevOps tasks — deployment, health checking, log rotation, and system monitoring.

---

## 📋 Prerequisites

- Bash shell (Linux/WSL2/macOS)
- ShellCheck installed: `sudo apt install -y shellcheck`

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

## ✅ Validation

- [ ] Deploy script runs without ShellCheck warnings
- [ ] Deploy script validates arguments and shows usage
- [ ] Deploy script uses a lock file to prevent concurrent runs
- [ ] Health monitor checks multiple services and reports status
- [ ] All scripts use `set -euo pipefail`
- [ ] All scripts include cleanup traps

---

[← Back to Module README](../README.md) | [Next Lab: Python Automation →](./lab-02-python-automation.md)
