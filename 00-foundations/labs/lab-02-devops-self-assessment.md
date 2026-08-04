# Lab 02: DevOps Self-Assessment & Environment Setup

## 🎯 Objective

Assess your current knowledge level and set up the foundational environment you'll use throughout this entire handbook. By the end of this lab, you'll know exactly where your gaps are and have a working development environment.

---

## 📋 Prerequisites

- A computer with at least 8GB RAM (16GB recommended)
- Internet connection
- Willingness to install software

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Commands you ran and the important output you used for validation
- Any files, scripts, configs, manifests, or workflows you created
- A short failure note describing one thing that broke, how you diagnosed it, and how you fixed it
- Cleanup commands or confirmation that no long-running resources remain

Treat the validation section as the minimum proof that the lab worked.

---

## 🔬 Exercise 1: Skills Self-Assessment

Rate yourself 1-5 on each skill. Be honest — this is for you, not anyone else.

```
1 = Never heard of it
2 = Know what it is but never used it
3 = Used it a few times
4 = Comfortable using it
5 = Can teach others
```

### Assessment Checklist

| Skill | Your Rating (1-5) | Module |
|-------|-------------------|--------|
| Linux command line basics | ___ | 01 |
| File permissions and ownership | ___ | 01 |
| Process management (ps, kill, systemd) | ___ | 01 |
| TCP/IP networking basics | ___ | 02 |
| DNS understanding | ___ | 02 |
| HTTP/HTTPS concepts | ___ | 02 |
| Git basics (commit, push, pull) | ___ | 03 |
| Git branching and merging | ___ | 03 |
| Bash scripting | ___ | 04 |
| Python basics | ___ | 04 |
| Docker (building/running containers) | ___ | 05 |
| Docker Compose | ___ | 05 |
| CI/CD concepts | ___ | 06 |
| Monitoring and alerting | ___ | 07 |
| Log management | ___ | 08 |
| Cloud services (any provider) | ___ | 09 |
| Infrastructure as Code | ___ | 10 |
| Kubernetes | ___ | 12 |

### Interpreting Your Scores

- **1-2 on most items**: Start from Module 00. Don't skip anything.
- **3-4 on Modules 01-04**: You can skim these but DO the labs anyway. You'll find gaps.
- **4-5 on Modules 01-05**: Start from Module 06, but read the theory sections of earlier modules.

---

## 🔬 Exercise 2: Setting Up Your Development Environment

### Option A: Native Linux (Best for Learning)

If you're on Debian/Ubuntu:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y \
    curl \
    wget \
    git \
    vim \
    nano \
    htop \
    net-tools \
    tree \
    jq \
    unzip \
    build-essential \
    software-properties-common

# Verify installations
git --version
curl --version
python3 --version
```

If you're on a RHEL-compatible distro:

```bash
# Update system
sudo dnf upgrade -y

# Install essential tools
sudo dnf groupinstall -y "Development Tools"
sudo dnf install -y \
    curl \
    wget \
    git \
    vim \
    nano \
    htop \
    net-tools \
    tree \
    jq \
    unzip \
    python3 \
    python3-pip

# Verify installations
git --version
curl --version
python3 --version
```

**Expected output** (versions may differ):
```
git version 2.43.0
curl 8.5.0
Python 3.12.3
```

### Option B: Windows with WSL2 (Windows Users)

```powershell
# Open PowerShell as Administrator
wsl --install -d Ubuntu-22.04

# After restart, open Ubuntu from Start Menu
# Set up your username and password when prompted
```

Then follow the Linux setup above.

### Option C: macOS

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install essential tools
brew install curl wget git vim htop tree jq

# Verify
git --version
curl --version
python3 --version
```

### Common Setup (All Platforms)

```bash
# Configure Git (use YOUR information)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
git config --global init.defaultBranch main
git config --global core.editor "vim"  # or nano, code, etc.

# Verify Git config
git config --list

# Create a working directory for this handbook
mkdir -p ~/devops-handbook-labs
cd ~/devops-handbook-labs

# Create a test file to verify everything works
echo "DevOps Handbook - Environment Ready!" > test.txt
cat test.txt
```

