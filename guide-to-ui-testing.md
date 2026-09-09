# Guide to UI Testing (Playwright)

The Playwright e2e tests live in `dashboard/tests-e2e/`. They use a real browser
and a local bench server. They mock all API responses, so they do not depend on
real data.

## One-time setup

### 1. Create a dedicated test user

Playwright needs a user that has a Team document. `Administrator` does not work.
The helper creates this user with `FREE_ACCOUNT` and `SKIP_ONBOARDING`. These
two flags stop the billing paywall and the onboarding wizard, which block the
tests.

```bash
bench --site <site-name> execute \
  press.press.doctype.team.test_team.create_test_press_admin_team \
  --kwargs '{"email": "playwright@example.com", "free_account": true, "skip_onboarding": true}'

bench --site <site-name> set-password "playwright@example.com" "playwright"
```

To do this manually, create a user and give the user the Press User role. Then
enable `FREE_ACCOUNT` and `SKIP_ONBOARDING` on the Team of that user.

### 2. Create `dashboard/tests-e2e/.env`

```
BASE_URL=http://<site-name>:8080
PRESS_ADMIN_USER_EMAIL=playwright@example.com
PRESS_ADMIN_USER_PASSWORD=playwright
```

Use the site name, for example `frappe_cloud_local`. Do not use `localhost`.
Use port `8080`, which is the port of the Vite dev server.

### 3. Start the bench and the dev server (two terminals)

```bash
# Terminal 1 — bench backend
cd /path/to/frappe-bench && bench start

# Terminal 2 — Vite dev server on port 8080
cd /path/to/frappe-bench/apps/press/dashboard && yarn dev
```

### 4. Install Playwright Chromium (once)

```bash
# Preferred: use system Chromium to avoid a 172 MB download
ln -sf /usr/bin/chromium-browser ~/.cache/ms-playwright/chromium-1181/chrome-linux/chrome
ln -sf $(which ffmpeg) ~/.cache/ms-playwright/ffmpeg-1011/ffmpeg-linux

# Or download Playwright's bundled browser (requires good internet)
cd dashboard && npx playwright install chromium
```

## Running tests

```bash
# From the dashboard/ directory:

# Headless
yarn test:e2e

# Headed — opens a real browser window
yarn test:e2e:headed

# Single file, headed
npx playwright test tests-e2e/tests/dashboard/site-update-banner.test.ts --headed

# Open the HTML report after a run
yarn test:e2e:report
```

The first run also executes `auth.setup.ts`. This file logs in one time and
saves the session to `tests-e2e/.auth/session.json`. The tests in the `chromium`
project use that session and run in parallel. The login does not occur again for
each test file.

To use the Chromium of the system instead of the bundled browser:

```bash
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium-browser yarn test:e2e:headed
```

## Test projects and file naming

The Playwright configuration defines three projects. The name of the file
selects the project:

| Pattern | Project | Purpose |
|---|---|---|
| `*.setup.ts` | `setup` | Runs first. Creates the session storage for the `chromium` project |
| `*.test.ts` | `chromium` | Dashboard UI tests. They depend on `setup` |
| `*.cron.spec.ts` | `cron` | Scheduled tests that the Frappe scheduler starts. They do not need `setup` |

Start the `cron` project with:

```bash
npm run test:e2e -- --project=cron
```

This keeps the scheduled smoke tests, such as the signup flow and the server
status checks, separate from the dashboard tests for developers.

## Writing tests

Tests live in `dashboard/tests-e2e/tests/dashboard/*.test.ts`. Import from the
coverage fixture:

```typescript
import { expect, test } from './coverage.fixture'
```

### Mocking API calls

Use **regex patterns**, not glob patterns. A glob pattern fails on a URL that
contains a port, for example `http://frappe_cloud_local:8080/...`. It gives no
error.

```typescript
// Mock press.api.client.get — dispatches on doctype from query string
await page.route(/\/api\/method\/press\.api\.client\.get\b/, async (route) => {
  const url = new URL(route.request().url())
  if (url.searchParams.get('doctype') === 'Site') {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: { name: 'my-site', status: 'Active', current_plan: null } }),
    })
  } else {
    await route.continue()  // pass through for Team, etc.
  }
})

// Mock press.api.client.get_list — dispatches on doctype from POST body
await page.route(/\/api\/method\/press\.api\.client\.get_list/, async (route) => {
  const doctype = route.request().postDataJSON()?.doctype

  if (doctype === 'Site Update') {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(siteUpdatesMock) })
  } else {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ message: [] }) })
  }
})
```

frappe-ui sends POST requests with `Content-Type: application/json`, so
`postDataJSON()` always works for the body. For `get`, the doctype is a **query
parameter** on a GET-style URL, not in the body.

### Response format

Put all mock responses in `{ message: ... }`. The `frappeRequest` function of
frappe-ui removes the `message` field before it gives the data to the resource
callbacks.

### Tips

- Use `await expect(locator).toBeVisible()`. Playwright retries until the timeout.
- To assert that an element is **absent**, first assert an element that is
  present. This shows that the page is fully loaded. Then assert the absence.
- Set `current_plan: null` in the site mock. This stops the upsell banner in
  tests that do not need it.
- Mock files (JSON fixtures) go in `dashboard/tests-e2e/mocks/<feature>/`.
- Playwright collects no coverage against the dev server, because the dev server
  has no production source maps. Coverage runs in CI, where the production build
  is present.
