# Module 11: Ansible — Resources

---

## 📖 Essential Reading

| Resource | Type | Difficulty | Notes |
|----------|------|------------|-------|
| [Ansible Documentation](https://docs.ansible.com/ansible/latest/) | Documentation | Beginner | Official docs — start with "Getting Started" |
| [Ansible Module Index](https://docs.ansible.com/ansible/latest/collections/index.html) | Reference | All | **Bookmark this** — every module and its parameters |
| [Ansible for DevOps (Jeff Geerling)](https://www.ansiblefordevops.com/) | Book | Intermediate | Best Ansible book — practical and hands-on |
| [Ansible Best Practices](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html) | Guide | Intermediate | Official tips and best practices |
| [Ansible Vault Documentation](https://docs.ansible.com/ansible/latest/vault_guide/index.html) | Documentation | Intermediate | Secrets management with Ansible |

---

## 🎥 Videos & Courses

| Resource | Type | Duration | Notes |
|----------|------|----------|-------|
| [Ansible Full Course (TechWorld with Nana)](https://www.youtube.com/watch?v=1id6ERvfozo) | Video | 2 hours | Best beginner Ansible walkthrough |
| [Ansible in 100 Seconds (Fireship)](https://www.youtube.com/watch?v=xRMPKQkvhKw) | Video | 2 min | Quick overview of what Ansible does |
| [Ansible Roles Explained (Jeff Geerling)](https://www.youtube.com/watch?v=ticOGAQy3HI) | Video | 30 min | Roles deep dive from the Ansible book author |
| [Ansible vs Terraform (IBM Technology)](https://www.youtube.com/watch?v=rx4Uh3jv1cA) | Video | 10 min | When to use each tool |
| [Ansible Galaxy Guide](https://www.youtube.com/watch?v=goclfp6a2IQ) | Video | 20 min | Using community roles |

---

## 🧰 Tools & References

| Resource | Type | Notes |
|----------|------|-------|
| [Ansible Galaxy](https://galaxy.ansible.com/) | Registry | Community roles and collections — don't reinvent the wheel |
| [ansible-lint](https://github.com/ansible/ansible-lint) | Linter | Check playbooks for best practices and common mistakes |
| [Molecule](https://github.com/ansible/molecule) | Testing | Test Ansible roles with Docker containers |
| [Ansible Vault](https://docs.ansible.com/ansible/latest/cli/ansible-vault.html) | Tool | Encrypt sensitive variables and files |
| [AWX / Ansible Tower](https://github.com/ansible/awx) | Platform | Web UI for Ansible — scheduling, RBAC, logging |
| [Jinja2 Template Designer](https://jinja.palletsprojects.com/en/3.1.x/templates/) | Reference | Template syntax for Ansible templates |

---

## 🎯 Recommended Practice Path

1. **Week 1**: Install Ansible. Set up a test environment with Vagrant or Docker containers. Write ad-hoc commands, then a playbook to install and configure Nginx. Practice inventory management.
2. **Week 2**: Build a role (nginx role with templates and handlers). Use Ansible Vault for secrets. Create a multi-host playbook that configures web servers and databases with different roles.
