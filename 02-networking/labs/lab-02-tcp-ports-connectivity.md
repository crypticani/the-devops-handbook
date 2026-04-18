<![CDATA[# Lab 02: TCP, Ports & Connectivity Testing

## 🎯 Objective

Master TCP connectivity testing, port scanning, and the debugging techniques you'll use daily to diagnose "I can't connect to X" issues in production.

---

## 📋 Prerequisites

- Completed Lab 01 (DNS Deep Dive)
- Ubuntu 22.04+ with `sudo` access
- Nginx installed (`sudo apt install -y nginx`)

```bash
# Install required tools
sudo apt install -y nginx netcat-openbsd curl net-tools nmap traceroute
```

---

## 🔬 Exercise 1: Understanding Ports and Listening Services

### Step 1: See What's Listening on Your System

```bash
# Show all TCP listening ports with process info
sudo ss -tlnp

# Output explained:
# State    Recv-Q Send-Q  Local Address:Port   Peer Address:Port  Process
# LISTEN   0      511       0.0.0.0:80           0.0.0.0:*       users:(("nginx",pid=1234,...))
# LISTEN   0      128       0.0.0.0:22           0.0.0.0:*       users:(("sshd",pid=567,...))

# Key details:
# 0.0.0.0:80 = Listening on ALL interfaces on port 80
# 127.0.0.1:80 = Listening ONLY on localhost (can't be reached from outside!)
# :::80 = Listening on ALL interfaces for IPv6

# Show UDP listeners too
sudo ss -ulnp

# Check if a specific port is in use
ss -tlnp | grep :80
ss -tlnp | grep :22
ss -tlnp | grep :443
```

### Step 2: The Critical Difference — 0.0.0.0 vs 127.0.0.1

```bash
# Start a server on localhost only
python3 -m http.server 9001 --bind 127.0.0.1 &
PID1=$!

# Start a server on all interfaces
python3 -m http.server 9002 --bind 0.0.0.0 &
PID2=$!

# Check the difference
ss -tlnp | grep -E "9001|9002"
# 9001 → 127.0.0.1:9001 (only accessible from this machine)
# 9002 → 0.0.0.0:9002 (accessible from any network)

# Test local access (both work)
curl -s http://127.0.0.1:9001 > /dev/null && echo "9001: accessible locally" || echo "9001: not accessible locally"
curl -s http://127.0.0.1:9002 > /dev/null && echo "9002: accessible locally" || echo "9002: not accessible locally"

# From another machine, only 9002 would be accessible
# 9001 would give "Connection refused"

# This is a VERY common production issue:
# "The app works when I test it on the server, but not from outside"
# → Check if it's bound to 127.0.0.1 instead of 0.0.0.0

# Clean up
kill $PID1 $PID2 2>/dev/null
```

---

## 🔬 Exercise 2: TCP Connection Testing

### Step 1: Test Connectivity with netcat

```bash
# Make sure Nginx is running
sudo systemctl start nginx

# Test connection to Nginx (port 80)
nc -zv localhost 80
# Expected: Connection to localhost 80 port [tcp/http] succeeded!

# Test a closed/unused port
nc -zv localhost 9999
# Expected: Connection refused

# Test with timeout
nc -zv -w 3 localhost 80
# -w 3 = 3 second timeout

# Scan a range of ports
nc -zv localhost 20-25
# Shows which ports are open in the range

# Test a remote host
nc -zv google.com 443
# Expected: Connection to google.com 443 port [tcp/https] succeeded!

nc -zv google.com 22
# Expected: Connection timed out (Google doesn't run SSH publicly)
```

### Step 2: Simulate a Client-Server Connection

```bash
# Terminal 1: Start a TCP listener
nc -l 12345
# This listens on port 12345 and waits for connections

# Terminal 2 (open a new terminal):
nc localhost 12345
# Type a message and press Enter
# You should see it appear in Terminal 1!

# This demonstrates:
# - How TCP connections work (client connects to server)
# - Port listeners and connections
# - That data flows over the TCP channel

# Press Ctrl+C in both terminals to stop
```

### Step 3: HTTP Request with netcat (Understanding HTTP Raw)

```bash
# Hand-craft an HTTP request with netcat
printf "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n" | nc localhost 80

# You'll see the raw HTTP response:
# HTTP/1.1 200 OK
# Server: nginx/1.24.0 (Ubuntu)
# Content-Type: text/html
# ... (headers)
#
# <!DOCTYPE html>
# ... (the Nginx welcome page HTML)

# This is EXACTLY what curl does, but curl handles the protocol for you
```

---

## 🔬 Exercise 3: curl for HTTP Debugging

### Step 1: Verbose HTTP Request

```bash
# The most important debugging flag: -v (verbose)
curl -v http://localhost 2>&1

# This shows:
# > GET / HTTP/1.1            ← Your request
# > Host: localhost            ← Request headers
# > User-Agent: curl/...      
# > Accept: */*
# >
# < HTTP/1.1 200 OK           ← Server response
# < Server: nginx/1.24.0      ← Response headers
# < Content-Type: text/html

# The > prefix = data YOU sent
# The < prefix = data the SERVER sent
# This level of detail is ESSENTIAL for debugging HTTP issues
```

### Step 2: Timing Analysis

```bash
# Measure WHERE time is spent in a request
curl -o /dev/null -s -w "\
  DNS Lookup:   %{time_namelookup}s\n\
  TCP Connect:  %{time_connect}s\n\
  TLS Setup:    %{time_appconnect}s\n\
  Start Transfer: %{time_starttransfer}s\n\
  Total Time:   %{time_total}s\n\
  HTTP Code:    %{http_code}\n\
  Size:         %{size_download} bytes\n\
" http://localhost

# Expected output (values approximate):
#   DNS Lookup:   0.001s     ← DNS resolution
#   TCP Connect:  0.001s     ← TCP handshake
#   TLS Setup:    0.000s     ← No TLS for HTTP
#   Start Transfer: 0.002s   ← Time to first byte (TTFB)
#   Total Time:   0.003s     ← Complete response
#   HTTP Code:    200
#   Size:         612 bytes

# Now try with an external site (HTTPS)
curl -o /dev/null -s -w "\
  DNS Lookup:   %{time_namelookup}s\n\
  TCP Connect:  %{time_connect}s\n\
  TLS Setup:    %{time_appconnect}s\n\
  Start Transfer: %{time_starttransfer}s\n\
  Total Time:   %{time_total}s\n\
  HTTP Code:    %{http_code}\n" \
  https://example.com

# Notice TLS Setup is no longer 0 — that's the TLS handshake time
```

### Step 3: Common curl Patterns for DevOps

```bash
# Health check (just status code)
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost)
echo "Health check: $STATUS"
if [ "$STATUS" -eq 200 ]; then
    echo "✅ Application is healthy"
else
    echo "❌ Application returned HTTP $STATUS"
fi

# Post JSON data
curl -X POST http://httpbin.org/post \
  -H "Content-Type: application/json" \
  -d '{"name": "DevOps", "version": 2}'

# Follow redirects
curl -L http://httpbin.org/redirect/3

# Download with progress
curl -# -O https://example.com/index.html

# Authentication header
curl -H "Authorization: Bearer my-token" http://httpbin.org/headers

# Custom timeout (important for scripts!)
curl --connect-timeout 5 --max-time 10 http://localhost
```

---

## 🔬 Exercise 4: Network Path Analysis

### Step 1: traceroute — Trace the Network Path

```bash
# Trace route to a public server
traceroute 8.8.8.8

# Each line is a "hop" (a router along the path)
# Format: HOP_NUMBER  ROUTER_NAME (IP)  LATENCY1  LATENCY2  LATENCY3

# What to look for:
# - Increasing latency at a specific hop = that hop is slow
# - "* * *" = that router doesn't respond (not always a problem)
# - Sudden large latency jump = bottleneck found

# UDP-based traceroute (default on Linux)
traceroute google.com

# ICMP-based traceroute (closer to ping)
sudo traceroute -I google.com

# TCP-based traceroute (useful when ICMP is blocked)
sudo traceroute -T -p 443 google.com
```

### Step 2: Monitor Network Connections in Real-Time

```bash
# Watch active connections
watch -n 1 'ss -tnp | head -20'
# Updates every second — shows active TCP connections

# Count connections by state
ss -s
# Shows: established, closed, time-wait, etc.

# Watch connections to a specific port
watch -n 1 'ss -tnp | grep :80 | wc -l'
# Shows how many connections Nginx is handling
```

---

## 🔬 Exercise 5: Firewall Testing

### Step 1: Test with UFW

```bash
# Check firewall status
sudo ufw status verbose

# If inactive, let's set it up carefully
# ALWAYS allow SSH first!
sudo ufw allow 22/tcp

# Enable the firewall
sudo ufw enable

# Allow HTTP (Nginx)
sudo ufw allow 80/tcp

# Verify
sudo ufw status numbered

# Test: Can we still reach Nginx?
curl -s -o /dev/null -w "%{http_code}" http://localhost
# Expected: 200

# Now block port 80
sudo ufw deny 80/tcp

# Test again — from localhost it still works (UFW doesn't block lo)
curl -s -o /dev/null -w "%{http_code}" http://localhost
# Still 200 from localhost

# But from another machine or using the actual IP:
# curl http://<YOUR_IP>:80
# Would be blocked!

# Re-allow port 80
sudo ufw delete deny 80/tcp
sudo ufw allow 80/tcp

# Verify rule set
sudo ufw status verbose
```

### Step 2: Test Service on a Non-Standard Port

```bash
# Start a service on port 8888
python3 -m http.server 8888 &
PID=$!

# Test connectivity
curl -s -o /dev/null -w "%{http_code}" http://localhost:8888
# Expected: 200

# This port is NOT in our firewall rules
# From outside, it would be blocked by default-deny policy

# Add the rule
sudo ufw allow 8888/tcp

# Now it would be accessible from outside too

# Clean up
kill $PID
sudo ufw delete allow 8888/tcp
```

---

## 🧨 Break It: Network Debugging Challenge

### Challenge 1: "Connection Refused"

```bash
# Stop Nginx
sudo systemctl stop nginx

# Try to connect
curl -v http://localhost 2>&1 | head -10
# You'll see: "Connection refused"

# Debug steps:
echo "=== Debugging 'Connection Refused' ==="

# 1. Is the service running?
systemctl is-active nginx
# Output: inactive ← FOUND IT

# 2. Check if anything is listening on port 80
ss -tlnp | grep :80
# Output: nothing ← Confirms no one is listening

# 3. Fix: Start the service
sudo systemctl start nginx

# 4. Verify
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost
# Expected: HTTP 200
```

### Challenge 2: "Connection Timed Out"

```bash
# Simulate a timeout using iptables (the firewall underneath UFW)
# Block traffic to port 80 silently (DROP instead of REJECT)
sudo iptables -A INPUT -p tcp --dport 80 -j DROP

# Try to connect (this will hang, then timeout)
curl --connect-timeout 5 http://localhost 2>&1
# Output: Connection timed out after 5001 milliseconds

# The difference:
# "Connection refused" = server received your packet and said NO
# "Connection timed out" = your packet was silently dropped (no response)

# Debug:
# 1. Can I ping the server? (Layer 3)
ping -c 1 localhost
# Yes → Network is fine

# 2. Is the service running?
systemctl is-active nginx
# active ← Service is running!

# 3. Is it listening on the port?
ss -tlnp | grep :80
# Yes ← It's listening!

# 4. Could it be a firewall?
sudo iptables -L INPUT -n -v | grep "80"
# A DROP rule! ← FOUND IT

# Fix: Remove the blocking rule
sudo iptables -D INPUT -p tcp --dport 80 -j DROP

# Verify
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost
# Expected: HTTP 200
```

### Challenge 3: Wrong Bind Address

```bash
# Start a service bound to localhost only
python3 -m http.server 7777 --bind 127.0.0.1 &
PID=$!

# Works from localhost
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:7777
# Expected: HTTP 200

# Check what it's bound to
ss -tlnp | grep 7777
# Shows: 127.0.0.1:7777 ← Only localhost!

# From another machine (or using machine's IP), this would fail
# curl http://<machine-ip>:7777 → Connection refused

# The fix: Bind to 0.0.0.0 (all interfaces)
kill $PID
python3 -m http.server 7777 --bind 0.0.0.0 &
PID=$!

ss -tlnp | grep 7777
# Now shows: 0.0.0.0:7777 ← All interfaces!

kill $PID
```

---

## ✅ Final Validation

You've completed this lab when you can:

- [ ] List all listening ports and identify which services own them
- [ ] Explain the difference between `0.0.0.0` and `127.0.0.1` binding
- [ ] Test TCP connectivity with `nc` and `curl`
- [ ] Use `curl -v` to debug HTTP request/response details
- [ ] Measure request timing with `curl -w`
- [ ] Use `traceroute` to trace the network path
- [ ] Distinguish between "Connection refused" and "Connection timed out"
- [ ] Debug firewall issues using `iptables` and `ufw`
- [ ] Write a basic health check script using `curl`

---

## 💡 Key Takeaways

1. **"Connection refused"** = service not running or wrong port; **"timed out"** = firewall or network issue
2. **0.0.0.0 vs 127.0.0.1** is the #1 "it works locally but not remotely" cause
3. **`curl -v`** is your best friend for HTTP debugging — use it daily
4. Always check **firewall rules** when connectivity fails despite service being up
5. **Timing analysis** with `curl -w` helps pinpoint latency sources (DNS, TCP, TLS, server)

---

[← Previous Lab](./lab-01-dns-deep-dive.md) | [Next Lab: Nginx Reverse Proxy Setup →](./lab-03-nginx-reverse-proxy.md)
]]>
