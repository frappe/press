# Testing guidelines

Guidelines for running and writing tests in this project.

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

If the test site does not have all the doctypes, migrate it first. Use `--skip-failing` so that unrelated errors do not block the migration:

```bash
bench --site <site> migrate --skip-failing
```

Read [docs/code/testing](docs/code/testing/index.md) to learn how to write tests for this project. The [Frappe testing docs](https://docs.frappe.io/framework/user/en/testing) give the framework-level reference.

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
