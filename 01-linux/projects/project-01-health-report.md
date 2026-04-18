<![CDATA[# Project: Linux Server Health Report Generator

## 🎯 Problem Statement

As a DevOps engineer, you need to quickly assess the health of a Linux server. Build an automated health report script that collects system metrics and generates a clean, readable report.

## 📐 Architecture

```
health_report.sh  →  Collects metrics  →  Generates report.txt
                  →  CPU, Memory, Disk, Network, Services
                  →  Flags warnings for any metric above threshold
```

## 🔧 Implementation

Create `health_report.sh`:

```bash
#!/bin/bash
#
# Linux Server Health Report Generator
# Usage: ./health_report.sh [output_file]
# 
# Generates a comprehensive server health report
#

set -euo pipefail

OUTPUT_FILE="${1:-/tmp/health_report_$(date +%Y%m%d_%H%M%S).txt}"
WARN_CPU=80
WARN_MEM=85
WARN_DISK=80

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    echo "================================================================"
    echo "  SERVER HEALTH REPORT"
    echo "  Hostname: $(hostname)"
    echo "  Generated: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo "  Uptime: $(uptime -p)"
    echo "================================================================"
    echo ""
}

check_cpu() {
    echo "📊 CPU INFORMATION"
    echo "──────────────────────────────────────"
    echo "  Model: $(grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)"
    echo "  Cores: $(nproc)"
    echo "  Load Average: $(cat /proc/loadavg | cut -d' ' -f1-3)"
    
    local load_1min=$(cat /proc/loadavg | cut -d' ' -f1)
    local cores=$(nproc)
    local load_pct=$(awk "BEGIN {printf \"%.0f\", ($load_1min / $cores) * 100}")
    
    if [ "$load_pct" -gt "$WARN_CPU" ]; then
        echo "  ⚠️  WARNING: CPU load at ${load_pct}% capacity!"
    else
        echo "  ✅ CPU load: ${load_pct}% capacity"
    fi
    echo ""
}

check_memory() {
    echo "🧠 MEMORY USAGE"
    echo "──────────────────────────────────────"
    free -h | awk '
    NR==1 {printf "  %-10s %10s %10s %10s %10s\n", "", $1, $2, $3, $6}
    NR==2 {printf "  %-10s %10s %10s %10s %10s\n", "RAM:", $2, $3, $4, $7}
    NR==3 {printf "  %-10s %10s %10s %10s\n", "Swap:", $2, $3, $4}'
    
    local mem_pct=$(free | awk 'NR==2 {printf "%.0f", ($3/$2)*100}')
    
    if [ "$mem_pct" -gt "$WARN_MEM" ]; then
        echo "  ⚠️  WARNING: Memory usage at ${mem_pct}%!"
    else
        echo "  ✅ Memory usage: ${mem_pct}%"
    fi
    echo ""
}

check_disk() {
    echo "💾 DISK USAGE"
    echo "──────────────────────────────────────"
    df -h --output=source,size,used,avail,pcent,target | grep -v "tmpfs\|devtmpfs\|udev" | head -10
    echo ""
    
    # Check for critical disk usage
    local warning_found=false
    while IFS= read -r line; do
        local usage=$(echo "$line" | awk '{print $5}' | tr -d '%')
        local mount=$(echo "$line" | awk '{print $6}')
        if [ "$usage" -gt "$WARN_DISK" ] 2>/dev/null; then
            echo "  ⚠️  WARNING: ${mount} is at ${usage}% usage!"
            warning_found=true
        fi
    done < <(df --output=source,size,used,avail,pcent,target | grep -v "tmpfs\|devtmpfs\|Filesystem\|udev")
    
    if [ "$warning_found" = false ]; then
        echo "  ✅ All disks within threshold"
    fi
    echo ""
}

check_network() {
    echo "🌐 NETWORK"
    echo "──────────────────────────────────────"
    echo "  IP Addresses:"
    ip -4 addr show | grep inet | grep -v 127.0.0.1 | awk '{print "    " $2 " on " $NF}'
    
    echo "  DNS Servers:"
    grep nameserver /etc/resolv.conf 2>/dev/null | awk '{print "    " $2}'
    
    echo "  Active Connections:"
    ss -s | head -5 | sed 's/^/    /'
    echo ""
}

check_services() {
    echo "⚙️  CRITICAL SERVICES"
    echo "──────────────────────────────────────"
    
    local services=("sshd" "nginx" "docker" "cron")
    for svc in "${services[@]}"; do
        if systemctl is-active "$svc" &>/dev/null; then
            echo "  ✅ ${svc}: running"
        elif systemctl list-unit-files "${svc}.service" &>/dev/null; then
            echo "  ❌ ${svc}: NOT running"
        else
            echo "  ⬜ ${svc}: not installed"
        fi
    done
    
    # Check for failed services
    local failed=$(systemctl list-units --state=failed --no-pager --no-legend 2>/dev/null | wc -l)
    if [ "$failed" -gt 0 ]; then
        echo ""
        echo "  ⚠️  ${failed} failed service(s):"
        systemctl list-units --state=failed --no-pager --no-legend | sed 's/^/    /'
    fi
    echo ""
}

check_security() {
    echo "🔐 SECURITY CHECKS"
    echo "──────────────────────────────────────"
    
    # Last 5 logins
    echo "  Last 5 logins:"
    last -5 -w 2>/dev/null | head -5 | sed 's/^/    /'
    
    # Failed login attempts (last 24 hours)
    if [ -f /var/log/auth.log ]; then
        local failed_logins=$(grep "Failed password" /var/log/auth.log 2>/dev/null | wc -l)
        echo "  Failed login attempts (auth.log): $failed_logins"
    fi
    
    # Check for users with UID 0 (root-level)
    local root_users=$(awk -F: '$3 == 0 {print $1}' /etc/passwd | wc -l)
    if [ "$root_users" -gt 1 ]; then
        echo "  ⚠️  WARNING: ${root_users} users with UID 0!"
    else
        echo "  ✅ Only root has UID 0"
    fi
    echo ""
}

top_processes() {
    echo "📈 TOP 5 PROCESSES BY CPU"
    echo "──────────────────────────────────────"
    ps aux --sort=-%cpu | head -6 | awk '{printf "  %-10s %5s %5s  %s\n", $1, $3"%", $4"%", $11}' 
    echo ""
    
    echo "📈 TOP 5 PROCESSES BY MEMORY"
    echo "──────────────────────────────────────"
    ps aux --sort=-%mem | head -6 | awk '{printf "  %-10s %5s %5s  %s\n", $1, $3"%", $4"%", $11}'
    echo ""
}

# Generate report
{
    print_header
    check_cpu
    check_memory
    check_disk
    check_network
    check_services
    check_security
    top_processes
    echo "================================================================"
    echo "  Report saved to: ${OUTPUT_FILE}"
    echo "================================================================"
} | tee "$OUTPUT_FILE"

echo ""
echo "Report saved to: ${OUTPUT_FILE}"
```

## 🔍 Expected Output

A clean report showing system status with warnings highlights:

```
================================================================
  SERVER HEALTH REPORT
  Hostname: web01
  Generated: 2024-01-15 10:30:00 UTC
  Uptime: up 42 days, 3 hours, 15 minutes
================================================================

📊 CPU INFORMATION
──────────────────────────────────────
  Model: Intel(R) Xeon(R) CPU @ 2.30GHz
  Cores: 4
  Load Average: 0.52 0.38 0.35
  ✅ CPU load: 13% capacity

🧠 MEMORY USAGE
──────────────────────────────────────
            total       used       free  available
  RAM:       7.8G       2.1G       3.5G       5.3G
  ✅ Memory usage: 27%
...
```

## 🧪 Debugging Scenarios

1. **What if disk usage > 90%?** → The script should flag it with ⚠️
2. **What if a critical service is down?** → Shows ❌ with service name
3. **What if there are failed login attempts?** → Shows the count

## ✅ Validation

- [ ] Script runs without errors
- [ ] Report shows all sections (CPU, Memory, Disk, Network, Services, Security)
- [ ] Warnings appear when thresholds are exceeded
- [ ] Report is saved to a file for later reference
- [ ] Script works on a fresh Ubuntu system

## 🚀 Extensions

- Add email notification for warnings
- Run via cron every hour
- Output as JSON for integration with monitoring tools
- Add historical comparison (compare to previous report)

---

[← Back to Module README](../README.md)
]]>
