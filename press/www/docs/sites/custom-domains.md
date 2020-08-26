---
title: Custom Domains - Sites
---

# Custom Domains

Frappe Cloud allows you to map custom domains that you own in a few simple steps.

1. From your site page, go to **Domains** tab.
2. Click on Add Domain.
3. Enter the custom domain.
4. Add a CNAME record to your domain pointing to your site from the dashboard of
   your domain provider.

   For example, if you want to use example.frappe.dev for your site
   example.frappe.cloud then add CNAME record for example.frappe.dev pointing to
   example.frappe.cloud.

   For the instructions to add such a record please contact your domain provider.

   [![Custom Domains](/assets/press/images/docs/custom-domains.png)](/assets/press/images/docs/custom-domains.png)
5. Click on Verify DNS.
6. If we can verify that you have correctly added the CNAME record, then you
   will see Add Domain button. Click on Add Domain.

> Note: We obtain an SSL certificate for the custom domain. So you will be able
> to use HTTPS with your domain.
