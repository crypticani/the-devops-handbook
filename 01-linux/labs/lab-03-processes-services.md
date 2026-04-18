<![CDATA[# Lab 03: Process Management & Systemd Services

## 🎯 Objective

Master process management and systemd — the skills you'll use to monitor running applications, debug slow servers, manage services, and create your own service definitions. This is core operational work.

---

## 📋 Prerequisites

- Completed Labs 01 and 02
- Ubuntu 22.04+ with `sudo` access

---

## 🔬 Exercise 1: Process Investigation

### Step 1: Understanding What's Running

```bash
# View all processes
ps aux | head -20

# Key columns to understand:
# USER    — Who owns the process
# PID     — Process ID (unique)
# %CPU    — CPU usage
# %MEM    — Memory usage
# VSZ     — Virtual memory size
# RSS     — Resident memory (actually using)
# STAT    — Process state
# COMMAND — What's running

# Process states you need to know:
# S  = Sleeping (waiting for something)
# R  = Running (actively using CPU)
# D  = Uninterruptible sleep (usually waiting on I/O — can't be killed)
# Z  = Zombie (finished but parent hasn't cleaned up)
# T  = Stopped (paused)
```

### Step 2: Finding Specific Processes

```bash
# Method 1: ps + grep
ps aux | grep ssh

# Problem: grep itself shows up in results!
# Method 2: Use a grep trick
ps aux | grep [s]shd
# The brackets prevent grep from matching itself

# Method 3: pgrep (cleaner)
pgrep -a sshd

# Method 4: pidof (PID only)
pidof sshd
```

### Step 3: Interactive Process Monitoring with htop

```bash
# Install htop
sudo apt install -y htop

# Run htop
htop

# Key shortcuts:
# F5 = Tree view (see parent-child relationships)
# F6 = Sort by column
# F9 = Kill a process
# F3 = Search
# F4 = Filter
# q  = Quit
# Space = Tag a process (for batch operations)

# Press F5 to see the process tree
# Notice how all processes trace back to PID 1 (systemd)
```

### Step 4: Real-Time Resource Monitoring

```bash
# Memory details
free -h

# Key insight: "available" is what matters, NOT "free"
# Linux uses unused RAM for disk cache (this is efficient, not a problem)
# "available" = free + reclaimable cache

# CPU info
lscpu | grep -E "^CPU\(s\)|^Model name|^Architecture"

# Load average — THE key metric
uptime
# Example: load average: 2.50, 1.80, 0.95

# Interpretation:
# Three numbers = 1 min, 5 min, 15 min average
# If you have 4 CPU cores:
#   load < 4.0 = System is handling the load fine
#   load = 4.0 = System is at 100% capacity
#   load > 4.0 = System is overloaded, processes are queuing

# Check number of cores
nproc
```

---

## 🔬 Exercise 2: Process Control

### Step 1: Running Background Processes

```bash
# Create a long-running test process
cat > /tmp/worker.sh << 'EOF'
#!/bin/bash
while true; do
    echo "[$(date)] Worker running... PID: $$"
    sleep 5
done
EOF
chmod +x /tmp/worker.sh

# Run in foreground
/tmp/worker.sh
# You'll see output every 5 seconds
# Press Ctrl+C to stop

# Run in background with &
/tmp/worker.sh &
# Output: [1] 12345   (job number and PID)

# List background jobs
jobs
# [1]+  Running    /tmp/worker.sh &

# The output is appearing mixed with your terminal - annoying!
# Redirect output to a file
kill %1   # Kill the background job

/tmp/worker.sh > /tmp/worker.log 2>&1 &
echo "Worker PID: $!"

# Now output goes to the file, your terminal is clean
tail -f /tmp/worker.log
# Press Ctrl+C to stop watching
```

### Step 2: Signals and Process Control

```bash
# Start workers we can experiment with
for i in 1 2 3; do
    /tmp/worker.sh > /tmp/worker$i.log 2>&1 &
    echo "Started worker $i with PID $!"
done

# Check they're running
ps aux | grep worker.sh | grep -v grep

# SIGTERM (15) — Graceful shutdown (default)
kill $(pgrep -f "worker.sh" | head -1)

# SIGHUP (1) — Often used to reload config
kill -HUP $(pgrep -f "worker.sh" | head -1)

# SIGKILL (9) — Force kill (last resort!)
kill -9 $(pgrep -f "worker.sh" | head -1)

# Kill all remaining workers
pkill -f worker.sh

# Verify they're all gone
ps aux | grep worker.sh | grep -v grep
# Should show nothing
```

### Step 3: nohup — Survive Terminal Disconnect

```bash
# Problem: Background processes die when you close the terminal
# Solution: nohup

nohup /tmp/worker.sh > /tmp/nohup-worker.log 2>&1 &
echo "Nohup worker PID: $!"

# This process will survive even if you close the terminal
# Verify it's running
ps aux | grep worker.sh | grep -v grep

# Clean up
pkill -f worker.sh
```

---

## 🔬 Exercise 3: Systemd Service Management

### Step 1: Working with Existing Services

```bash
# Install nginx for practice
sudo apt install -y nginx

# Check status
sudo systemctl status nginx
# Look for:
# Active: active (running) — GREEN dot
# Main PID
# Memory usage
# Recent log entries

# Check if it's enabled at boot
systemctl is-enabled nginx

# Restart vs Reload
sudo systemctl restart nginx    # Full restart (connections dropped)
sudo systemctl reload nginx     # Config reload (no downtime — PREFERRED)

# Stop and start
sudo systemctl stop nginx
systemctl is-active nginx       # Should say "inactive"
sudo systemctl start nginx
systemctl is-active nginx       # Should say "active"

# List all services
systemctl list-units --type=service --state=running

# List failed services (important for debugging!)
systemctl list-units --state=failed
```

### Step 2: Reading Service Logs

```bash
# Nginx logs via journalctl
journalctl -u nginx

# Just today's logs
journalctl -u nginx --since today

# Follow in real-time (like tail -f)
journalctl -u nginx -f

# Only errors
journalctl -u nginx -p err

# Specify time range
journalctl -u nginx --since "10 minutes ago"
journalctl -u nginx --since "2024-01-15 10:00" --until "2024-01-15 11:00"

# Output as JSON (useful for log processing)
journalctl -u nginx -o json-pretty | head -20
```

### Step 3: Create Your Own Systemd Service

```bash
# Create a simple application
sudo mkdir -p /opt/myapp
cat << 'APP' | sudo tee /opt/myapp/server.sh
#!/bin/bash
# Simple HTTP server simulation
echo "MyApp starting on port 9090..."
echo "PID: $$"

# Handle graceful shutdown
cleanup() {
    echo "Received shutdown signal. Cleaning up..."
    echo "MyApp stopped gracefully."
    exit 0
}
trap cleanup SIGTERM SIGINT

# Main loop
while true; do
    echo "[$(date)] Serving requests..."
    sleep 10
done
APP

sudo chmod +x /opt/myapp/server.sh

# Create a dedicated user
sudo useradd -r -s /usr/sbin/nologin myapp 2>/dev/null || true
sudo chown -R myapp:myapp /opt/myapp

# Create the service file
sudo tee /etc/systemd/system/myapp.service << 'SERVICE'
[Unit]
Description=My Custom Application
Documentation=https://example.com/myapp/docs
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=myapp
Group=myapp
WorkingDirectory=/opt/myapp
ExecStart=/opt/myapp/server.sh
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/myapp

[Install]
WantedBy=multi-user.target
SERVICE

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Start the service
sudo systemctl start myapp

# Check status
sudo systemctl status myapp
# Should show: Active: active (running)

# Check logs
journalctl -u myapp -f
# You should see: "Serving requests..." every 10 seconds
# Press Ctrl+C to stop watching

# Enable at boot
sudo systemctl enable myapp
```

---

## 🔬 Exercise 4: Service Failure and Recovery

### Step 1: Test Automatic Restart

```bash
# Our service has Restart=on-failure
# Let's kill it and watch it restart

# Get the PID
systemctl show myapp --property=MainPID
# Note the PID

# Kill it (simulate a crash)
sudo kill -9 $(systemctl show myapp --property=MainPID --value)

# Wait 6 seconds (RestartSec=5 + some time)
sleep 6

# Check — it should have restarted with a NEW PID
sudo systemctl status myapp
# Look for: Main PID changed, "Started My Custom Application"
```

### Step 2: Examine Restart Behavior

```bash
# See how many times it's been restarted
systemctl show myapp --property=NRestarts

# See the restart limit settings
systemctl show myapp --property=StartLimitBurst,StartLimitIntervalUSec

# If a service restarts too many times too quickly,
# systemd will give up and mark it as "failed"
# This prevents restart loops from consuming resources
```

### Step 3: Diagnose a Broken Service

```bash
# Break the service intentionally
sudo mv /opt/myapp/server.sh /opt/myapp/server.sh.bak

# Restart (will fail because the executable is missing)
sudo systemctl restart myapp 2>&1

# Check status
sudo systemctl status myapp
# Should show: Active: failed (Result: exit-code)

# The logs tell you exactly what went wrong:
journalctl -u myapp --since "1 minute ago" --no-pager
# Look for: "Exec format error" or "No such file or directory"

# Fix it
sudo mv /opt/myapp/server.sh.bak /opt/myapp/server.sh

# Reset the failure counter and restart
sudo systemctl reset-failed myapp
sudo systemctl start myapp

# Verify it's running
sudo systemctl status myapp
```

---

## 🧨 Break It: Advanced Debugging

### Failure: Zombie Processes

```bash
# Create a zombie process (for education)
cat > /tmp/zombie_maker.sh << 'ZOMBIE'
#!/bin/bash
# This creates a child process that becomes a zombie
bash -c 'exit 0' &
# Don't wait for the child — it becomes a zombie
sleep 30
ZOMBIE
chmod +x /tmp/zombie_maker.sh

/tmp/zombie_maker.sh &

# Look for zombie processes
ps aux | grep 'Z'
# Look for STAT column showing 'Z' or 'Z+'

# In production, zombies indicate a parent process
# not properly handling child process termination
# Usually fixed by: restarting the parent process

# Clean up
pkill -f zombie_maker
```

### Failure: Port Already In Use

```bash
# Start a process on port 8080
python3 -m http.server 8080 &

# Try starting another on the same port
python3 -m http.server 8080 2>&1
# Error: OSError: [Errno 98] Address already in use

# Debug: Find what's using the port
ss -tlnp | grep 8080
# Or
sudo lsof -i :8080

# Fix: Kill the process using the port
kill $(lsof -ti :8080)

# Verify port is free
ss -tlnp | grep 8080
# Should show nothing
```

---

## ✅ Final Validation

You've completed this lab when you can:

- [ ] Find any process by name, PID, or resource usage
- [ ] Explain the difference between SIGTERM, SIGKILL, and SIGHUP
- [ ] Run processes in the background with proper log redirection
- [ ] Create a systemd service file from scratch
- [ ] Start, stop, restart, enable, and disable services
- [ ] Read and filter journalctl logs effectively
- [ ] Debug a failed service using systemctl status + journalctl
- [ ] Explain what load average means relative to CPU count
- [ ] Find what process is using a specific port

---

## 💡 Key Takeaways

1. **htop > top** — use the better tool
2. **SIGTERM first, SIGKILL last** — give processes a chance to clean up
3. **Systemd is the backbone** of modern Linux service management
4. Service files should include **security hardening** directives
5. **Restart=on-failure** makes services self-healing
6. **journalctl** is your centralized log viewer — master it
7. When debugging: **check status → read logs → check what changed**

---

## 🧹 Cleanup

```bash
# Remove the test service
sudo systemctl stop myapp
sudo systemctl disable myapp
sudo rm /etc/systemd/system/myapp.service
sudo systemctl daemon-reload

# Remove test files
sudo rm -rf /opt/myapp
sudo userdel myapp 2>/dev/null
rm -f /tmp/worker*.sh /tmp/worker*.log /tmp/zombie_maker.sh /tmp/nohup-worker.log

# Stop any leftover processes
pkill -f worker.sh 2>/dev/null
```

---

[← Previous Lab](./lab-02-permissions-users.md) | [Next Lab: Text Processing & Log Analysis →](./lab-04-text-processing.md)
]]>
