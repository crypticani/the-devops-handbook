# Lab 02: Python Automation for DevOps

## 🎯 Objective

Build practical Python tools for DevOps automation — API health checkers, system inventory scripts, and log analyzers.

---

## 📋 Prerequisites

```bash
sudo apt install -y python3 python3-pip python3-venv
pip3 install requests pyyaml psutil
```

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

## ✅ Validation

- [ ] Health checker runs and reports status for all services
- [ ] Health checker exits with code 1 if any service is down
- [ ] Log analyzer correctly parses nginx log format
- [ ] Log analyzer produces useful aggregate statistics
- [ ] Both scripts handle errors gracefully (missing files, network issues)
- [ ] Both scripts include proper argument parsing

---

[← Previous Lab](./lab-01-bash-scripting.md) | [Back to Module README](../README.md)
