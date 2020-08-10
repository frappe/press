---
title: Backups - Sites
---

# Backups

Frappe Cloud takes automated backup of your sites every 6 hours.

1 out of every 4 automated backup is stored offsite, which means the files are
stored on a different server than the site. This ensures that you can access
your backups even in the unfortunate event of server downtime.

## Downloading backups

On the site page, go to the **Backups** tab. Here you will see the list of
backups that were taken of your site. Every backup consists of a database
backup, public files backup and private files backup.

## Trigger on-demand backup

You can also trigger a manual backup operation for your site anytime from the
**Backups** tab by clicking on the **Schedule Backup with Files** button.

The job will be queued and it will take a few minutes to complete.
