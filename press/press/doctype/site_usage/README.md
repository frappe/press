# Site Usage

A point-in-time snapshot of a site's resource consumption. One record is
inserted per site each time usage is fetched from the server (see
`Site._insert_site_usage`), so the latest record for a site is its current
usage. Duplicate consecutive snapshots are skipped.

## Units — sizes are in MB, not bytes

`database`, `public`, `private`, `backups`, and `database_free` are stored in
**megabytes**, despite being plain `Int` fields with no unit in the label.

This is easy to get wrong. The dashboard confirms it: `SiteOverview.vue`
renders these with `$format.bytes(value, 2, 2)`, where the third argument
(`current = 2`) shifts the unit scale to start at MB instead of bytes. So a
stored value of `1024` displays as "1 GB".

When comparing against a threshold in bytes, convert — e.g. 1 GB is `1024`
here, not `1024**3`. See `LARGE_DATABASE_SIZE` in `site_update.py` and
`Site.database_size`.
