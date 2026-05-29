# SiteUpdate

Moves a site from its current `Bench` to a newer one (within the same `ReleaseGroup`). This is how app version upgrades are delivered to sites — a new DeployCandidate is built, benches are created on target servers, then sites are moved over via SiteUpdate.

## Status lifecycle

```
Scheduled → Pending → Running → Success
                              → Failure → Recovering → Recovered
                                                      → Fatal
                              → Cancelled
```

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
