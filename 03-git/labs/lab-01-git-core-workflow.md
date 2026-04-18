# Lab 01: Git Core Workflow Mastery

## 🎯 Objective

Build complete fluency with Git's daily workflow — init, add, commit, branch, merge, and conflict resolution. By the end, these commands should be muscle memory.

---

## 📋 Prerequisites

- Git installed and configured (`git config --global user.name/email`)
- Terminal access

---

## 🔬 Exercise 1: Repository Lifecycle

### Step 1: Create and Initialize

```bash
mkdir -p ~/devops-labs/module-03/git-practice
cd ~/devops-labs/module-03/git-practice
git init

# Verify
ls -la .git/
# The .git/ directory IS your repository — everything Git tracks lives here

git status
# On branch main (or master)
# No commits yet
```

### Step 2: First Commits

```bash
# Create an application structure
mkdir -p src config

cat > src/app.py << 'APP'
#!/usr/bin/env python3
"""Simple web application"""

def get_status():
    return {"status": "healthy", "version": "1.0.0"}

def get_config():
    return {"port": 8080, "debug": False}

if __name__ == "__main__":
    print(get_status())
APP

cat > config/settings.yaml << 'CONFIG'
app:
  name: devops-demo
  port: 8080
  environment: development
  
database:
  host: localhost
  port: 5432
  name: myapp
CONFIG

cat > README.md << 'README'
# DevOps Demo App

A simple application for practicing Git workflows.

## Quick Start
```bash
python3 src/app.py
```
README

# Check status — all files are "untracked"
git status

# Stage files individually (understand what you're committing)
git add README.md
git status
# README.md is now in "Changes to be committed" (staged)

git add src/app.py
git add config/settings.yaml

# Commit
git commit -m "feat: initial project structure with app and config"

# View the commit
git log --oneline
```

### Step 3: Making Changes and Seeing Diffs

```bash
# Modify the app
cat >> src/app.py << 'UPDATE'

def get_metrics():
    """Return application metrics"""
    return {
        "requests_total": 0,
        "errors_total": 0,
        "uptime_seconds": 0
    }
UPDATE

# See what changed
git diff
# Shows exact lines added (green +) and removed (red -)

# Stage and commit
git add src/app.py
git diff --staged    # See what's about to be committed
git commit -m "feat: add metrics endpoint"

# View history
git log --oneline
# abc1234 feat: add metrics endpoint
# def5678 feat: initial project structure with app and config
```

---

## 🔬 Exercise 2: Branching and Merging

### Step 1: Feature Branch Workflow

```bash
# Create a feature branch
git checkout -b feature/add-logging

# Make changes on the branch
cat > src/logger.py << 'LOGGER'
#!/usr/bin/env python3
"""Logging configuration"""
import logging

def setup_logging(level="INFO"):
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    return logging.getLogger("app")
LOGGER

# Update app.py to use logging
cat >> src/app.py << 'LOG_UPDATE'

# Logging setup
from logger import setup_logging
logger = setup_logging()
logger.info("Application initialized")
LOG_UPDATE

git add -A
git commit -m "feat: add structured logging module"

# Check what branches exist
git branch
# * feature/add-logging
#   main

# See the divergence
git log --oneline --graph --all
```

### Step 2: Merge the Feature Branch

```bash
# Switch back to main
git checkout main

# Verify the logging files DON'T exist on main
ls src/
# Only app.py — logger.py is only on the feature branch

# Merge the feature branch
git merge feature/add-logging
# Fast-forward merge (no conflicts, linear history)

# Verify
ls src/
# app.py  logger.py — now both files exist on main

git log --oneline

# Delete the merged branch (clean up)
git branch -d feature/add-logging
```

---

## 🔬 Exercise 3: Merge Conflict Resolution

### Step 1: Create a Conflict

