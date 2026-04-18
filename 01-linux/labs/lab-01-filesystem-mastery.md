# Lab 01: Linux Filesystem Mastery

## 🎯 Objective

Navigate the Linux filesystem with confidence, understand the hierarchy, manage files and directories, and develop the muscle memory for commands you'll use every day as a DevOps engineer.

---

## 📋 Prerequisites

- A Linux system (Ubuntu 22.04+ recommended, WSL2 works)
- Terminal access
- No root access required except where `sudo` is specified

---

## 🔬 Exercise 1: Navigation and Discovery

### Step 1: Explore the Root Filesystem

```bash
# Start at root
cd /

# List everything with details
ls -la

# Use tree (install if needed)
sudo apt install -y tree
tree -L 1 /
```

**Expected output:**
```
/
├── bin -> usr/bin
├── boot
├── dev
├── etc
├── home
├── lib -> usr/lib
├── media
├── mnt
├── opt
├── proc
├── root
├── run
├── sbin -> usr/sbin
├── srv
├── sys
├── tmp
├── usr
└── var
```

### Step 2: Understand Each Critical Directory

```bash
# Configuration central — most important for DevOps
ls /etc/ | head -20

# Where are logs? (First place to check when debugging)
ls -la /var/log/

# What processes are running? (Virtual filesystem)
ls /proc/ | head -20

# System information from /proc
cat /proc/cpuinfo | head -10
cat /proc/meminfo | head -10
cat /proc/version
cat /proc/uptime

# What's the hostname?
cat /etc/hostname
hostname
```

### Step 3: Practice Navigation

```bash
# Go home
cd ~
pwd
# Expected: /home/<your-username>

# Create a workspace
mkdir -p ~/devops-labs/module-01/{scripts,configs,logs}

# Verify the structure
tree ~/devops-labs/module-01
# Expected:
# /home/<user>/devops-labs/module-01
# ├── configs
# ├── logs
# └── scripts

# Navigate around and practice cd -
cd ~/devops-labs/module-01/scripts
pwd
cd /var/log
pwd
cd -    # Goes back to scripts
pwd     # Should be back in scripts
```

---

## 🔬 Exercise 2: File Operations Deep Dive

### Step 1: Create and Manipulate Files

```bash
cd ~/devops-labs/module-01

# Create files with content
echo "server_name=web01" > configs/server.conf
echo "port=8080" >> configs/server.conf
echo "environment=production" >> configs/server.conf

# Verify content
cat configs/server.conf
# Expected:
# server_name=web01
# port=8080
# environment=production

# Create multiple files at once
touch logs/{app,error,access,debug}.log

# Verify
ls -la logs/
```

### Step 2: Copy, Move, Rename

```bash
# Copy a file
cp configs/server.conf configs/server.conf.backup

# Copy a directory
cp -r configs/ configs-backup/

# Rename a file
mv configs/server.conf.backup configs/server.conf.bak

# Move a file to a different directory
echo "test log entry" > /tmp/test.log
mv /tmp/test.log logs/

# Verify everything
tree ~/devops-labs/module-01
```

### Step 3: File Information

```bash
# File type detection
file configs/server.conf
# Expected: configs/server.conf: ASCII text

# File size and details
stat configs/server.conf

# Count lines, words, characters
wc configs/server.conf
wc -l configs/server.conf   # Just lines
```

---

## 🔬 Exercise 3: Finding Files (Real DevOps Scenarios)

### Scenario: Find All Config Files Modified Today

```bash
# Create some test files with different timestamps
echo "old config" > /tmp/old.conf
touch -d "2 days ago" /tmp/old.conf

echo "new config" > /tmp/new.conf

# Find files modified in the last day
find /tmp -name "*.conf" -mtime -1
# Should show: /tmp/new.conf

# Find files modified more than 1 day ago
find /tmp -name "*.conf" -mtime +0
# Should show: /tmp/old.conf
```

### Scenario: Find Large Log Files That Are Filling Disk

```bash
# Create test data
dd if=/dev/zero of=logs/large.log bs=1M count=50 2>/dev/null
dd if=/dev/zero of=logs/small.log bs=1K count=10 2>/dev/null

# Find files larger than 10MB
find ~/devops-labs -size +10M
# Should show: logs/large.log

# Find files larger than 10MB with details
find ~/devops-labs -size +10M -exec ls -lh {} \;

# Real-world: Find ALL large files on the system
sudo find / -type f -size +100M -exec ls -lh {} \; 2>/dev/null | sort -k5 -rh | head -10
```

