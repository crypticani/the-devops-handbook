# Module 11: Ansible — Lab Code

A working inventory, playbooks, and two roles — one introductory, one production-shaped.

These are the real files from this module's labs. `ansible-lint` runs against them in CI at
the **production** profile, so they stay idiomatic as Ansible evolves.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when comparing your version against a reference.

---

## Contents

### `lab-01/`

Docker-based managed nodes, an inventory, a webserver playbook, and a first role with tasks,
handlers, templates and defaults.

```
lab-01/
├── docker-compose.yml
├── inventory.ini
├── roles/webserver/defaults/main.yml
├── roles/webserver/handlers/main.yml
├── roles/webserver/tasks/main.yml
├── roles/webserver/templates/default.conf.j2
├── roles/webserver/templates/index.html.j2
├── site.yml
└── webserver.yml
```

### `lab-02/`

Three web nodes behind HAProxy, and a role built the way a shared role should be: a validated
argument spec, secrets marked `no_log`, honest change reporting, and a test suite.

```
lab-02/
├── .ansible-lint
├── ansible.cfg
├── compose.yaml
├── files/haproxy.cfg
├── inventory/group_vars/all.yml
├── inventory/hosts.yml
├── roles/webapp/defaults/main.yml
├── roles/webapp/handlers/main.yml
├── roles/webapp/meta/argument_specs.yml
├── roles/webapp/tasks/main.yml
├── roles/webapp/templates/app.py.j2
├── roles/webapp/templates/config.ini.j2
├── roles/webapp/templates/start.sh.j2
├── roles/webapp/vars/main.yml
├── site.yml
├── test.sh
└── tests/verify.yml
```

Worth reading in order: `meta/argument_specs.yml` (the role's validated interface) →
`defaults/main.yml` (what a caller may override) → `vars/main.yml` (internals, prefixed `_`) →
`tasks/main.yml` (note `changed_when` on every command) → `tests/verify.yml` → `test.sh`.

> 💡 `test.sh` is the gate: lint → syntax → converge → verify → **idempotence** → a grep
> asserting no secret leaked at `-vvv`. That last check is the one almost nobody writes.

---

## Using these files

```bash
mkdir -p ~/devops-labs/11-ansible && cd ~/devops-labs/11-ansible
cp -r /path/to/the-devops-handbook/11-ansible/code/lab-02/. .

docker compose up -d
ansible-galaxy collection install community.docker
ansible all -m ping

# Lab 02 expects Vault-encrypted variables — create them first
mkdir -p inventory/group_vars/webservers
echo 'lab-vault-password' > .vault-pass && chmod 600 .vault-pass
# ...then follow Exercise 3 in the lab.

./test.sh
```

⚠️ `.vault-pass` and any decrypted `vault.yml` are **not** in this directory, and must never
be committed.

---

<div align="center">

[← Module 11 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