**Expected output:**
```
DevOps Handbook - Environment Ready!
```

---

## 🔬 Exercise 3: Install Docker (Preview — Used Extensively from Module 05)

We install Docker now because some early labs benefit from it.

### Debian/Ubuntu/WSL2

```bash
# Remove old versions
sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null

# Install prerequisites
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add your user to the docker group (no sudo needed for docker commands)
sudo usermod -aG docker $USER

# Apply the group change (or log out and back in)
newgrp docker

# Verify Docker installation
docker --version
docker compose version
docker run hello-world
```

### RHEL-Compatible

```bash
# Remove old versions if present
sudo dnf remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine podman runc 2>/dev/null

# Add Docker CE repository
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Install Docker Engine
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable and start Docker
sudo systemctl enable --now docker

# Add your user to the docker group (no sudo needed for docker commands)
sudo usermod -aG docker $USER

# Apply the group change (or log out and back in)
newgrp docker

# Verify Docker installation
docker --version
docker compose version
docker run hello-world
```

**Expected output for `docker run hello-world`:**
```
Hello from Docker!
This message shows that your installation appears to be working correctly.
...
```

---

## 🔬 Exercise 4: Create Your Lab Notebook

A lab notebook is a critical DevOps practice — documenting what you learn and what broke.

```bash
# Create your notebook structure
mkdir -p ~/devops-handbook-labs/notes
cd ~/devops-handbook-labs/notes

# Create your first entry
cat > 00-foundations-notes.md << 'EOF'
# Module 00: Foundations — My Notes

## Date Started: $(date +%Y-%m-%d)

## Key Concepts I Learned
- 

## Things I Found Surprising
- 

## Questions I Still Have
- 

## Environment Setup Status
- [ ] Linux/WSL2/macOS ready
- [ ] Git installed and configured
- [ ] Docker installed
- [ ] Lab directory created
- [ ] This notebook created

## Commands I Want to Remember
```bash
# Add useful commands here
```
EOF

echo "Lab notebook created! Edit it as you learn."
```

---

## 🧨 Break It: Recover Your Own Environment

You just spent an hour setting up a working environment. Now break it deliberately — while nothing depends on it — and fix it yourself. Every one of these will happen to you eventually, usually the morning of something important.

> ⭐ These are **safe and fully reversible**. Read the fix before you break each one so you always have a way back. Write down your recovery steps as you go — that document *is* the deliverable.

### Scenario 1: "command not found" for Something You Just Installed

**Break it:**

```bash
# Snapshot your PATH first — this is your undo
echo "$PATH" > ~/path-backup.txt
cat ~/path-backup.txt

# Now cripple it for this shell only
export PATH="/usr/bin:/bin"
docker --version
git --version
```

**Symptom:** Tools that worked a minute ago now report `command not found` — but only in this terminal. Opening a new tab makes them work again, which is deeply confusing the first time you see it.

**Investigate:**

```bash
echo "$PATH"                       # what does the shell search?
which docker || echo "not on PATH"
ls -l /usr/local/bin/docker 2>/dev/null || ls -l /usr/bin/docker
type -a git                        # shows every match, plus aliases and functions
command -v python3
```

**Root cause:** The shell only searches directories listed in `$PATH`. Installers put binaries in places like `/usr/local/bin`, `~/.local/bin`, or a version-manager directory, and then add that path in `~/.bashrc` or `~/.profile`. Change or lose `$PATH` and the binary still exists — the shell just can't find it.

**Fix:**

