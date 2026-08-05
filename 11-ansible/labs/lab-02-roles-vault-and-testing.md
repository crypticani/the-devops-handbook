# Lab 02: Roles, Vault, and Testing

## 🎯 Objective

Turn a working playbook into something a team can maintain. You'll build a role with a proper interface, handle secrets with Ansible Vault without leaking them into logs, orchestrate a genuine zero-downtime rolling deploy, and — the part most people skip — **test** your automation so idempotency is proven rather than assumed.

---

## 📋 Prerequisites

- Completed [Lab 01: Ansible Basics](./lab-01-ansible-basics.md)
- Docker and Docker Compose (managed nodes run as containers)
- `ansible-lint`

```bash
ansible --version
ansible-lint --version 2>/dev/null || pip install --quiet ansible-lint
docker compose version
```

---

## 📦 Deliverables and Evidence

- A role with `defaults/`, `vars/`, `handlers/`, `templates/`, argument validation, and a README
- A Vault-encrypted variables file, plus proof no secret appeared in `-vvv` output
- A rolling deploy across three nodes with the load balancer draining each in turn
- Idempotency proof: a second run reporting `changed=0`
- `ansible-lint` clean output
- `failure-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-02/`](../code/lab-02/).

```bash
cp -r /path/to/the-devops-handbook/11-ansible/code/lab-02/. .
```

---

## 🔬 Exercise 1: The Lab Environment

### Step 1: Three Nodes and a Load Balancer

```bash
mkdir -p ansible-roles-lab && cd ansible-roles-lab
mkdir -p inventory/group_vars roles files

cat > compose.yaml <<'YAML'
# ⭐ A top-level extension field: shared settings without a duplicate `hostname` key
x-web: &web
  image: python:3.12-slim
  command: sleep infinity
  networks: [labnet]

services:
  web1:
    <<: *web
    hostname: web1        # the role's health endpoint reports this; tests assert on it
  web2:
    <<: *web
    hostname: web2
  web3:
    <<: *web
    hostname: web3
  lb:
    image: haproxy:2.9-alpine
    hostname: lb
    ports: ["8080:8080", "8404:8404"]
    volumes:
      - ./files/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    networks: [labnet]
    depends_on: [web1, web2, web3]
networks:
  labnet:
YAML

cat > files/haproxy.cfg <<'CFG'
global
    log stdout format raw local0
defaults
    mode    http
    timeout connect 5s
    timeout client  30s
    timeout server  30s
    option  httpchk GET /health

frontend http_in
    bind *:8080
    default_backend webservers

backend webservers
    balance roundrobin
    # ⭐ Health checks are what make the rolling deploy safe
    server web1 web1:8000 check inter 2s fall 2 rise 2
    server web2 web2:8000 check inter 2s fall 2 rise 2
    server web3 web3:8000 check inter 2s fall 2 rise 2

listen stats
    bind *:8404
    stats enable
    stats uri /
CFG

docker compose up -d
sleep 5
docker compose ps
```

### Step 2: Inventory and Config

```bash
cat > inventory/hosts.yml <<'YAML'
all:
  children:
    webservers:
      hosts:
        web1:
        web2:
        web3:
      vars:
        app_port: 8000
    loadbalancer:
      hosts:
        lb:
YAML

cat > ansible.cfg <<'CFG'
[defaults]
inventory            = ./inventory/hosts.yml
roles_path           = ./roles
host_key_checking    = False
stdout_callback      = yaml
callbacks_enabled    = timer, profile_tasks
interpreter_python   = auto_silent
retry_files_enabled  = False
forces_handlers      = False
deprecation_warnings = True

[ssh_connection]
pipelining = True
CFG

cat > inventory/group_vars/all.yml <<'YAML'
ansible_connection: community.docker.docker
ansible_user: root
YAML

ansible-galaxy collection install community.docker --quiet
ansible all -m ping
```

**✅ Checkpoint:** All four containers respond to `ping`. Using the Docker connection plugin means no SSH keys to manage, and the Ansible semantics are identical.

---

## 🔬 Exercise 2: A Role With a Real Interface

### Step 1: Scaffold

```bash
ansible-galaxy role init roles/webapp --offline
find roles/webapp -type f | sort
```

### Step 2: The Public Interface

