---
title: Migrate to Frappe Cloud - Sites
---

# Migrate to Frappe Cloud

To migrate your existing sites to Frappe Cloud, you can use the terminal or the dashboard. We'll go over some ways to move your site from your current hosting provider.

## Dashboard

Migrating your site from the FC dashboard is pretty straighforward. You fill in the "New Site" form and upload the backups of your site via the browser.

<!-- TODO: Add information about the Migrate from URL option here after we roll that out, too. -->

## bench CLI

    bench --site {sitename} migrate-to frappe.cloud

If you're running on the latest Frappe release for v11, v12, v13-beta or develop, you should be able to use this command from the terminal. The most crucial part of this operation is having the latest migration script and if you see something like the following when you execute the command, you're in luck.

    Retreiving Site Migrator...
    Site Migrator stored at /var/folders/pc/3s9xq5sj42l7qg7q7kkd47ww0000gn/T/tmpfsn0xyba
    Setting Up requirements...

In case you're not, don't worry we got you covered. Checkout the following section [Migrate Script](#migrate-script) for more information.


## Migrate Script

if you're heading down this road, you've decided to roll up your sleaves and do it yourself...well sort of. This script should trigger the site migration to frappecloud.com for you.

Make sure you have `wget` installed and run the following lines from your bench directory:

    wget https://frappecloud.com/assets/press/migrate
    chmod +x migrate
    ./migrate

