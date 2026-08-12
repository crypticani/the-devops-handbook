#!/usr/bin/env bash
#
# Registers this container as a self-hosted Azure Pipelines agent, runs one job, and
# leaves. `--once` plus a restart policy is the ephemeral-agent pattern: every job gets
# a clean machine, so nothing a build leaves behind can affect the next one.
#
# Required environment:
#   AZP_URL    https://dev.azure.com/<your-organisation>
#   AZP_TOKEN  a PAT with Agent Pools (read, manage)
#   AZP_POOL   agent pool name (default: Default)
#
set -euo pipefail

: "${AZP_URL:?set AZP_URL to https://dev.azure.com/<org>}"
: "${AZP_TOKEN:?set AZP_TOKEN to a PAT with Agent Pools (read, manage)}"
AZP_POOL="${AZP_POOL:-Default}"
AZP_AGENT_NAME="${AZP_AGENT_NAME:-docker-$(hostname)}"

cleanup() {
  # Without this, every restart leaves a dead agent listed in the pool, and the
  # pool eventually fills with ghosts that look like available capacity.
  if [ -e ./config.sh ]; then
    ./config.sh remove --unattended --auth pat --token "${AZP_TOKEN}" || true
  fi
}
trap cleanup EXIT

./config.sh \
  --unattended \
  --acceptTeeEula \
  --url "${AZP_URL}" \
  --auth pat \
  --token "${AZP_TOKEN}" \
  --pool "${AZP_POOL}" \
  --agent "${AZP_AGENT_NAME}" \
  --replace

# --once: take exactly one job, then exit. Drop it and the agent stays resident,
# which is faster but means job N sees whatever job N-1 left on disk.
exec ./run.sh --once