```bash
cat > roles/webapp/defaults/main.yml <<'YAML'
---
# ⭐ defaults/ is the role's PUBLIC API — lowest precedence, so callers can override
# anything here. Everything a user might reasonably want to change belongs in this file.

webapp_name: "demo"
webapp_version: "1.0.0"
webapp_port: 8000
webapp_bind_address: "0.0.0.0"

webapp_user: "appuser"
webapp_group: "appuser"
webapp_root: "/srv/webapp"

webapp_log_level: "info"
webapp_workers: 2

# Health check tuning for the rolling deploy
webapp_health_path: "/health"
webapp_health_retries: 20
webapp_health_delay: 1

# Set by the caller from a Vault-encrypted file
webapp_secret_key: ""
webapp_db_password: ""
YAML

cat > roles/webapp/vars/main.yml <<'YAML'
---
# ⭐ vars/ is INTERNAL. High precedence, hard for a caller to override — which is
# exactly what you want for values that are implementation details, not options.
_webapp_service_name: "webapp"
_webapp_config_path: "{{ webapp_root }}/config.ini"
_webapp_pid_file: "/run/webapp.pid"
YAML
```

### Step 3: Validate the Interface

```bash
mkdir -p roles/webapp/meta
cat > roles/webapp/meta/argument_specs.yml <<'YAML'
---
argument_specs:
  main:
    short_description: Install and configure the demo web application
    description:
      - Creates a service account, deploys the application, renders its config
        from a template, and manages the service lifecycle.
    options:
      webapp_name:
        type: str
        required: true
        description: Application name, used for paths and the service unit.
      webapp_version:
        type: str
        required: true
        description: Version string, rendered into the config and the health response.
      webapp_port:
        type: int
        default: 8000
        description: TCP port the application binds.
      webapp_log_level:
        type: str
        default: info
        choices: [debug, info, warning, error]
      webapp_workers:
        type: int
        default: 2
        description: Worker process count.
      webapp_secret_key:
        type: str
        required: true
        no_log: true          # ⭐ never printed, even at -vvv
        description: Application secret key. Supply from Vault.
      webapp_db_password:
        type: str
        required: true
        no_log: true
        description: Database password. Supply from Vault.
YAML
```

> ⭐ **`argument_specs.yml` is the single highest-value file in a shared role.** It validates types, applies defaults, enforces `choices`, and fails at the *start* of the play with a clear message — instead of halfway through, with a confusing template error. `no_log: true` here protects the value everywhere it's used.

### Step 4: Tasks

```bash
cat > roles/webapp/tasks/main.yml <<'YAML'
---
- name: Install runtime prerequisites
  ansible.builtin.apt:
    name: [python3-minimal, curl, procps]
    state: present
    update_cache: true
    cache_valid_time: 3600
  register: webapp_apt
  retries: 3
  delay: 5
  until: webapp_apt is succeeded

- name: Create the service group
  ansible.builtin.group:
    name: "{{ webapp_group }}"
    system: true
    state: present

- name: Create the service account
  ansible.builtin.user:
    name: "{{ webapp_user }}"
    group: "{{ webapp_group }}"
    system: true
    shell: /usr/sbin/nologin
    home: "{{ webapp_root }}"
    create_home: false
    state: present

- name: Create the application directory
  ansible.builtin.file:
    path: "{{ webapp_root }}"
    state: directory
    owner: "{{ webapp_user }}"
    group: "{{ webapp_group }}"
    mode: "0750"              # ⭐ quoted — unquoted 0750 is decimal 750

- name: Deploy the application
  ansible.builtin.template:
    src: app.py.j2
    dest: "{{ webapp_root }}/app.py"
    owner: "{{ webapp_user }}"
    group: "{{ webapp_group }}"
    mode: "0640"
    validate: "python3 -m py_compile %s"     # ⭐ never write a file that won't parse
  notify: restart webapp

- name: Render the configuration
  ansible.builtin.template:
    src: config.ini.j2
    dest: "{{ _webapp_config_path }}"
    owner: "{{ webapp_user }}"
    group: "{{ webapp_group }}"
    mode: "0600"              # contains secrets
  no_log: true                # ⭐ --diff would otherwise print the rendered secrets
  notify: restart webapp

- name: Install the start script
  ansible.builtin.template:
    src: start.sh.j2
    dest: "{{ webapp_root }}/start.sh"
    owner: "{{ webapp_user }}"
    group: "{{ webapp_group }}"
    mode: "0750"
  notify: restart webapp

- name: Ensure the application is running
  ansible.builtin.shell:
    cmd: |
      if [ -f {{ _webapp_pid_file }} ] && kill -0 "$(cat {{ _webapp_pid_file }})" 2>/dev/null; then
        echo "already-running"
      else
        setsid {{ webapp_root }}/start.sh >/var/log/webapp.log 2>&1 &
        echo $! > {{ _webapp_pid_file }}
        echo "started"
      fi
    executable: /bin/bash
  register: webapp_start
  changed_when: "'started' in webapp_start.stdout"     # ⭐ honest change reporting

- name: Wait for the application to become healthy
  ansible.builtin.uri:
    url: "http://127.0.0.1:{{ webapp_port }}{{ webapp_health_path }}"
    status_code: 200
  register: webapp_health_result
  retries: "{{ webapp_health_retries }}"
  delay: "{{ webapp_health_delay }}"
  until: _health.status == 200
  changed_when: false          # ⭐ a check must never report changed
  check_mode: false            # and must run even under --check
YAML
```

