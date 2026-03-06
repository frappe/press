# Settings

The Settings guard provides a decorator to conditionally execute functions
based on feature flags stored in **Press Settings**. It allows toggling
functionality on or off without code changes.

Source:
[`press/guards/settings.py`](https://github.com/frappe/press/blob/develop/press/guards/settings.py)

## `settings.enabled`

Checks whether a specific field in the `Press Settings` singleton doctype is
truthy. If the field value is falsy, the decorated function is skipped.

### Parameters

| Parameter       | Type   | Default | Description                                                          |
|-----------------|--------|---------|----------------------------------------------------------------------|
| `key`           | `str`  | —       | The field name in `Press Settings` to check.                         |
| `default_value` | `Any`  | `None`  | Value to return when the feature is disabled (and `raise_error` is `False`). |
| `raise_error`   | `bool` | `False` | If `True`, raises `frappe.ValidationError` when the feature is disabled. |

### Behavior

1. Reads the value of `key` from the `Press Settings` doctype (cached).
2. If the value is truthy, the decorated function executes normally.
3. If the value is falsy and `raise_error` is `True`, throws a
   `ValidationError` with the message "This feature is disabled".
4. If the value is falsy and `raise_error` is `False`, returns
   `default_value`.

### Example

```python
from press.guards import settings

@settings.enabled("disallow_disposable_emails")
def disallow_disposable_emails(self):
    """
    Disallow temporary email providers for account requests.
    Only runs if the "disallow_disposable_emails" field is
    enabled in Press Settings.
    """
    if disposable_emails.is_disposable(self.email):
        frappe.throw(
            "Temporary email providers are not allowed.",
            frappe.ValidationError,
        )
```

## Notes

- The settings value is read with `cache=True`, so repeated calls within the
  same request are efficient.
- This guard is useful for feature flags that need to be toggled at runtime via
  the Press Settings UI without deploying code changes.
- It can be used on both standalone functions and class methods.
