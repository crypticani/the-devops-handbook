# Lab 01: Ansible Basics — Configure Servers with Playbooks

## 🎯 Objective

Write and run Ansible playbooks against Docker containers as managed nodes. You'll build an inventory, run ad-hoc commands, write playbooks, create a role, and use templates — all without needing cloud servers.

---

## 📋 Prerequisites

- Docker and Docker Compose installed
- Ansible installed (`ansible --version`)
- Completed Module 10 (Terraform)

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Commands you ran and the important output you used for validation
- Any files, scripts, configs, manifests, or workflows you created
- A short failure note describing one thing that broke, how you diagnosed it, and how you fixed it
- Cleanup commands or confirmation that no long-running resources remain

Treat the validation section as the minimum proof that the lab worked.

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

This local lab uses Ubuntu containers because they are lightweight and predictable. The same Ansible patterns apply to RHEL-compatible hosts; use `ansible_os_family` facts, `package`, `dnf`, or `yum` instead of hard-coding `apt`.

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

# Install curl on web servers only (Ubuntu lab containers)
ansible webservers -i inventory.ini -m apt -a "name=curl state=present"

# Cross-distro alternative for real mixed fleets
ansible webservers -i inventory.ini -m package -a "name=curl state=present" --become

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
    - name: Update apt cache on Debian/Ubuntu
      apt:
        update_cache: true
        cache_valid_time: 3600
      when: ansible_os_family == "Debian"

    - name: Install required packages on any supported Linux family
      package:
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

## 🧨 Break It: Four Ways a Playbook Lies to You

A playbook that reports `ok=5 changed=0 failed=0` looks like success. Each scenario below produces green output while doing the wrong thing — or nothing at all.

### Scenario 1: The Task That Is Always "Changed"

**Break it:**

```bash
cd ansible-lab

cat > drift-test.yml <<'PLAYBOOK'
---
- name: Demonstrate false change reporting
  hosts: webservers
  tasks:
    - name: Ensure app directory exists
      ansible.builtin.file:
        path: /opt/myapp
        state: directory
        mode: "0755"

    - name: Write a build marker
      ansible.builtin.shell: "date > /opt/myapp/build-info.txt"

    - name: Check the service is enabled
      ansible.builtin.command: systemctl is-enabled nginx
PLAYBOOK

ansible-playbook -i inventory.ini drift-test.yml
ansible-playbook -i inventory.ini drift-test.yml     # run it a SECOND time
```

**Symptom:** The `file` task correctly reports `ok` on the second run. The two `command`/`shell` tasks report **`changed`** every single time — even though the third one only *reads* state and changes nothing.

**Investigate:**

```bash
ansible-playbook -i inventory.ini drift-test.yml --check
# The command tasks are SKIPPED in check mode — so --check tells you nothing about them

ansible-playbook -i inventory.ini drift-test.yml --diff
# No diff shown for shell/command either — Ansible has no idea what they did
```

**Root cause:** Ansible modules are idempotent because they *inspect* state before acting. `command` and `shell` cannot inspect anything — Ansible has no idea what your command does, so it conservatively reports `changed` every time.

This matters for three reasons: **(1)** you can never trust `changed=0` as "nothing drifted"; **(2)** a `notify:` on such a task fires its handler on **every run**, so Nginx restarts every time the playbook runs; **(3)** `--check` mode silently skips these tasks, so your dry run isn't a dry run.

**Fix — give Ansible a way to know:**

```yaml
# (a) creates: — skip entirely if the artifact already exists
- name: Extract the release bundle
  ansible.builtin.command: tar xzf /tmp/app.tar.gz -C /opt/myapp
  args:
    creates: /opt/myapp/VERSION        # ⭐ makes it idempotent AND check-mode safe

# (b) changed_when: — decide from the output
- name: Apply database migrations
  ansible.builtin.command: /opt/myapp/migrate.sh
  register: migrate
  changed_when: "'applied' in migrate.stdout"
  failed_when: migrate.rc != 0 and 'no pending migrations' not in migrate.stderr

# (c) A read-only check should NEVER report changed
- name: Check the service is enabled
  ansible.builtin.command: systemctl is-enabled nginx
  register: enabled_check
  changed_when: false                  # ⭐
  check_mode: false                    # safe to run even in --check
  failed_when: enabled_check.rc not in [0, 1]

# (d) Best of all: use the real module
- name: Ensure nginx is enabled
  ansible.builtin.systemd_service:
    name: nginx
    enabled: true
```

