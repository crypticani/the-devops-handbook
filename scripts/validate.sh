#!/usr/bin/env bash
#
# REPOSITORY MAINTENANCE — not lab material. Learners can ignore this file.
#
# Validate everything in this repository that can be checked automatically:
# internal links, Mermaid diagrams, and every file under */code/.
#
# Usage:  ./scripts/validate.sh [check ...]
#   with no arguments, runs every check that has its tool available
#
# Checks:  links  mermaid  yaml  json  python  bash  compose  terraform  ansible  go  labs
#
set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT="$PWD"

FAILED=0
RUN=()
SKIPPED=()

c_red=$'\033[31m'; c_grn=$'\033[32m'; c_yel=$'\033[33m'; c_dim=$'\033[2m'; c_off=$'\033[0m'

section() { printf '\n%s══ %s %s\n' "$c_dim" "$1" "$c_off"; }
pass()    { printf '  %s✅%s %s\n' "$c_grn" "$c_off" "$1"; }
fail()    { printf '  %s❌%s %s\n' "$c_red" "$c_off" "$1"; FAILED=1; }
skip()    { printf '  %s⏭  %s (not installed)%s\n' "$c_yel" "$1" "$c_off"; SKIPPED+=("$1"); }

want() {
  [[ ${#WANTED[@]} -eq 0 ]] && return 0
  local c; for c in "${WANTED[@]}"; do [[ "$c" == "$1" ]] && return 0; done
  return 1
}

WANTED=("$@")

# ─────────────────────────────────────────────────────────── links
if want links; then
  section "Internal links"
  if python3 - <<'PY'; then pass "all internal links resolve"; else fail "broken internal links"; fi
import os, re, glob, sys
bad = []
for f in glob.glob('**/*.md', recursive=True):
    if f.startswith(('.remember', 'node_modules')):
        continue
    d = os.path.dirname(f)
    for m in re.finditer(r'\]\((?!https?:|#|mailto:)([^)#]+)', open(f, encoding='utf-8').read()):
        p = os.path.normpath(os.path.join(d, m.group(1).strip()))
        if not os.path.exists(p):
            bad.append(f"{f} -> {m.group(1)}")
for b in bad:
    print(f"     {b}")
sys.exit(1 if bad else 0)
PY
  RUN+=(links)
fi

# ─────────────────────────────────────────────────────── mermaid
if want mermaid; then
  section "Mermaid diagrams"
  if command -v npx >/dev/null 2>&1 && [[ -d node_modules/mermaid ]]; then
    if node scripts/validate-mermaid.mjs .; then pass "all diagrams parse"; else fail "mermaid parse errors"; fi
    RUN+=(mermaid)
  else
    skip "mermaid (run: npm install mermaid jsdom)"
  fi
fi

# ────────────────────────────────────────────────────────── yaml
if want yaml; then
  section "YAML"
  if python3 - <<'PY'; then pass "all YAML parses"; else fail "invalid YAML"; fi
import glob, sys
try:
    import yaml
except ImportError:
    print("     PyYAML not installed — skipping"); sys.exit(0)
bad = 0
for f in sorted(glob.glob('*/code/**/*.y*ml', recursive=True)):
    try:
        list(yaml.safe_load_all(open(f, encoding='utf-8')))
    except Exception as e:
        bad += 1
        print(f"     {f}: {str(e).splitlines()[0]}")
sys.exit(1 if bad else 0)
PY
  RUN+=(yaml)
fi

# ────────────────────────────────────────────────────────── json
if want json; then
  section "JSON"
  ok=1
  while IFS= read -r f; do
    python3 -m json.tool "$f" >/dev/null 2>&1 || { fail "$f"; ok=0; }
  done < <(find ./*/code -name '*.json' 2>/dev/null)
  [[ $ok -eq 1 ]] && pass "all JSON parses"
  RUN+=(json)
fi

# ──────────────────────────────────────────────────────── python
if want python; then
  section "Python"
  ok=1
  while IFS= read -r f; do
    python3 -m py_compile "$f" 2>/dev/null || { fail "$f"; ok=0; }
  done < <(find ./*/code -name '*.py' 2>/dev/null)
  find . -name '__pycache__' -type d -not -path './.git/*' -exec rm -rf {} + 2>/dev/null
  [[ $ok -eq 1 ]] && pass "all Python compiles"
  if command -v ruff >/dev/null 2>&1; then
    ruff check ./*/code >/dev/null 2>&1 && pass "ruff clean" || printf '  %s⚠  ruff reported findings (non-blocking)%s\n' "$c_yel" "$c_off"
  fi
  RUN+=(python)
fi

# ────────────────────────────────────────────────────────── bash
if want bash; then
  section "Shell"
  ok=1
  while IFS= read -r f; do
    bash -n "$f" 2>/dev/null || { fail "$f (syntax)"; ok=0; }
  done < <(find ./*/code scripts -name '*.sh' 2>/dev/null)
  [[ $ok -eq 1 ]] && pass "all shell scripts parse"
  if command -v shellcheck >/dev/null 2>&1; then
    # shellcheck disable=SC2046
    shellcheck -S warning $(find ./*/code scripts -name '*.sh' 2>/dev/null) && pass "shellcheck clean" || fail "shellcheck findings"
  else
    skip "shellcheck"
  fi
  RUN+=(bash)
fi

# ─────────────────────────────────────────────────────── compose
if want compose; then
  section "Docker Compose"
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    ok=1
    while IFS= read -r f; do
      out=$(cd "$(dirname "$f")" && docker compose -f "$(basename "$f")" config -q 2>&1)
      [[ -z "$out" ]] || { fail "$f"; printf '     %s\n' "$out"; ok=0; }
    done < <(find ./*/code -name 'docker-compose*.yml' -o -name 'compose*.y*ml' 2>/dev/null)
    [[ $ok -eq 1 ]] && pass "all compose files valid"
    RUN+=(compose)
  else
    skip "docker compose"
  fi
fi

# ───────────────────────────────────────────────────── terraform
if want terraform; then
  section "Terraform"
  if command -v terraform >/dev/null 2>&1; then
    terraform fmt -check -recursive ./*/code >/dev/null 2>&1 \
      && pass "terraform fmt clean" || fail "terraform fmt — run: terraform fmt -recursive"

    # ⭐ Share one provider download across every config, or this takes minutes
    # per directory and times out in CI.
    export TF_PLUGIN_CACHE_DIR="${TF_PLUGIN_CACHE_DIR:-${TMPDIR:-/tmp}/tf-plugin-cache}"
    mkdir -p "$TF_PLUGIN_CACHE_DIR"

    ok=1
    while IFS= read -r d; do
      out=$( cd "$d" \
        && terraform init -backend=false -input=false -no-color 2>&1 \
        && terraform validate -no-color 2>&1 )
      if grep -q 'Success!' <<<"$out"; then :; else
        fail "terraform validate: $d"
        printf '     %s\n' "$(tail -6 <<<"$out")"
        ok=0
      fi
      rm -rf "$d/.terraform" "$d/.terraform.lock.hcl"
    done < <(find ./*/code -name '*.tf' -exec dirname {} \; 2>/dev/null | sort -u)
    [[ $ok -eq 1 ]] && pass "terraform validate clean"
    RUN+=(terraform)
  else
    skip "terraform"
  fi
fi

# ─────────────────────────────────────────────────────── ansible
if want ansible; then
  section "Ansible"
  if command -v ansible-lint >/dev/null 2>&1; then
    ok=1
    while IFS= read -r d; do
      out=$( cd "$d" && ansible-lint --offline --nocolor 2>&1 )
      if grep -q 'Passed' <<<"$out"; then :; else
        fail "ansible-lint: $d"
        printf '     %s\n' "$(grep -E '^(WARNING|ERROR)|name\[|var-naming|no-changed-when|yaml\[' <<<"$out" | head -8)"
        ok=0
      fi
    done < <(find ./*/code -name 'ansible.cfg' -exec dirname {} \; 2>/dev/null | sort -u)
    [[ $ok -eq 1 ]] && pass "ansible-lint clean (production profile)"
    RUN+=(ansible)
  else
    skip "ansible-lint"
  fi
fi

# ──────────────────────────────────────────────────────────── go
if want go; then
  section "Go"
  if command -v gofmt >/dev/null 2>&1; then
    out=$(find ./*/code -name '*.go' -exec gofmt -l {} \; 2>/dev/null)
    [[ -z "$out" ]] && pass "gofmt clean" || { fail "gofmt:"; printf '     %s\n' "$out"; }
    RUN+=(go)
  else
    skip "gofmt"
  fi
fi

# ─────────────────────────────────────────────────── lab contract
if want labs; then
  section "Lab contract"
  # A lab either has a Break It heading, or is itself entirely failure
  # scenarios and says so explicitly (see CONTRIBUTING.md).
  missing=$(for f in ./*/labs/lab-*.md; do
    grep -qiE '^#+.*(break it|🧨)' "$f" \
      || grep -qi 'this lab .*is.* the Break It section' "$f" \
      || echo "$f"
  done)
  [[ -z "$missing" ]] && pass "every lab has a Break It section" \
    || { fail "labs missing a Break It section:"; printf '     %s\n' "$missing"; }

  orphans=$(for d in ./*/code/lab-*; do
    [[ -d "$d" ]] || continue
    mod=$(basename "$(dirname "$(dirname "$d")")"); slug=$(basename "$d")
    ls "$mod"/labs/"$slug"-*.md >/dev/null 2>&1 || echo "$d (no matching lab)"
  done)
  [[ -z "$orphans" ]] && pass "every code/ dir has a matching lab" \
    || { fail "orphaned code directories:"; printf '     %s\n' "$orphans"; }
  RUN+=(labs)
fi

# ───────────────────────────────────────────────────────── summary
printf '\n%s────────────────────────────────────────%s\n' "$c_dim" "$c_off"
printf 'ran: %s\n' "${RUN[*]:-none}"
[[ ${#SKIPPED[@]} -gt 0 ]] && printf 'skipped: %s\n' "${SKIPPED[*]}"
if [[ $FAILED -eq 0 ]]; then
  printf '%s✅ all checks passed%s\n' "$c_grn" "$c_off"
else
  printf '%s❌ some checks failed%s\n' "$c_red" "$c_off"
fi
exit $FAILED