```bash
export PATH="$(cat ~/path-backup.txt)"     # restore this shell
docker --version                            # working again

# Permanent additions belong in your shell rc file:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

> 💡 This is the same root cause as "my script works in the terminal but fails in cron" (Module 04) and "works locally, fails in CI" (Module 06). Cron and CI runners start with a minimal `PATH`. Learning to recognise it now saves you three separate confusing afternoons later.

---

### Scenario 2: "permission denied" from the Docker Daemon

**Break it:**

```bash
docker ps                                   # works
# Simulate not being in the docker group
sg root -c "docker ps" 2>&1 | head -3
# or, to see it definitively:
sudo -u nobody docker ps 2>&1 | head -3
```

**Symptom:**

```
permission denied while trying to connect to the Docker daemon socket
at unix:///var/run/docker.sock
```

**Investigate:**

```bash
ls -l /var/run/docker.sock          # srw-rw---- 1 root docker
id                                   # are YOU in the docker group?
getent group docker                  # who is?
systemctl is-active docker           # is the daemon even running?
```

**Root cause:** `docker` the CLI is a thin client that talks to `dockerd` over a Unix socket owned by `root:docker` with mode `660`. If your user isn't in the `docker` group, the kernel refuses the connection before Docker is involved at all.

**Fix:**

```bash
sudo usermod -aG docker "$USER"
# ⚠️ Group membership is read at LOGIN. You must start a new session:
newgrp docker            # applies to this shell now
# or log out and back in for it to apply everywhere
id -nG | tr ' ' '\n' | grep docker
```

> ⚠️ **Understand what you just granted.** Membership in the `docker` group is effectively **root on the host** — anyone in it can run `docker run -v /:/host` and read or modify the entire filesystem. It's the right choice on your own machine; it is a privilege grant, not a convenience setting, on a shared server.

---

### Scenario 3: Git Refuses Your SSH Key

**Break it:**

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
ls -l ~/.ssh/ 2>/dev/null

# The classic mistake: copying keys around and losing their permissions
if [ -f ~/.ssh/id_ed25519 ]; then
    cp ~/.ssh/id_ed25519 ~/.ssh/id_ed25519.backup
    chmod 644 ~/.ssh/id_ed25519
    ssh -T git@github.com 2>&1 | head -8
fi
```

**Symptom:**

```
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@         WARNING: UNPROTECTED PRIVATE KEY FILE!          @
Permissions 0644 for '/home/you/.ssh/id_ed25519' are too open.
This private key will be ignored.
```

**Investigate:**

```bash
ls -ld ~ ~/.ssh ~/.ssh/id_ed25519 ~/.ssh/authorized_keys 2>/dev/null
ssh -vT git@github.com 2>&1 | grep -iE 'identity|offering|permission|authenticat'
ssh-add -l                          # is the agent even holding a key?
```

**Root cause:** SSH refuses to use a private key that other users could read. This is a feature, not a bug — but the error can be hidden behind a generic `Permission denied (publickey)` when you're not using `-v`.

**Fix — the permissions SSH insists on:**

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519           # private key
chmod 644 ~/.ssh/id_ed25519.pub       # public key
chmod 600 ~/.ssh/authorized_keys
chmod 600 ~/.ssh/config 2>/dev/null
# ⭐ Your HOME directory must also not be group- or world-writable
chmod g-w,o-w ~

ssh -T git@github.com                 # should now greet you by username
rm -f ~/.ssh/id_ed25519.backup
```

| Path | Mode |
|------|------|
| `~` | not group/world writable |
| `~/.ssh` | `700` |
| private keys | `600` |
| `*.pub` | `644` |
| `authorized_keys` | `600` |

---

### Scenario 4: The Full Disk

**Break it:**

```bash
df -h ~                                     # note your current free space

# Create a 1 GB file (safe — we delete it in a moment)
mkdir -p /tmp/fill-test
fallocate -l 1G /tmp/fill-test/blob 2>/dev/null || dd if=/dev/zero of=/tmp/fill-test/blob bs=1M count=1024
df -h /tmp
du -sh /tmp/fill-test
```

**Symptom (on a real, nearly-full disk):** builds fail with `no space left on device`, Docker refuses to pull images, log writes fail, and — most confusingly — some tools fail while others keep working, because they write to different filesystems.

**Investigate — the standard drill:**

```bash
df -h                                       # 1. which FILESYSTEM is full?
df -i                                       # 2. ⭐ or is it INODES, not bytes?
du -h --max-depth=1 / 2>/dev/null | sort -h | tail -10        # 3. walk down from the top
du -h --max-depth=1 ~ 2>/dev/null | sort -h | tail -10
docker system df                            # 4. ⭐ Docker is very often the answer
```

**Fix:**

```bash
rm -rf /tmp/fill-test
df -h /tmp

