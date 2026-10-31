### New SaaS Flow (Product Trial)

It has 2 doctypes.

1. **Product Trial** - Hold the configuration for a specific product.
2. **Product Trial Request** - This holds the records of request for a specific product from a user.

#### How to know, which site is available for allocation to user ?

In **Site** doctype, there will be a field `standby_for_product`, this field should have the link to the product trial (e.g. erpnext, crm)
If `is_standby` field is checked, that site can be allocated to a user.

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


#### AI keys for trial sites (Grove)

- Grove is the AI gateway. **Grove Settings** (module SaaS) holds its URL, the control credential Press mints there with **Enroll** (a bootstrap secret the Grove operator hands over), and a **Trials** tab: the **Trial Team** (`Press Team`, the one Grove Team trial keys go under; Enroll registers it at Grove on the tier `Press Trial`, and so does a save that renames it; Grove's operator tunes that tier and fixes the team's cap window Total, so a key's cap is for its life), the **Trial Key Geography** the pool's keys are minted in, the **Trial Model Group** they are minted into (blank: that geography's default group; the set of models a trial may call), the **Trial Pool Size** (0 keeps the pool off: a trial site then gets no key), the **Trial Key Expiry** (Never, or 1, 7, 14 or 30 days after the key's first request, not after the mint, so a key waiting in the pool does not age) and the **Trial Key Cap**.
- Every five minutes `refill_trial_keys` mints what the pool is missing with Grove's `provision_key` (untitled, under the trial team, in the geography and group, at the cap and expiry) and holds each as a **Grove Trial Key** record: the key's name, the team it was minted under, geography, gateway URL and secret. When a Product Trial Request reaches **Site Created** it takes the oldest ready key (one per site, ever: `site` is unique, and a request reaching Site Created again keeps the key its site took), records the site and request on it, and writes `{gateway_url, api_key}` into the site config as **`ai_keys`**, the shape Central writes for its own trial servers, through the site's config agent job. The `Site Config Key` is internal, so the dashboard neither shows nor edits it. An empty pool gives no key and no error: the trial runs without AI. **Revoke Key** on a record retires a key by hand.
- Hourly, `revoke_archived` queues a revoke at Grove for the key of every Archived trial site, under the team the record says it was minted under. Grove refuses a revoke inside six hours of the mint; the record stays Revoking and the refill job tries again once it has sat an hour.
