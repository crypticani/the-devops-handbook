# Lab 02: Python Automation for DevOps

## 🎯 Objective

Build practical Python tools for DevOps automation — API health checkers, system inventory scripts, and log analyzers.

---

## 📋 Prerequisites

```bash
sudo apt install -y python3 python3-pip python3-venv       # Debian/Ubuntu
sudo dnf install -y python3 python3-pip                    # RHEL-compatible
pip3 install requests pyyaml psutil
```

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Commands you ran and the important output you used for validation
- Any files, scripts, configs, manifests, or workflows you created
- A short failure note describing one thing that broke, how you diagnosed it, and how you fixed it
- Cleanup commands or confirmation that no long-running resources remain

Treat the validation section as the minimum proof that the lab worked.

---

## 📂 Lab Files

Every file this lab creates also exists as a real, CI-validated file in
[`../code/lab-02/`](../code/lab-02/) (2 files).

```bash
# Option A — type them out yourself (recommended the first time; that's the learning)
# Option B — start from the reference copies
cp -r /path/to/the-devops-handbook/04-scripting/code/lab-02/. .
```

Use Option B when you're comparing against a known-good version, or when something
won't start and you need to rule out a typo. See [`../code/README.md`](../code/README.md).

---

## 🔬 Exercise 1: Multi-Service Health Checker

```bash
mkdir -p ~/devops-labs/module-04/python
cd ~/devops-labs/module-04/python

cat > health_checker.py << 'HEALTH'
#!/usr/bin/env python3
"""
Multi-service health checker with configurable endpoints
Usage: python3 health_checker.py [--config config.yaml]
"""

import json
import sys
import time
import argparse
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    print("Install requests: pip3 install requests")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Default services to check
DEFAULT_SERVICES = [
    {"name": "Google DNS",    "url": "https://dns.google",        "timeout": 5},
    {"name": "GitHub",        "url": "https://api.github.com",    "timeout": 5},
    {"name": "GitHub Status", "url": "https://www.githubstatus.com/api/v2/status.json", "timeout": 5},
]

def check_service(service: dict) -> dict:
    """Check a single service health"""
    name = service["name"]
    url = service["url"]
    timeout = service.get("timeout", 5)
    expected_status = service.get("expected_status", 200)

    result = {
        "name": name,
        "url": url,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        start = time.time()
        response = requests.get(url, timeout=timeout)
        elapsed = round((time.time() - start) * 1000, 1)

        result.update({
            "status": "UP" if response.status_code == expected_status else "DEGRADED",
            "http_code": response.status_code,
            "response_ms": elapsed,
        })
    except requests.exceptions.Timeout:
        result.update({"status": "DOWN", "error": "timeout"})
    except requests.exceptions.ConnectionError:
        result.update({"status": "DOWN", "error": "connection_refused"})
    except Exception as e:
        result.update({"status": "DOWN", "error": str(e)})

    return result

def check_all_services(services: list) -> list:
    """Check all services concurrently"""
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_service, svc): svc for svc in services}
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda x: x["name"])

def print_report(results: list):
    """Print a formatted health report"""
    print("\n" + "=" * 60)
    print(f"  SERVICE HEALTH REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    up_count = sum(1 for r in results if r["status"] == "UP")
    total = len(results)

    for r in results:
        status_icon = {"UP": "✅", "DEGRADED": "⚠️ ", "DOWN": "❌"}.get(r["status"], "❓")
        response = f"{r.get('response_ms', 'N/A')}ms" if "response_ms" in r else r.get("error", "unknown")
        print(f"  {status_icon} {r['name']:<25} {r['status']:<10} {response}")

    print("-" * 60)
    print(f"  Summary: {up_count}/{total} services healthy")
    print("=" * 60 + "\n")

    return up_count == total

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Service Health Checker")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    results = check_all_services(DEFAULT_SERVICES)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        all_healthy = print_report(results)
        sys.exit(0 if all_healthy else 1)
HEALTH

chmod +x health_checker.py
python3 health_checker.py
```

---

## 🔬 Exercise 2: Log Analyzer

