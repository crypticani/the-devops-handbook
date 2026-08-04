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
