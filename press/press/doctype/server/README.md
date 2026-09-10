# Server, DatabaseServer, ProxyServer

A Frappe Cloud cluster has three server types, all extending `BaseServer` (defined in `server.py`):

```
Proxy Server (nginx + ProxySQL)
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

Runs nginx (HTTP routing) and ProxySQL (direct database access). Handles:
- TLS certificate provisioning
- Domain → upstream server mapping
- SSH proxy for user terminal access
- Direct MariaDB access via ProxySQL

## BaseServer

Shared base class. Handles:
- Ansible-based provisioning (`press/playbooks/`)
- Status lifecycle: `Pending → Active / Broken / Archived`
- Optional `VirtualMachine` linkage — servers can be provisioned automatically via cloud APIs or added manually by entering IP and credentials directly.

## Storage alert threshold

`storage_alert_threshold_percent` (default 90, valid 50-95) is the disk usage at
which the team is emailed about running out of space. The dashboard offers the
same range in steps of 5.

Prometheus, not Press, decides when the alert fires, so the alert rule has to be
written for it. Tick **Split By Server Storage Threshold** on the Prometheus
Alert Rule and use the two placeholders in its expression:

```
100 - (node_filesystem_avail_bytes{job="node", {{ instances }}}
  / node_filesystem_size_bytes{job="node", {{ instances }}} * 100) > {{ threshold }}
```

Press then emits one rule per threshold in use — the default one covering every
server that hasn't overridden it (`instance!~"..."`), and one for each group of
servers that has (`instance=~"..."`). All of them keep the alert's name, so the
reaction job is unchanged. Rules are pushed to the monitor server whenever a
server's threshold changes.
