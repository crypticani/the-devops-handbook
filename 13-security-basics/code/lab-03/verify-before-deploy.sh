#!/usr/bin/env bash
# Run before every deploy. Exits non-zero if the image is not trustworthy.
set -uo pipefail

IMAGE="${1:?usage: verify-before-deploy.sh <image>}"
PUBKEY="${COSIGN_PUBKEY:-cosign.pub}"
FAIL=0

echo "── 1. signature ──"
if cosign verify --key "$PUBKEY" --allow-insecure-registry "$IMAGE" >/dev/null 2>&1; then
  echo "  ✅ signed and verified"
else
  echo "  ❌ NOT signed by our key"; FAIL=1
fi

echo "── 2. SBOM attestation ──"
if cosign verify-attestation --key "$PUBKEY" --allow-insecure-registry \
     --type spdxjson "$IMAGE" >/dev/null 2>&1; then
  echo "  ✅ SBOM attestation present"
else
  echo "  ⚠️  no SBOM attestation"; FAIL=1
fi

echo "── 3. vulnerabilities ──"
if trivy image --quiet --severity CRITICAL --exit-code 1 --ignore-unfixed "$IMAGE" >/dev/null 2>&1; then
  echo "  ✅ no fixable CRITICALs"
else
  echo "  ❌ fixable CRITICAL vulnerabilities present"; FAIL=1
fi

echo "── 4. pinned by digest ──"
if [[ "$IMAGE" == *"@sha256:"* ]]; then
  echo "  ✅ digest-pinned"
else
  echo "  ⚠️  deploying a mutable TAG — the content can change under you"
fi

exit $FAIL
