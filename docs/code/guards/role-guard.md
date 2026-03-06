# Role

The role guard implements role-based access control (RBAC) for the Press
dashboard. It restricts access to API routes, document actions, and specific
documents based on roles defined in the `Press Role` doctype.

Source:
[`press/guards/role_guard/`](https://github.com/frappe/press/blob/develop/press/guards/role_guard/__init__.py)

## Overview

The role guard enforces permissions at three levels:

| Decorator             | Protects                  | Scope                                      |
|-----------------------|---------------------------|-------------------------------------------|
| `role_guard.api`      | API endpoints             | Billing, Partner access                    |
| `role_guard.action`   | Document lifecycle methods | Site/Server/Bench creation, Webhook config |
| `role_guard.document` | Document access            | Sites, Servers, Release Groups, and more   |

## When is it Active

Role guard checks are **only enforced** when all of the following are true:

1. **Roles exist** for the current team (`roles_enabled()` returns `True`).
2. The user is **not** in relaxed mode without any assigned roles
   (`skip_roles()` returns `False`).
3. The user is **not** a System Manager.
4. The user is **not** the team owner or a team admin.

If any of these conditions are not met, the guard is bypassed and the function
executes normally.

### Relaxed Mode

When a team has `relaxed_permissions` enabled, users with **no roles assigned**
are allowed to bypass role checks. This is useful during gradual RBAC rollout
where not all users have been assigned roles yet.

## `role_guard.api`

Protects API endpoints by checking if the user has a specific scope-level
permission in their Press Role.

### Parameters

| Parameter | Type      | Description                          |
|-----------|-----------|--------------------------------------|
| `scope`   | `Literal` | One of `"billing"` or `"partner"`.   |

### Scope Mapping

| Scope       | Press Role Field  |
|-------------|-------------------|
| `"billing"` | `allow_billing`   |
| `"partner"` | `allow_partner`   |

### Example

```python
from press.guards import role_guard

@frappe.whitelist()
@role_guard.api("billing")
def get_invoice_usage(invoice):
    team = get_current_team()
    doc = frappe.get_doc("Invoice", {"name": invoice, "team": team})
    out = doc.as_dict()
    out.formatted = make_formatted_doc(doc)
    out.invoice_pdf = doc.invoice_pdf or (doc.currency == "USD" and doc.get_pdf())
    return out
```

Only users with the `allow_billing` permission in their Press Role can call
this API. Note: the guard does **not** apply team filters to queries — you must
do that yourself.

```python
@frappe.whitelist()
@role_guard.api("partner")
def get_partner_request_status(team):
    return frappe.db.get_value(
        "Partner Approval Request", {"requested_by": team}, "status"
    )
```

## `role_guard.action`

Protects document lifecycle methods (like `validate`) by checking action-level
permissions. This is a class method decorator.

### Action Mapping

The action key is determined by the document type and state:

| Document Type   | Condition   | Press Role Field              |
|-----------------|-------------|-------------------------------|
| `Site`          | `is_new()`  | `allow_site_creation`         |
| `Server`        | `is_new()`  | `allow_server_creation`       |
| `Release Group` | `is_new()`  | `allow_bench_creation`        |
| `Press Webhook` | —           | `allow_webhook_configuration` |

If the document type does not match any known action, the guard is bypassed.

### Example

```python
from press.guards import role_guard

class Server(Document):
    @role_guard.action()
    def validate(self):
        super().validate()
        self.validate_managed_database_service()
```

When creating a new Server, the guard checks that the user has
`allow_server_creation` in their Press Role. For existing servers, no action
key matches so the guard is bypassed.

## `role_guard.document`

Protects access to specific documents or document types. Can be used on both
class methods and standalone functions.

### Parameters

| Parameter       | Type       | Description                                                           |
|-----------------|------------|-----------------------------------------------------------------------|
| `document_type` | `Callable` | Extracts the document type from the function's bound arguments.       |
| `document_name` | `Callable` | Extracts the document name. Defaults to empty string (type-level check). |
| `default_value` | `Callable` | Optional. Returns a default value instead of throwing on permission failure. |

### Supported Document Types

| Document Type           | Check Logic                                                  |
|-------------------------|--------------------------------------------------------------|
| `Site`                  | Checks against `Press Role Resource` entries.                |
| `Server`               | Checks against `Press Role Resource` entries.                |
| `Release Group`        | Checks against `Press Role Resource` entries.                |
| `Marketplace App`      | Checks the `allow_apps` flag on the Press Role.              |
| `Press Webhook`        | Checks the `allow_webhook_configuration` flag.               |
| `Press Webhook Attempt`| Checks the `allow_webhook_configuration` flag.               |
| `Press Webhook Log`    | Checks the `allow_webhook_configuration` flag.               |
| `Site Backup`          | Resolved through the parent Site's resource permission.      |
| `Server Snapshot`      | Resolved through the parent Server's resource permission.    |

For Sites, Servers, and Release Groups, an `all_<doctype>s` flag (e.g.,
`all_sites`) on the Press Role grants access to all documents of that type.
Otherwise, individual documents must be listed in the `Press Role Resource`
child table.

### Example

```python
from press.guards import role_guard

@frappe.whitelist()
@role_guard.document(document_type=lambda _: "Site")
@role_guard.document(document_type=lambda _: "Release Group")
def get_notifications(
    filters=None,
    order_by="creation desc",
    limit_start=None,
    limit_page_length=None,
    sites=None,
    release_groups=None,
):
    # ...
```

Multiple `@role_guard.document` decorators can be stacked. Each one
independently checks permission for its document type.

```python
@role_guard.document(
    document_type=lambda args: "Site",
    document_name=lambda args: args.get("site_name"),
    default_value=lambda args: [],
)
def get_site_data(site_name):
    # Returns [] if the user doesn't have permission
    # instead of throwing an error
    pass
```

## Utility Functions

### `role_guard.is_restricted()`

Returns `True` if the current user is subject to role-based restrictions (i.e.,
roles are enabled, the user is not a System Manager, and not a team
owner/admin).

### `role_guard.permitted_documents(document_type)`

Returns a list of document names that the current user has access to for the
given document type. Useful for filtering query results.

### `role_guard.roles_enabled()`

Returns `True` if any `Press Role` exists for the current team. This is the
primary toggle — if no roles are defined, RBAC is inactive for that team.

### `role_guard.base_query()`

Returns a base `QueryBuilder` query filtered to the current team and user,
joining `Press Role` with `Press Role User`. Used internally by the check
functions.

## Architecture

The role guard module is split across several files:

| File                | Purpose                                          |
|---------------------|--------------------------------------------------|
| `__init__.py`       | Main decorators (`api`, `action`, `document`) and orchestration. |
| `action.py`         | Maps document types to action permission keys.   |
| `api.py`            | Maps API scopes to permission keys.              |
| `document.py`       | Document-level permission checks and resource queries. |
| `marketplace.py`    | Marketplace App permission check.                |
| `server_snapshot.py`| Server Snapshot permission check (via parent Server). |
| `site_backup.py`    | Site Backup permission check (via parent Site).  |
| `webhook.py`        | Webhook permission check.                        |

## Warnings

While the role guard restricts who can call an API or access a document, it **does
not** modify queries or filter data. A protected API can still leak data if the
developer does not apply appropriate team filters. Always apply necessary
filters to ensure users can only access data they are authorized to see.

```python
# ✅ Good: team filter applied
@role_guard.api("billing")
def get_invoice(invoice):
    team = get_current_team()
    return frappe.get_doc("Invoice", {"name": invoice, "team": team})

# ❌ Bad: no team filter, any billing user can access any invoice
@role_guard.api("billing")
def get_invoice(invoice):
    return frappe.get_doc("Invoice", invoice)
```
