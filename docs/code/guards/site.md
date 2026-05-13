# Site

The Site guard enforces plan-based feature gating for sites. It checks whether
a site's current plan includes access to a specific feature before allowing the
decorated function to execute.

Source:
[`press/guards/site.py`](https://github.com/frappe/press/blob/develop/press/guards/site.py)

## `site.feature`

Checks whether the site's plan supports a given feature. Sites on a free plan
bypass the check entirely.

### Parameters

| Parameter     | Type   | Default  | Description                                                  |
|---------------|--------|----------|--------------------------------------------------------------|
| `key`         | `str`  | —        | The field name on `Site Plan` to check for the feature.      |
| `site_key`    | `str`  | `"site"` | Key to extract the site name from the request payload.       |
| `raise_error` | `bool` | `True`   | If `True`, raises `frappe.PermissionError` when the feature is unavailable. |

### Behavior

1. Extracts the site name from `frappe.request.json` or `frappe.request.form`
   using `site_key`.
2. Fetches the site's `plan` and `free` status from the `Site` doctype.
3. If the site is on a free plan, the function executes (bypass).
4. If the corresponding field on the `Site Plan` is truthy, the function
   executes.
5. If the feature is not available and `raise_error` is `True`, throws a
   `PermissionError` with the message "Current plan does not support this
   feature."
6. If the feature is not available and `raise_error` is `False`, returns
   `None`.

### Example

```python
from press.guards import site

@frappe.whitelist()
@protected("Site")
@site.feature("monitor_access")
def request_logs(site, timezone, date, sort=None, start=0):
    """
    Fetch request logs for a site. Only available if the site's
    plan has "monitor_access" enabled.
    """
    # ...
```

```python
@frappe.whitelist()
@protected("Site")
@site.feature("monitor_access")
def mariadb_slow_queries(site, start_datetime, stop_datetime, ...):
    """
    Fetch slow query data. Gated behind the "monitor_access"
    plan feature.
    """
    # ...
```

## Notes

- The site name is read from the request payload, so this guard is intended for
  use on whitelisted API endpoints where the site name is passed as a
  parameter.
- Free sites (`free = 1`) always bypass the feature check.
- This guard is typically stacked with `@protected("Site")` to ensure the user
  has access to the site before checking plan features.
