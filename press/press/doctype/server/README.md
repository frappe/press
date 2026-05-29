# Server, DatabaseServer, ProxyServer

A Frappe Cloud cluster has three server types, all extending `BaseServer` (defined in `server.py`):

```
Proxy Server (nginx)
 ├── App Server / Server (Frappe: gunicorn + redis + workers)
 │    └── Database Server (MariaDB)
 ├── App Server
 │    └── Database Server
 └── ...
```

The Proxy Server routes inbound HTTPS traffic to the correct App Server based on the site's domain. Each App Server is paired with a DatabaseServer. All three types run the Agent, which Press communicates with via `AgentJob`.

## Server (App Server)

Runs bench processes: gunicorn workers, RQ background workers, redis, and scheduler. Holds `Bench` documents. Key responsibilities:
- Scaling workers based on site load
- Managing the bench queue (creating/archiving benches)
- Building Docker images (if `use_for_build` is set)

## DatabaseServer

Runs MariaDB. Each App Server is paired with one. Handles:
- MariaDB variable management
- Binlog management and replication
- Per-site database user management

## ProxyServer

Runs nginx. Routes traffic to App Servers. Handles:
- TLS certificate provisioning
- Domain → upstream server mapping
- SSH proxy for user terminal access

## BaseServer

Shared base class. Handles:
- Ansible-based provisioning (`press/playbooks/`)
- Status lifecycle: `Pending → Active / Broken / Archived`
- VirtualMachine linkage (the underlying cloud VM)
