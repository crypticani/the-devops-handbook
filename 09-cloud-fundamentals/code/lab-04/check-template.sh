#!/usr/bin/env bash
#
# The gate you would run in CI before any Bicep template is allowed to deploy:
# it must pass the linter rules you chose, and it must compile to ARM JSON.
#
# Both steps are offline — neither contacts Azure or needs a subscription, which is
# why template review belongs on every pull request rather than in a deploy step,
# where a mistake has already cost you something.
#
# ⭐ Lint runs first on purpose. A rule at "error" level in bicepconfig.json also
# fails `az bicep build`, so without linting first you get a build failure whose
# real cause is a style rule — confusing the first time you meet it.
#
# Usage:  ./check-template.sh [file.bicep]
#
set -euo pipefail

TEMPLATE="${1:-main.bicep}"
OUTFILE="${TEMPLATE%.bicep}.json"
run() { docker compose run --rm --entrypoint /bin/sh cli -c "$1"; }

echo "══ Bicep version (installs on first run, cached after)"
run "az bicep install >/dev/null 2>&1 || true; az bicep version"

echo
echo "══ Linting ${TEMPLATE}"
if run "az bicep lint --file ${TEMPLATE}"; then
  echo "  ✅ lint clean"
else
  echo "  ❌ lint failed — fix the errors above, or decide the rule is wrong and edit bicepconfig.json"
  exit 1
fi

echo
echo "══ Compiling ${TEMPLATE} → ${OUTFILE}"
# A build failure here is a real type error: a property that does not exist on the
# resource, a wrong type, or a reference to something undeclared.
run "az bicep build --file ${TEMPLATE} --outfile ${OUTFILE}"
echo "  ✅ compiled — this ARM JSON is what Azure would actually receive"