### Step 5: Templates and Handlers

```bash
cat > roles/webapp/templates/app.py.j2 <<'JINJA'
#!/usr/bin/env python3
# {{ ansible_managed }}
import configparser, json, os
from http.server import BaseHTTPRequestHandler, HTTPServer

CFG = configparser.ConfigParser()
CFG.read("{{ _webapp_config_path }}")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = {
            "app":      "{{ webapp_name }}",
            "version":  "{{ webapp_version }}",
            "host":     os.uname().nodename,
            "workers":  {{ webapp_workers }},
            "log_level": "{{ webapp_log_level }}",
            # Never echo the secret itself — only prove it was loaded
            "secret_loaded": bool(CFG.get("app", "secret_key", fallback="")),
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode() + b"\n")

    def log_message(self, *args):
        pass

if __name__ == "__main__":
    HTTPServer(("{{ webapp_bind_address }}", {{ webapp_port }}), Handler).serve_forever()
JINJA

cat > roles/webapp/templates/config.ini.j2 <<'JINJA'
; {{ ansible_managed }}
[app]
name       = {{ webapp_name }}
version    = {{ webapp_version }}
log_level  = {{ webapp_log_level }}
secret_key = {{ webapp_secret_key }}

[database]
password = {{ webapp_db_password }}
JINJA

cat > roles/webapp/templates/start.sh.j2 <<'JINJA'
#!/usr/bin/env bash
# {{ ansible_managed }}
set -Eeuo pipefail
exec python3 {{ webapp_root }}/app.py
JINJA

cat > roles/webapp/handlers/main.yml <<'YAML'
---
- name: Restart webapp
  ansible.builtin.shell:
    cmd: |
      if [ -f {{ _webapp_pid_file }} ]; then
        kill "$(cat {{ _webapp_pid_file }})" 2>/dev/null || true
        sleep 1
      fi
      setsid {{ webapp_root }}/start.sh >/var/log/webapp.log 2>&1 &
      echo $! > {{ _webapp_pid_file }}
    executable: /bin/bash
  changed_when: true          # a restart is, by definition, a change
  listen: "restart webapp"

- name: Verify webapp
  ansible.builtin.uri:
    url: "http://127.0.0.1:{{ webapp_port }}{{ webapp_health_path }}"
    status_code: 200
  register: webapp_verify
  retries: 20
  delay: 1
  until: webapp_verify.status == 200
  listen: "restart webapp"     # ⭐ same topic — runs after the restart, every time
YAML
```

> 💡 `{{ ansible_managed }}` renders a "do not edit by hand" banner into every generated file. It's the cheapest way to stop someone hand-editing a file that Ansible will overwrite on the next run.

---

## 🔬 Exercise 3: Ansible Vault

### Step 1: The Indirection Pattern

```bash
echo 'lab-vault-password' > .vault-pass
chmod 600 .vault-pass
echo '.vault-pass' >> .gitignore

mkdir -p inventory/group_vars/webservers

# Encrypted file: every variable prefixed `vault_`
cat > inventory/group_vars/webservers/vault.yml <<'YAML'
---
vault_webapp_secret_key: "sk-prod-9f3c2a11e8b74d05"
vault_webapp_db_password: "Pr0d-DB-P@ssw0rd-2026"
YAML
ansible-vault encrypt --vault-password-file .vault-pass inventory/group_vars/webservers/vault.yml
head -2 inventory/group_vars/webservers/vault.yml

# Plaintext file: maps role variables to the vault ones
cat > inventory/group_vars/webservers/vars.yml <<'YAML'
---
webapp_secret_key: "{{ vault_webapp_secret_key }}"
webapp_db_password: "{{ vault_webapp_db_password }}"
YAML
```

**✅ Checkpoint:** You can now `grep -r webapp_db_password .` and see **where** each secret is used, without decrypting anything. That's the point of the indirection — an all-encrypted file is opaque to code review and to `grep`.

```bash
grep -rn 'webapp_db_password' inventory/ roles/ | grep -v Binary
```

### Step 2: Vault Operations

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=.vault-pass

ansible-vault view inventory/group_vars/webservers/vault.yml
ansible-vault edit inventory/group_vars/webservers/vault.yml     # decrypts to $EDITOR, re-encrypts on save

