---
title: Backups - Sites
---

# Backups

Frappe Cloud takes automated backup of your sites every 6 hours.

## Downloading backups

On the site page, go to the **Backups** tab. Here you will see the list of
backups that were taken of your site. Every backup consists of a database
backup, public files backup and private files backup.

[![Offsite Backups](/assets/press/images/docs/backups.png)](/assets/press/images/docs/backups.png)

## Offsite Backups

1 out of every 4 automated backup is stored offsite, which means the files are
stored on a different server than the site. This ensures that you can access
your backups even in the unfortunate event of server downtime.

Offsite backups are marked as such in the Backups tab.

## Trigger on-demand backup

You can also trigger a manual backup operation for your site anytime from the
**Backups** tab by clicking on the **Schedule Backup with Files** button.

The job will be queued and it will take a few minutes to complete.

## Backup Rotation

### Offsite

The offsite backups on Frappe Cloud are rotated in a scheme known as
Grandfather-father-son. This is done to store backups efficiently.
With the current scheme, for every day we store:

- 7 daily backups
- 4 weekly backups
- 12 monthly backups
- 10 yearly backups

If the current day is Jan 13, then the backups available will be like so:

![Offsite Backups](/assets/press/images/docs/calendar.png)

(Monthly and yearly backups before December 2020 not shown in picture)  

- Weekly backups are taken every Sunday
- Monthly backups taken every 1st day of the month
- Yearly backups taken every 1st day of the year

