# Lab 04: Text Processing & Log Analysis

## 🎯 Objective

Master the Linux text processing pipeline — the combination of `grep`, `awk`, `sed`, `sort`, `uniq`, and pipes that lets you analyze logs, extract data, and troubleshoot production issues from the command line. This is arguably the most practical DevOps skill.

---

## 📋 Prerequisites

- Completed Labs 01-03
- Ubuntu 22.04+ with `sudo` access

---

## 🔬 Setup: Generate Realistic Log Data

```bash
mkdir -p ~/devops-labs/module-01/log-analysis
cd ~/devops-labs/module-01/log-analysis

# Generate a realistic nginx access log (simulated)
cat > generate_logs.sh << 'SCRIPT'
#!/bin/bash
# Generate 500 realistic nginx access log entries

IPS=("192.168.1.10" "10.0.0.5" "172.16.0.100" "203.0.113.50" "198.51.100.25"
     "192.168.1.11" "10.0.0.6" "203.0.113.51" "172.16.0.101" "198.51.100.26")

PATHS=("/api/v1/users" "/api/v1/products" "/api/v1/orders" "/" "/login" 
       "/api/v1/health" "/static/css/main.css" "/api/v1/search" "/admin" "/api/v1/payments")

STATUSES=("200" "200" "200" "200" "200" "200" "200" "301" "304" "400" "401" "403" "404" "404" "500" "502" "503")

AGENTS=("Mozilla/5.0 Chrome/120.0" "curl/7.88.1" "python-requests/2.31" "PostmanRuntime/7.36" "Googlebot/2.1")

for i in $(seq 1 500); do
    ip=${IPS[$RANDOM % ${#IPS[@]}]}
    path=${PATHS[$RANDOM % ${#PATHS[@]}]}
    status=${STATUSES[$RANDOM % ${#STATUSES[@]}]}
    size=$((RANDOM % 50000 + 100))
    agent=${AGENTS[$RANDOM % ${#AGENTS[@]}]}
    
    # Generate timestamps across last 24 hours
    hour=$(printf "%02d" $((RANDOM % 24)))
    minute=$(printf "%02d" $((RANDOM % 60)))
    second=$(printf "%02d" $((RANDOM % 60)))
    
    echo "$ip - - [15/Jan/2024:${hour}:${minute}:${second} +0000] \"GET $path HTTP/1.1\" $status $size \"-\" \"$agent\""
done
SCRIPT

chmod +x generate_logs.sh
./generate_logs.sh > access.log

# Generate an application error log
cat > app_errors.log << 'ERRORS'
2024-01-15 08:15:30 ERROR [database] Connection timeout to postgresql://db:5432/myapp after 30s
2024-01-15 08:15:31 WARN [api] Retry attempt 1/3 for database connection
2024-01-15 08:15:32 WARN [api] Retry attempt 2/3 for database connection
2024-01-15 08:15:33 ERROR [api] All retry attempts failed for database connection
2024-01-15 08:15:33 ERROR [api] Request failed: GET /api/v1/users - 500 Internal Server Error
2024-01-15 09:00:00 INFO [scheduler] Running daily cleanup job
2024-01-15 09:00:05 INFO [scheduler] Cleanup complete: removed 142 expired sessions
2024-01-15 10:30:15 ERROR [auth] Invalid JWT token from IP 203.0.113.50
2024-01-15 10:30:16 ERROR [auth] Invalid JWT token from IP 203.0.113.50
2024-01-15 10:30:17 WARN [auth] Rate limit threshold reached for IP 203.0.113.50
2024-01-15 10:30:18 ERROR [auth] Invalid JWT token from IP 203.0.113.50
2024-01-15 10:30:18 ERROR [auth] Blocked IP 203.0.113.50 - exceeded rate limit
2024-01-15 11:00:00 INFO [deploy] Deployment started: v2.3.1
2024-01-15 11:00:30 INFO [deploy] Health check passed
2024-01-15 11:00:31 INFO [deploy] Deployment complete: v2.3.1
2024-01-15 14:22:10 ERROR [payment] Stripe API timeout for order #98712
2024-01-15 14:22:11 WARN [payment] Retrying Stripe API call for order #98712
2024-01-15 14:22:15 INFO [payment] Stripe API call succeeded on retry for order #98712
2024-01-15 16:45:00 ERROR [memory] Application memory usage at 92% (threshold: 85%)
2024-01-15 16:45:01 WARN [memory] Triggering garbage collection
2024-01-15 16:45:05 INFO [memory] Memory usage reduced to 67% after GC
2024-01-15 18:00:00 CRITICAL [disk] Disk usage at 95% on /var/log
2024-01-15 18:00:01 CRITICAL [disk] ALERT: Immediate action required - disk nearly full
2024-01-15 19:30:00 ERROR [database] Slow query detected: 15.3s for SELECT * FROM orders WHERE created_at > ...
2024-01-15 19:30:01 WARN [database] Query optimization recommended for orders table
2024-01-15 22:00:00 INFO [backup] Nightly backup started
2024-01-15 22:05:00 INFO [backup] Nightly backup completed: 2.3GB compressed
ERRORS

echo "Log files generated successfully!"
wc -l access.log app_errors.log
```