```bash
cat > log_analyzer.py << 'ANALYZER'
#!/usr/bin/env python3
"""
Analyze nginx/application log files
Usage: python3 log_analyzer.py <logfile>
"""

import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

def parse_nginx_line(line: str) -> dict:
    """Parse a standard nginx access log line"""
    pattern = r'(\S+) - \S+ \[(.*?)\] "(\S+) (\S+) \S+" (\d{3}) (\d+)'
    match = re.match(pattern, line)
    if match:
        return {
            "ip": match.group(1),
            "timestamp": match.group(2),
            "method": match.group(3),
            "path": match.group(4),
            "status": int(match.group(5)),
            "size": int(match.group(6)),
        }
    return None

def analyze_log(filepath: str):
    """Analyze a log file and print report"""
    ip_counter = Counter()
    status_counter = Counter()
    path_counter = Counter()
    error_ips = Counter()
    total_bytes = 0
    total_lines = 0
    parse_errors = 0

    with open(filepath, "r") as f:
        for line in f:
            total_lines += 1
            parsed = parse_nginx_line(line.strip())
            if not parsed:
                parse_errors += 1
                continue

            ip_counter[parsed["ip"]] += 1
            status_counter[parsed["status"]] += 1
            path_counter[parsed["path"]] += 1
            total_bytes += parsed["size"]

            if parsed["status"] >= 400:
                error_ips[parsed["ip"]] += 1

    # Print report
    print("=" * 60)
    print(f"  LOG ANALYSIS REPORT")
    print(f"  File: {filepath}")
    print(f"  Lines: {total_lines} ({parse_errors} parse errors)")
    print(f"  Total data: {total_bytes / (1024*1024):.1f} MB")
    print("=" * 60)

    print("\n📊 Status Code Distribution:")
    for status, count in sorted(status_counter.items()):
        pct = (count / total_lines) * 100
        bar = "█" * int(pct / 2)
        print(f"  {status}: {count:>6} ({pct:5.1f}%) {bar}")

    print("\n🌐 Top 10 Client IPs:")
    for ip, count in ip_counter.most_common(10):
        print(f"  {ip:<20} {count:>6} requests")

    print("\n📁 Top 10 Requested Paths:")
    for path, count in path_counter.most_common(10):
        print(f"  {path:<35} {count:>6}")

    if error_ips:
        print("\n⚠️  Top Error IPs (4xx/5xx):")
        for ip, count in error_ips.most_common(5):
            print(f"  {ip:<20} {count:>6} errors")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <logfile>")
        sys.exit(1)
    analyze_log(sys.argv[1])
ANALYZER

chmod +x log_analyzer.py

# Test with the log file from Module 01
if [ -f ~/devops-labs/module-01/log-analysis/access.log ]; then
    python3 log_analyzer.py ~/devops-labs/module-01/log-analysis/access.log
else
    echo "Generate test logs first (see Module 01, Lab 04)"
fi
```

---

## 🧨 Break It: Four Ways an Automation Script Bites You

Both scripts work against friendly inputs. Production inputs are not friendly.

### Scenario 1: The Hang With No Timeout

**Break it:**

```bash
cd ~/devops-labs/module-04/python

# Add an endpoint that accepts the connection then never responds.
# 10.255.255.1 is non-routable — the connection attempt just hangs.
python3 - <<'EOF'
import re, pathlib
p = pathlib.Path("health_checker.py")
s = p.read_text()
s = s.replace(
    '{"name": "Google DNS",',
    '{"name": "Black Hole", "url": "http://10.255.255.1:8080", "timeout": None},\n    {"name": "Google DNS",'
)
pathlib.Path("health_checker_broken.py").write_text(s)
EOF

time python3 health_checker_broken.py       # Ctrl-C when you get bored
```

**Symptom:** The script never returns. In cron, the next scheduled run starts anyway — after an hour you have 12 hung Python processes holding sockets.

**Investigate:**

```bash
# In another terminal, while it hangs:
ps aux | grep health_checker
ss -tnp | grep python                 # stuck in SYN-SENT
py-spy dump --pid <PID> 2>/dev/null   # or: kill -QUIT <PID> for a traceback
```

