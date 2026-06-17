# Site Update Recovery

When a site update (a `Pull` or `Migrate` deploy onto a new bench) fails, Press
tries to put the site back the way it was before the update. This page covers
that recovery flow — what runs automatically, when it retries, and when it gives
up and asks a human to step in.

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

### Retrying on transient database errors

A recovery job can fail for reasons that have nothing to do with the site — for
example the database server briefly dropping the connection
(`MySQL server has gone away`, `Lost connection to MySQL server`). These are
detected from the recover job's output/traceback (and its step output) by
`failed_due_to_transient_db_error`.

When recovery fails with a transient error and fewer than
`MAX_RECOVERY_RETRIES` (3) recovery attempts have failed, Press schedules a
fresh recovery job instead of going fatal (`should_retry_recovery` →
`retry_recovery`). The Site Update stays in `Recovering` while it retries.

Once the retries are exhausted, the Site Update goes `Fatal`, the site is marked
`Broken`, and `Site.fatal_site_update` is set to the failed update.

## Restoring tables after a fatal update

A site stuck on a `Fatal` Site Update can be recovered by restoring its tables
from the backup (`Site.restore_tables`, an `Restore Site Tables` agent job),
handled by `process_restore_tables_job_update`:

- **On success**, the site is reactivated, `fatal_site_update` is cleared, and
  the Site Update is marked `Recovered`.
- **On failure because a query exceeded `max_statement_time`**
  (`restore_tables_failed_due_to_statement_timeout`), Press bumps
  `max_statement_time` by one hour and retries the restore, up to
  `MAX_STATEMENT_TIMEOUT_RETRIES` (3) times. Each retry is recorded as a comment
  on the fatal Site Update.

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
        │                │
        │   transient DB error, < 3 attempts
        │                │
        │◄───────────────┘ retry
        │
        ├─ recover success ─────────► Recovered
        │
        └─ retries exhausted ───────► Fatal  (site Broken, fatal_site_update set)
                                          │
                                          ▼
                                   restore_tables
                                          │
                          ┌───────────────┴───────────────┐
                          │                               │
                  statement timeout,                  success
                  < 3 attempts                            │
                          │                               ▼
                          └─ bump max_statement_time   Recovered
                             and retry
```

## Key constants

| Constant | Value | Meaning |
|----------|-------|---------|
| `MAX_RECOVERY_RETRIES` | 3 | Recovery retries allowed on transient DB errors. |
| `MAX_STATEMENT_TIMEOUT_RETRIES` | 3 | Restore-tables retries allowed on `max_statement_time` timeouts. |
| `STATEMENT_TIME_INCREMENT` | 3600 | Seconds (one hour) `max_statement_time` is bumped by each time. |
| `DEFAULT_MAX_STATEMENT_TIME` | 3600 | Assumed `max_statement_time` when it isn't set on the database server. |
