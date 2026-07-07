# Best Practices

## Test Structure

Every test follows three steps:

1. **Arrange** — Create test records
2. **Act** — Run the code under test
3. **Assert** — Verify the results

## Creating Test Records

Press has many validations that make it tedious to create documents manually.
Instead, use utility factory functions (e.g. `create_test_bench` in
`test_bench.py`) that create valid documents with sensible defaults.

- Place factory functions in the corresponding doctype's test file.
- Add new parameters at the **end** of the argument list to avoid breaking
  existing tests.
- Import and reuse across test modules as needed.

For records shared across an entire `TestCase`, create them in `setUp`:

```python
def setUp(self):
    super().setUp()
    self.team = create_test_team()
```

## Naming Tests

Test method names should be **descriptive enough to explain the scenario
without reading the code**. Length does not matter — these methods are never
referenced elsewhere.

[Example](https://github.com/frappe/press/blob/2503e523284fb905eca60acf3271d3fb1dccbc3f/press/press/doctype/site/test_site.py#L215-L228)

A docstring on the method is also helpful — the test runner displays it when
the test fails.

## Rerunnability

Tests should leave the database in a clean state so they can be re-run without
a full reinstall. Use `tearDown` with a rollback:

```python
def tearDown(self):
    frappe.db.rollback()
```

This reverts any foreground database writes made during the test.

::: warning
If the code under test calls `frappe.db.commit`, mock it out — otherwise
records committed before the rollback will persist.
:::

```python
@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
class TestServer(FrappeTestCase):
    ...
```

## Background Jobs

Mocks and patches do not carry over to forked background job processes, and job
completion timing is unpredictable. The solution is to run the job in the
foreground during tests.

Use the `foreground_enqueue` utility:

[Import example](https://github.com/frappe/press/blob/23711e2799f2d24dfd7bbe2b6cd148f54f4b253b/press/press/doctype/database_server_mariadb_variable/test_database_server_mariadb_variable.py#L12)

[Usage example](https://github.com/frappe/press/blob/23711e2799f2d24dfd7bbe2b6cd148f54f4b253b/press/press/doctype/database_server_mariadb_variable/test_database_server_mariadb_variable.py#L104-L108)
