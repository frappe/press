# Mocking

Press depends heavily on external services (Agent, remote APIs). Python's
`unittest.mock` library lets us isolate tests from these dependencies.

## Mocking Agent Job Creation

Decorate the test class with `patch.object` to replace
`AgentJob.enqueue_http_request` with a no-op:

```python
from unittest.mock import Mock, patch
from press.press.doctype.agent_job.agent_job import AgentJob

@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestSite(FrappeTestCase):
    ...
```

`Mock()` acts as a silent stand-in — the method does nothing when called.

::: warning
Class decorators are **not inherited**. Apply this to every test class that
needs Agent Job mocking.
:::

## Faking Agent Job Results

A dedicated decorator lets you simulate full Agent Job round-trips — request
and response. This is powered by the
[responses](https://github.com/getsentry/responses) library which intercepts
HTTP requests.

### Basic usage

Fake the result of a specific job type:

[Example](https://github.com/frappe/press/blob/983631ccb59f88e57fd60fdad1615e9abd87d99f/press/api/tests/test_site.py#L243-L247)

### Faking job output

Supply custom output to test callbacks that consume job results:

[Example](https://github.com/frappe/press/blob/983631ccb59f88e57fd60fdad1615e9abd87d99f/press/api/tests/test_site.py#L305-L323)

### Multiple jobs in one context

When a single request or job triggers multiple Agent Jobs:

[Example](https://github.com/frappe/press/blob/983631ccb59f88e57fd60fdad1615e9abd87d99f/press/press/doctype/site_migration/test_site_migration.py#L29-L77)

::: warning
You cannot fake two results for the **same** job type in a single context. Use
nested `with` statements as a workaround.
:::

::: danger
Do **not** mock `AgentJob.enqueue_http_request` when using the job-faking
decorator — it will interfere with the HTTP interception needed to simulate
results.
:::

## Mocking Internal Code

### `patch` as a decorator

Mock specific symbols within a module for an entire test class or method:

```python
from unittest.mock import MagicMock, patch

@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
class TestBench(FrappeTestCase):
    ...
```

When used on a method, the mocked object is passed as an extra argument:

[Example](https://github.com/frappe/press/blob/6dd6b2c8193b04f1aec1601d52ba09ce9dca8dfe/press/tests/test_cleanup.py#L280-L290)

### `patch` as a context manager

Scope the mock to a specific block within a test:

[Example](https://github.com/frappe/press/blob/6dd6b2c8193b04f1aec1601d52ba09ce9dca8dfe/press/tests/test_audit.py#L97-L102)

Use the `new` argument to fake the return value of functions that call remote
endpoints.

### Preserving behavior with `wraps`

If you need to keep the original function working but also assert on calls, use
`wraps` instead of `new`:

[Example](https://github.com/frappe/press/blob/23711e2799f2d24dfd7bbe2b6cd148f54f4b253b/press/press/doctype/database_server_mariadb_variable/test_database_server_mariadb_variable.py#L138-L155)

::: tip
Document comparisons on `Mock` objects work as expected during tests because
`__eq__` is overridden on the `Document` class (see `before_test.py`). Without
this, two `Document` instances would compare by `id()`, which always differs.
:::
