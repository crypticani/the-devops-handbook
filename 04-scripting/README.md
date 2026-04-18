# Module 04: Scripting (Bash + Python)

> *"A DevOps engineer who can't script is a DevOps engineer who does everything manually — twice."*

---

## 🎯 Why This Module Matters

Scripting is the **bridge between manual operations and full automation**. Before you learn Terraform, Ansible, or CI/CD pipelines, you need to be able to write scripts that automate repetitive tasks, process data, and glue systems together.

**In real-world DevOps work**, you will:
- Write deployment scripts that handle rollbacks
- Build health check and monitoring scripts
- Automate log rotation and cleanup
- Create backup and restore scripts
- Write glue code between different tools and APIs
- Build CLI tools for your team

### Why Both Bash AND Python?

| Use Bash When | Use Python When |
|--------------|----------------|
| Quick system tasks (file ops, service control) | Complex logic or data processing |
| Chaining Linux commands together | API interactions (REST calls) |
| Simple automation (under 100 lines) | Error handling is critical |
| Cron jobs and one-liners | Working with JSON/YAML/CSV |
| Anything that's mostly shell commands | Scripts others need to maintain |

---

## 📚 Table of Contents

### Part 1: Bash Scripting
1. [Bash Fundamentals](#1-bash-fundamentals)
2. [Variables and Data Types](#2-variables-and-data-types)
3. [Control Flow](#3-control-flow)
4. [Functions](#4-functions)
5. [Input and Arguments](#5-input-and-arguments)
6. [Text Processing in Scripts](#6-text-processing-in-scripts)
7. [Error Handling](#7-error-handling)

### Part 2: Python for DevOps
8. [Python Fundamentals for DevOps](#8-python-fundamentals-for-devops)
9. [Working with Files and Data](#9-working-with-files-and-data)
10. [API Interactions](#10-api-interactions)
11. [System Administration with Python](#11-system-administration-with-python)

### General
12. [Common Mistakes and Anti-Patterns](#12-common-mistakes-and-anti-patterns)
13. [Debugging Mindset](#13-debugging-mindset)
14. [Security Considerations](#14-security-considerations)
15. [Interview Insights](#15-interview-insights)

---

# Part 1: Bash Scripting

## 1. Bash Fundamentals

### Your First Script

```bash
#!/bin/bash
# The shebang (#!/bin/bash) tells the system which interpreter to use
# ALWAYS include it as the first line

# Script header
# Description: My first Bash script
# Author: DevOps Engineer
# Date: 2024-01-15

echo "Hello, DevOps!"
echo "Today is $(date)"
echo "You are logged in as: $(whoami)"
echo "Working directory: $(pwd)"
```

```bash
# Save, make executable, and run
chmod +x myscript.sh
./myscript.sh
```

### The Essential First Line

```bash
#!/bin/bash
set -euo pipefail

# set -e     → Exit immediately if ANY command fails
# set -u     → Treat unset variables as errors
# set -o pipefail → Pipeline fails if ANY command in the pipe fails

# Without these, your script will silently continue after errors
# This is the #1 source of bugs in Bash scripts
```

---

## 2. Variables and Data Types

```bash
#!/bin/bash
set -euo pipefail

# Variable assignment (NO spaces around =)
app_name="web-server"
port=8080
environment="production"

# Using variables (always quote to handle spaces)
echo "Deploying ${app_name} on port ${port}"

# Command substitution
current_date=$(date +%Y-%m-%d)
hostname=$(hostname)
ip_address=$(hostname -I | awk '{print $1}')

echo "Server: ${hostname} (${ip_address})"
echo "Date: ${current_date}"

# Read-only variables (constants)
readonly MAX_RETRIES=3
readonly LOG_DIR="/var/log/myapp"

# Default values (use if variable is not set)
deploy_env="${DEPLOY_ENV:-staging}"   # Use "staging" if DEPLOY_ENV is not set
echo "Deploying to: ${deploy_env}"

# Arrays
servers=("web01" "web02" "web03" "db01")
echo "First server: ${servers[0]}"
echo "All servers: ${servers[@]}"
echo "Number of servers: ${#servers[@]}"

# Loop through array
for server in "${servers[@]}"; do
    echo "Checking: ${server}"
done
```

---

## 3. Control Flow

### If/Else

```bash
#!/bin/bash
set -euo pipefail

# File checks
if [ -f "/etc/nginx/nginx.conf" ]; then
    echo "✅ Nginx config exists"
else
    echo "❌ Nginx config NOT found"
    exit 1
fi

# Directory check
if [ -d "/var/log/nginx" ]; then
    echo "✅ Log directory exists"
fi

# String comparison
environment="production"
if [ "${environment}" = "production" ]; then
    echo "⚠️  Running in PRODUCTION mode"
elif [ "${environment}" = "staging" ]; then
    echo "Running in staging mode"
else
    echo "Running in development mode"
fi

# Numeric comparison
disk_usage=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
if [ "${disk_usage}" -gt 80 ]; then
    echo "⚠️  WARNING: Disk usage is ${disk_usage}%"
elif [ "${disk_usage}" -gt 60 ]; then
    echo "📊 Disk usage is ${disk_usage}% — monitor closely"
else
    echo "✅ Disk usage is ${disk_usage}% — healthy"
fi

# Check if a command exists
if command -v docker &> /dev/null; then
    echo "✅ Docker is installed: $(docker --version)"
else
    echo "❌ Docker is NOT installed"
fi

# Check if a service is running
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx is running"
else
    echo "❌ Nginx is NOT running"
fi
```

### Comparison Operators

```bash
# String comparisons (use [ ] or [[ ]])
[ "$a" = "$b" ]     # Equal
[ "$a" != "$b" ]    # Not equal
[ -z "$a" ]         # Is empty
[ -n "$a" ]         # Is not empty

# Numeric comparisons (use -eq, -ne, -gt, -lt, -ge, -le)
[ "$a" -eq "$b" ]   # Equal
[ "$a" -gt "$b" ]   # Greater than
[ "$a" -lt "$b" ]   # Less than
[ "$a" -ge 10 ]     # Greater or equal

# File tests
[ -f "file" ]       # File exists and is regular file
[ -d "dir" ]        # Directory exists
[ -r "file" ]       # File is readable
[ -w "file" ]       # File is writable
[ -x "file" ]       # File is executable
[ -s "file" ]       # File is not empty
```

### Loops

```bash
#!/bin/bash
set -euo pipefail

# For loop — iterate over a list
servers=("web01" "web02" "web03")
for server in "${servers[@]}"; do
    echo "Deploying to ${server}..."
    # ssh ${server} "sudo systemctl restart myapp"  # Real deployment
done

# For loop — numeric range
for i in {1..5}; do
    echo "Attempt ${i} of 5"
done

# For loop — C-style
for ((i=0; i<3; i++)); do
    echo "Index: ${i}"
done

# For loop — files
for file in /var/log/*.log; do
    size=$(stat --format="%s" "${file}" 2>/dev/null || echo "0")
    echo "${file}: ${size} bytes"
done

# While loop — retry pattern (VERY common in DevOps)
max_retries=5
retry_count=0
until curl -sf http://localhost:8080/health > /dev/null 2>&1; do
    retry_count=$((retry_count + 1))
    if [ ${retry_count} -ge ${max_retries} ]; then
        echo "❌ Health check failed after ${max_retries} attempts"
        exit 1
    fi
    echo "⏳ Waiting for service... (attempt ${retry_count}/${max_retries})"
    sleep 5
done
echo "✅ Service is healthy!"
```

---

## 4. Functions

```bash
#!/bin/bash
set -euo pipefail

# Function definition
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2
}

log_warn() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*"
}

# Function with arguments
check_service() {
    local service_name="$1"
    if systemctl is-active --quiet "${service_name}" 2>/dev/null; then
        log_info "${service_name} is running ✅"
        return 0
    else
        log_error "${service_name} is NOT running ❌"
        return 1
    fi
}

# Function with return value
get_disk_usage() {
    local mount_point="${1:-/}"
    df "${mount_point}" | awk 'NR==2 {print $5}' | tr -d '%'
}

# Function with validation
deploy() {
    local app_name="$1"
    local version="${2:-latest}"
    local environment="${3:-staging}"

    if [ -z "${app_name}" ]; then
        log_error "App name is required"
        return 1
    fi

    log_info "Deploying ${app_name}:${version} to ${environment}"
    # Deployment logic here
    log_info "Deployment complete"
}

# Usage
log_info "Starting health checks"
check_service "nginx" || log_warn "Nginx needs attention"
check_service "docker" || log_warn "Docker needs attention"

usage=$(get_disk_usage "/")
log_info "Disk usage: ${usage}%"

deploy "web-app" "v2.1.0" "production"
```

---

## 5. Input and Arguments

```bash
#!/bin/bash
set -euo pipefail

# Script arguments
# $0 = script name
# $1, $2, ... = arguments
# $# = number of arguments
# $@ = all arguments as separate words
# $? = exit code of last command

# Usage function (always include this)
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] <environment>

Deploy application to the specified environment.

Options:
    -v, --version VERSION    App version to deploy (default: latest)
    -r, --rollback           Rollback to previous version
    -d, --dry-run            Show what would happen without doing it
    -h, --help               Show this help message

Environments:
    staging, production

Examples:
    $(basename "$0") staging
    $(basename "$0") -v 2.1.0 production
    $(basename "$0") --rollback production
EOF
    exit 1
}

# Parse arguments
VERSION="latest"
ROLLBACK=false
DRY_RUN=false
ENVIRONMENT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -r|--rollback)
            ROLLBACK=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            ;;
        *)
            ENVIRONMENT="$1"
            shift
            ;;
    esac
done

# Validate required arguments
if [ -z "${ENVIRONMENT}" ]; then
    echo "Error: Environment is required"
    usage
fi

if [[ "${ENVIRONMENT}" != "staging" && "${ENVIRONMENT}" != "production" ]]; then
    echo "Error: Invalid environment '${ENVIRONMENT}'"
    usage
fi

echo "Environment: ${ENVIRONMENT}"
echo "Version: ${VERSION}"
echo "Rollback: ${ROLLBACK}"
echo "Dry run: ${DRY_RUN}"
```

---

## 6. Text Processing in Scripts

```bash
#!/bin/bash
set -euo pipefail

# String operations
filename="backup-2024-01-15.tar.gz"

# Substring extraction
echo "${filename%.tar.gz}"          # backup-2024-01-15 (remove suffix)
echo "${filename##*-}"              # 15.tar.gz (remove everything before last -)
echo "${filename%%-*}"              # backup (remove everything from first -)

# String replacement
echo "${filename/2024/2025}"        # Replace first occurrence
echo "${filename//backup/archive}"  # Replace all occurrences

# String length
echo "${#filename}"                 # 28

# Uppercase/lowercase (Bash 4+)
echo "${filename^^}"                # BACKUP-2024-01-15.TAR.GZ
echo "${filename,,}"                # backup-2024-01-15.tar.gz

# Read a file line by line
while IFS= read -r line; do
    # Skip empty lines and comments
    [[ -z "${line}" || "${line}" =~ ^# ]] && continue
    echo "Processing: ${line}"
done < config.txt

# Process CSV data
echo "name,role,ip" > /tmp/servers.csv
echo "web01,frontend,10.0.1.10" >> /tmp/servers.csv
echo "web02,frontend,10.0.1.11" >> /tmp/servers.csv
echo "db01,database,10.0.2.10" >> /tmp/servers.csv

while IFS=',' read -r name role ip; do
    echo "Server: ${name} | Role: ${role} | IP: ${ip}"
done < <(tail -n +2 /tmp/servers.csv)  # Skip header
```

---

## 7. Error Handling

```bash
#!/bin/bash
set -euo pipefail

# Trap — run cleanup on exit (success or failure)
cleanup() {
    local exit_code=$?
    echo "Cleaning up temporary files..."
    rm -f /tmp/deploy_lock.pid
    if [ ${exit_code} -ne 0 ]; then
        echo "❌ Script failed with exit code: ${exit_code}"
        # Send alert, rollback, etc.
    fi
}
trap cleanup EXIT

# Trap specific signals
handle_interrupt() {
    echo ""
    echo "⚠️  Received interrupt signal. Cleaning up..."
    exit 1
}
trap handle_interrupt SIGINT SIGTERM

# Retry function (production pattern)
retry() {
    local max_attempts="$1"
    local delay="$2"
    shift 2
    local command=("$@")

    local attempt=1
    until "${command[@]}"; do
        if [ ${attempt} -ge ${max_attempts} ]; then
            echo "❌ Command failed after ${max_attempts} attempts: ${command[*]}"
            return 1
        fi
        echo "⏳ Attempt ${attempt}/${max_attempts} failed. Retrying in ${delay}s..."
        sleep "${delay}"
        attempt=$((attempt + 1))
    done
}

# Usage: retry 5 3 curl -sf http://localhost:8080/health
# Tries 5 times with 3-second delays

# Lock file pattern (prevent concurrent runs)
LOCK_FILE="/tmp/deploy_lock.pid"
if [ -f "${LOCK_FILE}" ]; then
    existing_pid=$(cat "${LOCK_FILE}")
    if kill -0 "${existing_pid}" 2>/dev/null; then
        echo "❌ Another deployment is running (PID: ${existing_pid})"
        exit 1
    fi
fi
echo $$ > "${LOCK_FILE}"
```

---

# Part 2: Python for DevOps

## 8. Python Fundamentals for DevOps

```python
#!/usr/bin/env python3
"""Python fundamentals for DevOps engineers"""

import os
import sys
import json
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Logging setup (always use logging, not print, in scripts)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Environment variables
env = os.getenv("ENVIRONMENT", "development")
port = int(os.getenv("PORT", "8080"))
logger.info(f"Running in {env} mode on port {port}")

# Running shell commands
def run_command(cmd, check=True):
    """Run a shell command and return the output"""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        check=check
    )
    return result.stdout.strip()

# Usage
hostname = run_command("hostname")
logger.info(f"Hostname: {hostname}")

# Dictionaries (used EVERYWHERE in DevOps — configs, API responses)
server_config = {
    "name": "web-01",
    "ip": "10.0.1.10",
    "port": 8080,
    "tags": ["web", "production", "us-east-1"],
    "health_check": {
        "path": "/health",
        "interval": 30,
        "timeout": 5
    }
}

# Access nested values
health_path = server_config["health_check"]["path"]
is_production = "production" in server_config["tags"]

# List comprehensions (concise data transformation)
servers = ["web01", "web02", "web03", "db01", "db02"]
web_servers = [s for s in servers if s.startswith("web")]
# Result: ["web01", "web02", "web03"]
```

---

## 9. Working with Files and Data

```python
#!/usr/bin/env python3
"""Working with files, JSON, and YAML in DevOps scripts"""

import json
import yaml  # pip install pyyaml
from pathlib import Path

# JSON (API responses, configs, Terraform state)
config = {
    "app": "web-server",
    "version": "2.1.0",
    "instances": 3,
    "regions": ["us-east-1", "eu-west-1"]
}

# Write JSON
with open("config.json", "w") as f:
    json.dump(config, f, indent=2)

# Read JSON
with open("config.json", "r") as f:
    loaded = json.load(f)
    print(f"App: {loaded['app']}, Version: {loaded['version']}")

# YAML (Kubernetes manifests, Ansible playbooks, Docker Compose)
k8s_deployment = {
    "apiVersion": "apps/v1",
    "kind": "Deployment",
    "metadata": {"name": "web-app", "namespace": "production"},
    "spec": {
        "replicas": 3,
        "selector": {"matchLabels": {"app": "web-app"}},
    }
}

# Write YAML
with open("deployment.yaml", "w") as f:
    yaml.dump(k8s_deployment, f, default_flow_style=False)

# Read YAML
with open("deployment.yaml", "r") as f:
    loaded = yaml.safe_load(f)
    print(f"Deploying: {loaded['metadata']['name']}")

# File operations with pathlib
log_dir = Path("/var/log/myapp")
log_files = list(log_dir.glob("*.log")) if log_dir.exists() else []

for log_file in sorted(log_files):
    size_mb = log_file.stat().st_size / (1024 * 1024)
    print(f"{log_file.name}: {size_mb:.1f} MB")
```

---

## 10. API Interactions

```python
#!/usr/bin/env python3
"""Interacting with APIs — essential for DevOps automation"""

import requests  # pip install requests
import json

# GET request (monitoring, health checks)
def check_service_health(url, timeout=5):
    """Check if a service is healthy"""
    try:
        response = requests.get(url, timeout=timeout)
        return {
            "healthy": response.status_code == 200,
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds()
        }
    except requests.exceptions.Timeout:
        return {"healthy": False, "error": "timeout"}
    except requests.exceptions.ConnectionError:
        return {"healthy": False, "error": "connection_refused"}

# Usage
result = check_service_health("http://localhost:8080/health")
print(json.dumps(result, indent=2))

# POST request (creating resources, triggering deployments)
def trigger_deployment(api_url, app_name, version, token):
    """Trigger a deployment via API"""
    response = requests.post(
        f"{api_url}/deployments",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "application": app_name,
            "version": version,
            "environment": "production"
        },
        timeout=30
    )
    response.raise_for_status()  # Raises exception for 4xx/5xx
    return response.json()

# GitHub API example — list open PRs
def get_open_prs(repo, token):
    """Get open pull requests for a GitHub repo"""
    response = requests.get(
        f"https://api.github.com/repos/{repo}/pulls",
        headers={"Authorization": f"token {token}"},
        params={"state": "open"}
    )
    response.raise_for_status()
    prs = response.json()
    for pr in prs:
        print(f"#{pr['number']}: {pr['title']} (by {pr['user']['login']})")
    return prs
```

---

## 11. System Administration with Python

```python
#!/usr/bin/env python3
"""System administration tasks with Python"""

import os
import shutil
import psutil  # pip install psutil
from datetime import datetime

def get_system_info():
    """Gather system health information"""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "used_percent": psutil.virtual_memory().percent,
            "available_gb": round(psutil.virtual_memory().available / (1024**3), 1)
        },
        "disk": {
            "total_gb": round(psutil.disk_usage('/').total / (1024**3), 1),
            "used_percent": psutil.disk_usage('/').percent
        },
        "network_connections": len(psutil.net_connections()),
        "process_count": len(psutil.pids()),
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
    }

def find_large_files(directory, min_size_mb=100):
    """Find files larger than specified size"""
    large_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                size = os.path.getsize(filepath)
                if size > min_size_mb * 1024 * 1024:
                    large_files.append({
                        "path": filepath,
                        "size_mb": round(size / (1024 * 1024), 1)
                    })
            except (OSError, PermissionError):
                continue
    return sorted(large_files, key=lambda x: x["size_mb"], reverse=True)

def cleanup_old_logs(log_dir, max_age_days=30):
    """Delete log files older than max_age_days"""
    deleted = []
    now = datetime.now()
    for filepath in Path(log_dir).glob("*.log*"):
        file_age = now - datetime.fromtimestamp(filepath.stat().st_mtime)
        if file_age.days > max_age_days:
            filepath.unlink()
            deleted.append(str(filepath))
    return deleted

# Usage
if __name__ == "__main__":
    import json
    info = get_system_info()
    print(json.dumps(info, indent=2))
```

---

## 12. Common Mistakes and Anti-Patterns

### ❌ Not Using `set -euo pipefail` in Bash

```bash
# BAD: Script continues after errors
rm /some/file/that/doesnt/exist
echo "This still runs even though rm failed!"

# GOOD:
set -euo pipefail
rm /some/file/that/doesnt/exist
echo "This never runs — script exits on error"
```

### ❌ Not Quoting Variables in Bash

```bash
# BAD: Breaks with spaces in values
filename=$1
rm $filename       # If filename is "my file.txt", this deletes "my" and "file.txt"

# GOOD
filename="$1"
rm "${filename}"   # Correctly handles spaces
```

### ❌ Using `print()` Instead of `logging` in Python

```python
# BAD
print("Starting deployment")
print("ERROR: something failed")

# GOOD
import logging
logger = logging.getLogger(__name__)
logger.info("Starting deployment")
logger.error("Something failed")
# Logging gives you: timestamps, levels, file output, filtering
```

---

## 13. Debugging Mindset

### Bash Debugging

```bash
# Trace execution (shows every command as it runs)
bash -x script.sh

# Or add to your script temporarily
set -x    # Enable tracing
# ... code to debug ...
set +x    # Disable tracing

# Debug print (with stderr so it doesn't interfere with output)
echo "DEBUG: variable=${variable}" >&2
```

### Python Debugging

```python
# Quick debug
import pdb; pdb.set_trace()  # Drops into interactive debugger

# Better: Use structured logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug(f"Processing server: {server_name}")
```

---

## 14. Security Considerations

> 🔐 Scripts are common attack vectors. Handle them carefully.

- **Never hardcode secrets** — use environment variables or secret managers
- **Validate all input** — especially in scripts that run as root
- **Use `set -euo pipefail`** — prevent silent failures
- **Don't use `eval`** — it executes arbitrary code
- **Set proper permissions** — `chmod 700` for scripts with secrets
- **Use `shellcheck`** to lint Bash scripts: `shellcheck myscript.sh`

---

## 15. Interview Insights

**Q: Write a script to check if a service is running and restart it if not.**
```bash
#!/bin/bash
set -euo pipefail
SERVICE="$1"
if ! systemctl is-active --quiet "${SERVICE}"; then
    echo "$(date): ${SERVICE} is down, restarting..."
    sudo systemctl restart "${SERVICE}"
    sleep 5
    if systemctl is-active --quiet "${SERVICE}"; then
        echo "$(date): ${SERVICE} restarted successfully"
    else
        echo "$(date): FAILED to restart ${SERVICE}" >&2
        exit 1
    fi
else
    echo "$(date): ${SERVICE} is running"
fi
```

**Q: What does `set -euo pipefail` do?**
> `-e` exits on any error, `-u` treats unset variables as errors, `-o pipefail` catches errors in piped commands. Together they prevent silent failures — the #1 source of bugs in bash scripts.

**Q: When would you use Python over Bash?**
> Python for: complex logic, API interactions, JSON/YAML processing, error handling, scripts that need to be maintainable. Bash for: quick system tasks, chaining commands, simple automation, cron jobs, anything under ~50 lines.

---

## ➡️ What's Next?

You can now automate tasks. Next, we containerize applications with Docker — the foundation of modern deployment.

**[Module 05: Containers & Docker →](../05-containers-docker/)**

---

<div align="center">

**Module 04 Complete** ✅

[← Back to Git](../03-git/) | [Next: Docker →](../05-containers-docker/)

</div>
