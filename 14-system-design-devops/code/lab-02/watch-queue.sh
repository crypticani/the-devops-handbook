#!/usr/bin/env bash
#
# The four numbers that tell you whether a queue is healthy. Run it in a second terminal
# and leave it there — every scenario in this lab is visible in this output.
#
#   messages          ready + unacknowledged: the backlog
#   unacked           handed to a consumer, not yet acknowledged (in-flight work)
#   consumers         ⭐ zero here with messages waiting is the silent outage
#   dlq               anything above zero is work nobody is doing
#
# Usage:  ./watch-queue.sh [interval_seconds]
#
set -euo pipefail

INTERVAL="${1:-2}"
CONTAINER="${MQ_CONTAINER:-mq}"

q() { docker exec "$CONTAINER" rabbitmqctl list_queues --quiet --formatter table \
        name messages messages_unacknowledged consumers 2>/dev/null; }

printf '%-10s %10s %10s %10s %10s\n' TIME ORDERS UNACKED CONSUMERS DLQ
while true; do
  out=$(q) || { printf 'broker unreachable\n'; sleep "$INTERVAL"; continue; }

  read -r orders unacked consumers <<<"$(awk '$1=="orders"{print $2, $3, $4}' <<<"$out")"
  dlq=$(awk '$1=="orders.dlq"{print $2}' <<<"$out")

  printf '%-10s %10s %10s %10s %10s\n' \
    "$(date -u +%H:%M:%S)" "${orders:-0}" "${unacked:-0}" "${consumers:-0}" "${dlq:-0}"

  sleep "$INTERVAL"
done
