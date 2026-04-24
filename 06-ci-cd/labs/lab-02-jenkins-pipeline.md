# Lab 02: Jenkins Pipeline

## 🎯 Objective

Set up Jenkins from scratch using Docker, create a Declarative Pipeline, configure credentials and triggers, and debug common failures. Understanding Jenkins is essential — it's still the backbone of CI/CD in many enterprises.

---

## 📋 Prerequisites

- Docker installed and running
- Completed Lab 01 (GitHub Actions)
- A GitHub repository with your Python app from Lab 01

---

## 🔬 Exercise 1: Run Jenkins in Docker

### Step 1: Start Jenkins

```bash
mkdir -p ~/devops-labs/module-06/jenkins
cd ~/devops-labs/module-06/jenkins

# Create a Docker Compose file for Jenkins
cat > docker-compose.yml << 'COMPOSE'
version: "3.8"

services:
  jenkins:
    image: jenkins/jenkins:lts-jdk17
    container_name: jenkins
    ports:
      - "8080:8080"
      - "50000:50000"
    volumes:
      - jenkins_home:/var/jenkins_home
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - JAVA_OPTS=-Djenkins.install.runSetupWizard=false
    restart: unless-stopped

volumes:
  jenkins_home:
COMPOSE

# Start Jenkins
docker compose up -d

# Wait for Jenkins to start
echo "Waiting for Jenkins to start..."
sleep 30

# Get the initial admin password
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

### Step 2: Initial Setup

1. Open `http://localhost:8080` in your browser
2. Enter the admin password from the command above
3. Click **Install suggested plugins** (wait ~2 minutes)
4. Create your admin user
5. Accept the default Jenkins URL

### Step 3: Install Additional Plugins

Go to **Manage Jenkins → Plugins → Available plugins** and install:
- **Pipeline** (usually pre-installed)
- **Git**
- **Docker Pipeline**
- **Blue Ocean** (modern UI)

**✅ Checkpoint:** Jenkins dashboard is accessible at `http://localhost:8080`.

---

## 🔬 Exercise 2: Create a Declarative Pipeline

### Step 1: Create a Pipeline Job

1. Click **New Item** on the Jenkins dashboard
2. Enter name: `my-python-pipeline`
3. Select **Pipeline**
4. Click **OK**

### Step 2: Write the Pipeline Script

In the job configuration, scroll to **Pipeline** section. Select **Pipeline script** and paste:

```groovy
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo '📥 Checking out code...'
                // For this lab, we create files inline
                // In production, you'd use: checkout scm
                writeFile file: 'app.py', text: '''
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
'''
                writeFile file: 'test_app.py', text: '''
import pytest
from app import add, multiply, divide

def test_add():
    assert add(2, 3) == 5

def test_multiply():
    assert multiply(3, 4) == 12

def test_divide():
    assert divide(10, 2) == 5.0

def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(10, 0)
'''
                writeFile file: 'requirements.txt', text: 'pytest==8.0.0\npytest-cov==4.1.0\n'
            }
        }

        stage('Install Dependencies') {
            steps {
                echo '📦 Installing dependencies...'
                sh 'pip install -r requirements.txt || pip3 install -r requirements.txt'
            }
        }

        stage('Test') {
            steps {
                echo '🧪 Running tests...'
                sh 'python -m pytest test_app.py -v --junitxml=results.xml || python3 -m pytest test_app.py -v --junitxml=results.xml'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'results.xml'
                }
            }
        }

        stage('Build Info') {
            steps {
                echo "✅ Build #${env.BUILD_NUMBER} completed"
                echo "Job: ${env.JOB_NAME}"
                echo "Workspace: ${env.WORKSPACE}"
            }
        }
    }

    post {
        success {
            echo '🎉 Pipeline completed successfully!'
        }
        failure {
            echo '❌ Pipeline failed!'
        }
        always {
            echo '🧹 Cleaning up...'
            cleanWs()
        }
    }
}
```

### Step 3: Run the Pipeline

1. Click **Save**
2. Click **Build Now** (left sidebar)
3. Click on the build number → **Console Output** to see logs
4. Or click **Blue Ocean** (left sidebar) for the modern visual view

**✅ Checkpoint:** All stages should be green. Click into each stage to read the logs.

---

## 🔬 Exercise 3: Pipeline from SCM (Jenkinsfile)

### Step 1: Create a Jenkinsfile in Your Repo