# The three reclaims you'll use most often:
docker system df                            # look before you prune
docker system prune                         # stopped containers, unused networks, dangling images
docker system prune -a                      # ⚠️ also every image not used by a running container
sudo journalctl --vacuum-time=7d            # trim systemd logs
sudo apt clean || sudo dnf clean all        # package cache
```

> 💡 Two disk-full traps worth knowing now. **(1)** `df -h` shows plenty of space but writes still fail → you've run out of **inodes** (`df -i`), usually from millions of tiny files. **(2)** You deleted a huge log file and space didn't come back → a process still holds the file open. Find it with `lsof +L1` and restart it. The space returns when the last file handle closes, not when you delete the name.

---

### Deliverable: Your First Runbook

This is the real output of this exercise. Create `~/devops-handbook-labs/notes/environment-runbook.md`:

```markdown
# My Environment Recovery Runbook

## "command not found" for an installed tool
**Symptom:** ...
**Check:** `echo $PATH`, `which X`, `type -a X`
**Fix:** ...

## Docker: permission denied on the socket
...

## Git/SSH: permission denied (publickey)
...

## No space left on device
...
```

For each entry record: the **exact error text** (so you can search for it later), the **commands that diagnose it**, the **fix**, and **why it happens**.

- [ ] All four scenarios broken and recovered by you, not by copy-pasting the fix blindly
- [ ] `environment-runbook.md` committed to your portfolio repo
- [ ] Every tool verified working again: `git --version && docker run --rm hello-world && ssh -T git@github.com`

> ⭐ **Why start here**: writing a runbook while nothing is on fire is the single most useful habit in this handbook. Every module from here on ends with the same deliverable. In a real incident you will not think clearly — you will follow a document. Start building that document now, on failures that cost you nothing.

---

## ✅ Validation

You've completed this lab successfully when:

- [ ] You've completed the self-assessment honestly
- [ ] Your development environment is set up
- [ ] Git is installed and configured with your identity
- [ ] Docker is installed and `hello-world` ran successfully
- [ ] You've created your lab directory and notebook
- [ ] You can open a terminal and run basic commands

### Quick Validation Script

```bash
#!/bin/bash
echo "=== DevOps Handbook Environment Check ==="
echo ""

# Check Git
if command -v git &> /dev/null; then
    echo "✅ Git: $(git --version)"
else
    echo "❌ Git: NOT INSTALLED"
fi

# Check Python
if command -v python3 &> /dev/null; then
    echo "✅ Python: $(python3 --version)"
else
    echo "❌ Python: NOT INSTALLED"
fi

# Check Docker
if command -v docker &> /dev/null; then
    echo "✅ Docker: $(docker --version)"
else
    echo "❌ Docker: NOT INSTALLED"
fi

# Check Docker Compose
if docker compose version &> /dev/null; then
    echo "✅ Docker Compose: $(docker compose version)"
else
    echo "❌ Docker Compose: NOT INSTALLED"
fi

# Check curl
if command -v curl &> /dev/null; then
    echo "✅ curl: installed"
else
    echo "❌ curl: NOT INSTALLED"
fi

echo ""
echo "=== Check Complete ==="
```

Save and run:
```bash
chmod +x env-check.sh
./env-check.sh
```

---

## 💡 Key Takeaways

1. Self-assessment helps you focus your learning on real gaps
2. A consistent development environment prevents "works on my machine" issues
3. Documentation (notebooks) is a DevOps skill — start practicing now
4. Docker will be your most-used tool — getting it installed early is strategic

---

[← Previous Lab](./lab-01-mapping-delivery-pipeline.md) | [Back to Module README](../README.md)


## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- Completed self-assessment matrix with honest skill ratings
- Personal learning roadmap based on your gaps
- Notes on which modules to prioritize and why

---
