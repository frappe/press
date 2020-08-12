---
title: Creating a new site - Sites
---

# Creating a new site

1. From the Sites tab on the dashboard, click on **New Site**.
1. Choose a unique hostname for your site. Subdomain could be 5 to 32 characters
   long and contain lowercase alphabets, numbers, and hyphens. Subdomain can not
   start or end with hyphens.
1. From the dropdown, select the major version for your site. We currently offer
   Version 12, Version 13 and Nightly (bleeding edge) versions.
1. Choose the apps to install on your site. The Frappe app will always be
   installed on your site by default. You can install more apps after your site
   is created.
1. To create a site from an existing backup tick the "Create Site from Backup"
   checkbox. Upload a GZipped database backup file, a TAR file containing public
   files, and a TAR file containing private files.

Alternatively, you can use the `bench --site {name} migrate-to frappecloud.com`
to migrate a new site or restore an existing one from your currently hosted service
providers or local development setups. See [Moving Frappe Sites](/docs/sites/migrate-to-frappecloud)

   See [Restore an existing Site](/docs/sites/restore-an-existing-site).
1. Choose an appropriate plan for your site. For more details visit our [pricing
   page](/pricing).
1. It will take a few seconds for site creation depending on the apps you have
   chosen and the size of your backup files.
1. Click on Visit Site at the top of the page to access your site.
1. After site creation you will see a message, you can proceed to
   complete the setup wizard by clicking on login. Please log in and complete
   the setup wizard on your site. Analytics will be collected only after the
   setup is complete.

> Note: All sites are only available on HTTPS.
