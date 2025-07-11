# HTTP Load Test

This document explains how the `http_load_test.py` script works and lists the options available when calling the related APIs.

The script helps automate load testing of a Press instance by repeatedly creating new sites through HTTP calls. You can optionally archive the sites after creation.

## What the Script Does

1. **Creates Sites** – Calls either `/api/method/press.api.site.new` or `/api/method/press.api.saas.new_saas_site` depending on the `--saas` flag.
2. **Concurrent Requests** – Uses a thread pool to fire multiple requests at once. The level of concurrency is controlled by `--concurrency`.
3. **Archiving** – If `--cleanup` is supplied, each site is archived using `/api/method/press.api.site.archive` after creation.

The script accepts a template JSON payload that is merged with unique site names so you can customise parameters like installed apps or plan.

## API Endpoints

### `press.api.site.new`
Creates a regular site. The payload should be passed as `{"site": { ... }}`. Common fields include:

- `name` – subdomain for the site (auto-generated when omitted)
- `domain` – root domain to use
- `apps` – list of app names to install
- `plan` – site plan ("Free", "Standard", etc.)
- `cluster` – optional cluster name

### `press.api.saas.new_saas_site`
Creates a SaaS trial site. Expected parameters:

- `subdomain` – unique name for the trial site
- `app` – SaaS app to install

### `press.api.site.archive`
Archives an existing site so it no longer consumes resources. Parameters:

- `name` – site name to archive
- `force` – set to `true` to immediately archive without confirmation

## Script Options

Run `python http_load_test.py --help` for the latest details. Key options are:

- `--base-url` (**required**): Base URL of the Press instance.
- `--token` (**required**): API token for authentication.
- `--count` (default `10`): Number of sites to create during the test.
- `--concurrency` (default `5`): Number of concurrent HTTP requests.
- `--saas`: Use the SaaS creation API instead of the standard site API.
- `--cleanup`: Archive each site after it has been created.
- `--site-template`: JSON string providing additional fields for the create-site payload.

Example command:

```bash
python http_load_test.py \
    --base-url https://press.example.com \
    --token YOUR_API_TOKEN \
    --count 50 \
    --concurrency 10 \
    --site-template '{"apps": ["erpnext"], "plan": "Free"}' \
    --cleanup
```

