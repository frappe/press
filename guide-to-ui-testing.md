# Guide to UI Testing (Playwright)

Playwright e2e tests live in `dashboard/tests-e2e/`. They run against a real browser and a running bench server, but mock all API responses so they do not depend on real data.

## One-time setup

### 1. Create a dedicated test user

Playwright needs a user with a team doc — not `Administrator`. The helper creates one with `FREE_ACCOUNT` and `SKIP_ONBOARDING` enabled, which prevents billing paywalls and the onboarding wizard from blocking tests.

```bash
bench --site <site-name> execute \
  press.press.doctype.team.test_team.create_test_press_admin_team \
  --kwargs '{"email": "playwright@example.com", "free_account": true, "skip_onboarding": true}'

bench --site <site-name> set-password "playwright@example.com" "playwright"
```

If you prefer to do it manually: create a user, assign the Press User role, and enable `FREE_ACCOUNT` and `SKIP_ONBOARDING` on their Team.

### 2. Create `dashboard/tests-e2e/.env`

```
BASE_URL=http://<site-name>:8080
PRESS_ADMIN_USER_EMAIL=playwright@example.com
PRESS_ADMIN_USER_PASSWORD=playwright
```

Use the site name (e.g. `frappe_cloud_local`) not `localhost`, and port `8080` for the Vite dev server.

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

The first run also executes `auth.setup.ts`, which logs in once and saves the session to `tests-e2e/.auth/session.json`. All subsequent tests in the `chromium` project reuse that session and run in parallel — login does not repeat for each test file.

To use a system Chromium instead of Playwright's bundled one:

```bash
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium-browser yarn test:e2e:headed
```

## Test projects and file naming

The Playwright config defines three projects, each matched by filename convention:

| Pattern | Project | Purpose |
|---|---|---|
| `*.setup.ts` | `setup` | Runs first; creates session storage for the `chromium` project |
| `*.test.ts` | `chromium` | Standard dashboard UI tests; depend on `setup` |
| `*.cron.spec.ts` | `cron` | Scheduled tests triggered by Frappe's scheduler; run independently of setup |

The `cron` project is invoked with:

```bash
npm run test:e2e -- --project=cron
```

This keeps scheduled smoke tests (e.g. signup flows, server status checks) separate from developer-facing dashboard tests.

## Writing tests

Tests live in `dashboard/tests-e2e/tests/dashboard/*.test.ts`. Import from the coverage fixture:

```typescript
import { expect, test } from './coverage.fixture'
```

### Mocking API calls

Use **regex patterns**, not glob patterns. Glob patterns silently fail on URLs that contain a port (e.g. `http://frappe_cloud_local:8080/...`).

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

frappe-ui sends POST requests with `Content-Type: application/json`, so `postDataJSON()` always works for the body. For `get`, the doctype is a **query parameter** on a GET-style URL, not in the body.

### Response format

Wrap all mock responses in `{ message: ... }` — frappe-ui's `frappeRequest` unwraps the `message` field before passing data to resource callbacks.

### Tips

- Use `await expect(locator).toBeVisible()` — Playwright retries automatically until timeout.
- To assert something is **absent**, first assert something that IS present (confirms the page finished loading), then assert the absence.
- Set `current_plan: null` in the site mock to prevent the upsell banner from appearing unexpectedly in tests that don't need it.
- Mock files (JSON fixtures) go in `dashboard/tests-e2e/mocks/<feature>/`.
- Coverage collection is skipped automatically when running against the dev server (no production source maps). It runs in CI where the production build is present.
