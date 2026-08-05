#!/usr/bin/env bash
# The gate every Ansible change should pass.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
FAIL=0
step() { printf '\n── %s ──\n' "$1"; }

step "lint";         ansible-lint || FAIL=1
step "syntax";       ansible-playbook site.yml --syntax-check || FAIL=1
step "converge";     ansible-playbook site.yml -e webapp_version="${VERSION:-2.0.0}" || FAIL=1
step "verify";       ansible-playbook tests/verify.yml -e webapp_version="${VERSION:-2.0.0}" || FAIL=1

step "idempotence"
out=$(ansible-playbook site.yml -e webapp_version="${VERSION:-2.0.0}")
if grep -qE 'changed=[1-9]' <<<"$out"; then
  echo "❌ NOT IDEMPOTENT:"; grep -E 'changed=[1-9]' <<<"$out"; FAIL=1
else
  echo "✅ changed=0 on the second run"
fi

step "secret leakage"
ansible-playbook site.yml -vvv -e webapp_version="${VERSION:-2.0.0}" 2>&1 \
  | grep -qE 'Pr0d-DB-P@ssw0rd|sk-prod-9f3c2a11' \
  && { echo "❌ A SECRET APPEARED IN THE OUTPUT"; FAIL=1; } \
  || echo "✅ no secrets in -vvv output"

[ $FAIL -eq 0 ] && echo -e "\n✅ all checks passed" || echo -e "\n❌ failures above"
exit $FAIL
