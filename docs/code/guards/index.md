# Guards

Guards are decorator-based access control primitives used across the Press
codebase. They wrap API endpoints and document methods with pre-execution
checks — verifying permissions, feature flags, plan entitlements, and
authentication requirements before the underlying function runs.

## Why Guards

Without guards, every endpoint would need inline permission checks, leading to
duplicated logic and easy-to-miss security gaps. Guards centralise these checks
into composable, declarative decorators that can be stacked on any function:

```python
@frappe.whitelist()
@role_guard.api("billing")
@mfa.verify(raise_error=True)
def sensitive_billing_action():
    ...
```

Each decorator in the stack runs top-to-bottom. If any guard fails, the
function never executes — either raising an error or returning a safe default.

## Available Guards

| Guard | Purpose |
|-------|---------|
| [**Role**](./role-guard.md) | Role-based access control (RBAC) for API endpoints, document actions, and individual documents via the `Press Role` doctype. |
| [**Team**](./team-guard.md) | Team-level access control — restricts document methods to team owners, admins, or members. |
| [**2FA**](./mfa.md) | Enforces two-factor authentication checks, verifying TOTP codes on sensitive endpoints. |
| [**Site**](./site.md) | Plan-based feature gating — ensures a site's plan includes access to a specific feature. |
| [**Settings**](./settings.md) | Feature flag checks against `Press Settings`, allowing functionality to be toggled at runtime without code changes. |

## Design Principles

- **Composable.** Guards are standard Python decorators and can be freely
  stacked with each other, `@frappe.whitelist()`, `@protected()`,
  `@rate_limit()`, and any other decorator.
- **Fail-safe.** When a check fails, the default behaviour is to block
  execution. Most guards accept a `raise_error` flag to control whether they
  raise an exception or silently return a default value.
- **Bypass-aware.** Guards respect escape hatches like `ignore_permissions`,
  System Manager sessions, and team ownership so that administrative workflows
  are not blocked.
- **Minimal overhead.** Permission data is read from cached doctypes, keeping
  the per-request cost low.

## Source

All guard modules live under
[`press/guards/`](https://github.com/frappe/press/tree/develop/press/guards).
