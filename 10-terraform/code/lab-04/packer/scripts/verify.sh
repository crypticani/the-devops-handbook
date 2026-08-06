#!/bin/sh
#
# The gate between "the build commands ran" and "this image is fit to deploy".
#
# Every check here is something that has silently shipped broken in a real fleet. A build
# that does not verify itself is a build that will one day publish an image with no agent.

set -eu

fail() {
  echo "VERIFY FAILED: $1" >&2
  exit 1
}

command -v metrics-agent >/dev/null || fail "monitoring agent missing"
command -v curl >/dev/null || fail "curl missing"
id appuser >/dev/null 2>&1 || fail "appuser does not exist"

[ -d /app ] || fail "/app missing"
[ "$(stat -c '%U' /app)" = "appuser" ] || fail "/app is not owned by appuser"

# The package index should not be in the image — it is ~40 MB per instance of nothing.
[ -z "$(ls -A /var/lib/apt/lists 2>/dev/null)" ] || fail "apt lists were not cleaned"

# Anything that looks like a baked secret. Scenario 2 is how one gets here.
if env | grep -Eiq '(secret|password|token|api_key)='; then
  fail "a credential is present in the image environment"
fi

echo "verify: OK — agent, user, ownership, cleanliness, no baked credentials"
