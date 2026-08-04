# Module 11: Ansible — Lab Code

A working inventory, playbooks, and a reusable role.

These are the real, runnable files from this module's labs. They are validated in CI, so
they stay correct as tool versions move on.

The labs still show every file inline — **type them out the first time**, that's where the
learning happens. Use these when you want to skip the transcription, when you're comparing
your version against a reference, or when something isn't working and you need a known-good
starting point.

---

## Contents

### `lab-01/`

Docker-based managed nodes, an inventory, a webserver playbook, and a full role with tasks, handlers, templates and defaults.

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

---

## Using these files

```bash
# From the repo root — copy a lab's files into your working directory
mkdir -p ~/devops-labs/11-ansible && cd ~/devops-labs/11-ansible
cp -r /path/to/the-devops-handbook/11-ansible/code/lab-01/. .
```

Then follow the lab. Every command in the lab assumes these filenames and this layout.

---

<div align="center">

[← Module 11 README](../README.md) · [Labs](../labs/) · [Cheat Sheet](../cheatsheet.md) · [Handbook Quick Reference](../../QUICK-REFERENCE.md)

</div>
