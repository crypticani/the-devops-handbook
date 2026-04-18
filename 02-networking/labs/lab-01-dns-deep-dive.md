<![CDATA[# Lab 01: DNS Deep Dive

## 🎯 Objective

Master DNS resolution, understand how domain names work in practice, and learn to diagnose the most common networking issue in DevOps: DNS failures.

---

## 📋 Prerequisites

- Linux with internet access
- `dig`, `nslookup`, `host` installed
- `sudo` access (for editing `/etc/hosts`)

```bash
# Install DNS tools if not present
sudo apt install -y dnsutils net-tools
```

---

## 🔬 Exercise 1: DNS Resolution in Practice

### Step 1: Basic DNS Queries

```bash
# Resolve a domain to an IP address
dig google.com

# Understanding the output:
# ;; QUESTION SECTION:    What we asked
# ;; ANSWER SECTION:      The answer (IP address)
# ;; AUTHORITY SECTION:   Which nameservers are authoritative
# ;; Query time:          How long DNS lookup took

# Short format (just the answer)
dig +short google.com
# Output: 142.250.80.46 (your IP may differ)

# Multiple IPs mean load balancing or CDN
dig +short facebook.com
```

### Step 2: Different Record Types

```bash
# A record (IPv4 address)
dig google.com A
dig +short google.com A

# AAAA record (IPv6 address)
dig google.com AAAA

# MX records (mail servers)
dig google.com MX
# Output shows mail servers with priority numbers
# Lower priority = higher preference

# NS records (nameservers)
dig google.com NS

# TXT records (SPF, domain verification, etc.)
dig google.com TXT

# CNAME (alias)
dig www.github.com CNAME
# www.github.com points to github.com
```

### Step 3: Trace DNS Resolution (See the Full Journey)

```bash
# Watch DNS resolve step by step
dig +trace google.com

# This shows:
# 1. Root servers (.) 
# 2. TLD servers (.com)
# 3. Authoritative servers (google.com)
# 4. Final answer

# Compare resolution times for different domains
echo "=== DNS Resolution Times ==="
for domain in google.com github.com example.com cloudflare.com; do
    time=$(dig +noall +stats "$domain" | grep "Query time" | awk '{print $4}')
    printf "%-20s %s ms\n" "$domain" "$time"
done
```

---

## 🔬 Exercise 2: Local DNS Override with /etc/hosts

### Step 1: Understand /etc/hosts

```bash
# View current hosts file
cat /etc/hosts
# 127.0.0.1   localhost
# The system checks THIS FILE before DNS servers

# How resolution order works:
# 1. /etc/hosts (local file)
# 2. DNS resolver (configured in /etc/resolv.conf)

# Check the resolution order
cat /etc/nsswitch.conf | grep hosts
# hosts: files dns
# "files" first = /etc/hosts is checked first
```

### Step 2: Override a Domain (Testing Technique)

```bash
# Scenario: You want to test a new server before changing real DNS

# First, check real DNS for example.com
dig +short example.com
# Should return: 93.184.216.34

# Add a local override
echo "127.0.0.1 testsite.local" | sudo tee -a /etc/hosts

# Now testsite.local resolves locally
ping -c 2 testsite.local
# Should ping 127.0.0.1

# This is how you test:
# - A new server before DNS cutover
# - An internal service by name
# - Block a domain (point to 127.0.0.1)

# Clean up: Remove the test entry
sudo sed -i '/testsite.local/d' /etc/hosts

# Verify it's gone
grep testsite.local /etc/hosts
# Should return nothing
```

### Step 3: Internal DNS for DevOps

```bash
# In real environments, you'll often add entries like:
# 10.0.1.10   db.internal
# 10.0.1.11   cache.internal
# 10.0.1.12   api.internal

# This is common in:
# - Docker Compose (automatic DNS for service names)
# - Kubernetes (cluster DNS)
# - AWS (Route 53 private hosted zones)
```

---

## 🔬 Exercise 3: DNS Troubleshooting

### Scenario 1: "Name Resolution Failed"

```bash
# Simulate: What if DNS is broken?

# Check your current DNS servers
cat /etc/resolv.conf

# Test with a known-good public DNS
dig @8.8.8.8 google.com +short
dig @1.1.1.1 google.com +short

# If these work but your default DNS doesn't:
# → Your configured DNS server is the problem

# Compare response times
for dns in 8.8.8.8 1.1.1.1 9.9.9.9; do
    time=$(dig @$dns google.com +noall +stats | grep "Query time" | awk '{print $4}')
    printf "DNS Server %-10s: %s ms\n" "$dns" "$time"
done
```

### Scenario 2: DNS Propagation Delay

```bash
# When you change a DNS record, it doesn't update instantly
# TTL (Time To Live) determines how long caches keep old records

# Check TTL for a domain
dig google.com | grep -A1 "ANSWER SECTION"
# Look for the number between domain and record type
# That's the TTL in seconds

# Example: If TTL is 300 (5 minutes), after changing DNS:
# - Some users see old IP for up to 5 minutes
# - Different DNS servers update at different times

# Best practice for DNS changes:
# 1. Lower TTL to 60 seconds a day before the change
# 2. Make the DNS change
# 3. Monitor with: dig @different-dns-servers your-domain.com
# 4. After propagation completes, raise TTL back to 3600
```

### Scenario 3: DNS vs Hosts File Conflict

```bash
# Add a conflicting entry
echo "1.2.3.4 google.com" | sudo tee -a /etc/hosts

# Now try to resolve google.com
ping -c 1 google.com
# It will try to ping 1.2.3.4 (from /etc/hosts) not the real Google!

# This is why /etc/hosts should always be checked during debugging
cat /etc/hosts | grep -v "^#" | grep -v "^$"

# Clean up
sudo sed -i '/1.2.3.4.*google.com/d' /etc/hosts

# Verify Google resolves correctly again
dig +short google.com
```

---

## 🧨 Break It: DNS Debugging Challenge

### Challenge: The Website Won't Load

Simulate a DNS failure and debug it:

```bash
# 1. "Break" DNS by pointing to a non-existent DNS server
echo "Current DNS config:"
cat /etc/resolv.conf

# Backup resolver config
sudo cp /etc/resolv.conf /etc/resolv.conf.backup

# Point to a fake DNS server (temporarily)
echo "nameserver 192.0.2.1" | sudo tee /etc/resolv.conf

# 2. Try to access a website
curl -s --connect-timeout 5 http://example.com
# Should fail: "Could not resolve host"

# 3. Debug systematically:
echo "=== Debugging DNS failure ==="

# Can we reach the internet at all? (Use IP directly)
ping -c 2 8.8.8.8
# If YES → Internet works, DNS is the problem

# Can we resolve using a specific DNS server?
dig @8.8.8.8 example.com +short
# If YES → Our DNS configuration is wrong

# 4. Fix: Restore DNS config
sudo cp /etc/resolv.conf.backup /etc/resolv.conf

# 5. Verify
dig +short example.com
curl -s -o /dev/null -w "%{http_code}" http://example.com
echo ""  # Should show: 200

# 6. Clean up
sudo rm /etc/resolv.conf.backup
```

---

## ✅ Validation

You've completed this lab when you can:

- [ ] Use `dig` to resolve any DNS record type (A, AAAA, MX, NS, TXT, CNAME)
- [ ] Trace DNS resolution end-to-end with `dig +trace`
- [ ] Override DNS locally using `/etc/hosts`
- [ ] Test DNS resolution against different DNS servers
- [ ] Diagnose and fix DNS configuration issues
- [ ] Explain TTL and its impact on DNS changes
- [ ] Explain why `/etc/hosts` is checked before DNS servers

---

## 💡 Key Takeaways

1. **DNS is the most common source of network failures** — always check it first
2. `/etc/hosts` overrides DNS — this is both powerful and dangerous
3. TTL determines how long DNS records are cached — plan for propagation delays
4. `dig` is your primary DNS debugging tool
5. Always test with a known-good DNS server (8.8.8.8) to isolate problems

---

[← Back to Module README](../README.md) | [Next Lab: TCP, Ports & Connectivity →](./lab-02-tcp-ports-connectivity.md)
]]>
