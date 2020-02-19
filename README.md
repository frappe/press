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

Frappe Server will also require `mariadb_root_password` variable to be set

e.g.
```
ansible-playbook ./apps/press/press/playbooks/server.yml -i f1.frappe.dev, -u root -vv -e "server=f1.frappe.dev workers=1 password=magical mariadb_root_password=tada"
```

#### License

MIT

