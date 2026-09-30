# deployment

How Press itself runs in production, on the bench that hosts `frappe.cloud`.
This is not about the servers that Press creates for customers. Those come from
the Ansible playbooks in `press/playbooks/`.

Read [production.md](production.md) first. It gives the update procedure.

CAUTION: Do not run `bench update` on production. Pull each app manually.

The other files are copies of the production configuration, kept in git for
reference. Nothing applies them automatically.

| File | What it configures |
| --- | --- |
| `common_site_config.json` | Bench settings: worker counts, Redis ports, timeouts |
| `supervisor.conf` | The gunicorn, worker, and scheduler processes |
| `supervisord.conf` | The supervisor daemon |
| `nginx.conf` | The web server in front of the bench |
| `redis_cache.conf` | The Redis cache instance |
| `wait-for-redis.sh` | Waits until the cache and the queue reply to `PING` |
