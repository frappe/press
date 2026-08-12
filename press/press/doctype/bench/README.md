# Bench

A running `frappe-bench` installation on an App Server. A Bench is the convergence point of two chains:

- **What runs**: a specific `DeployCandidate` (and its Docker image via `DeployCandidateBuild`)
- **Where it runs**: a `Server` (App Server) + paired `DatabaseServer`

Multiple sites share a single bench. All sites on a bench run the same app versions.

## Status lifecycle

```
Pending → Installing → Active
                     → Broken
          Active     → Archived
```

## Created by

`Deploy.create_benches()` creates Bench records for each target server when a Deploy document is inserted. A bench is never created directly.

## Key relationships

- Belongs to one **ReleaseGroup** and one **DeployCandidate**
- Runs on one **Server**
- Has many **Sites**

## Lifecycle notes

- `EMPTY_BENCH_COURTESY_DAYS = 3`: empty benches (no active sites) are archived after 3 days.
- Worker counts (gunicorn, background) are scaled automatically based on server RAM and site load.
- Benches are immutable in terms of apps — to change app versions, a new DeployCandidate → new Bench is created, and sites are migrated over via `SiteUpdate`.