> ⭐ **The rule**: every `command`/`shell` task needs `creates:`, `changed_when:`, or both. A playbook where `changed=0` on the second run is the only kind you can trust to tell you about drift.

---

### Scenario 2: The Handler That Never Fires

**Break it:**

```bash
cat > handler-test.yml <<'PLAYBOOK'
---
- name: Handler failure modes
  hosts: webservers
  tasks:
    - name: Deploy a config file
      ansible.builtin.copy:
        content: "# managed by ansible\nworker_processes 2;\n"
        dest: /etc/nginx/conf.d/workers.conf
      notify: reload nginx

    - name: A task that fails AFTER the notify
      ansible.builtin.command: /bin/false

  handlers:
    - name: reload nginx
      ansible.builtin.service:
        name: nginx
        state: reloaded
PLAYBOOK

ansible-playbook -i inventory.ini handler-test.yml
```

**Symptom:** The copy task reports `changed`. The next task fails. The playbook aborts — and the handler **never runs**. You now have a new config file on disk that Nginx has not loaded. The running service and its config are out of sync, and nothing says so.

Then run it again:

```bash
ansible-playbook -i inventory.ini handler-test.yml
```

**Second symptom:** The copy task now reports `ok` (the file is already correct), so it does **not** notify, so the handler **still** never runs. The drift is now permanent and invisible.

**Investigate:**

```bash
# Config on disk vs config in the running process
docker compose exec web1 cat /etc/nginx/conf.d/workers.conf
docker compose exec web1 nginx -T 2>/dev/null | grep worker_processes
docker compose exec web1 ps aux | grep 'nginx: worker' | wc -l
```

**Root cause:** Handlers run **once, at the end of the play**, and only if the notifying task reported `changed`. Two consequences: a failure anywhere before the end cancels them, and a re-run won't re-notify because the change already happened.

**Fix:**

```yaml
- name: Handler failure modes
  hosts: webservers
  force_handlers: true          # ⭐ run notified handlers even if a later task fails
  tasks:
    - name: Deploy a config file
      ansible.builtin.template:
        src: workers.conf.j2
        dest: /etc/nginx/conf.d/workers.conf
        validate: "nginx -t -c %s"      # ⭐ never write a config that won't load
      notify: reload nginx

    - name: Flush handlers before anything risky
      ansible.builtin.meta: flush_handlers   # ⭐ run them NOW, not at the end
```

For recovery from an already-drifted state, make the desired end state explicit rather than relying on change detection:

```yaml
- name: Ensure the running config matches disk
  ansible.builtin.command: nginx -T
  register: running_cfg
  changed_when: false
  check_mode: false

- name: Reload if the running config is stale
  ansible.builtin.service: {name: nginx, state: reloaded}
  when: "'worker_processes 2' not in running_cfg.stdout"
```

---

### Scenario 3: The Variable That Silently Wasn't What You Thought

**Break it:**

```bash
mkdir -p group_vars host_vars
echo "app_port: 8080"  > group_vars/all.yml
echo "app_port: 9090"  > group_vars/webservers.yml
echo "app_port: 3000"  > host_vars/web1.yml

cat > var-test.yml <<'PLAYBOOK'
---
- name: Where did this value come from?
  hosts: webservers
  vars:
    app_port: 7070
  tasks:
    - name: Show the resolved value
      ansible.builtin.debug:
        msg: "{{ inventory_hostname }} → app_port={{ app_port }}"

    - name: Set a file mode
      ansible.builtin.file:
        path: /tmp/perm-test
        state: touch
        mode: 0644          # ⚠️ UNQUOTED
PLAYBOOK

ansible-playbook -i inventory.ini var-test.yml
ansible-playbook -i inventory.ini var-test.yml -e app_port=1234
docker compose exec web1 ls -l /tmp/perm-test
```

**Symptom one:** `app_port` resolves to `7070` on every host — play `vars:` beat both `group_vars` **and** `host_vars/web1.yml`, which most people expect to win. Then `-e` overrides everything.

**Symptom two:** the file mode is `--w----r-T` or similar nonsense, not `rw-r--r--`.

**Investigate:**

```bash
# ⭐ What does Ansible actually think this host's variables are?
ansible-inventory -i inventory.ini --host web1
ansible -i inventory.ini web1 -m debug -a "var=app_port"

# Trace precedence with verbosity
ansible-playbook -i inventory.ini var-test.yml -vvv | grep -i app_port | head
```

**Root cause (variables):** Ansible has **22 precedence levels**. `host_vars` sits at level 8; play `vars:` at level 10; `-e` extra vars at level 22 and always wins. "More specific host" does **not** mean "higher precedence".