# ⭐ Encrypt a single value, inline in an otherwise plaintext file
ansible-vault encrypt_string 'another-secret' --name 'webapp_api_token'

# Rotate the vault password itself
# ansible-vault rekey inventory/group_vars/webservers/vault.yml
```

### Step 3: Multiple Vault IDs

Different environments should not share one password:

```bash
echo 'dev-password'  > .vault-dev
echo 'prod-password' > .vault-prod
chmod 600 .vault-dev .vault-prod
printf '.vault-dev\n.vault-prod\n' >> .gitignore

# ansible-vault encrypt --encrypt-vault-id prod \
#   --vault-id prod@.vault-prod inventory/group_vars/prod/vault.yml
#
# ansible-playbook site.yml --vault-id dev@.vault-dev --vault-id prod@.vault-prod
#   ⭐ Ansible picks the right key per file. Someone with only the dev password
#      cannot decrypt prod, even with the whole repository.
```

### Step 4: Make Vault Files Diffable

```bash
cat > .gitattributes <<'EOF'
*vault.yml diff=ansible-vault merge=binary
EOF
git config diff.ansible-vault.textconv "ansible-vault view --vault-password-file .vault-pass"
echo "✅ git diff now shows decrypted content locally"
```

---

## 🔬 Exercise 4: Rolling Deploy

### Step 1: The Playbook

```bash
cat > site.yml <<'YAML'
---
- name: Deploy the web application with zero downtime
  hosts: webservers
  gather_facts: true

  # ⭐ The four keywords that make this a real rolling deploy
  serial: 1                        # one host at a time
  max_fail_percentage: 0           # any failure stops the rollout immediately
  order: inventory
  any_errors_fatal: false

  pre_tasks:
    - name: Drain this host from the load balancer
      ansible.builtin.command:
        cmd: >
          docker compose exec -T lb sh -c
          "echo 'disable server webservers/{{ inventory_hostname }}' | socat stdio /var/run/haproxy.sock"
      delegate_to: localhost
      become: false
      changed_when: true
      failed_when: false           # the lab HAProxy has no admin socket; the pattern is the point

    - name: Pause so in-flight requests can complete
      ansible.builtin.pause:
        seconds: 3

  roles:
    - role: webapp
      tags: [deploy]

  post_tasks:
    - name: Verify this host is serving the new version
      ansible.builtin.uri:
        url: "http://127.0.0.1:{{ webapp_port }}/health"
        return_content: true
      register: _check
      retries: 15
      delay: 1
      until:
        - _check.status == 200
        - _check.json.version == webapp_version      # ⭐ assert the NEW version
      changed_when: false

    - name: Return this host to the load balancer
      ansible.builtin.command:
        cmd: >
          docker compose exec -T lb sh -c
          "echo 'enable server webservers/{{ inventory_hostname }}' | socat stdio /var/run/haproxy.sock"
      delegate_to: localhost
      become: false
      changed_when: true
      failed_when: false

    - name: Report
      ansible.builtin.debug:
        msg: "{{ inventory_hostname }} now serving {{ _check.json.version }}"
YAML
```

### Step 2: Deploy

```bash
ansible-playbook site.yml -e webapp_version=1.0.0
```

Watch the recap: the play runs three times, once per host.

```bash
for h in web1 web2 web3; do
  echo -n "$h: "
  docker compose exec -T "$h" curl -s "http://127.0.0.1:8000/health"
done
docker compose exec -T lb sh -c 'wget -qO- http://web1:8000/health' 2>/dev/null || true
```

### Step 3: Prove Idempotency

```bash
ansible-playbook site.yml -e webapp_version=1.0.0 | tail -8
```

```
web1  : ok=11  changed=0  unreachable=0  failed=0     ⭐
web2  : ok=11  changed=0  unreachable=0  failed=0
web3  : ok=11  changed=0  unreachable=0  failed=0
```

**✅ Checkpoint:** `changed=0` on the second run. This is the **only** evidence that a playbook is idempotent — and idempotency is the entire reason to use configuration management instead of a shell script. Save this output as your proof.

```bash
ansible-playbook site.yml -e webapp_version=1.0.0 | tee run2.txt
grep -E 'changed=[1-9]' run2.txt && echo "❌ NOT IDEMPOTENT" || echo "✅ idempotent"
```

### Step 4: Roll Out a New Version

```bash
ansible-playbook site.yml -e webapp_version=2.0.0

for h in web1 web2 web3; do
  echo -n "$h: "
  docker compose exec -T "$h" curl -s http://127.0.0.1:8000/health | python3 -c 'import json,sys;print(json.load(sys.stdin)["version"])'
