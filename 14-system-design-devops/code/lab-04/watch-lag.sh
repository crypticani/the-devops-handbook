#!/usr/bin/env bash
#
# Per-partition consumer lag — the Kafka equivalent of "queue depth", except it is one
# number per partition and that is the whole point. Run it in a second terminal and leave
# it there; every scenario in this lab is visible in this output.
#
#   CURRENT   last committed offset for the group on that partition
#   END       last offset the producer has written
#   LAG       END - CURRENT: records committed by nobody yet
#   OWNER     which consumer holds the partition; "-" means nobody does
#
# Read it two ways: TOTAL lag answers "are we keeping up?", and the spread across
# partitions answers "is the work shared?" — a single hot partition and an evicted
# consumer both show a healthy total until you look per partition.
#
# Usage:  ./watch-lag.sh [interval_seconds]
#
set -euo pipefail

INTERVAL="${1:-3}"
CONTAINER="${KAFKA_CONTAINER:-kafka}"
GROUP="${GROUP:-orders}"

describe() {
  docker exec "$CONTAINER" /opt/kafka/bin/kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 --describe --group "$GROUP" 2>/dev/null
}

printf '%-10s %9s %9s %9s %7s  %s\n' TIME PARTITION CURRENT END LAG OWNER
while true; do
  if ! out=$(describe); then
    printf 'broker unreachable\n'
    sleep "$INTERVAL"
    continue
  fi

  # Columns: GROUP TOPIC PARTITION CURRENT-OFFSET LOG-END-OFFSET LAG CONSUMER-ID ...
  awk -v t="$(date -u +%H:%M:%S)" '
    $3 ~ /^[0-9]+$/ {
      cur += ($4 == "-" ? 0 : $4); end += $5; lag += ($6 == "-" ? 0 : $6)
      owner = ($7 == "" ? "-" : $7)
      if (owner != "-" && !(owner in seen)) { seen[owner] = 1; members++ }
      printf "%-10s %9s %9s %9s %7s  %s\n", t, $3, $4, $5, $6, substr(owner, 1, 30)
    }
    END {
      printf "%-10s %9s %9d %9d %7d  members=%d\n", t, "TOTAL", cur, end, lag, members + 0
    }' <<<"$out"
  printf '\n'

  sleep "$INTERVAL"
done