```bash
# Create two branches that modify the same file
git checkout -b branch-a
# Modify settings on branch-a
sed -i 's/port: 8080/port: 9090/' config/settings.yaml
git add config/settings.yaml
git commit -m "config: change port to 9090"

# Switch to main and create branch-b
git checkout main
git checkout -b branch-b
# Modify the SAME line differently
sed -i 's/port: 8080/port: 3000/' config/settings.yaml
git add config/settings.yaml
git commit -m "config: change port to 3000"

# Now merge branch-a into main
git checkout main
git merge branch-a    # This works fine (fast-forward)

# Now try to merge branch-b
git merge branch-b
# CONFLICT (content): Merge conflict in config/settings.yaml
# Automatic merge failed!
```

### Step 2: Resolve the Conflict

```bash
# See the conflict
git status
# both modified: config/settings.yaml

# Look at the conflict markers
cat config/settings.yaml
# You'll see:
# <<<<<<< HEAD
#   port: 9090
# =======
#   port: 3000
# >>>>>>> branch-b

# Edit the file — choose the correct value (or combine)
# Let's say we want port 3000
cat > config/settings.yaml << 'RESOLVED'
app:
  name: devops-demo
  port: 3000
  environment: development
  
database:
  host: localhost
  port: 5432
  name: myapp
RESOLVED

# Mark as resolved
git add config/settings.yaml
git commit -m "merge: resolve port conflict, using 3000 for new service"

# Clean up branches
git branch -d branch-a branch-b

# View the merge in history
git log --oneline --graph
```

---

## 🔬 Exercise 4: Undoing Mistakes

### Scenario 1: Uncommit the Last Commit (Keep Changes)

```bash
# Make a commit you want to undo
echo "temporary debug line" >> src/app.py
git add src/app.py
git commit -m "debug: add temp logging"

# Undo the commit but keep changes staged
git reset --soft HEAD~1
git status
# Changes are still staged — you can modify and recommit

# Or undo and unstage
git reset HEAD~1
git status
# Changes are in working directory, not staged

# Clean up
git checkout -- src/app.py
```

### Scenario 2: Revert a Pushed Commit (Safe for Shared Repos)

```bash
# Make a "bad" commit
echo "bad_config=true" >> config/settings.yaml
git add -A && git commit -m "config: add experimental setting"

# Revert it (creates a NEW commit that undoes the change)
git revert HEAD --no-edit

# View history — both commits are visible
git log --oneline -5
# The revert commit shows: Revert "config: add experimental setting"
```

### Scenario 3: Recover a Deleted Branch

```bash
# Create a branch with work
git checkout -b important-work
echo "critical code" > src/critical.py
git add -A && git commit -m "feat: add critical module"

# Switch to main and "accidentally" delete it
git checkout main
git branch -D important-work

# Oh no! But Git remembers — use reflog
git reflog | head -10
# Find the commit hash for "feat: add critical module"

# Recover it
git checkout -b important-work <commit-hash-from-reflog>
# Branch is back with all its work!

# Clean up
git checkout main
git branch -D important-work
```

---

## 🧨 Break It: Git Debugging

### Challenge: "What Changed?"

```bash
# Simulate a deployment investigation
echo "timeout: 5" >> config/settings.yaml
git add -A && git commit -m "v1.0 release"

echo "timeout: 30" >> config/settings.yaml
git add -A && git commit -m "v1.1: increase timeout"

echo "timeout: 1" >> config/settings.yaml
git add -A && git commit -m "v1.2: optimize timeout"

# Production issue: timeouts are too aggressive
# Find what changed:

# Method 1: git log for the file
git log --oneline -- config/settings.yaml

# Method 2: git blame (see who changed each line)
git blame config/settings.yaml

# Method 3: diff between versions
git diff HEAD~2..HEAD -- config/settings.yaml
```

---

## ✅ Validation

- [ ] Create a repo, make commits with proper messages
- [ ] Create and merge feature branches
- [ ] Resolve a merge conflict manually
- [ ] Use `git revert` to undo a commit safely
- [ ] Use `git reflog` to recover lost work
- [ ] Use `git blame` and `git log` to investigate changes
- [ ] Explain when to use merge vs rebase

---

[← Back to Module README](../README.md) | [Next Lab: GitHub Workflows & PRs →](./lab-02-github-workflows.md)