done
```

| Keyword | Effect |
|---------|--------|
| `serial: 1` | One host at a time. `serial: [1, "30%", "100%"]` gives you a canary then a ramp |
| `max_fail_percentage: 0` | ⭐ **Stop the rollout** on the first failure — don't break all three |
| `pre_tasks` / `post_tasks` | Drain and restore around the role |
| `delegate_to: localhost` | Run the LB call from the controller, not the target |
| `until` + `retries` | Wait for health rather than guessing with `sleep` |
| Asserting `_check.json.version` | ⭐ Proves the **new** code is live, not just that something answers |

---

## 🔬 Exercise 5: Test Your Automation

### Step 1: Lint

```bash
ansible-lint site.yml roles/ 2>&1 | tail -25
```

`ansible-lint` catches the exact mistakes from Lab 01's Break It section: `command` without `changed_when`, unquoted file modes, missing `name:`, deprecated syntax, and risky permissions.

```bash
cat > .ansible-lint <<'YAML'
---
profile: production        # ⭐ the strictest built-in profile
exclude_paths:
  - .cache/
  - .github/
skip_list: []
warn_list:
  - experimental
YAML
ansible-lint 2>&1 | tail -15
```

### Step 2: Syntax and Dry Run

```bash
ansible-playbook site.yml --syntax-check
ansible-playbook site.yml --check --diff -e webapp_version=2.0.0 2>&1 | tail -20
```

> ⚠️ `--check` skips `command`/`shell` tasks entirely, so a clean check is **not** a guarantee. That's why the role marks its read-only checks with `check_mode: false` — so they actually run and give the dry run something real to work with.

### Step 3: Assertion Tests

```bash
cat > tests/verify.yml <<'YAML'
---
- name: Verify the deployed state
  hosts: webservers
  gather_facts: false
  tasks:
    - name: Fetch the health endpoint
      ansible.builtin.uri:
        url: "http://127.0.0.1:{{ webapp_port }}/health"
        return_content: true
      register: health
      changed_when: false

    - name: Assert the application reports correctly
      ansible.builtin.assert:
        that:
          - health.status == 200
          - health.json.app == webapp_name
          - health.json.version == webapp_version
          - health.json.secret_loaded            # ⭐ the secret arrived, without printing it
          - health.json.host == inventory_hostname
        fail_msg: "health check mismatch on {{ inventory_hostname }}: {{ health.json }}"
        success_msg: "{{ inventory_hostname }} healthy on {{ health.json.version }}"

    - name: Check file permissions
      ansible.builtin.stat:
        path: "{{ item.path }}"
      register: st
      loop:
        - { path: "/srv/webapp/config.ini", mode: "0600" }
        - { path: "/srv/webapp/app.py", mode: "0640" }
        - { path: "/srv/webapp", mode: "0750" }
      changed_when: false

    - name: Assert permissions are correct
      ansible.builtin.assert:
        that: item.stat.mode == item.item.mode
        fail_msg: "{{ item.item.path }} is {{ item.stat.mode }}, expected {{ item.item.mode }}"
      loop: "{{ st.results }}"
      loop_control:
        label: "{{ item.item.path }}"

    - name: Assert the service account cannot log in
      ansible.builtin.command: getent passwd appuser
      register: pw
      changed_when: false
      failed_when: "'nologin' not in pw.stdout"
YAML
mkdir -p tests && mv tests/verify.yml tests/ 2>/dev/null || true
ansible-playbook tests/verify.yml -e webapp_version=2.0.0
```

### Step 4: The Full Test Gate

```bash
cat > test.sh <<'SH'
#!/usr/bin/env bash
# The gate every Ansible change should pass.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
FAIL=0
step() { printf '\n── %s ──\n' "$1"; }

step "lint";         ansible-lint || FAIL=1
step "syntax";       ansible-playbook site.yml --syntax-check || FAIL=1
step "converge";     ansible-playbook site.yml -e webapp_version="${VERSION:-2.0.0}" || FAIL=1
step "verify";       ansible-playbook tests/verify.yml -e webapp_version="${VERSION:-2.0.0}" || FAIL=1

step "idempotence"
out=$(ansible-playbook site.yml -e webapp_version="${VERSION:-2.0.0}")
if grep -qE 'changed=[1-9]' <<<"$out"; then
  echo "❌ NOT IDEMPOTENT:"; grep -E 'changed=[1-9]' <<<"$out"; FAIL=1
else
  echo "✅ changed=0 on the second run"
fi

step "secret leakage"
ansible-playbook site.yml -vvv -e webapp_version="${VERSION:-2.0.0}" 2>&1 \
  | grep -qE 'Pr0d-DB-P@ssw0rd|sk-prod-9f3c2a11' \
  && { echo "❌ A SECRET APPEARED IN THE OUTPUT"; FAIL=1; } \
  || echo "✅ no secrets in -vvv output"

