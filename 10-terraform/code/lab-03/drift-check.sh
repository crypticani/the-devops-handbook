#!/usr/bin/env bash
# Run on a schedule. Alerts when reality has diverged from code.
# Exit 0 = all clean, 1 = drift or error in at least one environment.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
STATUS=0
for env in environments/*/; do
  name=$(basename "$env")
  ( cd "$env" && terraform init -backend-config=backend.hcl -input=false >/dev/null 2>&1 )
  ( cd "$env" && terraform plan -detailed-exitcode -input=false -lock-timeout=5m >/dev/null 2>&1 )
  case $? in
    0) echo "✅ $name: no drift" ;;
    2) echo "⚠️  $name: DRIFT DETECTED"; STATUS=1
       ( cd "$env" && terraform plan -no-color -input=false 2>/dev/null | grep -E '^\s+[~+-]' | head -20 ) ;;
    *) echo "❌ $name: plan failed"; STATUS=1 ;;
  esac
done
exit $STATUS
