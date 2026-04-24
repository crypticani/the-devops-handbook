# Lab 01: GitHub Actions — Build Your First CI/CD Pipeline

## 🎯 Objective

Go from zero to a working CI/CD pipeline. You'll create GitHub Actions workflows that lint, test, build Docker images, and deploy — the exact pipeline pattern used in production.

---

## 📋 Prerequisites

- A GitHub account with a repository (public or private)
- Docker installed locally (`docker --version`)
- Python 3.10+ or Node.js 18+ installed
- Completed Module 05 (Docker)

---

## 🔬 Exercise 1: Your First Workflow

### Step 1: Create the Workflow File

```bash
# In your project repository
mkdir -p .github/workflows

cat > .github/workflows/hello.yml << 'WORKFLOW'
name: Hello CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:    # Manual trigger

jobs:
  hello:
    name: Hello World
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Print info
        run: |
          echo "🎉 Hello from GitHub Actions!"
          echo "Repository: ${{ github.repository }}"
          echo "Branch: ${{ github.ref_name }}"
          echo "Commit: ${{ github.sha }}"
          echo "Triggered by: ${{ github.event_name }}"
          echo "Runner OS: ${{ runner.os }}"

      - name: List files
        run: ls -la

      - name: Check tools
        run: |
          python3 --version || echo "No Python"
          node --version || echo "No Node"
          docker --version || echo "No Docker"
WORKFLOW
```

### Step 2: Push and Watch

```bash
git add .github/workflows/hello.yml
git commit -m "ci: add hello world workflow"
git push origin main
```

Go to your repo on GitHub → **Actions** tab → Watch the workflow run!

### Step 3: Trigger Manually

1. Go to **Actions** → **Hello CI** → **Run workflow** (dropdown on the right)
2. Click **Run workflow**
3. Watch it execute

**✅ Checkpoint:** You should see a green checkmark. Read every log line — understand what's happening.

---

## 🔬 Exercise 2: Build a Real CI Pipeline

### Step 1: Create a Python App to Test

```bash
# Create project structure
mkdir -p src tests

# Application code
cat > src/app.py << 'APP'
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

def divide(a: int, b: int) -> float:
    """Divide two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def is_even(n: int) -> bool:
    """Check if a number is even."""
    return n % 2 == 0
APP

# Tests
cat > tests/test_app.py << 'TEST'
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from app import add, multiply, divide, is_even

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

def test_multiply():
    assert multiply(3, 4) == 12
    assert multiply(-2, 3) == -6
    assert multiply(0, 100) == 0

def test_divide():
    assert divide(10, 2) == 5.0
    assert divide(7, 2) == 3.5

def test_divide_by_zero():
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide(10, 0)

def test_is_even():
    assert is_even(4) is True
    assert is_even(3) is False
    assert is_even(0) is True
TEST

# Requirements
cat > requirements.txt << 'REQ'
pytest==8.0.0
pytest-cov==4.1.0
flake8==7.0.0
black==24.1.0
REQ
```

### Step 2: Create the CI Workflow

```bash
cat > .github/workflows/ci.yml << 'WORKFLOW'
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
          restore-keys: ${{ runner.os }}-pip-

      - name: Install linters
        run: pip install flake8 black

      - name: Run flake8
        run: flake8 src/ tests/ --max-line-length=120

      - name: Check formatting
        run: black --check src/ tests/

  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    needs: lint
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ matrix.python-version }}-${{ hashFiles('requirements.txt') }}

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests with coverage
        run: pytest tests/ -v --cov=src --cov-report=xml --cov-report=term

      - name: Upload coverage report
        if: matrix.python-version == '3.12'
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage.xml
          retention-days: 7

  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
WORKFLOW
```

### Step 3: Add a Dockerfile

```bash
cat > Dockerfile << 'DOCKERFILE'
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
RUN useradd -r appuser
USER appuser
CMD ["python", "-c", "from src.app import add; print(f'2+3={add(2,3)}')"]
DOCKERFILE
```

### Step 4: Push and Verify

```bash
git add -A
git commit -m "ci: add full CI pipeline with lint, test, build"
git push origin main
```

Watch the pipeline in **Actions** tab:
1. **Lint** runs first (flake8 + black)
2. **Test** runs after lint passes (3 Python versions in parallel)
3. **Build** runs after all tests pass (pushes Docker image to GHCR)

**✅ Checkpoint:** All three jobs should be green. The Docker image should appear in your repo's Packages.

---

## 🔬 Exercise 3: Create a PR Workflow

### Step 1: Create a Feature Branch

```bash
git checkout -b feature/add-subtract

# Add new function
cat >> src/app.py << 'FUNC'

def subtract(a: int, b: int) -> int:
    """Subtract b from a."""
    return a - b
FUNC

# Add test
cat >> tests/test_app.py << 'TEST'

from app import subtract

def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(0, 5) == -5
    assert subtract(-3, -3) == 0
TEST

git add -A
git commit -m "feat: add subtract function"
git push origin feature/add-subtract
```

### Step 2: Create a Pull Request

1. Go to GitHub → your repo → **Pull requests** → **New pull request**
2. Select `feature/add-subtract` → `main`
3. Watch the CI pipeline run on the PR
4. Notice: **Build** job is skipped (it only runs on push to main)

**✅ Checkpoint:** The PR shows CI status checks. Lint and Test must pass before merging.

---

## 🧨 Break It: Debug Failing Workflows

### Failure 1: YAML Syntax Error

```yaml
# Create a broken workflow
name: Broken
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "hello"
       - run: echo "bad indent"   # ← Wrong indentation!
```

Push this and observe: the workflow won't even start. GitHub shows a YAML parse error. **Fix:** proper indentation.

### Failure 2: Missing Secret

```yaml
      - name: Deploy
        env:
          API_KEY: ${{ secrets.MY_API_KEY }}   # Secret doesn't exist!
        run: |
          if [ -z "$API_KEY" ]; then
            echo "ERROR: API_KEY not set!"
            exit 1
          fi
```

The variable will be empty, not cause an error by default. **Fix:** Add the secret in Settings → Secrets → Actions.

### Failure 3: Test Failures

```bash
# Break a test intentionally
echo "def test_broken(): assert 1 == 2" >> tests/test_app.py
git add tests/ && git commit -m "test: broken test"
git push
```

Watch the pipeline fail at the Test stage. Read the logs — find the assertion error. **Fix:** correct the test, push again.

---

## ✅ Validation

- [ ] Create and run a basic GitHub Actions workflow
- [ ] Build a multi-stage CI pipeline (lint → test → build)
- [ ] Use matrix builds to test across multiple Python versions
- [ ] Cache dependencies to speed up pipelines
- [ ] Upload artifacts (coverage reports)
- [ ] Build and push Docker images from CI
- [ ] Create a PR and observe CI checks
- [ ] Debug a failing workflow by reading logs
- [ ] Explain the difference between `push` and `pull_request` triggers

---

[← Back to Module README](../README.md) | [Next Lab: Jenkins Pipeline →](./lab-02-jenkins-pipeline.md)
