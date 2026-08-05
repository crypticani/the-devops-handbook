# Module 11: Ansible — Cheat Sheet

> CLI, inventory, playbook keywords, modules, filters, and Vault. Concepts live in the [module README](./README.md).
> Cross-module daily commands: **[QUICK-REFERENCE.md](../QUICK-REFERENCE.md)**

**Jump to:** [CLI](#cli) · [Inventory](#inventory) · [Ad-hoc](#ad-hoc-commands) · [Playbook keywords](#playbook-keywords) · [Modules](#module-reference) · [Variables](#variables--precedence) · [Facts](#facts) · [Loops & conditions](#loops--conditionals) · [Handlers & templates](#handlers--templates) · [Roles](#roles) · [Vault](#ansible-vault) · [Config](#configuration) · [Errors](#error-decoder)

---

## CLI

```bash
ansible --version
ansible-inventory --list -i inventory.ini          # ⭐ resolved inventory as JSON
ansible-inventory --graph                          # tree view of groups and hosts
ansible-inventory --host web-01                    # all variables for one host

ansible all -m ping                                # ⭐ connectivity check
ansible webservers -m ping -i inventory.ini
ansible all -m setup                               # dump every fact

ansible-playbook site.yml
ansible-playbook site.yml -i production.ini
ansible-playbook site.yml --check                  # ⭐ DRY RUN — changes nothing
ansible-playbook site.yml --check --diff           # ⭐⭐ dry run + show file diffs
ansible-playbook site.yml --diff                   # show what changed in files
ansible-playbook site.yml --limit web-01           # one host
ansible-playbook site.yml --limit 'webservers:!web-03'   # group minus a host
ansible-playbook site.yml --tags deploy,config
ansible-playbook site.yml --skip-tags slow
ansible-playbook site.yml --list-tasks             # what would run, in order
ansible-playbook site.yml --list-hosts
ansible-playbook site.yml --list-tags
ansible-playbook site.yml --start-at-task "Install nginx"    # ⭐ resume after a failure
ansible-playbook site.yml --step                   # confirm each task interactively
ansible-playbook site.yml -e "version=1.2.3"       # extra vars (highest precedence)
ansible-playbook site.yml -e @vars/prod.yml
ansible-playbook site.yml -f 20                    # 20 hosts in parallel (default 5)
ansible-playbook site.yml -v / -vvv / -vvvv        # verbosity; -vvvv includes SSH debug
ansible-playbook site.yml -b -K                    # become root, prompt for sudo password
ansible-playbook site.yml --syntax-check

ansible-galaxy install -r requirements.yml         # install roles/collections
ansible-galaxy collection install community.general
ansible-galaxy role init myrole                    # ⭐ scaffold a role
ansible-galaxy list

ansible-lint playbook.yml                          # ⭐ run this in CI
ansible-doc apt                                    # module documentation offline
ansible-doc -l | grep aws                          # list modules
ansible-config dump --only-changed                 # non-default settings
```

---

## Inventory

### INI format

```ini
[webservers]
web-01 ansible_host=10.0.1.10
web-02 ansible_host=10.0.1.11
web-[03:05] ansible_host=10.0.1.1[3:5]       # range expansion

[dbservers]
db-01 ansible_host=10.0.2.10 ansible_port=2222

[production:children]
webservers
dbservers

[webservers:vars]
http_port=80
app_env=production

[all:vars]
ansible_user=deploy
ansible_ssh_private_key_file=~/.ssh/deploy_ed25519
ansible_python_interpreter=/usr/bin/python3
```

### YAML format (preferred for anything non-trivial)

```yaml
all:
  vars:
    ansible_user: deploy
    ansible_ssh_common_args: '-o ProxyJump=bastion.example.com'
  children:
    production:
      children:
        webservers:
          hosts:
            web-01: {ansible_host: 10.0.1.10}
            web-02: {ansible_host: 10.0.1.11}
          vars:
            http_port: 80
        dbservers:
          hosts:
            db-01: {ansible_host: 10.0.2.10}
```

### Variable directories (⭐ the scalable pattern)

```
inventory/
├── production.ini
├── group_vars/
│   ├── all.yml
│   ├── webservers.yml
│   └── production/
│       ├── vars.yml
│       └── vault.yml        # encrypted
└── host_vars/
    └── web-01.yml
```

### Dynamic inventory

```bash
ansible-inventory -i aws_ec2.yml --graph
```

```yaml
# inventory/aws_ec2.yml
plugin: amazon.aws.aws_ec2
regions: [us-east-1]
filters:
  tag:Environment: production
  instance-state-name: running
keyed_groups:
  - key: tags.Role
    prefix: role
  - key: placement.availability_zone
    prefix: az
hostnames: [private-ip-address]
compose:
  ansible_host: private_ip_address
```

**Key connection variables:** `ansible_host` · `ansible_port` · `ansible_user` · `ansible_ssh_private_key_file` · `ansible_ssh_common_args` · `ansible_become` · `ansible_become_user` · `ansible_become_method` · `ansible_python_interpreter` · `ansible_connection` (`ssh`, `local`, `docker`, `kubectl`, `winrm`)

---

## Ad-Hoc Commands

```bash
ansible all -m ping
ansible all -m command -a "uptime"
ansible all -m shell -a "df -h | grep -v tmpfs"          # shell = pipes/redirects allowed
ansible all -m setup -a "filter=ansible_distribution*"
ansible all -m apt -a "name=nginx state=present" -b      # -b = become root
ansible all -m service -a "name=nginx state=restarted" -b
ansible all -m copy -a "src=/local/f dest=/etc/f mode=0644" -b
ansible all -m file -a "path=/srv/app state=directory owner=deploy mode=0755" -b
ansible all -m user -a "name=deploy groups=docker append=yes" -b
ansible all -m git -a "repo=https://... dest=/srv/app version=main"
ansible all -m reboot -b
ansible all -a "systemctl is-active nginx" --one-line    # ⭐ compact output
ansible webservers -m command -a "nginx -t" -b --limit web-01
```

> 💡 Ad-hoc is for **inspection and emergencies**. Anything you'd run twice belongs in a playbook — that's the whole point of configuration management.

---

## Playbook Keywords

```yaml
---
- name: Configure web servers
  hosts: webservers
  become: true
  become_user: root
  gather_facts: true
  serial: 2                        # ⭐ rolling: 2 hosts at a time
  # serial: ["1", "30%", "100%"]   # canary, then ramp
  max_fail_percentage: 25          # abort if more than 25% fail
  any_errors_fatal: false          # true = one failure stops ALL hosts
  order: shuffle                   # inventory | sorted | reverse_sorted | shuffle
  strategy: linear                 # linear | free | host_pinned
  force_handlers: false            # run handlers even if a later task fails
  throttle: 5
  connection: ssh
  remote_user: deploy
  environment:
    PATH: "/usr/local/bin:{{ ansible_env.PATH }}"
    HTTP_PROXY: "http://proxy:3128"

  vars:
    app_version: "1.2.3"
  vars_files:
    - vars/common.yml
    - vars/{{ ansible_distribution | lower }}.yml
  vars_prompt:
    - name: db_password
      prompt: "Database password"
      private: true

  pre_tasks:
    - name: Remove from load balancer
      ansible.builtin.uri:
        url: "http://lb/api/drain/{{ inventory_hostname }}"
        method: POST
      delegate_to: localhost

  roles:
    - common
    - role: nginx
      vars: {nginx_worker_processes: 4}
      tags: [web]

  tasks:
    - name: Install packages
      ansible.builtin.package:
        name: "{{ packages }}"
        state: present
      notify: restart nginx
      tags: [packages]

  post_tasks:
    - name: Return to load balancer
      ansible.builtin.uri:
        url: "http://lb/api/enable/{{ inventory_hostname }}"
        method: POST
      delegate_to: localhost

  handlers:
    - name: restart nginx
      ansible.builtin.service:
        name: nginx
        state: restarted
```

### Task-level keywords

| Keyword | Purpose |
|---------|---------|
| `name` | Human description — ⭐ always set one |
| `when` | Conditional execution |
| `loop` / `with_items` | Repetition (`loop` is the modern form) |
| `register` | Save the result to a variable |
| `notify` | Trigger a handler (only when the task **changed**) |
| `tags` | Selective execution |
| `become` / `become_user` | Privilege escalation for this task |
| `delegate_to` | Run on a different host (`localhost` for API calls) |
| `run_once` | Execute on the first host only |
| `ignore_errors: true` | Continue on failure ⚠️ use sparingly |
| `failed_when` / `changed_when` | ⭐ Override failure/change detection |
| `until` + `retries` + `delay` | Retry loop |
| `no_log: true` | ⭐ Suppress output — mandatory for secrets |
| `check_mode: false` | Always run, even in `--check` |
| `async` + `poll` | Long-running or fire-and-forget tasks |
| `block` / `rescue` / `always` | Try/catch/finally |

```yaml
- name: Wait for the app to become healthy
  ansible.builtin.uri:
    url: "http://localhost:8080/health"
    status_code: 200
  register: health
  until: health.status == 200
  retries: 30
  delay: 2

- name: Run a migration that reports change correctly
  ansible.builtin.command: /srv/app/migrate.sh
  register: migrate
  changed_when: "'applied' in migrate.stdout"       # ⭐ command is ALWAYS 'changed' otherwise
  failed_when: migrate.rc != 0 and 'no pending' not in migrate.stderr

- name: Handle failure gracefully
  block:
    - name: Deploy new version
      ansible.builtin.command: /srv/app/deploy.sh {{ app_version }}
  rescue:
    - name: Roll back
      ansible.builtin.command: /srv/app/rollback.sh
    - name: Fail loudly
      ansible.builtin.fail:
        msg: "Deploy failed and was rolled back"
  always:
    - name: Clean up
      ansible.builtin.file: {path: /tmp/deploy.lock, state: absent}
```

---

## Module Reference

Use **fully-qualified collection names** (FQCN) — `ansible.builtin.apt`, not `apt`.

### Packages & services

```yaml
- ansible.builtin.package: {name: nginx, state: present}      # ⭐ OS-agnostic
- ansible.builtin.apt: {name: [nginx, curl], state: present, update_cache: true, cache_valid_time: 3600}
- ansible.builtin.dnf: {name: nginx, state: latest}
- ansible.builtin.pip: {name: boto3, state: present, virtualenv: /srv/venv}
- ansible.builtin.systemd_service: {name: nginx, state: started, enabled: true, daemon_reload: true}
- ansible.builtin.service: {name: nginx, state: reloaded}
```

### Files

```yaml
- ansible.builtin.file:
    path: /srv/app
    state: directory        # directory | file | link | absent | touch
    owner: deploy
    group: deploy
    mode: "0755"            # ⭐ quote it — 0755 unquoted is octal→decimal 493
    recurse: true

- ansible.builtin.copy:
    src: files/app.conf
    dest: /etc/app.conf
    mode: "0640"
    backup: true            # ⭐ keep a timestamped copy
    validate: "nginx -t -c %s"

- ansible.builtin.template:
    src: templates/nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    mode: "0644"
    validate: "nginx -t -c %s"     # ⭐ don't write a broken config
  notify: reload nginx

- ansible.builtin.lineinfile:
    path: /etc/ssh/sshd_config
    regexp: '^#?PermitRootLogin'
    line: 'PermitRootLogin no'
    validate: '/usr/sbin/sshd -t -f %s'

- ansible.builtin.blockinfile:
    path: /etc/hosts
    marker: "# {mark} ANSIBLE MANAGED: cluster"
    block: |
      10.0.1.10 web-01
      10.0.1.11 web-02

- ansible.builtin.replace: {path: /etc/f, regexp: 'old', replace: 'new'}
- ansible.builtin.unarchive: {src: app.tar.gz, dest: /srv, remote_src: false}
- ansible.builtin.get_url: {url: "https://...", dest: /tmp/f, checksum: "sha256:abc..."}
- ansible.builtin.stat: {path: /etc/app.conf}
  register: cfg
- ansible.builtin.find: {paths: /var/log, patterns: "*.log", age: 30d}
```

### Users, commands, and cloud

```yaml
- ansible.builtin.user: {name: deploy, groups: [docker, sudo], append: true, shell: /bin/bash, state: present}
- ansible.builtin.group: {name: deployers, state: present}
- ansible.posix.authorized_key: {user: deploy, key: "{{ lookup('file', 'id_ed25519.pub') }}"}

- ansible.builtin.command: /usr/bin/mycmd --flag       # ⭐ no shell — safer
  args: {chdir: /srv/app, creates: /srv/app/.done}     # 'creates' makes it idempotent
- ansible.builtin.shell: "cat a.txt | grep x > b.txt"  # only when you NEED pipes/redirects
- ansible.builtin.raw: "apt-get install -y python3"    # for hosts without Python yet
- ansible.builtin.script: files/bootstrap.sh

- ansible.builtin.uri: {url: "https://api/health", method: GET, status_code: 200, return_content: true}
- ansible.builtin.wait_for: {port: 8080, host: localhost, timeout: 60, delay: 5}
- ansible.builtin.wait_for_connection: {timeout: 300}   # after a reboot
- ansible.builtin.reboot: {reboot_timeout: 600}
- ansible.builtin.cron: {name: "nightly backup", minute: "30", hour: "2", job: "/srv/backup.sh"}
- ansible.builtin.git: {repo: "https://...", dest: /srv/app, version: v1.2.3}
- ansible.builtin.debug: {var: myvar}
- ansible.builtin.debug: {msg: "Deploying {{ app_version }} to {{ inventory_hostname }}"}
- ansible.builtin.assert:
    that: [ansible_distribution_major_version | int >= 22]
    fail_msg: "Ubuntu 22.04 or newer required"
- ansible.builtin.set_fact: {app_dir: "/srv/{{ app_name }}"}
- ansible.builtin.include_tasks: tasks/deploy.yml
- ansible.builtin.import_tasks: tasks/common.yml       # static, parsed at load time
- ansible.builtin.include_role: {name: nginx}

- community.docker.docker_container: {name: app, image: "myapp:{{ version }}", state: started}
- kubernetes.core.k8s: {state: present, src: manifests/deploy.yml}
- amazon.aws.ec2_instance: {name: web, instance_type: t3.micro, state: running}
```

> 💡 **`command` vs `shell`**: `command` doesn't invoke a shell — no pipes, redirects, or globs, but no injection risk either. Use `command` by default and reach for `shell` only when you genuinely need shell features.

---

## Variables & Precedence

**Lowest → highest** (later wins):

1. Role defaults (`roles/x/defaults/main.yml`) — ⭐ where role authors put overridable values
2. Inventory file/script group vars
3. `inventory/group_vars/all`
4. Playbook `group_vars/all`
5. `inventory/group_vars/<group>`
6. Playbook `group_vars/<group>`
7. Inventory host vars
8. `host_vars/<host>`
9. Host facts / cached `set_fact`
10. Play `vars`
11. Play `vars_prompt`
12. Play `vars_files`
13. Role vars (`roles/x/vars/main.yml`) — ⭐ hard to override; use sparingly
14. Block vars
15. Task vars
16. `include_vars`
17. `set_fact` / registered vars
18. Role/include params
19. **`-e` extra vars** — always wins

```yaml
{{ myvar }}
{{ myvar | default('fallback') }}
{{ hostvars['web-01']['ansible_default_ipv4']['address'] }}     # ⭐ another host's facts
{{ groups['webservers'] }}                                      # list of hosts in a group
{{ groups['webservers'] | map('extract', hostvars, 'ansible_host') | list }}
{{ inventory_hostname }} / {{ inventory_hostname_short }}
{{ ansible_play_hosts }}                                        # hosts still active in this play
{{ play_hosts }} / {{ group_names }}
{{ lookup('env', 'HOME') }}
{{ lookup('file', '/etc/hostname') }}
{{ lookup('password', '/dev/null length=20') }}
{{ lookup('amazon.aws.aws_secret', 'prod/db/password') }}
```

---

## Facts

```bash
ansible web-01 -m setup                                  # everything
ansible web-01 -m setup -a "filter=ansible_distribution*"
ansible web-01 -m setup -a "filter=ansible_mounts"
```

| Fact | Example value |
|------|---------------|
| `ansible_distribution` | `Ubuntu`, `RedHat`, `Rocky` |
| `ansible_distribution_version` | `22.04` |
| `ansible_distribution_major_version` | `22` |
| `ansible_os_family` | ⭐ `Debian`, `RedHat` — branch on this, not the distro |
| `ansible_hostname` / `ansible_fqdn` | Host names |
| `ansible_default_ipv4.address` | Primary IP |
| `ansible_processor_vcpus` | CPU count |
| `ansible_memtotal_mb` | RAM in MB |
| `ansible_mounts` | List of mounted filesystems |
| `ansible_architecture` | `x86_64`, `aarch64` |
| `ansible_service_mgr` | `systemd` |
| `ansible_python_version` | Interpreter version |
| `ansible_date_time.iso8601` | Timestamp |

```yaml
gather_facts: false        # ⭐ big speedup when you don't need facts

- name: Gather only what's needed
  ansible.builtin.setup:
    gather_subset: ['!all', 'network', 'distribution']
```

```ini
# ansible.cfg — cache facts across runs
[defaults]
gathering = smart
fact_caching = jsonfile
fact_caching_connection = /tmp/ansible_facts
fact_caching_timeout = 7200
```

---

## Loops & Conditionals

```yaml
- name: Install packages
  ansible.builtin.package: {name: "{{ item }}", state: present}
  loop: [nginx, curl, git]

- name: Create users
  ansible.builtin.user:
    name: "{{ item.name }}"
    groups: "{{ item.groups }}"
  loop:
    - {name: alice, groups: sudo}
    - {name: bob,   groups: docker}
  loop_control:
    label: "{{ item.name }}"          # ⭐ keeps output readable
    index_var: idx
    pause: 2

- loop: "{{ users | dict2items }}"          # iterate a dict
- loop: "{{ range(1, 5) | list }}"
- loop: "{{ query('fileglob', 'configs/*.conf') }}"
- loop: "{{ groups['webservers'] }}"
- loop: "{{ list_a | zip(list_b) | list }}"
- loop: "{{ nested | subelements('children') }}"
```

```yaml
when: ansible_os_family == "Debian"
when: ansible_distribution_major_version | int >= 22
when: app_env is defined
when: app_env is not defined
when: result.rc == 0
when: "'nginx' in ansible_facts.packages"
when: myvar | bool
when: item.enabled | default(true)
when:                                     # ⭐ a list is an implicit AND
  - ansible_os_family == "Debian"
  - install_nginx | bool
when: ansible_os_family == "Debian" or ansible_os_family == "RedHat"
when: inventory_hostname in groups['production']
```

### Jinja2 filters worth knowing

```jinja
{{ x | default('v') }}          {{ x | default(omit) }}    {# ⭐ omit the parameter entirely #}
{{ list | length }}             {{ list | first }}  {{ list | last }}
{{ list | unique | sort }}      {{ list | join(',') }}
{{ list | select('match','^web') | list }}
{{ list | reject('equalto','x') | list }}
{{ list | map(attribute='name') | list }}
{{ dict | dict2items }}         {{ items | items2dict }}
{{ a | combine(b, recursive=True) }}      {# ⭐ merge dicts #}
{{ x | to_json }}  {{ x | to_nice_yaml }}  {{ s | from_json }}
{{ s | regex_replace('^v', '') }}   {{ s | regex_search('\\d+') }}
{{ s | b64encode }}  {{ s | b64decode }}
{{ p | basename }}  {{ p | dirname }}  {{ p | realpath }}
{{ s | password_hash('sha512') }}
{{ '10.0.0.0/24' | ansible.utils.ipaddr('net') }}
{{ x | int }}  {{ x | float }}  {{ x | string }}  {{ x | bool }}
{{ x | ternary('yes','no') }}
{{ x | mandatory }}             {# fail if undefined #}
```

---

## Handlers & Templates

```yaml
tasks:
  - name: Deploy nginx config
    ansible.builtin.template:
      src: nginx.conf.j2
      dest: /etc/nginx/nginx.conf
      validate: "nginx -t -c %s"
    notify:
      - reload nginx
      - verify nginx

handlers:
  - name: reload nginx
    ansible.builtin.service: {name: nginx, state: reloaded}
    listen: "nginx changed"          # multiple handlers can share a topic

  - name: verify nginx
    ansible.builtin.uri: {url: "http://localhost/health", status_code: 200}
```

**Handler rules:**

- Fire only when the notifying task reports **changed**
- Run **once**, at the **end of the play** (not immediately) — use `meta: flush_handlers` to force them early
- Skipped by default if any task later fails — set `force_handlers: true` to override

```yaml
- name: Force handlers to run now
  ansible.builtin.meta: flush_handlers
```

### Jinja2 templates

```jinja
{# templates/nginx.conf.j2 #}
worker_processes {{ nginx_worker_processes | default(ansible_processor_vcpus) }};

{% for server in groups['appservers'] %}
upstream backend {
    server {{ hostvars[server]['ansible_default_ipv4']['address'] }}:8080;
}
{% endfor %}

server {
    listen {{ http_port }};
    server_name {{ server_name }};
{% if enable_tls | default(false) %}
    listen 443 ssl;
    ssl_certificate     /etc/ssl/{{ server_name }}.crt;
    ssl_certificate_key /etc/ssl/{{ server_name }}.key;
{% endif %}
}

{# whitespace control: {%- strips before, -%} strips after #}
{# Managed by Ansible — do not edit by hand #}
```

---

## Roles

```
roles/nginx/
├── defaults/main.yml     # ⭐ lowest precedence — the role's public API
├── vars/main.yml         # high precedence — internal constants
├── tasks/main.yml        # entry point
├── handlers/main.yml
├── templates/            # .j2 files
├── files/                # static files to copy
├── meta/main.yml         # dependencies, Galaxy metadata
├── library/              # custom modules
├── tests/
└── README.md             # ⭐ document every default
```

```yaml
# meta/main.yml
dependencies:
  - role: common
  - role: firewall
    vars: {firewall_allowed_ports: [80, 443]}

galaxy_info:
  role_name: nginx
  platforms:
    - name: Ubuntu
      versions: [jammy, noble]
```

```yaml
# requirements.yml
roles:
  - name: geerlingguy.nginx
    version: "3.1.4"
  - src: https://github.com/myorg/ansible-role-app.git
    scm: git
    version: v1.2.0             # ⭐ pin a tag, never a branch
collections:
  - name: community.general
    version: ">=8.0.0"
  - name: amazon.aws
```

```bash
ansible-galaxy install -r requirements.yml --force
ansible-galaxy role init myrole
molecule init role myrole --driver-name docker    # role testing framework
molecule test
```

---

## Ansible Vault

```bash
ansible-vault create secrets.yml
ansible-vault edit secrets.yml
ansible-vault view secrets.yml
ansible-vault encrypt existing.yml
ansible-vault decrypt secrets.yml
ansible-vault rekey secrets.yml                            # change the password

# ⭐ Encrypt a single value, inline in an otherwise plaintext file
ansible-vault encrypt_string 'supersecret' --name 'db_password'

ansible-playbook site.yml --ask-vault-pass
ansible-playbook site.yml --vault-password-file ~/.vault_pass
ansible-playbook site.yml --vault-id prod@~/.vault_prod --vault-id dev@~/.vault_dev
```

```yaml
# group_vars/production/vault.yml (encrypted)
vault_db_password: "..."

# group_vars/production/vars.yml (plaintext — ⭐ the indirection pattern)
db_password: "{{ vault_db_password }}"
# Now you can grep for where db_password is USED without decrypting anything
```

```ini
# ansible.cfg
[defaults]
vault_password_file = ~/.vault_pass
```

```bash
# Make encrypted files diffable in git
echo '*.yml diff=ansible-vault merge=binary' >> .gitattributes
git config --global diff.ansible-vault.textconv "ansible-vault view"
```

> ⚠️ **Always set `no_log: true`** on any task that handles a secret. Without it, `-v` output and the task result will print your decrypted password into CI logs.

---

## Configuration

```ini
# ansible.cfg — searched in: ANSIBLE_CONFIG env → ./ansible.cfg → ~/.ansible.cfg → /etc/ansible/ansible.cfg
[defaults]
inventory            = ./inventory/production.ini
roles_path           = ./roles:~/.ansible/roles
collections_path     = ./collections
host_key_checking    = False          # ⚠️ convenient in CI, weaker security
retry_files_enabled  = False
stdout_callback      = yaml           # ⭐ far more readable output
callbacks_enabled    = timer, profile_tasks    # ⭐ shows which tasks are slow
forks                = 20
timeout              = 30
interpreter_python   = auto_silent
deprecation_warnings = True
gathering            = smart
fact_caching         = jsonfile
fact_caching_connection = /tmp/ansible_facts
fact_caching_timeout = 7200

[ssh_connection]
pipelining           = True           # ⭐ big speedup; requires no 'requiretty' in sudoers
ssh_args             = -o ControlMaster=auto -o ControlPersist=60s
control_path         = /tmp/ansible-%%h-%%p-%%r

[privilege_escalation]
become        = True
become_method = sudo
become_user   = root
become_ask_pass = False
```

**Performance checklist:** `pipelining = True` · raise `forks` · `gather_facts: false` where possible · fact caching · `strategy: free` for independent hosts · `async` for long tasks · avoid `loop` over `package` (pass the whole list to one call).

---

## Error Decoder

| Error | Cause | Fix |
|-------|-------|-----|
| `UNREACHABLE! ... Permission denied (publickey)` | SSH auth | Check `ansible_user`, key path, `ssh-add -l`, and the target's `authorized_keys` |
| `Host key verification failed` | Unknown host key | `ssh-keyscan host >> ~/.ssh/known_hosts`, or `host_key_checking=False` |
| `/usr/bin/python: not found` | No Python on the target | `raw` module to bootstrap, or set `ansible_python_interpreter` |
| `Missing sudo password` | `become` without a password | `-K`, or configure NOPASSWD in sudoers |
| `sudo: sorry, you must have a tty` | `requiretty` in sudoers + pipelining | Remove `requiretty`, or disable pipelining |
| Task always reports **changed** | `command`/`shell` can't detect change | Add `changed_when:` or `creates:` |
| `The task includes an option with an undefined variable` | Typo, or the var isn't in scope | `ansible-inventory --host X`; add `\| default(...)` |
| `AnsibleUndefinedVariable` in a template | Variable missing for **that** host | Use `default()`, or define it in `group_vars/all` |
| Handler never runs | The notifying task didn't change | Verify with `--diff`; check the handler `name` matches exactly |
| Playbook succeeded but nothing changed | You were in `--check` mode | Drop `--check` |
| Mode set to something bizarre (e.g. `-r-x-wS`) | Unquoted octal `0644` | ⭐ Quote it: `mode: "0644"` |
| Very slow runs | Fact gathering + no pipelining | `gather_facts: false`, `pipelining = True`, raise `forks` |
| Secret printed in the output | Missing `no_log` | `no_log: true` on the task |
| `FAILED! => changed=false ... Could not find or access` | Wrong `src` path | Paths are relative to the playbook/role `files/` dir |

---

<div align="center">

[← Module 11 README](./README.md) · [Resources](./resources.md) · [Labs](./labs/) · [Handbook Quick Reference](../QUICK-REFERENCE.md)

</div>
