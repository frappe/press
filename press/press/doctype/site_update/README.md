# SiteUpdate

Moves a site from its current `Bench` to a newer one (within the same `ReleaseGroup`). This is how app version upgrades are delivered to sites — a new DeployCandidate is built, benches are created on target servers, then sites are moved over via SiteUpdate.

## Status lifecycle

```
Scheduled → Pending → Running → Success
                              → Failure → Recovering → Recovered
                                                      → Fatal
                              → Cancelled
```

| Status | Terminal | Meaning |
|--------|----------|---------|
| `Scheduled` | No | Waiting for the scheduled window |
| `Pending` | No | Queued, AgentJob not yet started |
| `Running` | No | AgentJob in progress on the server |
| `Success` | Yes | Update completed successfully |
| `Failure` | **No** | AgentJob failed; a recovery job is being created automatically. This is a transient state — the record will move to `Recovering` shortly |
| `Recovering` | No | Recovery (rollback) job is running |
| `Recovered` | Yes | Update failed but the site was rolled back to its previous bench successfully |
| `Fatal` | Yes | Update failed and recovery also failed; site needs manual intervention |
| `Cancelled` | Yes | Update was cancelled before or during execution |

`Failure` is **not** a terminal state. Do not treat it as a final outcome when reading a site update record — wait for the transition to `Recovered` or `Fatal`.

## Deploy types

| Type | Description |
|------|-------------|
| `Pull` | Pull new Docker image on the bench, restart workers |
| `Migrate` | Pull + run `bench migrate` (schema changes) |

The deploy type is determined by whether the update includes database schema changes (`touched_tables`).

## Scheduling

`schedule_updates` (runs every 15 min) looks for sites eligible for update and creates `SiteUpdate` records. `run_scheduled_updates` (runs every 5 min) picks up `Scheduled` records and moves them to `Pending`, triggering the AgentJob.

Sites can have a preferred update window (`update_trigger_time`, `update_trigger_frequency`).

## Key relationships

- Belongs to one **Site**
- References source and destination **Bench**
- References destination **ReleaseGroup** (for cross-group version upgrades, see `VersionUpgrade`)
- Creates an **AgentJob** (`update_job`) to perform the actual work