**Root cause:** `timeout=None` means "wait forever". `requests` has **no default timeout** — omitting the argument is exactly as dangerous as passing `None`. `ThreadPoolExecutor` will not force a worker to stop, so one hung request pins a thread indefinitely.

**Fix:**

```python
# Always pass an explicit tuple: (connect_timeout, read_timeout)
response = requests.get(url, timeout=(3.05, 10))

# And bound the whole batch, not just each request
for future in as_completed(futures, timeout=60):
    ...
# plus, in cron:  timeout 120 python3 health_checker.py
```

```bash
rm -f health_checker_broken.py
```

---

### Scenario 2: The Log Line That Doesn't Match

**Break it:**

```bash
mkdir -p /tmp/pylab && cd /tmp/pylab
cat > messy.log <<'EOF'
10.0.0.1 - - [04/Aug/2026:09:00:00 +0000] "GET /api/users HTTP/1.1" 200 512
this line is not a log line at all
10.0.0.2 - - [04/Aug/2026:09:00:01 +0000] "POST /api/orders HTTP/1.1" 500 128
::1 - - [04/Aug/2026:09:00:02 +0000] "GET /health HTTP/1.1" 200 -
10.0.0.3 - - [04/Aug/2026:09:00:03 +0000] "GET /a b c HTTP/1.1" 404 0

EOF

python3 ~/devops-labs/module-04/python/log_analyzer.py /tmp/pylab/messy.log
```

**Symptom:** Either a traceback (`IndexError`, `ValueError: invalid literal for int()`), or — worse — it completes and silently reports numbers that are wrong because malformed lines were dropped without a word.

**Investigate:**

```bash
python3 -c "
import re
pat = re.compile(r'(\S+) \S+ \S+ \[([^]]+)\] \"(\S+) (\S+)[^\"]*\" (\d{3}) (\S+)')
for i, line in enumerate(open('/tmp/pylab/messy.log'), 1):
    if not pat.match(line.strip()):
        print(f'line {i} did NOT match: {line.strip()[:60]!r}')
"
```

**Root cause:** Real logs contain blank lines, IPv6 addresses, `-` where a byte count should be, request paths with spaces, and truncated writes. A regex tuned to clean sample data throws or silently skips.

**Fix — count what you skip, and never let a parse failure be invisible:**

```python
parsed = skipped = 0
for lineno, line in enumerate(fh, 1):
    line = line.strip()
    if not line:
        continue
    m = LOG_PATTERN.match(line)
    if not m:
        skipped += 1
        if skipped <= 5:
            log.warning("line %d unparseable: %.60s", lineno, line)
        continue
    size = m.group(6)
    bytes_sent = int(size) if size.isdigit() else 0    # handle '-'
    parsed += 1

if skipped:
    log.warning("skipped %d of %d lines (%.1f%%)", skipped, parsed + skipped,
                100 * skipped / (parsed + skipped))
    if skipped > 0.1 * (parsed + skipped):
        raise SystemExit("more than 10% of lines unparseable — wrong log format?")
```

> 💡 A parser that silently drops 40% of your log lines produces a beautiful, confident, completely wrong report. **Always emit the skip count.**

---

### Scenario 3: The Memory Blow-Up

**Break it:**

```bash
cd /tmp/pylab
# Generate a 500 MB log
python3 -c "
import random
with open('huge.log','w') as f:
    for i in range(4_000_000):
        f.write(f'10.0.0.{i%254+1} - - [04/Aug/2026:09:00:00 +0000] \"GET /p/{i} HTTP/1.1\" {random.choice([200,200,200,404,500])} {random.randint(100,5000)}\n')
"
ls -lh huge.log

# The anti-pattern — watch RSS climb
/usr/bin/time -v python3 -c "
lines = open('/tmp/pylab/huge.log').readlines()   # ❌ whole file into a list
print(len(lines))
" 2>&1 | grep -E 'Maximum resident|Elapsed'
```

**Symptom:** Several GB of RSS for a 500 MB file, or the process is **OOMKilled** (exit 137) on a small container.

**Investigate:**

```bash
/usr/bin/time -v python3 -c "
total = 0
with open('/tmp/pylab/huge.log') as fh:
    for line in fh:            # ✅ streams, constant memory
        total += 1
print(total)
" 2>&1 | grep -E 'Maximum resident|Elapsed'
```