**Root cause (mode):** unquoted `0644` in YAML is parsed as the **decimal integer 644**, which as an octal permission is `1204` — garbage. Ansible warns about this, but the warning scrolls past.

**Fix:**

```yaml
# Always quote file modes
mode: "0644"

# Put overridable values in role defaults/ (lowest precedence, level 1),
# not in vars/ (level 13, nearly impossible for a caller to override).
# Use -e only for genuine run-time overrides, never for configuration.
```

```bash
rm -rf group_vars host_vars var-test.yml
```

---

### Scenario 4: `--check` Says "No Changes", Reality Disagrees

**Break it:**

```bash
cat > check-lies.yml <<'PLAYBOOK'
---
- name: Check mode blind spots
  hosts: webservers
  tasks:
    - name: Create a directory (check-mode aware)
      ansible.builtin.file:
        path: /opt/stage1
        state: directory

    - name: Generate a config from that directory's contents
      ansible.builtin.shell: "ls /opt/stage1 > /tmp/manifest.txt"
      register: manifest

    - name: Deploy based on the manifest
      ansible.builtin.copy:
        src: /tmp/manifest.txt
        remote_src: true
        dest: /opt/stage1/manifest.txt
PLAYBOOK

ansible-playbook -i inventory.ini check-lies.yml --check --diff
```

**Symptom:** `--check` reports that the directory *would* be created and the shell task is **skipped**. The third task then fails or reports misleadingly, because it depends on a file the skipped task would have made. Your dry run tells you nothing useful about the second half of the playbook.

**Investigate:**

```bash
ansible-playbook -i inventory.ini check-lies.yml --check --diff -vv | grep -E 'skipped|changed|failed'
```

**Root cause:** `--check` only works for modules that implement check mode. `command`, `shell`, `script`, and `raw` are skipped entirely. Any task depending on their output then behaves differently — so a green `--check` is not a guarantee.

**Fix:**

```yaml
# Mark read-only commands as safe to run during a check
- name: Read the current version
  ansible.builtin.command: cat /opt/myapp/VERSION
  register: version
  changed_when: false
  check_mode: false        # ⭐ actually run this, even in --check

# Guard dependent tasks so they behave sanely in check mode
- name: Deploy based on the manifest
  ansible.builtin.copy: {src: /tmp/manifest.txt, remote_src: true, dest: /opt/stage1/manifest.txt}
  when: not ansible_check_mode
```

**And use the tooling that catches this statically:**

```bash
ansible-lint check-lies.yml      # flags command-instead-of-module, no-changed-when, risky-file-permissions
ansible-playbook --syntax-check -i inventory.ini site.yml
```

```bash
rm -f check-lies.yml drift-test.yml handler-test.yml
```

---

### The Idempotency Contract

Prove your playbook is honest before you call it done:

```bash
# Run 1: converge
ansible-playbook -i inventory.ini site.yml | tee run1.txt

# Run 2: MUST be changed=0
ansible-playbook -i inventory.ini site.yml | tee run2.txt
grep -E 'changed=[1-9]' run2.txt && echo "❌ NOT IDEMPOTENT" || echo "✅ idempotent"

# Run 3: check mode must also be clean
ansible-playbook -i inventory.ini site.yml --check --diff
```

| Failure | Detection | Fix |
|---------|-----------|-----|
| Always-changed task | `changed != 0` on run 2 | `creates:`, `changed_when:`, or a real module |
| Handler never fired | Config on disk ≠ running config | `force_handlers`, `meta: flush_handlers`, `validate:` |
| Wrong variable value | `ansible-inventory --host X` | Understand precedence; use `defaults/` not `vars/` |
| Nonsense file mode | `ls -l` shows garbage bits | Quote it: `mode: "0644"` |
| `--check` gives false confidence | Tasks skipped in check output | `check_mode: false` on reads; `when: not ansible_check_mode` |
| Secret printed in output | Plaintext in `-v` logs or CI | `no_log: true` |

> ⭐ **The one-line summary**: `changed=0` on a second run is the *only* evidence that a playbook is idempotent — and idempotency is the entire reason to use configuration management instead of a shell script. Commit `run2.txt` as your proof.

**Write this up** in `failure-notes.md`.

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


## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- Inventory file and ansible.cfg
- Playbook YAML files from Exercise 3
- Role directory structure from Exercise 4
- Idempotency proof — output from running the playbook twice

---

[← Back to Module README](../README.md)
