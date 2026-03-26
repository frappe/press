# Two-Factor Authentication (2FA)

The 2FA guard protects sensitive API endpoints by enforcing two-factor
authentication checks. It provides two decorators: `enabled` and `verify`.

Source:
[`press/guards/mfa.py`](https://github.com/frappe/press/blob/develop/press/guards/mfa.py)

## `mfa.enabled`

Checks whether two-factor authentication is enabled for the current user. If
the user is a Guest, the user identity is extracted from the request payload
using the provided key.

### Parameters

| Parameter     | Type   | Default  | Description                                                        |
|---------------|--------|----------|--------------------------------------------------------------------|
| `user_key`    | `str`  | `"user"` | Key to retrieve the user from the request form when session user is Guest. |
| `raise_error` | `bool` | `False`  | If `True`, raises `frappe.PermissionError` when 2FA is not enabled. |

### Behavior

1. Determines the current user (from session or request payload).
2. Checks the `User 2FA` doctype to see if 2FA is enabled for that user.
3. If enabled, the wrapped function executes normally.
4. If not enabled and `raise_error` is `True`, throws a `PermissionError`.
5. If not enabled and `raise_error` is `False`, returns `None`.

### Example

```python
from press.guards import mfa

@frappe.whitelist()
@mfa.enabled(raise_error=True)
def sensitive_action():
    # Only runs if the user has 2FA enabled
    pass
```

## `mfa.verify`

Verifies that the user has provided a valid TOTP code. If the user does not
have 2FA enabled, the function executes without verification. This allows
endpoints to be decorated with `mfa.verify` without breaking for users who
haven't set up 2FA.

### Parameters

| Parameter     | Type   | Default       | Description                                                        |
|---------------|--------|---------------|--------------------------------------------------------------------|
| `user_key`    | `str`  | `"user"`      | Key to retrieve the user from the request form when session user is Guest. |
| `code_key`    | `str`  | `"totp_code"` | Key to retrieve the TOTP code from the request payload.            |
| `raise_error` | `bool` | `False`       | If `True`, raises `frappe.PermissionError` when verification fails. |

### Behavior

1. Determines the current user and extracts the TOTP code from the request.
2. If the user does not have 2FA enabled, the function executes normally
   (bypass).
3. If 2FA is enabled and a valid TOTP code is provided, the function executes.
4. If verification fails and `raise_error` is `True`, throws a
   `PermissionError`.
5. If verification fails and `raise_error` is `False`, returns `None`.

### Example

```python
from press.guards import mfa

@frappe.whitelist(allow_guest=True)
@mfa.verify(user_key="email", raise_error=True)
def send_reset_password_email(email: str):
    """
    Sends reset password email to the user.
    If the user has 2FA enabled, a valid TOTP code must be
    provided in the request payload under the "totp_code" key.
    """
    frappe.utils.validate_email_address(email, throw=True)
    # ...
```

## Notes

- Both decorators read from `frappe.request.json` or `frappe.request.form` to
  extract user and code values.
- TOTP verification uses the `pyotp` library against the secret stored in the
  `User 2FA` doctype.
- These guards are designed to be stacked with other decorators like
  `@frappe.whitelist()` and `@rate_limit()`.
