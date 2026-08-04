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