### Scenario: Find All Files Owned by a Specific User

```bash
# Find all files owned by you in /tmp
find /tmp -user $(whoami) -type f 2>/dev/null

# Find all files NOT owned by root in /etc (security audit)
sudo find /etc -not -user root -type f 2>/dev/null
```

---

## 🔬 Exercise 4: Links — Hard vs Soft

```bash
cd ~/devops-labs/module-01

# Create a source file
echo "original content" > configs/original.txt

# Create a hard link
ln configs/original.txt configs/hardlink.txt

# Create a soft (symbolic) link
ln -s configs/original.txt configs/softlink.txt

# Compare
ls -li configs/original.txt configs/hardlink.txt configs/softlink.txt
# Notice: hard link has SAME inode number, soft link has different inode

# Modify through the hard link
echo "modified by hardlink" >> configs/hardlink.txt
cat configs/original.txt
# The change shows up in original! (Same underlying data)

# Delete the original
rm configs/original.txt

# Hard link still works
cat configs/hardlink.txt
# Output: original content\nmodified by hardlink

# Soft link is BROKEN
cat configs/softlink.txt
# Error: No such file or directory

# See the broken link
ls -la configs/softlink.txt
# The link shows in red and points to a missing file
```

### ✅ Validation: Understanding Links

Answer these questions:
- [ ] Can you create a hard link across different filesystems? (No)
- [ ] What happens to a soft link when the target is moved? (It breaks)
- [ ] Why would you use a soft link in DevOps? (e.g., `/etc/nginx/sites-enabled/mysite` → `../sites-available/mysite`)

---

## 🧨 Break It: Intentional Failure Scenarios

### Failure 1: "Permission Denied" When Running a Script

```bash
# Create a script
echo '#!/bin/bash
echo "Hello from the script!"' > scripts/hello.sh

# Try to run it
./scripts/hello.sh
# ERROR: bash: ./scripts/hello.sh: Permission denied

# Debug: Check permissions
ls -la scripts/hello.sh
# -rw-r--r-- (no execute permission!)

# Fix
chmod +x scripts/hello.sh
./scripts/hello.sh
# Output: Hello from the script!
```

### Failure 2: "No Space Left on Device"

```bash
# Simulate filling a small filesystem (using a tmpfs)
sudo mkdir -p /mnt/smalldisk
sudo mount -t tmpfs -o size=5m tmpfs /mnt/smalldisk

# Fill it up
dd if=/dev/zero of=/mnt/smalldisk/bigfile bs=1M count=10 2>&1
# Error: No space left on device

# Verify
df -h /mnt/smalldisk
# Should show 100% usage

# Clean up
sudo rm /mnt/smalldisk/bigfile
sudo umount /mnt/smalldisk
sudo rmdir /mnt/smalldisk
```

### Failure 3: Accidentally Deleting Important Files

```bash
# THIS IS WHY WE ALWAYS MAKE BACKUPS BEFORE CHANGES

# Create an "important" config
echo "database_url=postgresql://prod:5432/myapp" > configs/production.conf

# Oops! Wrong rm command (simulate)
rm configs/production.conf

# It's gone. No recycle bin. No undo.
ls configs/production.conf
# Error: No such file or directory

# Lesson: ALWAYS create backups before modifying configs
# cp file.conf file.conf.bak.$(date +%Y%m%d)
```

---

## ✅ Final Validation

You've completed this lab successfully when you can:

- [ ] Navigate to any directory using absolute and relative paths
- [ ] Use `find` to locate files by name, size, date, and owner
- [ ] Explain the difference between hard links and soft links
- [ ] Create a directory structure without errors
- [ ] Explain what each directory under `/` is for
- [ ] Recover from a "permission denied" error on a script
- [ ] Create file backups before making changes

---

## 💡 Key Takeaways

1. The filesystem hierarchy is standardized — learn it once, use it everywhere
2. `/etc` for configs, `/var/log` for logs — these are your debugging starting points
3. `find` is one of your most powerful tools for operations work
4. Hard links share data; soft links point to paths — different use cases
5. **Always back up config files before editing them**

---

[← Back to Module README](../README.md) | [Next Lab: Permissions & Users →](./lab-02-permissions-users.md)