[ $FAIL -eq 0 ] && echo -e "\n✅ all checks passed" || echo -e "\n❌ failures above"
exit $FAIL
SH
chmod +x test.sh && ./test.sh
```

**✅ Checkpoint:** Five gates — lint, syntax, converge, verify, idempotence — plus a check that no secret leaked at maximum verbosity. That last one is the test almost nobody writes and everybody needs.

> 💡 **Molecule** formalises exactly this loop (`create → converge → idempotence → verify → destroy`) with throwaway Docker or Podman instances. `molecule init role myrole --driver-name docker` then `molecule test`. The script above is the same idea without the extra dependency.

---

## 🧨 Break It: Four Role and Vault Failures

### Scenario 1: The Secret in the Output

**Break it:**

```bash
cat > leak-demo.yml <<'YAML'
---
- name: Demonstrate secret leakage
  hosts: web1
  gather_facts: false
  tasks:
    - name: Debug the config  # ❌ prints the secret
      ansible.builtin.debug:
        var: webapp_db_password

    - name: Write a file with the secret, no no_log
      ansible.builtin.copy:
        content: "password={{ webapp_db_password }}\n"
        dest: /tmp/leaked.conf
        mode: "0600"
YAML
ansible-playbook leak-demo.yml --diff 2>&1 | grep -c 'Pr0d-DB-P@ssw0rd'
```

**Symptom:** The password appears in the console, and `--diff` prints the entire rendered file content. In CI that output is stored, indexed, and retained — often readable by anyone with repository access.

**Investigate:**

```bash
# Where else does it leak?
ansible-playbook leak-demo.yml -vvv 2>&1 | grep -c 'Pr0d-DB-P@ssw0rd'

# ⭐ Ansible writes a per-task JSON payload to the target — with -vvv you can see the path
ansible-playbook leak-demo.yml -vvv 2>&1 | grep -oE 'AnsiballZ_[a-z]+\.py' | head -2
```

**Root cause:** Ansible has no idea which variables are sensitive unless you tell it. `debug`, `--diff`, `-vvv`, and any registered result containing the value will all print it.

**Fix:**

```bash
cat > leak-fixed.yml <<'YAML'
---
- name: Handle secrets correctly
  hosts: web1
  gather_facts: false
  tasks:
    - name: Confirm the secret is set, without printing it
      ansible.builtin.assert:
        that: webapp_db_password | length > 0
        success_msg: "db password is set ({{ webapp_db_password | length }} chars)"

    - name: Write a file containing the secret
      ansible.builtin.copy:
        content: "password={{ webapp_db_password }}\n"
        dest: /tmp/safe.conf
        mode: "0600"
      no_log: true              # ⭐ suppresses the task's output AND its diff
YAML
ansible-playbook leak-fixed.yml --diff -vvv 2>&1 | grep -c 'Pr0d-DB-P@ssw0rd' || echo "  ✅ nothing leaked"
```

| Leak path | Guard |
|-----------|-------|
| `debug: var=secret` | Assert on a property (length, presence) instead |
| Task output / `--diff` | `no_log: true` on the task |
| Registered results | `no_log: true`, or don't register |
| Role variables | `no_log: true` in `argument_specs.yml` ⭐ covers every use |
| `-vvv` module args | `no_log: true` |
| CI logs | The `test.sh` grep gate above |

```bash
rm -f leak-demo.yml leak-fixed.yml
```

---

### Scenario 2: The Handler That Skipped a Host

**Break it:**

```bash
cat > handler-gap.yml <<'YAML'
---
- name: Handler skipped by a later failure
  hosts: webservers
  serial: 1
  gather_facts: false
  # ❌ no force_handlers
  tasks:
    - name: Change the config
      ansible.builtin.copy:
        content: "log_level=debug\n"
        dest: /srv/webapp/extra.conf
        mode: "0640"
      notify: reload app

    - name: A task that fails on web2 only
      ansible.builtin.command: /bin/false
      when: inventory_hostname == 'web2'

  handlers:
    - name: reload app
      ansible.builtin.debug:
        msg: "RELOADED on {{ inventory_hostname }}"
YAML
ansible-playbook handler-gap.yml 2>&1 | grep -E 'RELOADED|fatal|PLAY RECAP' -A4 | tail -15
```

**Symptom:** `web1` reloads. `web2` writes the config and then fails, so its handler **never runs** — the file on disk and the running process are now out of sync, silently. `web3` may not run at all.

**Investigate:**

```bash
for h in web1 web2 web3; do
  echo -n "$h extra.conf: "
  docker compose exec -T "$h" cat /srv/webapp/extra.conf 2>/dev/null || echo "(absent)"