Compare the two `Maximum resident set size` values.

**Root cause:** `.readlines()`, `.read()`, and `list(fh)` materialise the whole file. Python string objects carry ~49 bytes of overhead each, so a list of 4M lines costs far more than the file on disk.

**Fix:** iterate the file object directly; use `collections.Counter` for aggregation instead of accumulating rows; if you must hold results, cap them (`heapq.nlargest`) rather than sorting everything.

```bash
rm -f /tmp/pylab/huge.log
```

---

### Scenario 4: The Exception That Ate the Error

**Break it:**

```bash
cd /tmp/pylab
cat > swallow.py <<'EOF'
#!/usr/bin/env python3
import requests

def get_status(url):
    try:
        r = requests.get(url, timeout=5)
        return r.json()["status"]
    except Exception:
        return "unknown"        # ❌ every failure looks identical

for url in ["https://www.githubstatus.com/api/v2/status.json",
            "https://httpbin.org/status/500",
            "http://does-not-exist.invalid"]:
    print(f"{url:<55} → {get_status(url)}")
EOF
python3 swallow.py
```

**Symptom:** Everything reports `unknown`. You cannot tell a DNS failure from a 500 from a JSON schema change — and your health check reports "unknown" as if it were a normal state, so nothing alerts.

**Investigate:**

```bash
python3 - <<'EOF'
import requests, traceback
for url in ["https://httpbin.org/status/500", "http://does-not-exist.invalid"]:
    try:
        r = requests.get(url, timeout=5); r.raise_for_status(); print(r.json())
    except Exception:
        print(f"--- {url}"); traceback.print_exc()
EOF
```

**Root cause:** A bare `except Exception` with a generic fallback converts every distinct failure into one indistinguishable value. It also swallows `KeyError` from a changed API schema — a bug in *your* code, disguised as a service being down.

**Fix — catch specifically, and always call `raise_for_status()`:**

```python
def get_status(url):
    try:
        r = requests.get(url, timeout=(3.05, 10))
        r.raise_for_status()
        return {"state": "up", "status": r.json()["status"]}
    except requests.exceptions.Timeout:
        return {"state": "down", "reason": "timeout"}
    except requests.exceptions.ConnectionError as e:
        return {"state": "down", "reason": f"connection: {e.__class__.__name__}"}
    except requests.exceptions.HTTPError as e:
        return {"state": "down", "reason": f"http {e.response.status_code}"}
    except (ValueError, KeyError) as e:      # bad JSON / schema change = OUR bug
        log.exception("unexpected response shape from %s", url)
        return {"state": "error", "reason": f"parse: {e}"}
```

```bash
cd ~ && rm -rf /tmp/pylab
```

---

### Prevention Checklist

```bash
cd ~/devops-labs/module-04/python
ruff check .                       # catches bare excepts, unused vars, more
mypy health_checker.py             # catches None where a number is expected
bandit -r .                        # flags requests-without-timeout, among others
```

| Failure mode | Guard |
|--------------|-------|
| Hang forever | Explicit `timeout=(connect, read)` on **every** network call |
| Malformed input | Count and report skipped records; fail if the skip rate is high |
| Memory blow-up | Stream files; aggregate with `Counter`; never `.readlines()` a log |
| Swallowed error | Catch specific exceptions; `raise_for_status()`; log the traceback |
| Silent partial success | Distinguish "healthy", "unhealthy", and "could not determine" |

**Write this up** in `failure-notes.md` — symptom, investigation, root cause, fix for each.

---

## ✅ Validation

- [ ] Health checker runs and reports status for all services
- [ ] Health checker exits with code 1 if any service is down
- [ ] Log analyzer correctly parses nginx log format
- [ ] Log analyzer produces useful aggregate statistics
- [ ] Both scripts handle errors gracefully (missing files, network issues)
- [ ] Both scripts include proper argument parsing

---

[← Previous Lab](./lab-01-bash-scripting.md) | [Back to Module README](../README.md)


## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- Multi-service health checker script
- Log analyzer script with sample output
- Requirements file for dependencies used
- Notes on error handling and edge cases you encountered

---
