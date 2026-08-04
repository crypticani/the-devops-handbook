# Module 04: Scripting — Cheat Sheet

> Bash and Python patterns for automation. Concepts live in the [module README](./README.md).
> Cross-module daily commands: **[QUICK-REFERENCE.md](../QUICK-REFERENCE.md)**

**Jump to:** [Script skeleton](#the-script-skeleton) · [Variables](#variables--expansion) · [Tests](#test-conditions) · [Control flow](#control-flow) · [Functions](#functions) · [Arguments](#arguments--input) · [Arrays](#arrays--maps) · [Error handling](#error-handling) · [Debugging](#debugging-bash) · [Python](#python-for-devops) · [Pitfalls](#common-pitfalls)

---

## The Script Skeleton

Start every script with this. It turns silent, dangerous failures into loud, immediate ones.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

# -E  ERR trap is inherited by functions and subshells
# -e  exit immediately if any command fails
# -u  error on undefined variables       ⭐ catches typos
# -o pipefail  a pipeline fails if ANY stage fails, not just the last
# IFS  only split on newlines and tabs, not spaces — filenames with spaces survive

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

log()  { printf '[%(%Y-%m-%dT%H:%M:%S%z)T] %s\n' -1 "$*" >&2; }
die()  { log "ERROR: $*"; exit 1; }

cleanup() {
  local rc=$?
  [[ -n "${TMPDIR_:-}" && -d "$TMPDIR_" ]] && rm -rf -- "$TMPDIR_"
  exit "$rc"
}
trap cleanup EXIT
trap 'die "failed at line $LINENO: $BASH_COMMAND"' ERR

TMPDIR_="$(mktemp -d)"

main() {
  log "starting"
  # ... work ...
  log "done"
}

main "$@"
```

> 💡 `set -e` has real gotchas: it does **not** trigger inside `if`/`while` conditions, on the left of `&&`/`||`, or in a function whose result is tested. When correctness matters, check exit codes explicitly rather than relying on `-e` alone.

---

## Variables & Expansion

```bash
name="value"                # no spaces around =
readonly CONST="fixed"
local scoped="x"            # inside functions only
export VISIBLE_TO_CHILDREN=1

echo "$name"                # ⭐ ALWAYS quote — unquoted vars word-split and glob
echo "${name}_suffix"       # braces disambiguate
```

### Parameter expansion (bash's hidden superpower)

| Expression | Result |
|------------|--------|
| `${var:-default}` | `var` if set and non-empty, else `default` |
| `${var:=default}` | ...and **assign** the default to `var` |
| `${var:?message}` | Exit with `message` if `var` is unset ⭐ great for required config |
| `${var:+alt}` | `alt` only if `var` **is** set |
| `${#var}` | Length |
| `${var:2:5}` | Substring from index 2, length 5 |
| `${var#prefix}` | Strip shortest matching prefix |
| `${var##*/}` | Strip longest prefix up to `/` → **basename** |
| `${var%suffix}` | Strip shortest matching suffix |
| `${var%.*}` | Strip the extension |
| `${var%/*}` | → **dirname** |
| `${var/old/new}` | Replace the **first** occurrence |
| `${var//old/new}` | Replace **all** occurrences |
| `${var/#old/new}` | Replace only at the start |
| `${var^^}` / `${var,,}` | Upper-case / lower-case |
| `${!prefix*}` | Names of all variables starting with `prefix` |

```bash
: "${DATABASE_URL:?DATABASE_URL must be set}"   # ⭐ fail fast on missing config
port="${PORT:-8080}"
file="/var/log/nginx/access.log"
echo "${file##*/}"    # access.log
echo "${file%/*}"     # /var/log/nginx
echo "${file%.log}"   # /var/log/nginx/access
```

### Command substitution & arithmetic

```bash
now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"     # ⭐ $(...) not backticks — it nests
count="$(grep -c ERROR app.log)"

(( total = 3 * 7 ))
(( count++ ))
(( a > b )) && echo "a wins"
percent=$(( used * 100 / total ))
echo "$(( RANDOM % 100 ))"
awk "BEGIN{printf \"%.2f\", 22/7}"       # bash has no floats — use awk or bc
```

### Special variables

| Var | Meaning |
|-----|---------|
| `$0` | Script name |
| `$1`…`$9` | Positional arguments |
| `$#` | Number of arguments |
| `"$@"` | All arguments, **each properly quoted** ⭐ |
| `$*` | All arguments as one string |
| `$?` | Exit status of the last command |
| `$$` | This script's PID |
| `$!` | PID of the last background job |
| `$LINENO` | Current line number |
| `${BASH_SOURCE[0]}` | This file's path (works when sourced; `$0` doesn't) |
| `$PIPESTATUS` | Array of exit codes from every stage of the last pipeline |

---

## Test Conditions

Prefer `[[ ]]` over `[ ]` in bash — no word-splitting surprises, supports `&&`, `||`, `=~`.

### Files

| Test | True when |
|------|-----------|
| `[[ -e path ]]` | Exists (any type) |
| `[[ -f path ]]` | Is a regular file |
| `[[ -d path ]]` | Is a directory |
| `[[ -L path ]]` | Is a symlink |
| `[[ -s path ]]` | Exists and is **non-empty** |
| `[[ -r/-w/-x path ]]` | Readable / writable / executable |
| `[[ f1 -nt f2 ]]` | f1 is newer than f2 |

### Strings & numbers

| Test | True when |
|------|-----------|
| `[[ -z "$s" ]]` | String is empty |
| `[[ -n "$s" ]]` | String is non-empty |
| `[[ "$a" == "$b" ]]` | Strings equal |
| `[[ "$a" == pat* ]]` | **Glob** match (don't quote the pattern) |
| `[[ "$a" =~ ^[0-9]+$ ]]` | **Regex** match (don't quote the regex) |
| `[[ $a -eq $b ]]` | Numeric equal (`-ne -lt -le -gt -ge`) |
| `(( a > b ))` | Arithmetic comparison — reads more naturally |

```bash
[[ -f "$config" ]] || die "config not found: $config"
[[ "$env" =~ ^(dev|staging|prod)$ ]] || die "invalid environment: $env"
[[ -n "${DEBUG:-}" ]] && set -x
```

---

## Control Flow

```bash
if [[ cond ]]; then
  ...
elif [[ cond ]]; then
  ...
else
  ...
fi

case "$1" in
  start)        start_service ;;
  stop)         stop_service ;;
  restart)      stop_service; start_service ;;
  status|check) show_status ;;
  *)            die "usage: $0 {start|stop|restart|status}" ;;
esac

for f in *.log; do
  [[ -e "$f" ]] || continue        # ⭐ guard: an unmatched glob stays literal
  gzip "$f"
done

for i in {1..5};        do echo "$i"; done
for i in $(seq 0 10 100); do echo "$i"; done
for ((i = 0; i < 10; i++)); do echo "$i"; done

# ⭐ Read a file line by line — SAFELY
while IFS= read -r line; do
  echo "processing: $line"
done < input.txt

# Iterate over command output without a subshell losing your variables
while IFS= read -r pod; do
  kubectl delete pod "$pod"
done < <(kubectl get pods -o name)

# Retry with backoff
for attempt in 1 2 3 4 5; do
  if curl -sSf --max-time 5 "$url" >/dev/null; then break; fi
  log "attempt $attempt failed; retrying in $((attempt * 2))s"
  sleep $((attempt * 2))
  (( attempt == 5 )) && die "giving up on $url"
done

# Wait for a condition with a timeout
deadline=$(( SECONDS + 60 ))
until curl -sf "$url/health" >/dev/null; do
  (( SECONDS > deadline )) && die "timed out waiting for $url"
  sleep 2
done
```

---

## Functions

```bash
greet() {
  local name="${1:?name required}"      # locals are essential — no accidental globals
  local greeting="${2:-Hello}"
  printf '%s, %s!\n' "$greeting" "$name"
}

greet "World"
greet "DevOps" "Welcome"

# Return a value: echo it and capture, or use a nameref
get_version() { echo "1.2.3"; }
version="$(get_version)"

# Exit status as a boolean
is_running() { systemctl is-active --quiet "$1"; }
if is_running nginx; then echo "up"; fi

# Nameref (bash 4.3+) — "return" into a caller's variable
set_result() { local -n out="$1"; out="computed"; }
set_result myvar; echo "$myvar"
```

> 💡 `return` in bash only sets an exit status (0–255). To hand back data, `echo` it and capture with `$(...)`, or use a nameref.

---

## Arguments & Input

```bash
# Simple positional handling
[[ $# -ge 1 ]] || die "usage: $0 <environment> [region]"
environment="$1"
region="${2:-us-east-1}"

# Flags with getopts (short options)
usage() { cat <<EOF
Usage: $0 -e ENV [-r REGION] [-v] [-h]
  -e ENV      environment: dev|staging|prod  (required)
  -r REGION   AWS region (default: us-east-1)
  -v          verbose
EOF
exit 1; }

verbose=0; region="us-east-1"; env=""
while getopts ":e:r:vh" opt; do
  case "$opt" in
    e) env="$OPTARG" ;;
    r) region="$OPTARG" ;;
    v) verbose=1 ;;
    h) usage ;;
    :) die "-$OPTARG requires an argument" ;;
    \?) die "unknown option: -$OPTARG" ;;
  esac
done
shift $((OPTIND - 1))
[[ -n "$env" ]] || usage

# Long options — parse manually
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)     env="$2"; shift 2 ;;
    --env=*)   env="${1#*=}"; shift ;;
    --dry-run) dry_run=1; shift ;;
    --)        shift; break ;;
    -*)        die "unknown option: $1" ;;
    *)         args+=("$1"); shift ;;
  esac
done
```

```bash
read -rp "Continue? [y/N] " answer          # -r = don't mangle backslashes
[[ "$answer" =~ ^[Yy]$ ]] || exit 0
read -rsp "Password: " pass; echo           # -s = silent

# Heredoc
cat > config.yml <<EOF
env: $environment          # variables ARE expanded
EOF

cat > script.sh <<'EOF'
echo "$HOME"               # quoted delimiter = NO expansion  ⭐
EOF

cat <<-EOF                 # <<- strips leading TABS (not spaces)
	indented heredoc
EOF
```

---

## Arrays & Maps

```bash
# Indexed arrays
servers=("web-01" "web-02" "db-01")
servers+=("cache-01")
echo "${servers[0]}"          # first element
echo "${servers[@]}"          # all elements
echo "${#servers[@]}"         # count
echo "${servers[@]:1:2}"      # slice
for s in "${servers[@]}"; do echo "$s"; done       # ⭐ always quote [@]

mapfile -t lines < file.txt              # read a file into an array, no trailing newlines
readarray -t pods < <(kubectl get pods -o name)

# Associative arrays (bash 4+)
declare -A ports=([http]=80 [https]=443 [ssh]=22)
ports[postgres]=5432
echo "${ports[https]}"
for svc in "${!ports[@]}"; do            # ! gives the KEYS
  echo "$svc → ${ports[$svc]}"
done
[[ -v ports[http] ]] && echo "key exists"
unset 'ports[ssh]'
```

---

## Error Handling

```bash
# Explicit checks beat relying on set -e
if ! command -v terraform >/dev/null 2>&1; then
  die "terraform is not installed"
fi

output="$(some_command 2>&1)" || die "some_command failed: $output"

# Capture status without tripping set -e
set +e; risky_command; rc=$?; set -e
(( rc == 0 )) || log "risky_command returned $rc, continuing anyway"

# Check every stage of a pipeline
cmd1 | cmd2 | cmd3
echo "${PIPESTATUS[@]}"        # e.g. "0 1 0" — stage 2 failed

# Guaranteed cleanup
tmp="$(mktemp)"
trap 'rm -f -- "$tmp"' EXIT

# Prevent concurrent runs
exec 200>/var/lock/myscript.lock
flock -n 200 || die "another instance is already running"

# Idempotency: make the script safe to re-run
mkdir -p "$dir"                        # not: mkdir "$dir"
grep -qxF "$line" "$file" || echo "$line" >> "$file"
id -u appuser &>/dev/null || useradd -r appuser
```

**Standard exit codes:**

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Misuse of a shell builtin / bad arguments |
| `126` | Command found but not executable |
| `127` | Command not found |
| `128+N` | Killed by signal N (`130` = Ctrl-C/SIGINT, `137` = SIGKILL/OOM, `143` = SIGTERM) |

---

## Debugging Bash

```bash
bash -n script.sh              # syntax check, don't execute  ⭐
bash -x script.sh              # trace every command as it runs
bash -u script.sh              # error on undefined variables
set -x / set +x                # trace just one section
PS4='+ ${BASH_SOURCE}:${LINENO}:${FUNCNAME[0]:-main}: '   # ⭐ richer trace prefix

# shellcheck — install it, run it on everything
shellcheck script.sh
shellcheck -S warning script.sh
# In CI:  find . -name '*.sh' -print0 | xargs -0 shellcheck

# Trace to a file without polluting stdout
exec 5> >(logger -t myscript); BASH_XTRACEFD=5; set -x
```

---

## Python for DevOps

### Script skeleton

```python
#!/usr/bin/env python3
"""One-line description of what this does."""
from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="file to process")
    p.add_argument("-e", "--env", choices=["dev", "staging", "prod"], required=True)
    p.add_argument("-n", "--dry-run", action="store_true")
    p.add_argument("-v", "--verbose", action="count", default=0)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
    )
    if not args.path.exists():
        log.error("not found: %s", args.path)
        return 1
    log.info("processing %s for %s", args.path, args.env)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Files and paths (`pathlib`)

```python
from pathlib import Path

p = Path("/var/log/app.log")
p.exists(); p.is_file(); p.is_dir()
p.name          # 'app.log'
p.stem          # 'app'
p.suffix        # '.log'
p.parent        # PosixPath('/var/log')
p.stat().st_size

text = p.read_text(encoding="utf-8")
p.write_text("content\n")
Path("out/dir").mkdir(parents=True, exist_ok=True)

for f in Path("/etc").glob("*.conf"):        ...
for f in Path("/srv").rglob("*.yml"):        ...   # recursive

with open(p, encoding="utf-8") as fh:              # streams — safe for huge files
    for line in fh:
        if "ERROR" in line:
            print(line.rstrip())
```

### JSON, YAML, CSV

```python
import json, csv
import yaml           # pip install pyyaml

data = json.loads(raw)
raw  = json.dumps(data, indent=2, sort_keys=True)
with open("f.json") as fh: data = json.load(fh)
with open("f.json", "w") as fh: json.dump(data, fh, indent=2)

with open("deploy.yml") as fh: cfg = yaml.safe_load(fh)      # ⭐ safe_load, never load
with open("out.yml", "w") as fh: yaml.safe_dump(cfg, fh, sort_keys=False)

with open("hosts.csv", newline="") as fh:
    for row in csv.DictReader(fh):
        print(row["hostname"], row["ip"])
```

### Running commands

```python
import subprocess

r = subprocess.run(
    ["kubectl", "get", "pods", "-o", "json"],
    capture_output=True, text=True, timeout=30, check=False,
)
if r.returncode != 0:
    raise RuntimeError(f"kubectl failed: {r.stderr.strip()}")
pods = json.loads(r.stdout)

subprocess.run(["terraform", "apply", "-auto-approve"], check=True)   # raises on failure

# ⚠️ Never do this with untrusted input — shell=True is a command-injection hole
subprocess.run(f"rm -rf {user_input}", shell=True)    # ❌
subprocess.run(["rm", "-rf", user_input])             # ✅ argument list, no shell
```

### HTTP

```python
import requests    # pip install requests

r = requests.get(url, timeout=10, headers={"Authorization": f"Bearer {token}"})
r.raise_for_status()          # ⭐ raises on 4xx/5xx — never skip this
data = r.json()

r = requests.post(url, json={"key": "value"}, timeout=10)

# Retry with backoff on a shared session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

s = requests.Session()
s.mount("https://", HTTPAdapter(max_retries=Retry(
    total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
)))
```

### Environment & config

```python
import os

token = os.environ["API_TOKEN"]              # KeyError if missing — often what you want
debug = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
port  = int(os.getenv("PORT", "8080"))

from dotenv import load_dotenv               # pip install python-dotenv
load_dotenv()
```

### Useful stdlib for ops

| Module | For |
|--------|-----|
| `pathlib` | Filesystem paths |
| `subprocess` | Running commands |
| `argparse` | CLI arguments |
| `logging` | Structured output |
| `json` / `csv` / `configparser` | Data formats |
| `datetime` / `zoneinfo` | Timestamps |
| `re` | Regex |
| `shutil` | Copy, move, `disk_usage`, `which` |
| `tempfile` | Safe temp files (`TemporaryDirectory`) |
| `socket` | Port checks, hostname |
| `hashlib` | Checksums |
| `concurrent.futures` | Parallel API calls / SSH fan-out |

```python
# Parallel work over many hosts
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(check_host, h): h for h in hosts}
    for fut in as_completed(futures):
        host = futures[fut]
        try:
            print(host, fut.result())
        except Exception as exc:
            print(f"{host} failed: {exc}")
```

### Tooling

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip freeze > requirements.txt

ruff check .            # fast linter (replaces flake8/isort/pyupgrade)
ruff format .           # formatter (black-compatible)
mypy script.py          # static type checking
pytest -v               # tests
pytest --cov=src        # coverage
bandit -r .             # security linting
```

---

## Common Pitfalls

| ❌ Don't | ✅ Do | Why |
|----------|-------|-----|
| `rm -rf $DIR` | `rm -rf -- "${DIR:?}"` | Unset variable → deletes the wrong thing |
| `if [ $x = "y" ]` | `if [[ "$x" == "y" ]]` | Empty `$x` makes `[` a syntax error |
| `for f in $(ls)` | `for f in *` | `ls` output breaks on spaces/newlines |
| `cat f \| grep x` | `grep x f` | Useless use of cat |
| `` `cmd` `` | `$(cmd)` | Nests correctly, easier to read |
| `cd /some/dir` | `cd /some/dir \|\| exit 1` | A failed `cd` runs the rest in the wrong place |
| `echo $var` | `printf '%s\n' "$var"` | `echo` mangles backslashes and leading `-` |
| `sleep 30` then assume ready | Poll with a timeout | Fixed sleeps are flaky and slow |
| Parsing `ls`/`ps` output | `find -print0`, `pgrep` | Output formats vary |
| Secrets in the script | Env vars or a secret manager | Scripts get committed |
| `curl url \| bash` | Download, read, then run | Blind remote execution |
| No `set -euo pipefail` | Always start with it | Silent failures compound |

```bash
# Race-free "wait until ready"
timeout 60 bash -c 'until curl -sf localhost:8080/health; do sleep 2; done' \
  || die "service never became healthy"
```

---

<div align="center">

[← Module 04 README](./README.md) · [Resources](./resources.md) · [Labs](./labs/) · [Handbook Quick Reference](../QUICK-REFERENCE.md)

</div>
