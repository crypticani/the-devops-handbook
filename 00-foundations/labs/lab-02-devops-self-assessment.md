<![CDATA[# Lab 02: DevOps Self-Assessment & Environment Setup

## 🎯 Objective

Assess your current knowledge level and set up the foundational environment you'll use throughout this entire handbook. By the end of this lab, you'll know exactly where your gaps are and have a working development environment.

---

## 📋 Prerequisites

- A computer with at least 8GB RAM (16GB recommended)
- Internet connection
- Willingness to install software

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

If you're on Ubuntu/Debian:

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

### Ubuntu/Debian/WSL2

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
]]>
