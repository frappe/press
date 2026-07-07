# Testing

## Prerequisites

Ensure the pre-commit hook for styling tools is set up so CI won't fail on
formatting issues. See [setup instructions](https://github.com/frappe/press/issues/424#issuecomment-1193375098).

## Test Site Setup

Tests can leave behind fake records that pollute your local database. Use a
dedicated test site:

```sh
bench new-site --db-root-password admin --admin-password admin test_site
bench --site test_site install-app press
bench --site test_site add-to-hosts
bench --site test_site set-config allow_tests true
```

Start bench so background workers are available:

```sh
bench start
```

To reset all test data:

```sh
bench --site test_site reinstall --yes
```

## Running Tests

Run all tests (usually only needed in CI):

```sh
bench --site test_site run-tests --app press
```

Run a single module:

```sh
bench --site test_site run-tests --app press \
  --module press.press.doctype.some_doctype.test_some_doctype
```

Run a specific test:

```sh
bench --site test_site run-tests \
  --module press.press.doctype.some_doctype.test_some_doctype \
  --test test_very_specific_thing
```

### Editor Integration

- **Neovim**: [frappe_test.vim](https://github.com/ankush/frappe_test.vim/)
- **VS Code**: [frappe-test-runner](https://marketplace.visualstudio.com/items?itemName=AnkushMenat.frappe-test-runner)

::: tip
For Neovim quickfix support, you can use a
[custom errorformat](https://github.com/balamurali27/dotfiles/blob/85dc18a/.config/nvim/after/plugin/frappe.vim#LL10C1-L10C128)
with [makeprg hacks](https://github.com/balamurali27/dotfiles/blob/0bcd6270770d0b67b63fc0ea308e6834fefda5a6/.config/nvim/init.vim#L150C7-L163).
:::

## References

- [Frappe Testing Docs](https://frappeframework.com/docs/v14/user/en/testing)
- [unittest.mock — Python Docs](https://docs.python.org/3/library/unittest.mock.html)
