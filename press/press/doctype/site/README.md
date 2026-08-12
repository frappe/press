# Site

A Frappe site. The core product of Frappe Cloud — what customers create, pay for, and use. Lives on a `Bench` (and therefore on a `Server` + `DatabaseServer`). Belongs to a `Team`.

## Status lifecycle

```
Pending → Installing → Active
Active  → Updating
        → Recovering
        → Inactive    (manually deactivated)
        → Suspended   (unpaid / policy)
        → Archived    (deleted; data may be retained for a period)
Active  → Broken      (something went wrong)
```

## Key operations (all go through AgentJob)

| Operation | Trigger |
|-----------|---------|
| Create site | `Site.after_insert` |
| Install / uninstall app | `Site.install_app`, `Site.uninstall_app` |
| Update (move to new bench) | `SiteUpdate` |
| Backup | `SiteBackup` |
| Migrate to another server | `SiteMigration` |
| Restore from backup | Restore flow via `Remote File` |

## Key relationships

- Belongs to one **Bench** → one **Server** + **DatabaseServer**
- Belongs to one **Team**
- Belongs to one **ReleaseGroup** (denormalized from bench)
- Has one active **Subscription** (for billing)
- Can have many **SiteBackup**, **SiteDomain**, **SiteConfig** records

## Submodules

The `site/` folder contains several focused modules:
- `backups.py` — scheduled backup logic
- `site_usages.py` — CPU/disk usage tracking
- `sync.py` — setup wizard status sync
- `saas_pool.py` / `saas_site.py` — SaaS trial pool management
