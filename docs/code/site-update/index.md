# Site Update Recovery

When a site update (a `Pull` or `Migrate` deploy onto a new bench) fails, Press
tries to put the site back the way it was before the update. This page covers
that recovery flow — what runs automatically, the one-shot table restore Press
falls back to, and when it gives up and asks a human to step in.

The logic lives in the **Site Update** doctype
(`press/press/doctype/site_update/site_update.py`) and the **Site** doctype
(`press/press/doctype/site/site.py`).

## The happy path fails

An update runs as an `Update Site Pull` or `Update Site Migrate` agent job. When
that job fails (`handle_failure`):

1. The site is marked `Broken`.
2. If the update was run **with backups** (the normal case), a recovery job is
   triggered to move the site back to its source bench.
3. If the update was run **with backups skipped**, recovery is impossible —
   there is nothing to roll back to. The Site Update goes straight to `Fatal`
   and the user is notified to fix the site over SSH (see
   [Skipped backups](#skipped-backups)).

## Recovery

`trigger_recovery_job` moves the site back to its source bench
(`Recover Failed Site Pull` / `Recover Failed Site Migrate`) or, if the site
never left the source bench, just disables maintenance mode
(`Recover Failed Site Update`).

### Bumping `max_statement_time` before a migrate recovery

Recovering a `Migrate` runs heavy restore/migrate queries. On large sites these
can exceed the database server's `max_statement_time` and get killed mid-query,
turning a recoverable failure into a fatal one.

To avoid that, before triggering a recovery **migrate** job, Press proactively
increases `max_statement_time` on the database server by one hour
(`Site.increase_max_statement_time`). `max_statement_time` is a dynamic MariaDB
variable stored as a row in the Database Server's variables child table, so the
change applies without a restart. The bump is recorded as a comment on the Site
Update.

### When recovery fails

If the recovery job fails, the Site Update goes `Fatal`, the site is marked
`Broken`, and `Site.fatal_site_update` is set to the failed update.

When a **migrate** recovery (`Recover Failed Site Migrate`) is the one that
failed, Press makes one automatic attempt to bring the site back up before
leaving it for a human (`restore_tables_after_failed_recovery`):

- A failed migrate recovery has *already moved the site back* to the source
  bench; only its table restore is left undone. Re-running the whole recovery
  would fail at "Move Site" because the agent's `move_site` is not idempotent —
  the site directory is no longer on the destination bench.
- So instead of re-running the recovery, Press re-issues just a
  `Restore Site Tables` job (see below) and links it on the Site Update as a
  comment for traceability.

## Restoring tables after a fatal update

Restoring a site's tables from its backup (`Site.restore_tables`, a
`Restore Site Tables` agent job) is what brings a `Fatal` site back up — both
the automatic fallback above and a manual operator click go through the same
job, handled by `process_restore_tables_job_update`:

- **On success**, the site is reactivated. If it was stuck on a fatal update,
  that update **stays `Fatal`** but its cause of failure is marked resolved
  (`set_cause_of_failure_is_resolved`, which also clears the site's
  `fatal_site_update`). The site is usable again; the update itself still failed
  and is recorded as such.
- **On failure**, the site stays `Broken` and `fatal_site_update` remains set.
  Statement timeouts are avoided proactively by the one-hour `max_statement_time`
  bump done before the recovery migrate (see above), so there is no per-attempt
  retry loop here.

## Skipped backups

If a user runs an update with backups skipped and it fails, the database may be
left partially migrated with no backup to restore from. The site cannot be
recovered automatically.

In this case the failure notification (`agent_job_notifications.py`) is replaced
with an actionable message — *"Site update failed and cannot be recovered
automatically"* — telling the user to connect over SSH and fix the site
manually.

## Status lifecycle

```
Update fails
   │
   ├─ skipped backups ──────────────► Fatal  (SSH notification)
   │
   └─ with backups
        │
        ▼
     Recovering ──► (recover job)
        │
        ├─ recover success ─────────► Recovered
        │
        └─ recover failure ─────────► Fatal  (site Broken, fatal_site_update set)
                                          │
                       migrate recovery? one-shot restore_tables fallback
                                          │
                                   restore_tables
                                          │
                          ┌───────────────┴───────────────┐
                          │                               │
                      failure                         success
                          │                               │
                          ▼                               ▼
                       Broken                    Fatal, cause resolved
                  (fatal_site_update             (site Active again,
                       remains set)               fatal_site_update cleared)
```

## Key constants

| Constant | Value | Meaning |
|----------|-------|---------|
| `STATEMENT_TIME_INCREMENT` | 3600 | Seconds (one hour) `max_statement_time` is bumped by before a recovery migrate on large sites. |
| `LARGE_DATABASE_SIZE` | 2048 | DB size (MB) above which the `max_statement_time` bump is applied. |
| `DEFAULT_MAX_STATEMENT_TIME` | 3600 | Assumed `max_statement_time` when it isn't set on the database server. |
