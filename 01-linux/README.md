<![CDATA[# Module 01: Linux

> *"If you can't navigate Linux confidently, you cannot do DevOps. Period."*

---

## 🎯 Why This Module Matters

**Linux runs the internet.** Over 96% of the world's top web servers run Linux. Every Docker container is Linux. Every CI/CD runner is Linux. Every Kubernetes node is Linux. AWS, GCP, and Azure all default to Linux instances.

**In real-world DevOps work**, you will:
- SSH into servers to troubleshoot production issues at 3 AM
- Write scripts that manage hundreds of servers
- Read and parse logs that are thousands of lines long
- Configure services that have no GUI
- Debug permission issues that block deployments

If you're uncomfortable in a Linux terminal, you are stuck. This module makes you fluent.

---

## 📚 Table of Contents

1. [Linux Fundamentals](#1-linux-fundamentals)
2. [The Filesystem Hierarchy](#2-the-filesystem-hierarchy)
3. [Essential Commands](#3-essential-commands)
4. [File Permissions and Ownership](#4-file-permissions-and-ownership)
5. [Users and Groups](#5-users-and-groups)
6. [Process Management](#6-process-management)
7. [Package Management](#7-package-management)
8. [Systemd and Services](#8-systemd-and-services)
9. [Text Processing](#9-text-processing)
10. [Disk and Storage](#10-disk-and-storage)
11. [SSH and Remote Access](#11-ssh-and-remote-access)
12. [Environment Variables and Shell Configuration](#12-environment-variables-and-shell-configuration)
13. [Cron Jobs and Scheduling](#13-cron-jobs-and-scheduling)
14. [Common Mistakes and Anti-Patterns](#14-common-mistakes-and-anti-patterns)
15. [Debugging Mindset](#15-debugging-mindset)
16. [Security Considerations](#16-security-considerations)
17. [Interview Insights](#17-interview-insights)

---

## 1. Linux Fundamentals

### What Is Linux?

Linux is an **open-source operating system kernel** created by Linus Torvalds in 1991. What we call "Linux" is actually GNU/Linux — the Linux kernel combined with GNU tools and utilities.

### Why Ubuntu?

We standardize on **Ubuntu** in this handbook because:
- Most widely used server distribution
- Excellent documentation
- LTS (Long Term Support) versions with 5-year support
- Default on most cloud providers
- Large community for troubleshooting

### The Linux Architecture

```
┌──────────────────────────────────────────┐
│           User Applications               │
│     (nginx, docker, python, bash)         │
├──────────────────────────────────────────┤
│              Shell (Bash)                 │
│    (command interpreter, scripting)        │
├──────────────────────────────────────────┤
│          System Libraries (glibc)         │
│     (standard functions for programs)     │
├──────────────────────────────────────────┤
│            Linux Kernel                   │
│  (process mgmt, memory, filesystem, I/O)  │
├──────────────────────────────────────────┤
│              Hardware                     │
│    (CPU, RAM, Disk, Network)              │
└──────────────────────────────────────────┘
```

### The Shell

The shell is your **command interpreter** — it translates your commands into actions the kernel can execute.

```bash
# Check your current shell
echo $SHELL
# Output: /bin/bash

# List available shells
cat /etc/shells

# Key concept: Everything in Linux is either a FILE or a PROCESS
```

---

## 2. The Filesystem Hierarchy

Understanding the filesystem is **non-negotiable**. Every DevOps task touches it.

```
/                       # Root — everything starts here
├── bin/                # Essential user binaries (ls, cp, mv, cat)
├── sbin/               # System binaries (iptables, fdisk, reboot)
├── etc/                # Configuration files (THE most important for DevOps)
│   ├── nginx/          #   Nginx config
│   ├── ssh/            #   SSH config
│   ├── systemd/        #   Service definitions
│   ├── hosts           #   Local DNS
│   ├── passwd          #   User accounts
│   ├── shadow          #   Password hashes
│   └── fstab           #   Filesystem mount table
├── home/               # User home directories
│   └── ubuntu/         #   Default user on Ubuntu
├── var/                # Variable data (changes during operation)
│   ├── log/            #   System and application logs ⭐
│   ├── www/            #   Web server content
│   └── lib/            #   Variable state (databases, etc.)
├── tmp/                # Temporary files (cleared on reboot)
├── opt/                # Optional/third-party software
├── usr/                # User programs and data
│   ├── bin/            #   Non-essential binaries
│   ├── lib/            #   Libraries
│   └── local/          #   Locally installed software
├── proc/               # Virtual filesystem — running process info
├── sys/                # Virtual filesystem — kernel and hardware info
├── dev/                # Device files
└── mnt/ & media/       # Mount points for external storage
```

### Critical Directories for DevOps

| Directory | Why You'll Use It |
|-----------|-------------------|
| `/etc/` | Every service configuration lives here |
| `/var/log/` | First place to look when debugging |
| `/home/` | User scripts, SSH keys, dotfiles |
| `/tmp/` | Temporary build artifacts, quick scripts |
| `/opt/` | Third-party tools (Prometheus, Grafana, etc.) |
| `/proc/` | Live system information (CPU, memory, processes) |

---

## 3. Essential Commands

### Navigation

```bash
# Where am I?
pwd
# Output: /home/ubuntu

# List files (basic)
ls

# List with details (permissions, size, date)
ls -la

# List with human-readable sizes
ls -lah

# Go to a directory
cd /var/log

# Go home
cd ~    # or just: cd

# Go back to previous directory
cd -

# Create directories (including parents)
mkdir -p /tmp/project/src/models

# Show directory tree
tree -L 2 /etc
```

### File Operations

```bash
# Create a file
touch newfile.txt

# Create a file with content
echo "Hello DevOps" > hello.txt          # Overwrite
echo "Another line" >> hello.txt         # Append

# Copy files
cp source.txt destination.txt
cp -r source_dir/ destination_dir/       # Recursive (directories)

# Move/rename files
mv oldname.txt newname.txt
mv file.txt /tmp/                        # Move to another directory

# Delete files (CAREFUL — no recycle bin!)
rm file.txt
rm -r directory/                         # Delete directory
rm -rf directory/                        # Force delete (DANGEROUS)

# Find files
find /var/log -name "*.log" -mtime -1    # Logs modified in last day
find / -name "nginx.conf" 2>/dev/null    # Find nginx config, suppress errors
find /home -size +100M                   # Files larger than 100MB

# Which binary am I using?
which python3
# Output: /usr/bin/python3

whereis nginx
```

### Reading Files

```bash
# Print entire file
cat file.txt

# Print with line numbers
cat -n file.txt

# Page through a file
less /var/log/syslog                     # q to quit, / to search

# First/last N lines
head -20 /var/log/syslog                 # First 20 lines
tail -50 /var/log/syslog                 # Last 50 lines

# Follow a log in real-time (ESSENTIAL for debugging)
tail -f /var/log/syslog                  # Ctrl+C to stop

# Word/line/byte count
wc -l file.txt                           # Count lines
```

### Searching Within Files

```bash
# Search for a pattern
grep "error" /var/log/syslog
grep -i "error" /var/log/syslog          # Case-insensitive
grep -r "TODO" /home/ubuntu/project/     # Recursive search
grep -c "error" /var/log/syslog          # Count matches
grep -n "error" /var/log/syslog          # Show line numbers
grep -v "debug" /var/log/syslog          # Invert (exclude debug)

# Search with context
grep -A 3 "error" /var/log/syslog        # 3 lines AFTER match
grep -B 3 "error" /var/log/syslog        # 3 lines BEFORE match
grep -C 3 "error" /var/log/syslog        # 3 lines before AND after

# Real-world example: Find all failed SSH attempts
grep "Failed password" /var/log/auth.log | tail -20
```

---

## 4. File Permissions and Ownership

### Understanding Permission Notation

```
-rwxr-xr-- 1 ubuntu devops 4096 Jan 15 10:30 deploy.sh
│├──┤├──┤├──┤ │  │      │     │      │         │
│ │   │   │  │  │      │     │      │         └── Filename
│ │   │   │  │  │      │     │      └── Last modified
│ │   │   │  │  │      │     └── Size in bytes
│ │   │   │  │  │      └── Group owner
│ │   │   │  │  └── User owner
│ │   │   │  └── Hard link count
│ │   │   └── Others permissions (r--)
│ │   └── Group permissions (r-x)
│ └── Owner permissions (rwx)
└── File type (- = file, d = directory, l = link)
```

### Permission Values

```
r (read)    = 4
w (write)   = 2
x (execute) = 1

Common combinations:
rwx = 4+2+1 = 7  (full access)
r-x = 4+0+1 = 5  (read + execute)
r-- = 4+0+0 = 4  (read only)
--- = 0+0+0 = 0  (no access)

Common permission sets:
755 = rwxr-xr-x  (directories, scripts)
644 = rw-r--r--  (regular files)
600 = rw-------  (sensitive files like SSH keys)
700 = rwx------  (private directories/scripts)
```

### Changing Permissions and Ownership

```bash
# Change permissions (numeric)
chmod 755 deploy.sh                      # Owner: full, Group: rx, Others: rx
chmod 600 ~/.ssh/id_rsa                  # Owner: rw only (SSH key requirement)

# Change permissions (symbolic)
chmod +x script.sh                       # Add execute for all
chmod u+x script.sh                      # Add execute for owner only
chmod g-w file.txt                       # Remove write from group
chmod o-rwx secret.txt                   # Remove all permissions from others

# Change owner
chown ubuntu:devops file.txt             # Change user and group
chown -R ubuntu:devops /var/www/         # Recursive

# Change group only
chgrp devops file.txt

# Special: setuid, setgid, sticky bit
chmod u+s /usr/bin/program               # Runs as file owner (DANGEROUS)
chmod g+s /shared/dir                    # New files inherit directory group
chmod +t /tmp                            # Sticky bit (only owner can delete)
```

### 🔐 Security Note: Permission Mistakes That Cause Production Incidents

| Mistake | Impact | Correct Setting |
|---------|--------|-----------------|
| `chmod 777 /var/www/` | Anyone can modify web files | `755` for dirs, `644` for files |
| SSH key with `644` | SSH refuses to use it | `600` for private keys |
| `.env` file with `644` | Secrets readable by all users | `600` or `640` |
| Script without `+x` | "Permission denied" when running | `chmod +x script.sh` |

---

## 5. Users and Groups

### Understanding Users

```bash
# Current user
whoami
# Output: ubuntu

# User details
id
# Output: uid=1000(ubuntu) gid=1000(ubuntu) groups=1000(ubuntu),4(adm),27(sudo),999(docker)

# All users on the system
cat /etc/passwd

# User entry format:
# username:x:UID:GID:comment:home_dir:shell
# ubuntu:x:1000:1000:Ubuntu User:/home/ubuntu:/bin/bash

# Users currently logged in
w
who
```

### Managing Users

```bash
# Create a user
sudo useradd -m -s /bin/bash -G sudo,docker newuser

# Flags explained:
#   -m          Create home directory
#   -s /bin/bash Set bash as default shell
#   -G sudo,docker  Add to these groups

# Set password
sudo passwd newuser

# Delete a user
sudo userdel -r olduser    # -r removes home directory too

# Modify user
sudo usermod -aG docker existinguser   # Add to docker group
# IMPORTANT: -a means APPEND. Without -a, it REPLACES all groups!

# Lock/unlock user
sudo usermod -L username    # Lock
sudo usermod -U username    # Unlock
```

### Understanding sudo

```bash
# Run as root
sudo command

# Run as another user
sudo -u www-data command

# Open root shell (use sparingly)
sudo -i

# Check sudo privileges
sudo -l

# Edit sudoers file (NEVER edit directly, use visudo)
sudo visudo
```

> **🔐 Security**: Never work as root directly. Use `sudo` for individual commands. This provides an audit trail of who did what.

---

## 6. Process Management

### Viewing Processes

```bash
# List all processes (snapshot)
ps aux
# USER  PID %CPU %MEM    VSZ   RSS TTY  STAT START   TIME COMMAND
# root    1  0.0  0.1 169328 11168 ?    Ss   Jan10   0:13 /sbin/init

# Key columns:
# PID   - Process ID
# %CPU  - CPU usage
# %MEM  - Memory usage
# STAT  - Process state (S=sleeping, R=running, Z=zombie, T=stopped)
# TIME  - Total CPU time used

# Interactive process viewer (way better than ps)
htop
# Press: F5 for tree view, F6 to sort, F9 to kill, q to quit

# Find specific processes
ps aux | grep nginx
pgrep -a nginx                           # Cleaner way
pidof nginx                              # Get PID only

# Process tree
pstree -p
```

### Managing Processes

```bash
# Run a process in the background
./long-running-script.sh &

# List background jobs
jobs

# Bring to foreground
fg %1

# Send to background
bg %1

# Stop a process
kill PID          # Graceful (SIGTERM - allows cleanup)
kill -9 PID       # Force kill (SIGKILL - immediate, last resort)
kill -HUP PID     # Reload config (SIGHUP - used by nginx, etc.)

# Kill by name
pkill nginx
killall nginx

# Key signals to know:
# SIGTERM (15) - "Please shut down gracefully"
# SIGKILL (9)  - "Stop NOW, no cleanup" (CAN'T be caught)
# SIGHUP (1)   - "Reload your config"
# SIGINT (2)   - Ctrl+C, "Interrupt"
# SIGSTOP (19) - "Pause" (can't be caught)
# SIGCONT (18) - "Resume"
```

### Resource Monitoring

```bash
# CPU and memory overview
top
htop                                     # Better version

# Memory usage
free -h
# Output:
#               total        used        free      shared  buff/cache   available
# Mem:           7.8G        2.1G        3.5G        120M        2.2G        5.3G
# Swap:          2.0G          0B        2.0G

# IMPORTANT: "available" is what matters, not "free"
# Linux uses free RAM for caching — this is GOOD, not a problem

# Disk I/O
iostat -x 1                              # Per-disk I/O stats, every 1 second

# System load average
uptime
# Output: 10:30:45 up 42 days, load average: 0.52, 0.38, 0.35
# load average = 1-min, 5-min, 15-min
# If load > number of CPU cores, system is overloaded

# Number of CPU cores
nproc
# or
cat /proc/cpuinfo | grep processor | wc -l
```

---

## 7. Package Management

### APT (Ubuntu/Debian)

```bash
# Update package list (always do this first!)
sudo apt update

# Upgrade all packages
sudo apt upgrade -y

# Install a package
sudo apt install -y nginx

# Remove a package
sudo apt remove nginx                    # Keep config files
sudo apt purge nginx                     # Remove everything

# Search for packages
apt search nginx

# Show package info
apt show nginx

# List installed packages
dpkg -l | grep nginx

# Clean up
sudo apt autoremove -y                   # Remove unneeded dependencies
sudo apt clean                           # Clear download cache
```

### Real-World Package Management

```bash
# Add a third-party repository (example: Docker)
# 1. Add the GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 2. Add the repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list

# 3. Update and install
sudo apt update
sudo apt install -y docker-ce

# Check what repository a package comes from
apt policy nginx
```

---

## 8. Systemd and Services

### Why Systemd Matters

Systemd is the **init system** — it manages everything that runs on a modern Linux system. As a DevOps engineer, you'll manage services with systemd daily.

### Core Commands

```bash
# Check service status
sudo systemctl status nginx
# Output tells you:
# - Active: active (running) or inactive (dead) or failed
# - PID and memory usage
# - Recent log entries

# Start/stop/restart
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx             # Full restart (brief downtime)
sudo systemctl reload nginx              # Reload config (no downtime, preferred)

# Enable/disable at boot
sudo systemctl enable nginx              # Start on boot
sudo systemctl disable nginx             # Don't start on boot
sudo systemctl enable --now nginx        # Enable AND start immediately

# List all services
systemctl list-units --type=service

# List failed services
systemctl list-units --state=failed

# Check if a service is enabled
systemctl is-enabled nginx

# Check if a service is active
systemctl is-active nginx
```

### Creating a Custom Service

This is something you'll do regularly — deploying applications as systemd services.

```bash
# Create a service file
sudo vim /etc/systemd/system/myapp.service
```

```ini
[Unit]
Description=My Application
Documentation=https://github.com/myorg/myapp
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/myapp
ExecStart=/usr/bin/python3 /opt/myapp/main.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=NODE_ENV=production
Environment=PORT=8080

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
# After creating/modifying a service file
sudo systemctl daemon-reload             # Reload systemd config
sudo systemctl start myapp
sudo systemctl enable myapp

# Read service logs
journalctl -u myapp                      # All logs
journalctl -u myapp -f                   # Follow (real-time)
journalctl -u myapp --since "1 hour ago" # Recent logs
journalctl -u myapp -p err               # Only errors
```

### Journalctl — The Centralized Log Viewer

```bash
# System logs
journalctl                               # All logs
journalctl -b                            # Since last boot
journalctl -b -1                         # Previous boot
journalctl --since "2024-01-15 10:00"    # Since specific time
journalctl --since "1 hour ago"          # Relative time
journalctl -p err                        # Only errors and above
journalctl -f                            # Follow in real-time

# Service-specific logs
journalctl -u nginx -f

# Disk usage of journal
journalctl --disk-usage

# Clean old logs
sudo journalctl --vacuum-time=7d         # Keep only last 7 days
sudo journalctl --vacuum-size=500M       # Keep only 500MB
```

---

## 9. Text Processing

### The Text Processing Pipeline

This is one of the **most valuable skills** in DevOps — processing logs, configs, and data on the command line.

### Pipes and Redirection

```bash
# Pipe: send output of one command to another
cat /var/log/syslog | grep "error" | wc -l

# Redirect output to file
command > file.txt                       # Overwrite
command >> file.txt                      # Append
command 2> error.txt                     # Redirect stderr
command > output.txt 2>&1               # Redirect both stdout and stderr
command &> output.txt                    # Shorthand for the above

# /dev/null — the black hole
command > /dev/null 2>&1                 # Discard all output
```

### Essential Text Tools

```bash
# awk — column-based text processing (POWERFUL)
# Print specific columns
ps aux | awk '{print $1, $2, $11}'       # User, PID, Command
df -h | awk '{print $1, $5}'             # Filesystem, Usage%

# Filter with condition
ps aux | awk '$3 > 50 {print $1, $2, $3, $11}'  # Processes using >50% CPU

# Sum a column
cat data.txt | awk '{sum += $2} END {print "Total:", sum}'

# sed — stream editor (find and replace)
sed 's/old/new/g' file.txt               # Replace all occurrences
sed -i 's/old/new/g' file.txt            # Edit file in-place
sed -n '10,20p' file.txt                 # Print lines 10-20
sed '/^#/d' config.txt                   # Delete comment lines

# cut — extract columns with delimiter
echo "user:password:uid:gid" | cut -d: -f1,3    # Output: user:uid
cat /etc/passwd | cut -d: -f1                    # List all usernames

# sort
sort file.txt                            # Alphabetical
sort -n file.txt                         # Numeric
sort -r file.txt                         # Reverse
sort -u file.txt                         # Unique only
sort -t: -k3 -n /etc/passwd             # Sort by 3rd field (UID)

# uniq — deduplicate (MUST sort first)
sort file.txt | uniq
sort file.txt | uniq -c                  # Count occurrences
sort file.txt | uniq -c | sort -rn       # Most frequent first

# tr — translate characters
echo "HELLO" | tr 'A-Z' 'a-z'           # Lowercase
cat file.txt | tr -d '\r'               # Remove Windows line endings
```

### Real-World Text Processing Examples

```bash
# Find top 10 IP addresses hitting your web server
cat /var/log/nginx/access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -10

# Find all 500 errors in the last hour
grep "$(date -d '1 hour ago' '+%d/%b/%Y:%H')" /var/log/nginx/access.log | grep '" 500 '

# Extract and count HTTP status codes
awk '{print $9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn

# Find largest files on disk
find / -type f -size +100M -exec ls -lh {} \; 2>/dev/null | sort -k5 -rh | head -20

# Monitor log file for errors in real-time
tail -f /var/log/syslog | grep --color -i "error\|fail\|critical"
```

---

## 10. Disk and Storage

```bash
# Disk usage overview
df -h
# Filesystem      Size  Used Avail Use% Mounted on
# /dev/sda1        50G   18G   30G  38% /

# Directory sizes
du -sh /var/log/                         # Total size of /var/log
du -sh /var/log/* | sort -rh | head -10  # Largest subdirectories

# Disk I/O monitoring
iostat -x 1 5                            # Every 1 sec, 5 times

# Check for disk issues
sudo dmesg | grep -i "error\|fail\|disk"

# Mount a device
sudo mount /dev/sdb1 /mnt/data
sudo umount /mnt/data

# Persistent mounts (survive reboot)
# Edit /etc/fstab:
# /dev/sdb1  /mnt/data  ext4  defaults  0  2
```

---

## 11. SSH and Remote Access

### SSH Basics

```bash
# Connect to a remote server
ssh username@hostname
ssh -p 2222 username@hostname            # Different port
ssh -i ~/.ssh/mykey.pem ubuntu@10.0.1.5  # With specific key

# Generate SSH key pair
ssh-keygen -t ed25519 -C "your.email@example.com"
# Save to default location (~/.ssh/id_ed25519)
# Optionally set a passphrase (recommended)

# Copy public key to server
ssh-copy-id username@hostname
# Manual method:
cat ~/.ssh/id_ed25519.pub | ssh user@host "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# SSH config for convenience
cat ~/.ssh/config
# Example:
# Host production
#     HostName 10.0.1.5
#     User ubuntu
#     IdentityFile ~/.ssh/production.pem
#     Port 22
#
# Now just:  ssh production
```

### SSH File Transfer

```bash
# Copy file to remote
scp file.txt user@host:/path/to/destination/

# Copy from remote
scp user@host:/var/log/app.log ./

# Copy directory
scp -r ./project/ user@host:/opt/

# rsync (better than scp — incremental, resumable)
rsync -avz ./project/ user@host:/opt/project/
# -a = archive (preserves permissions, timestamps)
# -v = verbose
# -z = compress during transfer
```

### 🔐 SSH Security Hardening

```bash
# Edit SSH config
sudo vim /etc/ssh/sshd_config

# Key changes:
# PermitRootLogin no                     # Disable root SSH
# PasswordAuthentication no              # Key-based only
# Port 2222                              # Change default port
# MaxAuthTries 3                         # Limit login attempts
# AllowUsers ubuntu deploy               # Whitelist users

# Apply changes
sudo systemctl restart sshd
```

---

## 12. Environment Variables and Shell Configuration

```bash
# View all environment variables
env
printenv

# View a specific variable
echo $HOME
echo $PATH
echo $USER

# Set a variable (current session only)
export MY_VAR="hello"

# Set permanently (add to ~/.bashrc or ~/.profile)
echo 'export MY_VAR="hello"' >> ~/.bashrc
source ~/.bashrc                         # Apply immediately

# PATH — where Linux looks for commands
echo $PATH
# /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Add to PATH
export PATH="$PATH:/opt/mytools/bin"

# Important files:
# ~/.bashrc    — Runs for every new bash shell
# ~/.profile   — Runs on login
# /etc/environment    — System-wide variables
# /etc/profile.d/*.sh — System-wide scripts
```

---

## 13. Cron Jobs and Scheduling

```bash
# Edit cron jobs for current user
crontab -e

# List cron jobs
crontab -l

# Cron format:
# ┌───────────── minute (0 - 59)
# │ ┌───────────── hour (0 - 23)
# │ │ ┌───────────── day of month (1 - 31)
# │ │ │ ┌───────────── month (1 - 12)
# │ │ │ │ ┌───────────── day of week (0 - 6, Sun=0)
# │ │ │ │ │
# * * * * * command

# Examples:
# Every 5 minutes
*/5 * * * * /opt/scripts/health-check.sh

# Every day at 2:30 AM
30 2 * * * /opt/scripts/backup.sh

# Every Monday at 9 AM
0 9 * * 1 /opt/scripts/weekly-report.sh

# First day of every month
0 0 1 * * /opt/scripts/monthly-cleanup.sh

# IMPORTANT: Always redirect output to a log
*/5 * * * * /opt/scripts/health-check.sh >> /var/log/health-check.log 2>&1
```

---

## 14. Common Mistakes and Anti-Patterns

### ❌ Running Everything as Root

```bash
# BAD
sudo su -
apt install nginx
vim /etc/nginx/nginx.conf
systemctl restart nginx
# You're root for everything — no audit trail, easy to destroy things

# GOOD
sudo apt install nginx
sudo vim /etc/nginx/nginx.conf
sudo systemctl restart nginx
# Each command is explicit, auditable
```

### ❌ Using `chmod 777`

```bash
# BAD — "just make it work"
chmod 777 /var/www/html/

# GOOD — minimum required permissions
chmod 755 /var/www/html/          # Directory
chmod 644 /var/www/html/*.html    # Files
chown -R www-data:www-data /var/www/html/
```

### ❌ Not Checking Disk Space

```bash
# BAD: Assume disk is fine
# Log files fill up → service crashes → production down

# GOOD: Monitor proactively
df -h
du -sh /var/log/* | sort -rh | head -5

# Even better: Set up alerts (covered in Module 07)
```

### ❌ Editing Config Files Without Backup

```bash
# BAD
sudo vim /etc/nginx/nginx.conf

# GOOD
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak.$(date +%Y%m%d)
sudo vim /etc/nginx/nginx.conf
sudo nginx -t   # Test config before reloading!
sudo systemctl reload nginx
```

---

## 15. Debugging Mindset

### The Linux Troubleshooting Framework

```
Problem reported
       │
       ▼
1. CHECK RESOURCES ──────────────────────────────────┐
   free -h          (memory)                         │
   df -h            (disk)                           │
   top/htop         (cpu/processes)                  │
   uptime           (load average)                   │
       │                                             │
       ▼                                             │
2. CHECK LOGS ───────────────────────────────────────┤
   journalctl -u service -f                          │
   tail -f /var/log/syslog                           │
   tail -f /var/log/app.log                          │
       │                                             │
       ▼                                             │
3. CHECK SERVICES ───────────────────────────────────┤
   systemctl status service                          │
   systemctl list-units --state=failed               │
       │                                             │
       ▼                                             │
4. CHECK NETWORK ────────────────────────────────────┤
   ping hostname                                     │
   curl -v http://localhost:8080                      │
   ss -tlnp                                          │
       │                                             │
       ▼                                             │
5. CHECK RECENT CHANGES ─────────────────────────────┘
   last                    (recent logins)
   history                 (recent commands)
   ls -lt /etc/            (recently changed configs)
   dpkg -l --last-modified (recently installed packages)
```

### Common Scenarios

**"Service won't start"**
```bash
# 1. Check the status
sudo systemctl status myservice

# 2. Read the logs
journalctl -u myservice --no-pager -n 50

# 3. Common causes:
#    - Port already in use: ss -tlnp | grep PORT
#    - Permission denied: check file ownership and permissions
#    - Config error: test config if tool supports it (nginx -t)
#    - Missing dependency: check if required service is running
```

**"Server is slow"**
```bash
# 1. Check load average
uptime
# Load > nproc? CPU bottleneck

# 2. Check memory
free -h
# Available near zero? Memory pressure

# 3. Check disk I/O
iostat -x 1
# %util > 80%? Disk bottleneck

# 4. Check for runaway processes
ps aux --sort=-%cpu | head -10
ps aux --sort=-%mem | head -10
```

---

## 16. Security Considerations

> 🔐 Security is embedded throughout this handbook. Here are Linux-specific practices.

### SSH Hardening
- Disable root login via SSH
- Use key-based authentication only
- Change the default SSH port
- Use `fail2ban` to block brute force attempts

### File Permissions
- Follow principle of least privilege
- Never use `chmod 777`
- Protect sensitive files (keys, configs, secrets)
- Use proper ownership (`chown`)

### System Updates
```bash
# Keep your system patched
sudo apt update && sudo apt upgrade -y

# Enable automatic security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Firewall Basics (UFW)
```bash
# Enable firewall
sudo ufw enable

# Allow SSH (do this BEFORE enabling!)
sudo ufw allow 22/tcp

# Allow web traffic
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status verbose

# Deny by default, allow explicitly
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

---

## 17. Interview Insights

### Frequently Asked Questions

**Q: What happens when you type `ls -la` and press Enter?**
> The shell (bash) parses the command, searches `$PATH` for the `ls` binary, forks a child process, calls `execve()` to run `ls` with the `-la` flag, which uses system calls to read directory entries and file metadata (inodes), then outputs formatted results to stdout.

**Q: Explain Linux file permissions.**
> Every file has three permission sets: owner, group, others. Each set can have read (4), write (2), and execute (1) permissions. Directories need execute permission to be entered. Common examples: 755 for executables/directories, 644 for regular files, 600 for sensitive files like SSH keys.

**Q: What's the difference between a process and a thread?**
> A process has its own memory space, PID, and resources. A thread shares memory space with other threads in the same process. Processes are isolated (security boundary); threads are lightweight and share data more easily.

**Q: How do you troubleshoot a server that's running slowly?**
> Start with `uptime` (load), `free -h` (memory), `df -h` (disk), `top`/`htop` (CPU-heavy processes). Check `iostat` for disk I/O. Look at logs. Check for recent changes. Work from the most impactful resource downward.

**Q: What's the difference between `kill` and `kill -9`?**
> `kill` sends SIGTERM (signal 15) — the process gets to clean up (close connections, write files, remove temp files). `kill -9` sends SIGKILL (signal 9) — the kernel immediately terminates the process with no cleanup. Always try SIGTERM first; use SIGKILL only as a last resort.

**Q: Explain the difference between soft links and hard links.**
> A hard link is another directory entry pointing to the same inode (same data on disk). Deleting the original doesn't affect the hard link. A soft (symbolic) link is a file that points to a path. If the original is deleted, the soft link is broken. Hard links can't cross filesystems; soft links can.

### Scenario-Based Questions

**Q: You SSH into a server and can't run any commands. "bash: command not found" for everything. What happened?**
> The `$PATH` variable is wrong or empty. Check with `echo $PATH`. If it's empty, set it manually: `export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"`. Then check `~/.bashrc` and `/etc/environment` for what corrupted it.

**Q: Disk space is full, but you can't find large files. What do you check?**
> Check for deleted files still held open by processes: `lsof | grep deleted`. A process may have deleted a large log file but still has the file handle open. Restart the process to release the space. Also check `du -sh /proc/*/fd 2>/dev/null` and look for large inodes with `df -i`.

---

## ➡️ What's Next?

You now have solid Linux fundamentals. Next, we tackle the network layer — understanding how machines talk to each other is essential for debugging and securing infrastructure.

**[Module 02: Networking →](../02-networking/)**

---

<div align="center">

**Module 01 Complete** ✅

[← Back to Foundations](../00-foundations/) | [Next: Networking →](../02-networking/)

</div>
]]>