---

## 🔬 Exercise 1: grep — Pattern Matching

### Step 1: Basic Searches

```bash
# Count total log entries
wc -l access.log
# Expected: 500

# Find all 500 errors
grep '" 500 ' access.log
# Note the quotes and spaces — be specific to avoid false matches

# Count 500 errors
grep -c '" 500 ' access.log

# Find all error-level messages in app log
grep "ERROR" app_errors.log

# Case-insensitive search
grep -i "error\|fail\|critical" app_errors.log
```

### Step 2: Context Searches (Critical for Debugging!)

```bash
# When you find an error, you need CONTEXT
# Show 3 lines before and after each error
grep -C 3 "Connection timeout" app_errors.log

# Show 5 lines after the deployment started
grep -A 5 "Deployment started" app_errors.log

# Show 2 lines before a critical alert
grep -B 2 "CRITICAL" app_errors.log
```

### Step 3: Advanced grep

```bash
# Multiple patterns (OR logic)
grep -E "500|502|503" access.log

# Inverse match (exclude patterns)
grep -v "200\|301\|304" access.log | head -10
# Shows only non-success responses

# Count by pattern
echo "=== Response Code Distribution ==="
for code in 200 301 304 400 401 403 404 500 502 503; do
    count=$(grep -c "\" $code " access.log)
    printf "  HTTP %s: %d requests\n" "$code" "$count"
done
```

---

## 🔬 Exercise 2: awk — Column-Based Processing

### Step 1: Extract Specific Fields

```bash
# Extract just the IP addresses (field 1)
awk '{print $1}' access.log | head -10

# Extract IP and status code (fields 1 and 9)
awk '{print $1, $9}' access.log | head -10

# Extract the request path (part of field 7)
awk '{print $7}' access.log | head -10
```

### Step 2: Filter with Conditions

```bash
# Find all requests with status 500
awk '$9 == 500 {print $1, $7, $9}' access.log

# Find all requests from a specific IP
awk '$1 == "203.0.113.50" {print $0}' access.log | head -10

# Find requests with response size > 10000 bytes
awk '$10 > 10000 {print $1, $7, $10}' access.log | head -10
```

### Step 3: Aggregation and Calculation

```bash
# Count requests per IP
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -10
# This pipeline: extract IPs → sort → count unique → sort by count → top 10

# Calculate total bytes transferred
awk '{sum += $10} END {printf "Total bytes: %d (%.2f MB)\n", sum, sum/1024/1024}' access.log

# Requests per status code
awk '{count[$9]++} END {for (code in count) printf "%s: %d\n", code, count[code]}' access.log | sort

# Requests per hour
awk -F'[/: ]' '{print $7}' access.log | sort | uniq -c | sort -k2n
```

