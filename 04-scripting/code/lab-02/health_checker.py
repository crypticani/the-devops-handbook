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
