#!/usr/bin/env bash
#
# The page. Run this to start the incident — it prints the alert exactly as an on-call
# tool would deliver it, and nothing else. Working out what is wrong is your job.
#
# Usage:  ./page.sh
#
set -euo pipefail

now() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

cat <<EOF

  ┌────────────────────────────────────────────────────────────────────┐
  │  PAGE — you are on call                                            │
  └────────────────────────────────────────────────────────────────────┘

  $(now)   [FIRING:1]  CheckoutErrorRateHigh

  alertname   CheckoutErrorRateHigh
  service     checkout-api
  severity    critical
  summary     5xx rate on /checkout is 71% (threshold 5%, for: 2m)
  runbook     docs/runbook.md#checkouterroratehigh   (does not exist yet — note that)
  dashboard   http://grafana.internal/d/checkout     (not available in this lab)

  Acknowledged at: $(now)

EOF

printf '  Start your clock. First status update is due within 5 minutes.\n\n'
printf '  Record this timestamp as T+0 in your timeline: %s\n\n' "$(now)"
