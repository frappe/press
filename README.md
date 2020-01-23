## Press

Managed Frappe Hosting

### Usage

#### Install Frappe Agent

**Note:** Substitute `<server>`,`<password>` and `<workers>` with appropriate values
```
ansible-playbook ./apps/press/press/playbooks/server.yml -i <server>, -u root -vv -e "server=<server> workers=<workers> password=<password>"
```

e.g.
```
ansible-playbook ./apps/press/press/playbooks/server.yml -i n1.frappe.dev, -u root -vv -e "server=n1.frappe.dev workers=1 password=magical"
```

#### License

MIT