---

## 🔬 Exercise 3: sed — Stream Editing

### Step 1: Find and Replace

```bash
# Replace "ERROR" with "❌ ERROR" for visibility
sed 's/ERROR/❌ ERROR/g' app_errors.log | head -10

# Replace in-place (BE CAREFUL — modifies the file!)
# Always make a backup first
cp app_errors.log app_errors.log.bak
sed -i 's/CRITICAL/🔴 CRITICAL/g' app_errors.log
grep "CRITICAL" app_errors.log

# Restore from backup
cp app_errors.log.bak app_errors.log
```

### Step 2: Line Operations

```bash
# Print specific line range
sed -n '10,15p' app_errors.log

# Delete comment lines (lines starting with #)
echo "# This is a comment" > /tmp/config_test.txt
echo "server_name=web01" >> /tmp/config_test.txt
echo "# Another comment" >> /tmp/config_test.txt
echo "port=8080" >> /tmp/config_test.txt

sed '/^#/d' /tmp/config_test.txt
# Output:
# server_name=web01
# port=8080

# Delete empty lines
sed '/^$/d' /tmp/config_test.txt
```

---

## 🔬 Exercise 4: Real-World Log Analysis Scenarios

### Scenario 1: Identify an Ongoing Attack

```bash
echo "=== Scenario: Is someone attacking our server? ==="

# Step 1: Find IPs with the most requests
echo "--- Top 10 IPs by request count ---"
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -10

# Step 2: Check for excessive 401/403 errors from specific IPs
echo ""
echo "--- IPs with auth failures ---"
awk '$9 == 401 || $9 == 403 {print $1}' access.log | sort | uniq -c | sort -rn | head -5

# Step 3: Check for requests to admin paths
echo ""
echo "--- Requests to /admin ---"
grep "/admin" access.log | awk '{print $1}' | sort | uniq -c | sort -rn

# Step 4: Check if blocked IPs kept trying
echo ""
echo "--- Auth errors from app log ---"
grep "auth" app_errors.log | grep -i "error\|block"
```

### Scenario 2: Post-Deployment Health Check

```bash
echo "=== Scenario: We just deployed v2.3.1 — is everything OK? ==="

# Step 1: Find the deployment timestamp
echo "--- Deployment timeline ---"
grep "deploy" app_errors.log

# Step 2: Check for errors after deployment
echo ""
echo "--- Errors after 11:00 (deployment time) ---"
awk '$2 >= "11:00:00" && /ERROR|CRITICAL/' app_errors.log

# Step 3: Check API error rate
echo ""
echo "--- Error responses count ---"
awk '$9 >= 500 {count++} END {printf "Server errors: %d out of 500 total (%0.1f%%)\n", count, count/500*100}' access.log
```

### Scenario 3: Disk Space Emergency

```bash
echo "=== Scenario: Disk alert fired! What do we do? ==="

# Step 1: Check the alert
grep "CRITICAL.*disk" app_errors.log

# Step 2: In real life, you'd run these:
echo ""
echo "--- Disk usage ---"
df -h

echo ""
echo "--- Largest files in common log directories ---"
du -sh /var/log/* 2>/dev/null | sort -rh | head -10

echo ""
echo "--- Largest files in current directory ---"
ls -lhS ~/devops-labs/module-01/log-analysis/ | head -10
```

---

## 🔬 Exercise 5: Building a Log Analysis One-Liner

### The Ultimate Access Log Summary