done
```

**Root cause:** Handlers run **once, at the end of the play**, and are cancelled if the play fails first. The config change already happened; the reload didn't.

**Fix:**

```yaml
- name: Handler runs regardless
  hosts: webservers
  serial: 1
  force_handlers: true          # ⭐ notified handlers run even if a later task fails
  tasks:
    - name: Change the config
      ansible.builtin.template:
        src: extra.conf.j2
        dest: /srv/webapp/extra.conf
        mode: "0640"
        validate: "test -s %s"  # ⭐ don't write something invalid in the first place
      notify: reload app

    - name: Apply pending handlers before anything risky
      ansible.builtin.meta: flush_handlers    # ⭐ run them NOW
```

```bash
rm -f handler-gap.yml
docker compose exec -T web1 rm -f /srv/webapp/extra.conf 2>/dev/null
docker compose exec -T web2 rm -f /srv/webapp/extra.conf 2>/dev/null
```

---

### Scenario 3: The Role Variable a Caller Cannot Override

**Break it:**

```bash
# Move a tunable from defaults/ into vars/
echo 'webapp_workers: 8' >> roles/webapp/vars/main.yml

cat > override-attempt.yml <<'YAML'
---
- name: Try to override the worker count
  hosts: web1
  gather_facts: false
  roles:
    - role: webapp
      vars:
        webapp_workers: 2          # the caller's intent
YAML
ansible-playbook override-attempt.yml -e webapp_version=2.0.0 2>&1 | tail -4
docker compose exec -T web1 curl -s http://127.0.0.1:8000/health \
  | python3 -c 'import json,sys;print("workers:", json.load(sys.stdin)["workers"])'
```

**Symptom:** `workers: 8`. The caller asked for 2, passed it the documented way, and was silently ignored. No warning, no error.

**Investigate:**

```bash
ansible web1 -m debug -a "var=webapp_workers" -e webapp_version=2.0.0 2>/dev/null | tail -3
grep -n 'webapp_workers' roles/webapp/defaults/main.yml roles/webapp/vars/main.yml
```

**Root cause:** Ansible's precedence. `defaults/main.yml` is level **1** (lowest, easily overridden); `vars/main.yml` is level **13** — above play vars, above role params, above `host_vars`. Only `-e` beats it.

**Fix:**

```bash
# Remove it from vars/ — it belongs in defaults/
sed -i '/webapp_workers: 8/d' roles/webapp/vars/main.yml
ansible-playbook override-attempt.yml -e webapp_version=2.0.0 >/dev/null 2>&1
docker compose exec -T web1 curl -s http://127.0.0.1:8000/health \
  | python3 -c 'import json,sys;print("workers:", json.load(sys.stdin)["workers"])'   # ⭐ 2
rm -f override-attempt.yml
```

| Put it in | When |
|-----------|------|
| `defaults/main.yml` (prec. 1) | ⭐ Anything a caller might reasonably change. **The default choice** |
| `vars/main.yml` (prec. 13) | Internal constants only. Prefix them `_role_name_` so nobody mistakes them for options |
| `-e` extra vars (prec. 22) | Genuine run-time overrides — a version, an environment. Never configuration |

> 💡 A useful rule: if it appears in your role's README as an input, it belongs in `defaults/`. If a caller setting it would break the role, it belongs in `vars/` with an underscore prefix.

---

### Scenario 4: The Vault Password in CI

**Break it:**

```bash
cat > .github-workflow-bad.yml <<'YAML'
name: Deploy
on: [push]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Write the vault password
        run: echo "${{ secrets.VAULT_PASSWORD }}" > .vault-pass     # ⚠️ now on disk
      - name: Deploy
        run: ansible-playbook site.yml --vault-password-file .vault-pass -vvv
        # ⚠️ -vvv in CI, with a vault password file sitting in the workspace
YAML
echo "written (not committed)"
```

**Symptom:** Three compounding problems. The password is written to the workspace, where any later step — including a third-party action — can read it. `-vvv` risks printing decrypted values. And if the job fails after that step, the file may persist in a cached workspace or an uploaded artifact.

**Investigate:**

```bash
# In your own repo, look for the pattern:
grep -rn 'vault-password-file\|VAULT_PASSWORD' . --include='*.yml' --include='*.yaml' 2>/dev/null | grep -v '^\./\.git' | head
# And check nothing sensitive is committed:
git status --short 2>/dev/null | grep -E 'vault-pass|\.vault' || echo "  ✅ nothing staged"
```

**Root cause:** Ansible needs the password as a **file path**, which pushes people into writing it to disk. The safe pattern uses a *script* that fetches it on demand and never persists it.

**Fix:**

```yaml
# ⭐ A vault password CLIENT — an executable that prints the password to stdout.
#    Nothing is ever written to disk.
- name: Deploy
  env:
    VAULT_PASSWORD: ${{ secrets.VAULT_PASSWORD }}    # env, not a file
  run: |
    cat > /tmp/vault-client.sh <<'EOF'
    #!/usr/bin/env bash
    printf '%s' "$VAULT_PASSWORD"
    EOF
    chmod +x /tmp/vault-client.sh
    ansible-playbook site.yml --vault-password-file /tmp/vault-client.sh   # no -vvv
