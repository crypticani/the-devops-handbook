<![CDATA[# Module 02: Networking

> *"If you don't understand networking, every single production issue will confuse you. Networking is the circulatory system of every modern application."*

---

## 🎯 Why This Module Matters

**Every DevOps problem is a networking problem — until proven otherwise.**

When a service is "down," when containers can't talk to each other, when a deployment fails, when latency spikes, when a database connection times out — the first thing you investigate is the network.

**In real-world DevOps work**, you will:
- Debug "connection refused" and "connection timed out" errors
- Configure DNS records for domain management
- Set up reverse proxies (Nginx) to route traffic
- Configure firewalls and security groups in the cloud
- Troubleshoot container networking in Docker and Kubernetes
- Understand load balancers, CDNs, and TLS certificates

Without networking skills, you are **blind** to most production issues.

---

## 📚 Table of Contents

1. [The OSI Model — Simplified](#1-the-osi-model--simplified)
2. [IP Addressing and Subnets](#2-ip-addressing-and-subnets)
3. [TCP vs UDP](#3-tcp-vs-udp)
4. [Ports — The Application Doorway](#4-ports--the-application-doorway)
5. [DNS — The Internet's Phone Book](#5-dns--the-internets-phone-book)
6. [HTTP/HTTPS — The Language of the Web](#6-httphttps--the-language-of-the-web)
7. [Firewalls and Network Security](#7-firewalls-and-network-security)
8. [Network Troubleshooting Tools](#8-network-troubleshooting-tools)
9. [Reverse Proxies and Load Balancers](#9-reverse-proxies-and-load-balancers)
10. [Common Mistakes and Anti-Patterns](#10-common-mistakes-and-anti-patterns)
11. [Debugging Mindset](#11-debugging-mindset)
12. [Security Considerations](#12-security-considerations)
13. [Interview Insights](#13-interview-insights)

---

## 1. The OSI Model — Simplified

You don't need to memorize all 7 layers for DevOps. You need to understand what happens **in practice**.

### The Practical Layers

```
Layer 7 — Application     HTTP, HTTPS, DNS, SSH, SMTP
                          "What protocol are we using?"
                          
Layer 4 — Transport        TCP, UDP
                          "How do we deliver data reliably?"
                          "What PORT are we connecting to?"
                          
Layer 3 — Network          IP (IPv4, IPv6)
                          "What IP ADDRESS are we sending to?"
                          "How does data get ROUTED?"
                          
Layer 2 — Data Link        Ethernet, MAC addresses
                          "How do devices talk on the same network?"
                          
Layer 1 — Physical         Cables, WiFi, hardware
                          "Is the cable plugged in?"
```

### How Data Actually Flows

When you type `https://api.example.com/users` in your browser:

```
Your Browser
    │
    ▼
1. DNS Resolution (Layer 7)
   "api.example.com" → 93.184.216.34
    │
    ▼
2. TCP Connection (Layer 4)
   Three-way handshake: SYN → SYN-ACK → ACK
   Connect to port 443 (HTTPS)
    │
    ▼
3. TLS Handshake (Layer 6/7)
   Verify certificate, establish encrypted connection
    │
    ▼
4. HTTP Request (Layer 7)
   GET /users HTTP/1.1
   Host: api.example.com
    │
    ▼
5. IP Routing (Layer 3)
   Packet travels through routers to reach 93.184.216.34
    │
    ▼
6. Server processes request
    │
    ▼
7. HTTP Response travels back through the same layers
```

> **💡 DevOps Impact**: When troubleshooting, you work **bottom-up**. Can you ping it? (Layer 3) Can you connect to the port? (Layer 4) Is the HTTP response correct? (Layer 7)

---

## 2. IP Addressing and Subnets

### IPv4 Addresses

```
An IPv4 address: 192.168.1.100
                 ├─────┤ ├──┤
                 Network  Host
                 Portion  Portion (depends on subnet mask)
```

### Private vs Public IP Ranges

| Range | Class | Use | Example |
|-------|-------|-----|---------|
| `10.0.0.0/8` | Class A | Large private networks, cloud VPCs | `10.0.1.50` |
| `172.16.0.0/12` | Class B | Docker default bridge network | `172.17.0.2` |
| `192.168.0.0/16` | Class C | Home/office networks | `192.168.1.100` |
| `127.0.0.0/8` | Loopback | localhost (this machine) | `127.0.0.1` |
| Everything else | Public | Internet-routable | `93.184.216.34` |

### Subnet Masks (CIDR Notation)

```
CIDR     Subnet Mask       Usable Hosts    Common Use
/32      255.255.255.255   1               Single host
/24      255.255.255.0     254             Small network, typical for subnets
/16      255.255.0.0       65,534          Medium network
/8       255.0.0.0         16,777,214      Large network
```

**CIDR in practice:**
```bash
# A /24 network: 192.168.1.0/24
# Network: 192.168.1.0
# First usable: 192.168.1.1
# Last usable: 192.168.1.254
# Broadcast: 192.168.1.255
# Total usable: 254 addresses

# In AWS: You create a VPC with 10.0.0.0/16 (65k addresses)
# Then create subnets like:
#   10.0.1.0/24  (public subnet - 254 hosts)
#   10.0.2.0/24  (private subnet - 254 hosts)
#   10.0.3.0/24  (database subnet - 254 hosts)
```

### Check Your IP Information

```bash
# Your IP addresses
ip addr show
# or shorter
ip a

# Just IPv4
ip -4 addr show

# Your default gateway (router)
ip route show
# default via 192.168.1.1 dev eth0 ...

# Your DNS servers
cat /etc/resolv.conf
```

---

## 3. TCP vs UDP

### TCP — Transmission Control Protocol

```
TCP = Reliable delivery (like registered mail)

Three-Way Handshake:
Client              Server
  │── SYN ────────────▶│    "I want to connect"
  │◀── SYN-ACK ────────│    "OK, I acknowledge"
  │── ACK ────────────▶│    "Great, we're connected"
  │                     │
  │── Data ───────────▶│    Data transfer begins
  │◀── ACK ────────────│    "Got it"
  │                     │
  │── FIN ────────────▶│    "I'm done"
  │◀── ACK ────────────│    "OK, goodbye"

Features:
✅ Guaranteed delivery (retransmits lost packets)
✅ Ordered delivery (packets arrive in order)
✅ Error checking (checksums)
✅ Flow control (doesn't overwhelm receiver)

Used by: HTTP, HTTPS, SSH, FTP, SMTP, databases
```

### UDP — User Datagram Protocol

```
UDP = Fast delivery, no guarantees (like regular mail)

Client              Server
  │── Data ───────────▶│    "Here's some data"
  │── Data ───────────▶│    "Here's more data"
  │── Data ───────────▶│    "And more"
  (No acknowledgment, no retransmission)

Features:
✅ Fast (no handshake, no waiting for ACKs)
✅ Low overhead
❌ No delivery guarantee
❌ No ordering guarantee

Used by: DNS (queries), video streaming, gaming, VoIP, monitoring (StatsD)
```

### Why This Matters for DevOps

| Scenario | Protocol | Why |
|----------|----------|-----|
| Web traffic | TCP | Reliability required for page loads |
| Database connections | TCP | Data integrity is critical |
| DNS queries | UDP | Speed matters, small packets |
| Prometheus metrics | TCP (HTTP) | Need complete metric data |
| Log shipping (syslog) | UDP or TCP | UDP for speed, TCP for reliability |
| Container health checks | TCP | Need to know if service is alive |

---

## 4. Ports — The Application Doorway

An IP address gets you to a machine. A port gets you to a **specific service** on that machine.

### Well-Known Ports

| Port | Service | DevOps Use |
|------|---------|------------|
| **22** | SSH | Remote server administration |
| **25** | SMTP | Email sending |
| **53** | DNS | Name resolution |
| **80** | HTTP | Web traffic (unencrypted) |
| **443** | HTTPS | Web traffic (encrypted) — **always use this** |
| **3000** | Grafana (default) | Monitoring dashboards |
| **3306** | MySQL | Database |
| **5432** | PostgreSQL | Database |
| **5601** | Kibana | Log visualization |
| **6379** | Redis | Caching |
| **8080** | HTTP (alt) | Java apps, development servers |
| **8443** | HTTPS (alt) | Alternative HTTPS |
| **9090** | Prometheus | Metric collection |
| **9200** | Elasticsearch | Search/logging |
| **9090** | Prometheus | Metrics |
| **27017** | MongoDB | NoSQL database |

### Checking Open Ports

```bash
# List all listening ports
ss -tlnp
# t = TCP
# l = Listening
# n = Numeric (don't resolve names)
# p = Show process

# Example output:
# State  Recv-Q Send-Q  Local Address:Port  Peer Address:Port  Process
# LISTEN 0      511        0.0.0.0:80         0.0.0.0:*       users:(("nginx",...))
# LISTEN 0      128        0.0.0.0:22         0.0.0.0:*       users:(("sshd",...))

# Check if a specific port is open
ss -tlnp | grep :80

# Alternative: netstat (older, but still widely used)
sudo netstat -tlnp

# Check what's using a specific port
sudo lsof -i :8080
```

---

## 5. DNS — The Internet's Phone Book

### How DNS Works

```
You type: www.example.com
                │
                ▼
    ┌─── Browser DNS Cache ───┐
    │  Do I already know this? │
    │  YES → Use cached IP     │
    │  NO  → Ask OS resolver   │
    └──────────┬───────────────┘
               │
    ┌──── OS Resolver ────────┐
    │  Check /etc/hosts first  │
    │  Check local DNS cache  │
    │  NO → Ask DNS server     │
    └──────────┬───────────────┘
               │
    ┌─── Recursive Resolver ──┐
    │  (Your ISP or 8.8.8.8)  │
    │  Ask Root → TLD → Auth  │
    └──────────┬───────────────┘
               │
    ┌── Root Servers (.com?) ─┐
    │  "Ask the .com servers" │
    └──────────┬───────────────┘
               │
    ┌── TLD Servers ──────────┐
    │  example.com NS →       │
    │  ns1.example.com        │
    └──────────┬───────────────┘
               │
    ┌── Auth NS (ns1.example) ┐
    │  www.example.com        │
    │  → 93.184.216.34        │
    └──────────────────────────┘
```

### DNS Record Types

| Type | Purpose | Example | DevOps Use |
|------|---------|---------|------------|
| **A** | Domain → IPv4 address | `example.com → 93.184.216.34` | Point domain to server |
| **AAAA** | Domain → IPv6 address | `example.com → 2606:2800:...` | IPv6 support |
| **CNAME** | Domain → another domain | `www.example.com → example.com` | Aliases, CDN setup |
| **MX** | Mail server for domain | `example.com → mail.example.com` | Email routing |
| **TXT** | Arbitrary text | `example.com → "v=spf1 ..."` | SPF, DKIM, domain verification |
| **NS** | Nameserver for domain | `example.com → ns1.example.com` | DNS delegation |
| **SRV** | Service location | `_sip._tcp.example.com → ...` | Service discovery |
| **PTR** | IP → Domain (reverse) | `34.216.184.93 → example.com` | Reverse DNS lookups |

### DNS Tools

```bash
# Resolve a domain
dig example.com
# Look for the ANSWER SECTION:
# example.com.  3600  IN  A  93.184.216.34

# Short format
dig +short example.com
# Output: 93.184.216.34

# Specific record type
dig example.com MX
dig example.com NS
dig example.com TXT

# Trace the full resolution path
dig +trace example.com

# Reverse DNS lookup
dig -x 8.8.8.8

# Alternative: nslookup
nslookup example.com

# Alternative: host (simplest)
host example.com

# Check local DNS configuration
cat /etc/resolv.conf

# The local hosts file (overrides DNS)
cat /etc/hosts
# 127.0.0.1    localhost
# you can add: 192.168.1.50  myapp.local
```

### DNS Caching and TTL

```bash
# TTL (Time To Live) controls how long a DNS record is cached
dig example.com | grep -A 1 "ANSWER SECTION"
# example.com.  3600  IN  A  93.184.216.34
#               ^^^^
#               TTL in seconds (3600 = 1 hour)

# When changing DNS records:
# 1. Lower TTL to 60 seconds (before the change)
# 2. Wait for old TTL to expire
# 3. Make the DNS change
# 4. Verify with dig
# 5. Raise TTL back to normal (300-3600 seconds)
```

### `/etc/hosts` — Local DNS Override

```bash
# This file is checked BEFORE DNS servers
# Useful for testing, development, and blocking

# Example: Test a new server before changing DNS
echo "10.0.1.50 staging.myapp.com" | sudo tee -a /etc/hosts

# Now "staging.myapp.com" resolves to 10.0.1.50 on this machine only
ping staging.myapp.com

# Remove when done
sudo sed -i '/staging.myapp.com/d' /etc/hosts
```

---

## 6. HTTP/HTTPS — The Language of the Web

### HTTP Request/Response

```
CLIENT REQUEST:
┌────────────────────────────────────────┐
│ GET /api/v1/users HTTP/1.1             │  ← Method + Path + Version
│ Host: api.example.com                  │  ← Required header
│ Authorization: Bearer eyJhbGc...       │  ← Auth token
│ Accept: application/json               │  ← Desired response format
│ User-Agent: curl/7.88.1               │  ← Client info
│                                        │
│ [empty body for GET requests]          │
└────────────────────────────────────────┘

SERVER RESPONSE:
┌────────────────────────────────────────┐
│ HTTP/1.1 200 OK                        │  ← Status code
│ Content-Type: application/json         │  ← Response format
│ Content-Length: 256                     │  ← Body size
│ X-Request-Id: abc-123                  │  ← Tracking header
│                                        │
│ {"users": [{"id": 1, "name": "..."}]} │  ← Body
└────────────────────────────────────────┘
```

### HTTP Methods

| Method | Purpose | Idempotent? | Example |
|--------|---------|-------------|---------|
| **GET** | Read data | Yes | `GET /users` |
| **POST** | Create data | No | `POST /users` (with body) |
| **PUT** | Replace data | Yes | `PUT /users/1` (full update) |
| **PATCH** | Partial update | Not always | `PATCH /users/1` (partial) |
| **DELETE** | Remove data | Yes | `DELETE /users/1` |
| **HEAD** | Get headers only | Yes | Health checks |
| **OPTIONS** | Get allowed methods | Yes | CORS preflight |

### HTTP Status Codes (Memorize These!)

```
1xx — Informational
2xx — Success
  200 OK                    — Request succeeded
  201 Created               — Resource created (POST response)
  204 No Content            — Success, no body (DELETE response)

3xx — Redirection
  301 Moved Permanently     — URL changed, update your links
  302 Found                 — Temporary redirect
  304 Not Modified          — Use your cached version

4xx — Client Error (YOUR fault)
  400 Bad Request           — Malformed request
  401 Unauthorized          — Not authenticated (need to log in)
  403 Forbidden             — Authenticated but no permission
  404 Not Found             — Resource doesn't exist
  405 Method Not Allowed    — Wrong HTTP method
  408 Request Timeout       — Client took too long
  429 Too Many Requests     — Rate limited

5xx — Server Error (SERVER's fault)
  500 Internal Server Error — Generic server error
  502 Bad Gateway           — Upstream server returned invalid response
  503 Service Unavailable   — Server overloaded or in maintenance
  504 Gateway Timeout       — Upstream server didn't respond in time
```

### Making HTTP Requests with curl

```bash
# Basic GET request
curl http://httpbin.org/get

# GET with verbose output (shows headers — ESSENTIAL for debugging)
curl -v http://httpbin.org/get

# GET with specific headers
curl -H "Authorization: Bearer mytoken" http://httpbin.org/headers

# POST with JSON body
curl -X POST http://httpbin.org/post \
  -H "Content-Type: application/json" \
  -d '{"name": "DevOps", "type": "handbook"}'

# Just get the response headers
curl -I http://httpbin.org/get

# Get just the status code
curl -s -o /dev/null -w "%{http_code}" http://httpbin.org/get

# Follow redirects
curl -L http://httpbin.org/redirect/3

# Download a file
curl -O https://example.com/file.tar.gz

# Timeout (important for health checks)
curl --connect-timeout 5 --max-time 10 http://httpbin.org/delay/30
```

### HTTPS and TLS

```
HTTPS = HTTP + TLS (Transport Layer Security)

TLS Handshake:
Client                          Server
  │── ClientHello ───────────────▶│  "I support TLS 1.3, these ciphers..."
  │◀── ServerHello ───────────────│  "Let's use TLS 1.3, this cipher"
  │◀── Certificate ───────────────│  "Here's my certificate (proves identity)"
  │── Verify Certificate          │  (Client checks with CA)
  │── Key Exchange ──────────────▶│  (Establish shared secret)
  │◀── Finished ──────────────────│
  │── Encrypted Data ────────────▶│  (Everything is now encrypted)
```

```bash
# Check TLS certificate details
openssl s_client -connect example.com:443 -brief

# Check certificate expiry
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -dates

# Check full certificate chain
curl -vI https://example.com 2>&1 | grep -A 5 "SSL certificate"
```

---

## 7. Firewalls and Network Security

### UFW (Uncomplicated Firewall) — Ubuntu's Firewall

```bash
# Check status
sudo ufw status verbose

# IMPORTANT: Enable SSH BEFORE enabling the firewall!
sudo ufw allow 22/tcp    # SSH
sudo ufw enable

# Common rules
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw allow 8080/tcp   # Application port

# Allow from specific IP only
sudo ufw allow from 10.0.1.0/24 to any port 5432   # PostgreSQL from internal network only

# Deny a port
sudo ufw deny 3306/tcp    # Block MySQL from outside

# Delete a rule
sudo ufw delete allow 8080/tcp

# Reset all rules
sudo ufw reset

# Best practice: Default deny incoming
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

### iptables (Lower Level — Know the Concept)

```bash
# List all rules
sudo iptables -L -n -v

# iptables uses chains:
# INPUT    — Traffic coming IN to the server
# OUTPUT   — Traffic going OUT from the server
# FORWARD  — Traffic passing THROUGH the server

# Docker heavily uses iptables for container networking
# That's why you sometimes see Docker-related rules in iptables
sudo iptables -L -n -v | head -30
```

### 🔐 Network Security Principles

1. **Default deny** — Block everything, then allow what's needed
2. **Least privilege** — Only open ports that are required
3. **Defense in depth** — Firewall + application security + encryption
4. **Encrypt in transit** — Use HTTPS/TLS everywhere
5. **Segment networks** — Databases should NOT be on public networks

---

## 8. Network Troubleshooting Tools

### The Troubleshooting Ladder

```
Problem: "I can't reach the server!"

Step 1: Can I resolve the DNS name?
   dig api.example.com

Step 2: Can I reach the IP? (Layer 3)
   ping 93.184.216.34

Step 3: Can I reach the port? (Layer 4)
   telnet 93.184.216.34 443
   nc -zv 93.184.216.34 443

Step 4: Does the application respond? (Layer 7)
   curl -v https://api.example.com

Step 5: Is the path correct?
   traceroute 93.184.216.34
```

### ping — Basic Connectivity

```bash
# Test if a host is reachable
ping -c 4 8.8.8.8
# -c 4 = send 4 packets (default is infinite)

# What to look for:
# - "Request timed out" = host is unreachable or blocking ICMP
# - "Destination host unreachable" = routing problem
# - High latency (>100ms for same region) = network issue
# - Packet loss > 0% = network instability

# Note: Many servers block ICMP (ping)
# A failed ping DOESN'T always mean the service is down!
```

### traceroute — Path Discovery

```bash
# See the network path to a destination
traceroute 8.8.8.8
# or
tracepath 8.8.8.8

# Each line is a "hop" (router along the path)
# High latency on a specific hop = that router/link is the bottleneck
# "* * *" = that router doesn't respond to traceroute (not necessarily a problem)
```

### netcat (nc) — Swiss Army Knife

```bash
# Test if a port is open (most useful)
nc -zv 10.0.1.5 22
# Connection to 10.0.1.5 22 port [tcp/ssh] succeeded!

nc -zv 10.0.1.5 8080
# Connection refused = service not running on that port

# Scan multiple ports
nc -zv 10.0.1.5 20-25

# Create a simple TCP listener (testing)
nc -l 9999
# On another terminal: nc localhost 9999
# You can now type messages between them
```

### ss — Socket Statistics (Replaces netstat)

```bash
# All listening TCP ports
ss -tlnp

# All established connections
ss -tnp

# Connections to a specific port
ss -tnp | grep :443

# Count connections by state
ss -s

# Monitor connection states over time
watch -n 1 'ss -s'
```

### curl for Debugging

```bash
# Verbose mode — shows EVERYTHING
curl -v https://api.example.com 2>&1

# Timing breakdown (VERY useful for latency debugging)
curl -o /dev/null -s -w "\
    DNS:        %{time_namelookup}s\n\
    Connect:    %{time_connect}s\n\
    TLS:        %{time_appconnect}s\n\
    Start:      %{time_starttransfer}s\n\
    Total:      %{time_total}s\n\
    HTTP Code:  %{http_code}\n" \
    https://example.com

# Output tells you WHERE the latency is:
# DNS: 0.050s        ← DNS resolution time
# Connect: 0.120s    ← TCP connection time
# TLS: 0.250s        ← TLS handshake time
# Start: 0.380s      ← Time to first byte (server processing)
# Total: 0.450s      ← Total request time
```

---

## 9. Reverse Proxies and Load Balancers

### What Is a Reverse Proxy?

```
WITHOUT Reverse Proxy:
Internet → Server:8080 (application directly exposed)

WITH Reverse Proxy (Nginx):
Internet → Nginx:443 → Application:8080
           ├── TLS termination
           ├── Load balancing
           ├── Caching
           ├── Rate limiting
           ├── Request logging
           └── Security headers
```

### Nginx as a Reverse Proxy (Preview — Used Extensively Later)

```nginx
# /etc/nginx/sites-available/myapp
server {
    listen 80;
    server_name myapp.example.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name myapp.example.com;
    
    ssl_certificate /etc/letsencrypt/live/myapp.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/myapp.example.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /health {
        proxy_pass http://localhost:8080/health;
        access_log off;  # Don't log health checks
    }
}
```

### Load Balancing Concepts

```
                    ┌──── App Server 1 (10.0.1.10)
                    │
Client ── Nginx ────┼──── App Server 2 (10.0.1.11)
          (LB)      │
                    └──── App Server 3 (10.0.1.12)
```

**Load Balancing Algorithms:**

| Algorithm | How It Works | Best For |
|-----------|-------------|----------|
| **Round Robin** | Rotate through servers equally | Servers with similar specs |
| **Least Connections** | Send to server with fewest active connections | Varying request durations |
| **IP Hash** | Same client IP always goes to same server | Session stickiness |
| **Weighted** | More powerful servers get more traffic | Mixed server specs |

---

## 10. Common Mistakes and Anti-Patterns

### ❌ Not Understanding the Difference Between 401 and 403

```
401 Unauthorized = "Who are you?" (not authenticated)
  → Solution: Provide credentials
  
403 Forbidden = "I know who you are, but you're not allowed" (not authorized)
  → Solution: Request proper permissions
```

### ❌ Forgetting to Allow SSH Before Enabling Firewall

```bash
# THIS LOCKS YOU OUT OF YOUR SERVER:
sudo ufw enable         # Blocks everything, including SSH!
# You can never SSH back in. Server is lost.

# CORRECT ORDER:
sudo ufw allow 22/tcp   # Allow SSH first!
sudo ufw enable          # Then enable firewall
```

### ❌ Using HTTP for Sensitive Data

```
NEVER transmit passwords, tokens, or PII over plain HTTP.
ALWAYS use HTTPS. No exceptions.
Even internal services should use TLS in production.
```

### ❌ Exposing Database Ports to the Internet

```bash
# BAD: Database accessible from anywhere
sudo ufw allow 5432/tcp

# GOOD: Database only from application servers
sudo ufw allow from 10.0.1.0/24 to any port 5432
```

### ❌ Hardcoding IP Addresses

```bash
# BAD: 
curl http://10.0.1.50:8080/api/users

# GOOD: Use DNS names
curl http://api.internal.myapp.com:8080/api/users
# IPs change; DNS names are stable and updatable
```

---

## 11. Debugging Mindset

### The Network Debugging Playbook

```
"Can't connect to the service!"
        │
        ▼
1. Is DNS resolving correctly?
   dig service.example.com
   → Does the IP look right?
        │
        ▼
2. Can you reach the IP?
   ping <IP>
   → Timeout? Network/firewall issue
        │
        ▼
3. Can you reach the PORT?
   nc -zv <IP> <PORT>
   → Connection refused? Service not running
   → Timeout? Firewall blocking the port
        │
        ▼
4. Does the SERVICE respond correctly?
   curl -v http://<IP>:<PORT>/health
   → 5xx? Application error
   → 4xx? Auth or routing issue
        │
        ▼
5. Is the APPLICATION healthy?
   Check application logs
   Check resource usage (CPU, memory, disk)
   Check dependent services (database, cache)
```

### Common Error Messages and What They Mean

| Error | Layer | Meaning | Fix |
|-------|-------|---------|-----|
| `Name or service not known` | DNS | DNS resolution failed | Check DNS config, `/etc/hosts`, domain spelling |
| `Connection refused` | Layer 4 | Port is not accepting connections | Service not running, wrong port, binding to wrong interface |
| `Connection timed out` | Layer 3/4 | No response from server | Firewall blocking, server down, wrong IP |
| `502 Bad Gateway` | Layer 7 | Reverse proxy can't reach upstream | Backend app is down or unresponsive |
| `504 Gateway Timeout` | Layer 7 | Upstream took too long to respond | Backend app is overloaded, increase timeouts |
| `SSL: certificate has expired` | TLS | TLS certificate expired | Renew the certificate |

---

## 12. Security Considerations

> 🔐 Networking security is fundamental. Most breaches involve network-layer vulnerabilities.

### Key Principles

1. **Encrypt everything** — HTTPS everywhere, even internally
2. **Default deny firewall** — Only open what's explicitly needed
3. **Network segmentation** — Public, private, and database subnets
4. **Monitor traffic** — Know what's normal so you can spot anomalies
5. **Patch regularly** — Network devices and OS get security updates

### Security Headers (HTTP)

```nginx
# Essential security headers in Nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Content-Security-Policy "default-src 'self'" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

---

## 13. Interview Insights

### Frequently Asked Questions

**Q: What happens when you type `google.com` in your browser?**
> 1. Browser checks its DNS cache
> 2. OS checks `/etc/hosts`, then DNS resolver cache
> 3. DNS query to configured nameserver (recursive resolution)
> 4. Root → TLD (.com) → Authoritative NS → A record returned
> 5. TCP three-way handshake (SYN → SYN-ACK → ACK)
> 6. TLS handshake (certificate verification, key exchange)
> 7. HTTP GET request sent
> 8. Server processes request, returns HTML
> 9. Browser parses HTML, requests additional resources (CSS, JS, images)
> 10. Page renders

**Q: Explain the difference between TCP and UDP.**
> TCP is connection-oriented (three-way handshake), reliable (guarantees delivery and ordering), and used for HTTP, SSH, databases. UDP is connectionless, faster but unreliable (no delivery guarantees), used for DNS queries, video streaming, and monitoring.

**Q: What is a subnet, and why is it used?**
> A subnet divides a larger network into smaller, isolated segments. It's used for security (isolating sensitive systems like databases), traffic management (reducing broadcast domains), and organization (grouping related services). In cloud, you create public subnets for load balancers and private subnets for applications and databases.

**Q: How do you troubleshoot "connection refused"?**
> "Connection refused" means the server received the connection attempt but actively rejected it. Check: Is the service running? (`systemctl status`). Is it listening on the correct port? (`ss -tlnp`). Is it binding to the right interface? (0.0.0.0 vs 127.0.0.1). Is a firewall allowing the port?

**Q: What's the difference between a forward proxy and a reverse proxy?**
> A forward proxy sits in front of clients (outbound traffic control, anonymity, caching). A reverse proxy sits in front of servers (load balancing, SSL termination, caching, security). Nginx as a reverse proxy is the standard DevOps pattern.

### Scenario-Based Questions

**Q: Users report the website is slow for the past hour. How do you investigate?**
> 1. Check monitoring dashboards for latency/error spikes
> 2. Use curl timing to pinpoint where latency is (DNS? TCP? TLS? Server?)
> 3. Check server resources (CPU, memory, disk, network)
> 4. Check application logs for errors or slow queries
> 5. Check upstream dependencies (database, APIs, cache)
> 6. Check for recent deployments or config changes
> 7. Check CDN/DNS if the issue is regional

**Q: Your Nginx returns 502 Bad Gateway. What do you do?**
> 502 means Nginx can't reach the backend. Check: Is the backend process running? (`ps`, `systemctl status`). Is it on the correct port? (`ss -tlnp`). Can Nginx reach it? (`curl -v http://localhost:8080`). Check Nginx error logs (`/var/log/nginx/error.log`). Check backend application logs.

---

## ➡️ What's Next?

You now understand how data moves across networks and how to debug connectivity issues. Next, we learn **Git** — the version control system that tracks every change across your entire DevOps workflow.

**[Module 03: Git →](../03-git/)**

---

<div align="center">

**Module 02 Complete** ✅

[← Back to Linux](../01-linux/) | [Next: Git →](../03-git/)

</div>
]]>
