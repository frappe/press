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

See [guide-to-testing.md](guide-to-testing.md) for how to write tests for this project, and the [Frappe testing docs](https://docs.frappe.io/framework/user/en/testing) for framework-level testing reference.

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

## Finding docs.frappe.io/cloud URLs

Error messages and dialogs often link to Frappe Cloud docs. Don't guess slugs —
they 404 (the uninstall page is `how-to-uninstall-an-app-from-the-site`, not
`sites/uninstall-an-app`). Search the wiki API instead:

```bash
curl -s "https://docs.frappe.io/api/method/wiki.frappe_wiki.doctype.wiki_document.search.search?query=<TERM>&space=0uh9cfn2fk"
```

Returns `{message:{results:[{title, route, content, score}], total}}`. Take the
top result's `route` and prepend `https://docs.frappe.io/`. `space=0uh9cfn2fk`
scopes results to the **Cloud** space (all routes start with `cloud/`); omit
`space` to search all of docs.frappe.io (framework, etc.).
