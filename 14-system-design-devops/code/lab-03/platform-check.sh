#!/usr/bin/env bash
#
# The policy gate. Everything the platform promises, verified — because a default that
# nobody checks is a suggestion, and services drift the moment someone edits a manifest.
#
# Run it on one service or on all of them. CI runs the same script, which is the point.
#
# Usage:  ./platform-check.sh [path ...]      (default: every service under ../services)
#
set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1

PLATFORM_VERSION="$(cat PLATFORM-VERSION)"
FAILED=0
CHECKED=0
DRIFTED=()

red=$'\033[31m'; grn=$'\033[32m'; yel=$'\033[33m'; dim=$'\033[2m'; off=$'\033[0m'

ok()   { printf '    %s✅%s %s\n' "$grn" "$off" "$1"; }
bad()  { printf '    %s❌%s %s\n' "$red" "$off" "$1"; FAILED=1; }
warn() { printf '    %s⚠️ %s %s\n' "$yel" "$off" "$1"; }

need() {  # need <file> <pattern> <description>
  if grep -qE "$2" "$1" 2>/dev/null; then ok "$3"; else bad "$3"; fi
}

check_service() {
  local dir="$1" name
  name="$(basename "$dir")"
  printf '\n%s══ %s %s\n' "$dim" "$name" "$off"
  CHECKED=$((CHECKED + 1))

  # ── Ownership: without this, an incident has no one to page
  if [[ -f "$dir/service.yaml" ]]; then
    need "$dir/service.yaml" '^owner: +[a-z].*'   'has an owner'
    need "$dir/service.yaml" '^tier: +[123]'      'has a tier'
  else
    bad 'has a catalogue entry (service.yaml)'
  fi

  # ── Reliability defaults
  local d="$dir/k8s/deployment.yml"
  if [[ -f "$d" ]]; then
    need "$d" 'livenessProbe'                  'liveness probe'
    need "$d" 'readinessProbe'                 'readiness probe'
    need "$d" 'requests:'                      'resource requests'
    need "$d" 'limits:'                        'resource limits'
    need "$d" 'runAsNonRoot: +true'            'runs as non-root'
    need "$d" 'allowPrivilegeEscalation: +false' 'no privilege escalation'
    if grep -qE 'image: .*:latest' "$d"; then bad 'image is not :latest'; else ok 'image is not :latest'; fi
  else
    bad "has k8s/deployment.yml"
  fi

  # ── Observability
  [[ -f "$dir/monitoring/alerts.yml" ]] && ok 'has alert rules' || bad 'has alert rules'
  need "$dir/app/app.py" '/metrics'            'exposes /metrics'
  need "$dir/app/app.py" '/readyz'             'exposes /readyz'

  # ── Delivery
  [[ -f "$dir/.github/workflows/ci.yml" ]] && ok 'has a pipeline' || bad 'has a pipeline'

  # ── Template drift: is this service still on the current platform version?
  local v
  v="$(grep -oP '(?<=^platform-version: ).*' "$dir/service.yaml" 2>/dev/null || echo unknown)"
  if [[ "$v" == "$PLATFORM_VERSION" ]]; then
    ok "on platform version $v"
  else
    warn "platform version $v, current is $PLATFORM_VERSION — drifted"
    DRIFTED+=("$name ($v)")
  fi
}

targets=("$@")
if [[ ${#targets[@]} -eq 0 ]]; then
  mapfile -t targets < <(find services -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort)
fi
[[ ${#targets[@]} -eq 0 ]] && { echo "no services found — run ./new-service.sh first"; exit 0; }

for t in "${targets[@]}"; do check_service "$t"; done

printf '\n%s────────────────────────────────────────%s\n' "$dim" "$off"
printf 'checked: %d service(s)\n' "$CHECKED"
# ⭐ Adoption and drift are the platform's own metrics. A platform team that doesn't
# measure them builds what's interesting instead of what's needed.
printf 'on current template (%s): %d/%d\n' "$PLATFORM_VERSION" "$((CHECKED - ${#DRIFTED[@]}))" "$CHECKED"
[[ ${#DRIFTED[@]} -gt 0 ]] && printf 'drifted: %s\n' "${DRIFTED[*]}"

if [[ $FAILED -eq 0 ]]; then
  printf '%s✅ every service meets the platform contract%s\n' "$grn" "$off"
else
  printf '%s❌ policy violations above%s\n' "$red" "$off"
fi
exit $FAILED
