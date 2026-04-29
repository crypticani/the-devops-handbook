# Lab 01: Ansible Basics — Configure Servers with Playbooks

## 🎯 Objective

Write and run Ansible playbooks against Docker containers as managed nodes. You'll build an inventory, run ad-hoc commands, write playbooks, create a role, and use templates — all without needing cloud servers.

---

## 📋 Prerequisites

- Docker and Docker Compose installed
- Ansible installed (`ansible --version`)
- Completed Module 10 (Terraform)

---

## 🔬 Exercise 1: Set Up the Lab Environment

### Step 1: Create Docker Containers as Managed Nodes

```bash
mkdir -p ansible-lab && cd ansible-lab

cat > docker-compose.yml << 'COMPOSE'
services:
  web1:
    image: ubuntu:22.04
    container_name: web1
    command: >
      bash -c "apt-get update && apt-get install -y openssh-server python3 &&
      mkdir /run/sshd &&
      echo 'root:ansible' | chpasswd &&
      sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config &&
      /usr/sbin/sshd -D"
    ports:
      - "2221:22"

  web2:
    image: ubuntu:22.04
    container_name: web2
    command: >
      bash -c "apt-get update && apt-get install -y openssh-server python3 &&
      mkdir /run/sshd &&
      echo 'root:ansible' | chpasswd &&
      sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config &&
      /usr/sbin/sshd -D"
    ports:
      - "2222:22"

  db1:
    image: ubuntu:22.04
    container_name: db1
    command: >
      bash -c "apt-get update && apt-get install -y openssh-server python3 &&
      mkdir /run/sshd &&
      echo 'root:ansible' | chpasswd &&
      sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config &&
      /usr/sbin/sshd -D"
    ports:
      - "2223:22"
COMPOSE

docker compose up -d
```

### Step 2: Create Inventory

```bash
cat > inventory.ini << 'INV'
[webservers]
web1 ansible_host=127.0.0.1 ansible_port=2221
web2 ansible_host=127.0.0.1 ansible_port=2222

[databases]
db1 ansible_host=127.0.0.1 ansible_port=2223

[all:vars]
ansible_user=root
ansible_password=ansible
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
INV
```

### Step 3: Test Connectivity

```bash
# Ping all hosts
ansible all -i inventory.ini -m ping

# Expected output:
# web1 | SUCCESS => { "ping": "pong" }
# web2 | SUCCESS => { "ping": "pong" }
# db1  | SUCCESS => { "ping": "pong" }
```

**✅ Checkpoint:** All three hosts respond with "pong".

---

## 🔬 Exercise 2: Ad-Hoc Commands

```bash
# Check uptime on all hosts
ansible all -i inventory.ini -m command -a "uptime"

# Install curl on web servers only
ansible webservers -i inventory.ini -m apt -a "name=curl state=present"

# Check disk space
ansible all -i inventory.ini -m command -a "df -h"

# Gather facts about web1
ansible web1 -i inventory.ini -m setup | head -50

# Create a file
ansible webservers -i inventory.ini -m file -a "path=/tmp/ansible-test state=touch"

# Verify the file exists
ansible webservers -i inventory.ini -m command -a "ls -la /tmp/ansible-test"
```

**✅ Checkpoint:** You ran ad-hoc commands on specific groups.

---

## 🔬 Exercise 3: Write a Playbook

### Step 1: Create a Web Server Playbook

```bash
cat > webserver.yml << 'PLAYBOOK'
---
- name: Configure Web Servers
  hosts: webservers
  gather_facts: true

  tasks:
    - name: Update apt cache
      apt:
        update_cache: true
        cache_valid_time: 3600

    - name: Install required packages
      apt:
        name:
          - nginx
          - curl
          - htop
        state: present

    - name: Deploy custom index page
      copy:
        content: |
          <!DOCTYPE html>
          <html>
          <body>
            <h1>Hello from Ansible!</h1>
            <p>Server: {{ inventory_hostname }}</p>
            <p>OS: {{ ansible_distribution }} {{ ansible_distribution_version }}</p>
            <p>Managed by Ansible</p>
          </body>
          </html>
        dest: /var/www/html/index.html
        mode: "0644"

    - name: Start Nginx
      service:
        name: nginx
        state: started
        enabled: true

    - name: Verify Nginx is running
      command: curl -s http://localhost
      register: result
      changed_when: false

    - name: Show web page content
      debug:
        var: result.stdout_lines
PLAYBOOK
```

### Step 2: Run the Playbook

```bash
# Dry run first
ansible-playbook -i inventory.ini webserver.yml --check

# Real run
ansible-playbook -i inventory.ini webserver.yml

# Run again — observe idempotency (most tasks show "ok", not "changed")
ansible-playbook -i inventory.ini webserver.yml
```

**✅ Checkpoint:** Second run shows mostly "ok" — Ansible is idempotent.

---

## 🔬 Exercise 4: Create a Role

### Step 1: Generate Role Structure

```bash
mkdir -p roles
ansible-galaxy init roles/webserver
```

### Step 2: Populate the Role

```bash
# defaults
cat > roles/webserver/defaults/main.yml << 'YAML'
---
http_port: 80
server_name: localhost
app_name: "My App"
YAML

# tasks
cat > roles/webserver/tasks/main.yml << 'YAML'
---
- name: Install Nginx
  apt:
    name: nginx
    state: present
    update_cache: true

- name: Deploy Nginx config
  template:
    src: default.conf.j2
    dest: /etc/nginx/sites-available/default
  notify: Restart Nginx

- name: Deploy index page
  template:
    src: index.html.j2
    dest: /var/www/html/index.html
    mode: "0644"

- name: Ensure Nginx is running
  service:
    name: nginx
    state: started
    enabled: true
YAML

# handlers
cat > roles/webserver/handlers/main.yml << 'YAML'
---
- name: Restart Nginx
  service:
    name: nginx
    state: restarted
YAML

# templates
cat > roles/webserver/templates/default.conf.j2 << 'TEMPLATE'
server {
    listen {{ http_port }};
    server_name {{ server_name }};

    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
TEMPLATE

cat > roles/webserver/templates/index.html.j2 << 'TEMPLATE'
<!DOCTYPE html>
<html>
<head><title>{{ app_name }}</title></head>
<body>
  <h1>{{ app_name }}</h1>
  <p>Server: {{ inventory_hostname }}</p>
  <p>Port: {{ http_port }}</p>
  <p>Deployed by Ansible Role</p>
</body>
</html>
TEMPLATE
```

### Step 3: Use the Role

```bash
cat > site.yml << 'PLAYBOOK'
---
- name: Deploy using roles
  hosts: webservers
  roles:
    - role: webserver
      vars:
        app_name: "DevOps Handbook Lab"
        server_name: "devops-lab.local"
PLAYBOOK

ansible-playbook -i inventory.ini site.yml
```

**✅ Checkpoint:** Role deployed with templates and handlers. Config change triggers Nginx restart.

---

## 🧹 Cleanup

```bash
docker compose down -v
cd .. && rm -rf ansible-lab
```

---

## ✅ Validation

- [ ] Set up Docker containers as Ansible managed nodes
- [ ] Run ad-hoc commands on specific host groups
- [ ] Write and run a playbook that installs and configures Nginx
- [ ] Observe idempotency on second run (ok vs changed)
- [ ] Create a role with tasks, templates, handlers, and defaults
- [ ] Use Jinja2 templates with variables
- [ ] Explain why handlers only run when notified
- [ ] Explain the difference between Ansible and Terraform

---

[← Back to Module README](../README.md)
