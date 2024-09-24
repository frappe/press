## Press SaaS API

These APIs has been introduced with the release of SaaS v2. It will provide a interface to communicate back to Frappe Cloud from deployed site.


### Authentication using secret token

In Site configuration, the authentication token will be provided - **fc_communication_secret**

For any kind of requests, from client-end, we need to set the credentials in header

```
X-Site: example.erpnext.com
X-Site-Token: 319f41d07d430ed77df3d41a82787f4edff1440f12e43784a7ce8b4e
```

> All the api functions are wrapped in frappe.whitelist(allow_guest=True) .
> However, due to the custom authentication wrapper, guest can't access the endpoints

### Authentication using access token

**Why ?**

Sometimes, we may need to pass the secret token to frontend for some specific tasks (example - in-desk checkout). In those case, instead of using our authentication secret token, we can generate a temporary access token from frappe cloud and use that for the session.

> Note: Generated access tokens are **valid for 15 minutes**.

#### Generate Access Token

**Request**

```bash
curl --location --request POST 'http://fc.local:8000/api/method/press.saas.api.auth.generate_access_token' \
--header 'x-site: oka-hdz-qpj.tanmoy.fc.frappe.dev' \
--header 'x-site-token: 004f85a3ae93927d2f0fcc668d11cb71'
```

**Response**

```json
{
    "message": "fbk23eva6k:3e2882eff23d4145ddfefaebf5ac6135"
}
```

After we generated our access token, set this specific header to any saas api requests to frappe cloud.
```
X-Site-Access-Token: fbk23eva6k:3e2882eff23d4145ddfefaebf5ac6135
```


### Usage Guide

- In `press.saas.api` `__init__` file, there is a decorator `@whitelist_saas_api` which can be used to convert the functions to api
- `@whitelist_saas_api` also set the site's team's user as current session user to make the session properly authenticated.
- `@whitelist_saas_api` also add couple of variable and functions to `frappe.local`.
  | Type | Name | Description |
  | ---- | ---- | ----------- |
  | Variable | frappe.local.site_name | Site name |
  | Variable | frappe.local.team_name | Current team name |
  | Function | frappe.local.get_site() -> Site | Fetch current site doctype record |
  | Function | frappe.local.get_team() -> Team | Fetch current team doctype record |
  | Variable (Additional) | frappe.session.user | Logged in user name, This will be also available as we have set `team.user` to logged in user |
- Sample Code
  ```python
  @whitelist_saas_api
  def hello():
      print(frappe.local.site_name)
      print(frappe.local.get_site())
      print(frappe.local.team_name)
      print(frappe.local.get_team())
      return f"👋 Hi! {frappe.local.site_name} is authenticated"
  ```
