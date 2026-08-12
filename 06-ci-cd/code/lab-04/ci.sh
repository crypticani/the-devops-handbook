#!/usr/bin/env bash
#
# ⭐ The pipeline calls this script. So do you, locally, with the same arguments.
#
# That is the single most useful CI habit there is: the pipeline becomes a thin
# wrapper that provides an environment and runs your script, instead of a pile of
# YAML-only logic you can only test by pushing a commit and waiting.
#
# Usage:  ./ci.sh lint | test | package | all
#
set -euo pipefail

VERSION="${BUILD_BUILDNUMBER:-0.0.0-local}"   # Azure Pipelines sets BUILD_BUILDNUMBER

lint() {
  echo "── lint"
  python3 -m py_compile app/app.py
  echo "   ✅ syntax ok"
}

test_() {
  echo "── test"
  python3 app/app.py            # the assert-based self-check
}

package() {
  echo "── package (version ${VERSION})"
  mkdir -p dist
  tar czf "dist/app-${VERSION}.tar.gz" app/
  echo "   ✅ dist/app-${VERSION}.tar.gz"
}

case "${1:-all}" in
  lint) lint ;;
  test) test_ ;;
  package) package ;;
  all) lint; test_; package ;;
  *) echo "usage: $0 {lint|test|package|all}" >&2; exit 2 ;;
esac
