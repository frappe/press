# Press App - Agent Notes

## Running Tests

Before running tests, always ask the user which site to use.

Use the following command format (note: `--site` goes before `run-tests`, not after):

```bash
bench --site <site> run-tests --app press --module press.press.doctype.site_update.test_site_update
```

To run a single test:

```bash
bench --site <site> run-tests --app press --module press.press.doctype.site_update.test_site_update --test test_specific_thing
```

If the test site is missing doctypes, migrate it first (use `--skip-failing` to avoid getting blocked by unrelated errors):

```bash
bench --site <site> migrate --skip-failing
```

See [docs/code/testing](docs/code/testing/index.md) for how to write tests for this project, and the [Frappe testing docs](https://docs.frappe.io/framework/user/en/testing) for framework-level testing reference.

## Running UI Tests (Playwright)

See [guide-to-ui-testing.md](guide-to-ui-testing.md) for setup and conventions.

Quick reference — run from `dashboard/`:

```bash
# Headed (opens browser)
yarn test:e2e:headed

# Single file
npx playwright test tests-e2e/tests/dashboard/site-update-banner.test.ts --headed
```

Requires a running bench (`bench start`) and `dashboard/tests-e2e/.env` with credentials.
