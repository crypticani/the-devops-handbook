<![CDATA[# Lab 02: Permissions, Users, and Security

## 🎯 Objective

Master Linux permissions, user management, and security fundamentals. These skills are critical for securing servers, debugging "permission denied" errors, and implementing least-privilege access — all daily DevOps tasks.

---

## 📋 Prerequisites

- Completed Lab 01 (Filesystem Mastery)
- Ubuntu 22.04+ (or WSL2)
- `sudo` access

---

## 🔬 Exercise 1: Understanding Permissions Deeply

### Step 1: Reading Permission Output

```bash
cd ~/devops-labs/module-01

# Create test files with specific permissions
echo '#!/bin/bash
echo "deploy starting..."
sleep 1
echo "deploy complete!"' > scripts/deploy.sh

echo "DB_PASSWORD=supersecret123" > configs/.env
echo "Welcome to our app" > configs/index.html

# Check their default permissions
ls -la scripts/deploy.sh configs/.env configs/index.html
```

**Expected output (similar to):**
```
-rw-r--r-- 1 ubuntu ubuntu  72 Jan 15 10:30 scripts/deploy.sh
-rw-r--r-- 1 ubuntu ubuntu  29 Jan 15 10:30 configs/.env
-rw-r--r-- 1 ubuntu ubuntu  21 Jan 15 10:30 configs/index.html
```

### Step 2: Practice the Permission Math

```bash
# Let's verify we understand the numbers

# Set specific permissions and verify
chmod 755 scripts/deploy.sh
ls -la scripts/deploy.sh
# Expected: -rwxr-xr-x (owner: rwx=7, group: r-x=5, other: r-x=5)

chmod 640 configs/.env
ls -la configs/.env
# Expected: -rw-r----- (owner: rw-=6, group: r--=4, other: ---=0)

chmod 644 configs/index.html
ls -la configs/index.html
# Expected: -rw-r--r-- (owner: rw-=6, group: r--=4, other: r--=4)
```

### Step 3: Special File — SSH Key Permissions

```bash
# Create a fake SSH key to practice permission requirements
echo "FAKE_PRIVATE_KEY_DO_NOT_USE" > configs/id_rsa
echo "FAKE_PUBLIC_KEY" > configs/id_rsa.pub

# SSH requires STRICT permissions on private keys
# Try the wrong permission first
chmod 644 configs/id_rsa
# If this were a real key, SSH would refuse with:
# "WARNING: UNPROTECTED PRIVATE KEY FILE!"
# "Permissions 0644 for 'id_rsa' are too open."

# Set correct permissions
chmod 600 configs/id_rsa      # Only owner can read/write
chmod 644 configs/id_rsa.pub  # Public key can be readable

# Verify
ls -la configs/id_rsa configs/id_rsa.pub
# Expected:
# -rw------- 1 ubuntu ubuntu  27 ... configs/id_rsa
# -rw-r--r-- 1 ubuntu ubuntu  17 ... configs/id_rsa.pub
```

---

## 🔬 Exercise 2: User and Group Management

### Step 1: Understand Your Current User Context

```bash
# Who am I?
whoami
id

# What groups am I in?
groups

# Detailed user entry
grep $(whoami) /etc/passwd

# Understanding the passwd format:
# username:x:UID:GID:comment:home:shell
# The 'x' means password is stored in /etc/shadow
```

### Step 2: Create a Service User (DevOps Pattern)

In production, applications run as dedicated service users — not root, not your personal account.

```bash
# Create a user for a web application
sudo useradd -r -s /usr/sbin/nologin -d /opt/webapp -m webapp

# Flags explained:
# -r             System account (UID < 1000)
# -s /usr/sbin/nologin  Can't log in interactively (security!)
# -d /opt/webapp  Home directory
# -m             Create the home directory

# Verify
grep webapp /etc/passwd
id webapp

# Try to login as this user
sudo su - webapp 2>&1
# Expected error: "This account is currently not available."
# This is CORRECT — service accounts shouldn't allow login!

# Create the app structure
sudo mkdir -p /opt/webapp/{bin,config,logs}
sudo chown -R webapp:webapp /opt/webapp
sudo chmod -R 750 /opt/webapp

# Verify ownership
ls -la /opt/webapp/
```

### Step 3: Group-Based Access Control

```bash
# Create a group for the DevOps team
sudo groupadd devops

# Add your user to the devops group
sudo usermod -aG devops $(whoami)

# Create a shared directory
sudo mkdir -p /opt/shared-configs
sudo chown root:devops /opt/shared-configs
sudo chmod 2775 /opt/shared-configs

# The '2' is the setgid bit — files created here inherit the 'devops' group
# The '77' means owner and group have full access
# The '5' means others can read and traverse

# Apply group changes (or log out and back in)
newgrp devops

# Verify you can write to the shared directory
echo "shared config value" > /opt/shared-configs/shared.conf
ls -la /opt/shared-configs/shared.conf
# Should show 'devops' as the group owner
```

---

## 🔬 Exercise 3: sudo — Power and Responsibility

### Step 1: Understanding sudo

```bash
# Check your sudo privileges
sudo -l

# Run a command as root
sudo whoami
# Output: root

# Run a command as another user
sudo -u webapp whoami
# Output: webapp

# Key concept: sudo provides AUDIT TRAIL
# Every sudo command is logged in /var/log/auth.log
sudo grep "sudo" /var/log/auth.log | tail -5
```

### Step 2: Examining sudoers (Read Only!)

```bash
# NEVER edit /etc/sudoers directly — ALWAYS use visudo
# (visudo checks syntax before saving, preventing lockouts)

# View the sudoers file safely
sudo cat /etc/sudoers

# Look for:
# 1. %sudo ALL=(ALL:ALL) ALL
#    = Users in the 'sudo' group can run any command as any user
#
# 2. root ALL=(ALL:ALL) ALL
#    = root can do everything
```

### Step 3: The Danger of Root

```bash
# Demonstrate why running everything as root is bad

# As root, there's no safety net:
# rm -rf /    ← would destroy the ENTIRE system, no confirmation

# As a regular user:
rm /etc/hostname 2>&1
# Output: rm: cannot remove '/etc/hostname': Permission denied
# The system PROTECTED you!

# With sudo, you're explicitly choosing to bypass that protection:
# sudo rm /etc/hostname  ← DON'T RUN THIS, just understand the concept
```

---

## 🔬 Exercise 4: Real-World Permission Scenarios

### Scenario 1: Web Server File Permissions

```bash
# Simulate a web server setup
sudo mkdir -p /var/www/mysite/{html,uploads,cgi-bin}

# Web server runs as www-data user
# HTML files: readable by all, writable by owner only
sudo chown -R www-data:www-data /var/www/mysite
sudo chmod -R 755 /var/www/mysite/html          # Directories
sudo find /var/www/mysite/html -type f -exec chmod 644 {} \;  # Files

# Upload directory: writable by web server
sudo chmod 775 /var/www/mysite/uploads

# CGI scripts: executable
sudo chmod 755 /var/www/mysite/cgi-bin

# Verify the structure
ls -laR /var/www/mysite/
```

### Scenario 2: Protecting Application Secrets

```bash
# Create a secrets directory (common pattern)
sudo mkdir -p /etc/myapp/secrets

# Store a secret
echo "API_KEY=sk-live-abc123xyz" | sudo tee /etc/myapp/secrets/api.key > /dev/null

# Lock it down
sudo chown root:webapp /etc/myapp/secrets/api.key
sudo chmod 640 /etc/myapp/secrets/api.key

# Verify
ls -la /etc/myapp/secrets/api.key
# Expected: -rw-r----- 1 root webapp ...

# Test: Can you read it without sudo?
cat /etc/myapp/secrets/api.key 2>&1
# Should fail: Permission denied

# Test: Can the webapp user read it?
sudo -u webapp cat /etc/myapp/secrets/api.key
# Should succeed (webapp is in the group)
```

### Scenario 3: Deployment Script Permissions

```bash
# Create a deployment script
cat > /tmp/deploy.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

echo "[$(date)] Starting deployment..."
echo "[$(date)] Pulling latest code..."
# In real life: git pull or docker pull
echo "[$(date)] Restarting service..."
# In real life: systemctl restart myapp
echo "[$(date)] Running health check..."
# In real life: curl -f http://localhost:8080/health
echo "[$(date)] Deployment complete!"
SCRIPT

sudo mv /tmp/deploy.sh /opt/webapp/bin/deploy.sh
sudo chown webapp:devops /opt/webapp/bin/deploy.sh
sudo chmod 750 /opt/webapp/bin/deploy.sh

# Only webapp user and devops group members can run it
# Others cannot even read it

# Verify
ls -la /opt/webapp/bin/deploy.sh
```

---

## 🧨 Break It: Permission Debugging

### Failure 1: "Permission denied" on a Script

```bash
# Create a script without execute permission
echo '#!/bin/bash
echo "This script works!"' > /tmp/broken.sh

# Try to run it
/tmp/broken.sh 2>&1
# Error: bash: /tmp/broken.sh: Permission denied

# Debugging steps:
# 1. Check permissions
ls -la /tmp/broken.sh
# 2. Identify the issue: no 'x' permission
# 3. Fix it
chmod +x /tmp/broken.sh
# 4. Verify
/tmp/broken.sh
# Output: This script works!
```

### Failure 2: Nginx Can't Read Web Files

```bash
# Simulate: wrong ownership on web files
sudo mkdir -p /tmp/www-test
echo "<h1>Hello</h1>" | sudo tee /tmp/www-test/index.html
sudo chown root:root /tmp/www-test/index.html
sudo chmod 600 /tmp/www-test/index.html

# Can www-data read it?
sudo -u www-data cat /tmp/www-test/index.html 2>&1
# Error: Permission denied

# Debug:
ls -la /tmp/www-test/index.html
# Show: -rw------- root root — only root can read!

# Fix:
sudo chown www-data:www-data /tmp/www-test/index.html
sudo chmod 644 /tmp/www-test/index.html

# Verify:
sudo -u www-data cat /tmp/www-test/index.html
# Output: <h1>Hello</h1>
```

### Failure 3: Group Permission Not Working

```bash
# Common mistake: Forgetting -a when adding to a group
# usermod -G docker username  ← REPLACES all groups!
# usermod -aG docker username ← APPENDS to groups!

# Check current groups
id $(whoami)
# Note: Always use -aG (append) to add users to groups
```

---

## ✅ Final Validation

You've completed this lab when you can:

- [ ] Read and interpret `ls -la` output completely
- [ ] Set permissions using both numeric (chmod 755) and symbolic (chmod u+x) notation
- [ ] Create service users with appropriate restrictions
- [ ] Set up group-based access control for shared resources
- [ ] Protect sensitive files (secrets, keys) with correct permissions
- [ ] Debug "permission denied" errors systematically
- [ ] Explain why `chmod 777` is dangerous
- [ ] Explain why `usermod -aG` vs `usermod -G` matters

---

## 💡 Key Takeaways

1. **Principle of least privilege** — give minimum permissions needed
2. Service accounts should have **no login shell** (`/usr/sbin/nologin`)
3. **Never use `chmod 777`** — it's a security risk and a bad habit
4. Always use `sudo` for individual commands, not `sudo su -`
5. SSH keys **require** strict permissions (600) or SSH will refuse them
6. Use groups to manage team access, not per-user permissions

---

[← Previous Lab](./lab-01-filesystem-mastery.md) | [Next Lab: Process Management & Services →](./lab-03-processes-services.md)
]]>
