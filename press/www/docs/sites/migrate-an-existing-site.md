---
title: Restore an existing site - Sites
---

# Migrate an existing site

Restore an existing site by uploading backup files or by using bench from your
local setup or from your cloud provider.

## Restore from Backup Files

The easiest way to migrate an existing site on Frappe Cloud is to restore it
from backup files.

1. [Download backup](https://docs.erpnext.com/docs/user/manual/en/setting-up/data/download-backup) files of your site.
1. You must have 3 files that should be named like the following:
   - 20200817\_125915-sitename-database.sql.gz (Database)
   - 20200817\_125915-sitename-files.tar (Public Files)
   - 20200817\_125915-sitename-private-files.tar (Private Files)
1. Click on **New Site** from the Sites tab in the Frappe Cloud Dashboard.
1. Fill out the subdomain and select the version.
1. Click on **Create Site from Backup**.
1. Now, upload each file you got in Step 2 in their corresponding upload boxes.
2. Select a Plan.
3. Click on **Create Site**.

> Note: This method is ideal if your backup files size is less 200MB. If you
> have larger backup files, you should use the `bench` command to migrate your site.

## Migrate using Bench

If you are running Frappe sites, most likely you have `bench` installed. You can
run the following command to restore a site from your bench to Frappe Cloud.

```sh
bench --site {name} migrate-to frappecloud.com
```

You can run this command even from your local setup. If your site is hosted on a
cloud provider like Digital Ocean or Amazon AWS, you must ssh into your server,
and run this command.

> **Note**: This method will work only if your sites are on Version 11 or greater.
> If you are on an older version or this command didn't work for you, you can
> try the Python Script method explained later.

> **Note**: This method works for backup files sizes of less than or equal to 500MB.
> If you have larger backup files, you can send us request to migrate your site.

## Migrate using Python Script

If you are on an older version of Frappe (older than version 11) or the Bench
command didn't work for you, you can try this method.

Make sure you have `wget` installed. Run the following commands from your bench
directory:

```sh
wget https://frappecloud.com/assets/press/migrate
chmod +x migrate
./migrate
```