```bash
echo "============================================"
echo "   ACCESS LOG ANALYSIS REPORT"
echo "   Generated: $(date)"
echo "============================================"
echo ""

echo "📊 Total Requests: $(wc -l < access.log)"
echo ""

echo "📈 Status Code Distribution:"
awk '{print $9}' access.log | sort | uniq -c | sort -rn | while read count code; do
    printf "   HTTP %s: %5d requests\n" "$code" "$count"
done
echo ""

echo "🌐 Top 5 Client IPs:"
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -5 | while read count ip; do
    printf "   %-18s %5d requests\n" "$ip" "$count"
done
echo ""

echo "📁 Top 5 Requested Paths:"
awk '{print $7}' access.log | sort | uniq -c | sort -rn | head -5 | while read count path; do
    printf "   %-30s %5d requests\n" "$path" "$count"
done
echo ""

echo "⚠️  Error Requests (4xx + 5xx):"
awk '$9 >= 400 {print $9, $7}' access.log | sort | uniq -c | sort -rn | head -10 | while read count code path; do
    printf "   HTTP %s %-30s %5d times\n" "$code" "$path" "$count"
done
echo ""

echo "🤖 User Agents:"
awk -F'"' '{print $6}' access.log | sort | uniq -c | sort -rn | while read count agent; do
    printf "   %-35s %5d requests\n" "$agent" "$count"
done

echo ""
echo "============================================"
```

Save this as a reusable script:

```bash
cat > ~/devops-labs/module-01/log-analysis/analyze_access_log.sh << 'ANALYZER'
#!/bin/bash
# Usage: ./analyze_access_log.sh <access.log>

LOG_FILE="${1:-access.log}"

if [ ! -f "$LOG_FILE" ]; then
    echo "Error: File '$LOG_FILE' not found!"
    exit 1
fi

TOTAL=$(wc -l < "$LOG_FILE")

echo "=== Log Analysis: $LOG_FILE ==="
echo "Total Requests: $TOTAL"
echo ""
echo "Status Codes:"
awk '{print $9}' "$LOG_FILE" | sort | uniq -c | sort -rn
echo ""
echo "Top 10 IPs:"
awk '{print $1}' "$LOG_FILE" | sort | uniq -c | sort -rn | head -10
echo ""
echo "Top 10 Paths:"
awk '{print $7}' "$LOG_FILE" | sort | uniq -c | sort -rn | head -10
ANALYZER

chmod +x ~/devops-labs/module-01/log-analysis/analyze_access_log.sh

# Run it
./analyze_access_log.sh access.log
```

---

## 🧨 Break It: Text Processing Pitfalls

### Pitfall 1: Grepping Without Enough Context

```bash
# BAD: This catches false positives
grep "error" access.log | head -5
# Might match "Internal Server Error" in the path, user-agent, etc.

# GOOD: Be specific about what you're searching
grep '" 500 ' access.log    # Status code 500 specifically
awk '$9 == 500' access.log   # Even better — field-based
```

### Pitfall 2: Forgetting to Sort Before uniq

```bash
# BAD: uniq only removes ADJACENT duplicates
echo -e "apple\nbanana\napple\nbanana" | uniq
# Output: apple, banana, apple, banana (NOT deduplicated!)

# GOOD: Always sort first
echo -e "apple\nbanana\napple\nbanana" | sort | uniq
# Output: apple, banana
```

---

## ✅ Final Validation

You've completed this lab when you can:

- [ ] Use grep with context flags (-A, -B, -C) for debugging
- [ ] Extract specific columns with awk
- [ ] Filter data with awk conditions
- [ ] Build a complete log analysis pipeline using pipes
- [ ] Create a reusable log analysis script
- [ ] Analyze logs to answer: "Who is hitting my server?", "Are there errors?", "What changed after deployment?"
- [ ] Avoid common pitfalls (grep specificity, sort before uniq)

---

## 💡 Key Takeaways

1. **Pipes are power** — chain simple tools together for complex analysis
2. **grep for finding, awk for extracting, sed for transforming**
3. **Always sort before uniq** — `uniq` only works on adjacent lines
4. **Context matters** — use `grep -C 3` to see what happened around an error
5. These skills directly transfer to Prometheus queries, Elasticsearch queries, and every log system you'll use

---

[← Previous Lab](./lab-03-processes-services.md) | [Back to Module README](../README.md)