```bash
cd ~/devops-labs/module-06

# Create a sample project with a Jenkinsfile
mkdir -p jenkins-project && cd jenkins-project
git init

# Create the Jenkinsfile
cat > Jenkinsfile << 'JENKINSFILE'
pipeline {
    agent any

    environment {
        APP_NAME = 'my-app'
        APP_VERSION = '1.0.0'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo "Building ${APP_NAME} v${APP_VERSION}"
            }
        }

        stage('Lint') {
            steps {
                echo '🔍 Linting...'
                sh '''
                    if command -v flake8 > /dev/null 2>&1; then
                        flake8 *.py --max-line-length=120 || true
                    else
                        echo "flake8 not installed, skipping lint"
                    fi
                '''
            }
        }

        stage('Test') {
            steps {
                echo '🧪 Testing...'
                sh '''
                    pip install pytest --quiet 2>/dev/null || pip3 install pytest --quiet 2>/dev/null
                    python -m pytest test_app.py -v 2>/dev/null || python3 -m pytest test_app.py -v 2>/dev/null || echo "No tests found"
                '''
            }
        }

        stage('Deploy to Staging') {
            when {
                branch 'main'
            }
            steps {
                echo '🚀 Deploying to staging...'
                echo "Would deploy ${APP_NAME}:${APP_VERSION}"
            }
        }

        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            input {
                message 'Deploy to production?'
                ok 'Yes, deploy!'
                submitter 'admin'
            }
            steps {
                echo '🚀 Deploying to production...'
                echo "Deployed ${APP_NAME}:${APP_VERSION} to production"
            }
        }
    }

    post {
        success {
            echo "✅ ${APP_NAME} pipeline succeeded"
        }
        failure {
            echo "❌ ${APP_NAME} pipeline failed"
        }
    }
}
JENKINSFILE

git add -A
git commit -m "ci: add Jenkinsfile"
```

### Step 2: Create a Pipeline Job from SCM

1. Jenkins dashboard → **New Item** → name: `scm-pipeline` → **Pipeline**
2. Under **Pipeline**, change **Definition** to: **Pipeline script from SCM**
3. **SCM**: Git
4. **Repository URL**: path to your local repo or GitHub URL
5. **Branch**: `*/main`
6. **Script Path**: `Jenkinsfile`
7. **Save** → **Build Now**

**✅ Checkpoint:** Jenkins reads the Jenkinsfile from your repo and executes the pipeline.

---

## 🧨 Break It: Debug Jenkins Failures

### Failure 1: Groovy Syntax Error

```groovy
// Add this broken stage to your Jenkinsfile
stage('Broken') {
    steps {
        echo 'Missing closing brace'
    }
// Missing closing brace for stage!
```

**What happens:** Pipeline fails to parse. The error message points to a line number.
**Fix:** Always match braces. Use an IDE with Groovy syntax highlighting.

### Failure 2: Permission Denied

```groovy
stage('Docker') {
    steps {
        sh 'docker build -t myapp .'  // Jenkins user can't access Docker socket
    }
}
```

**What happens:** `permission denied` when accessing `/var/run/docker.sock`.
**Fix:** Add Jenkins user to docker group, or mount the socket with proper permissions.

### Failure 3: Workspace Issues

```groovy
stage('Read File') {
    steps {
        sh 'cat /some/absolute/path/config.yml'  // Path doesn't exist on agent
    }
}
```

**What happens:** File not found. Jenkins runs on agents — files must be in the workspace.
**Fix:** Use `${WORKSPACE}` path or `checkout scm` to get files.

---

## 🧹 Clean Up

```bash
# Stop Jenkins
cd ~/devops-labs/module-06/jenkins
docker compose down -v

# Remove all lab data (optional)
# rm -rf ~/devops-labs/module-06
```

---

## ✅ Validation

- [ ] Run Jenkins in Docker and complete initial setup
- [ ] Create and run a Declarative Pipeline with multiple stages
- [ ] Read and understand Jenkins Console Output logs
- [ ] Create a Pipeline from SCM (Jenkinsfile in repo)
- [ ] Use `post` blocks for cleanup and notifications
- [ ] Use `input` for manual approval gates
- [ ] Use `when` conditions for branch-specific stages
- [ ] Debug at least one pipeline failure by reading error logs
- [ ] Explain the difference between Scripted and Declarative pipelines

---

[← Previous Lab: GitHub Actions](./lab-01-github-actions.md) | [← Back to Module README](../README.md)
