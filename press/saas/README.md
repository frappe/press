### New SaaS Flow (Product Trial)

It has 2 doctypes.

1. **Product Trial** - Hold the configuration for a specific product.
2. **Product Trial Request** - This holds the records of request for a specific product from a user.

#### How to know, which site is available for allocation to user ?

In **Site** doctype, there will be a field `standby_for_product`, this field should have the link to the product trial (e.g. erpnext, crm)
If `is_standby` field is checked, that site can be allocated to a user.

#### Signup Domains (apex vs. cluster subdomains)

A Product Trial's **Domain** is the *apex* (e.g. `frappe.cloud`). Signups must **never**
land on the apex — AWS Route 53 hosted-zone limits mean we spread sites across per-cluster
subdomains (`m.frappe.cloud` = Mumbai, `v.frappe.cloud` = Virginia, …), each a `Root
Domain` whose `default_cluster` names the cluster it serves. The subdomain a signup gets
is the **signup domain**.

Resolution (both on `ProductTrial`):
1. `get_cluster_for_request(account_request)` → target cluster (hybrid-pool rules, else
   `get_nearest_cluster(country)`, falling back to IP geolocation).
2. `get_signup_domain(cluster)` → the cluster's enabled `*.{apex}` subdomain, falling back
   to the **nearest** enabled subdomain (`get_nearest_cluster_among`, by cluster
   coordinates — e.g. UAE → Bahrain), then the apex's `default_cluster` subdomain. Returns
   the apex *only* when no subdomains exist.

`create_site` re-resolves server-side, so an apex posted by a stale frontend (or a failed
geo lookup) can't slip through; `create_standby_site` uses the same resolver for pooled
sites.

> [!CAUTION]
> Old bug: when the cluster resolved to `None` (geo lookup down, no country on the Account
> Request) or to a cluster with no `*.frappe.cloud` subdomain, it silently fell back to the
> apex. Keep `get_signup_domain`'s "never apex" invariant intact.

#### Configure a new Product Trial
- Create a new record in `Product Trial` doctype
- **Details Tab**
  - **Name** - should be a unique one and will be used as a id in signup/login flows. e.g. For `Frappe CRM` it could be `crm`
  - **Published**, **Title**, **Logo**,  **Domain**, **Release Group**, **Trial Duration (days)**, **Trial Plan** - as the name implies, all fields are mandatory.
  - **Apps** - List of apps those will be installed on the site. First app should be `Frappe` in the list.
- **Pooling Tab**
  - **Enable Pooling** - Checkbox to enable/disable pooling. If you enable pooling, you will have standby sites and will be quick to provision sites.
  - **Standby Pool Size** - The total number of sites that will be maintained in the pool.
  - **Standby Queue Size** - Number of standby sites that will be queued at a time.
- **Sign-up Details Tab**
  - **Sign-up Fields** - If you need some information from user at the time of sign-up, you can configure this. Check the field description of this field in doctype.
  - **E-mail Account** - If you want to use some specific e-mail account for the saas sign-up, you can configure it here
  - **E-mail Full Logo** - This logo will be sent in verification e-mails.
  - **E-mail Subject** - Subject of verification e-mail. You can put `{otp}` to insert the value in subject. Example - `{otp} - OTP for CRM Registration`
  - **E-mail Header Content** - Header part of e-mail.
    ```html
    <p><strong>You're almost done!</strong></p>
    <p>Just one quick step left to get you started with Frappe CRM!</p>
    ``` 
- **Setup Wizard Tab**-
  - **Setup Wizard Completion Mode** - 
    - **auto** - setup wizard of site will be completed in background and after signup + setup, user will get direct access to desk or portal of app
    - **manual** - after signup, user will be logged in to the site and user need to complete the setup wizard of framework
  - **Setup Wizard Payload Generator Script** [only for **auto** mode] - Check the field description in doctype.

    Sample Payload Script - 
    ```python
    payload = {
        "language":"English",
        "country": team.country,
        "timezone":"Asia/Kolkata",
        "currency": team.currency,
        "full_name": team.user.full_name,
        "email": team.user.email,
        "password": decrypt_password(signup_details.login_password)
    }
    ``` 
  - **Create Additional System User** [only for **manual** mode] - If this is checked, we will add an additional system user with the team's information after creating a new site. 
  - **Redirect To After Login** - After SaaS signup/login, user is directly logged-in to his site. By default, we redirect the user to desk of site. With this option, we can configure the redirect path. For example, for gameplan the path would be `/g`

#### FC Dashboard
- UI/UX - The pages are available in https://github.com/frappe/press/tree/master/dashboard/src2/pages/saas
- The required apis for these pages are available in https://github.com/frappe/press/blob/master/press/api/product_trial.py

#### Billing APIs for Integration in Framework

> [!CAUTION]
> Changes in any of these APIs can cause disruption in on-site billing system.

- All the required APIs for billing in site is available in https://github.com/frappe/press/tree/master/press/saas/api
- These APIs use a different type of authentication mechanism. Check this readme for more info https://github.com/frappe/press/blob/master/press/saas/api/readme.md
- Reference of integration in framework
  - https://github.com/frappe/frappe/tree/develop/billing
  - https://github.com/frappe/frappe/blob/develop/frappe/integrations/frappe_providers/frappecloud_billing.py