```

Better still, skip the vault password entirely:

```yaml
# ⭐⭐ Fetch secrets at run time from a secret manager, using OIDC.
#     Nothing encrypted in git, no vault password anywhere.
- name: Read secrets from AWS
  run: |
    export WEBAPP_DB_PASSWORD=$(aws secretsmanager get-secret-value \
      --secret-id prod/webapp/db --query SecretString --output text)
    ansible-playbook site.yml
```

```yaml
# Or from within the playbook:
webapp_db_password: "{{ lookup('amazon.aws.aws_secret', 'prod/webapp/db') }}"
webapp_db_password: "{{ lookup('community.hashi_vault.hashi_vault', 'secret=secret/webapp:db_password') }}"
```

```bash
rm -f .github-workflow-bad.yml
```

| Approach | Password on disk? | Rotation |
|----------|------------------|----------|
| `--vault-password-file .vault-pass` written by CI | ⚠️ Yes | Manual, re-encrypt everything |
| Vault password **client script** reading an env var | ✅ No | Manual, re-encrypt everything |
| ⭐ Secret manager lookup at run time | ✅ No | Automatic, nothing to re-encrypt |
| ⭐⭐ Secret manager + OIDC | ✅ No credential at all | Automatic |

---

### Summary

| Failure | Detection | Prevention |
|---------|-----------|------------|
| Secret in output | `grep` the `-vvv` output for a known value | `no_log: true`, in `argument_specs.yml` |
| Handler skipped | Config on disk ≠ running process | `force_handlers`, `meta: flush_handlers`, `validate:` |
| Variable can't be overridden | Caller's value silently ignored | `defaults/` for options, `vars/` for internals only |
| Vault password on disk in CI | `grep` for `vault-password-file` | Password client script, or a secret manager |

**The role checklist:**

- [ ] Every option in `defaults/`, documented in the README
- [ ] `meta/argument_specs.yml` with types, `choices`, and `no_log` on secrets
- [ ] Internal values in `vars/`, prefixed with an underscore
- [ ] Every `command`/`shell` has `changed_when` or `creates`
- [ ] Every read-only check has `changed_when: false` and `check_mode: false`
- [ ] `validate:` on every generated config file
- [ ] File modes **quoted**
- [ ] Handlers idempotent; `force_handlers` where partial application is dangerous
- [ ] `ansible-lint` clean at the `production` profile
- [ ] Idempotence proven: `changed=0` on the second run, committed as evidence
- [ ] A test asserting **no secret appears** in `-vvv` output

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
cd ansible-roles-lab 2>/dev/null || true
docker compose down -v
cd .. && rm -rf ansible-roles-lab
docker ps -a | grep -E 'web[123]|^.*lb ' || echo "✅ clean"
```

---

## ✅ Validation

- [ ] Explain the difference between `defaults/` and `vars/`, and their precedence levels
- [ ] Write `argument_specs.yml` with types, `choices`, and `no_log`
- [ ] Use the `vault_` indirection pattern and explain why it aids code review
- [ ] Use multiple vault IDs so dev and prod don't share a password
- [ ] Run a rolling deploy that drains each host and asserts the **new version** is live
- [ ] Explain `serial`, `max_fail_percentage`, and `delegate_to`
- [ ] Prove idempotency with `changed=0` on a second run
- [ ] Explain why `--check` is not a guarantee
- [ ] Write assertion tests that verify state without printing secrets
- [ ] Explain why `force_handlers` exists and when partial application is dangerous
- [ ] Describe two ways to avoid a vault password file in CI

---

## 📝 What to Commit

- The complete `roles/webapp/` including `argument_specs.yml` and its README
- `site.yml`, `tests/verify.yml`, `test.sh`, `.ansible-lint`
- The **encrypted** `vault.yml` and the plaintext `vars.yml` mapping (⚠️ **never** `.vault-pass`)
- `run2.txt` showing `changed=0` — your idempotency proof
- `ansible-lint` clean output
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: Ansible Basics](./lab-01-ansible-basics.md) | [Back to Module README](../README.md) | [Module 12: Kubernetes →](../../12-kubernetes/)
