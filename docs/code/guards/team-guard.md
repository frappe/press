# Team

The Team guard enforces team-level access control on document class methods. It
provides three decorators — `only_owner`, `only_admin`, and `only_member` —
each restricting method execution to users with the appropriate team
relationship.

Source:
[`press/guards/team_guard.py`](https://github.com/frappe/press/blob/develop/press/guards/team_guard.py)

> **Important:** All three decorators can **only** be used on class methods
> (i.e., methods where `self` is the first argument). They are not intended for
> standalone functions.

## Common Behavior

All team guard decorators share these behaviors:

- If `self.flags.ignore_permissions` is set, the check is bypassed.
- If the current user is a **System Manager**, the check is bypassed.
- The `team` parameter is a callable that extracts the team name from the
  document instance and bound arguments. It defaults to `document.team`.

## `team_guard.only_owner`

Restricts the method to the **team owner** only.

### Parameters

| Parameter | Type       | Default                         | Description                                     |
|-----------|------------|---------------------------------|-------------------------------------------------|
| `team`    | `Callable` | `lambda document, _: str(document.team)` | Extracts the team name from the document and arguments. |

### Example

```python
from press.guards import team_guard

class PressRole(Document):
    @dashboard_whitelist()
    @team_guard.only_owner()
    def delete(self, *_args, **_kwargs):
        return super().delete()
```

Only the team owner can delete a Press Role. All other users receive a
`PermissionError`.

## `team_guard.only_admin`

Restricts the method to **team admins** (including the team owner).

### Parameters

| Parameter | Type       | Default                         | Description                                     |
|-----------|------------|---------------------------------|-------------------------------------------------|
| `team`    | `Callable` | `lambda document, _: str(document.team)` | Extracts the team name from the document and arguments. |
| `skip`    | `Callable` | `lambda _, __: False`           | If returns `True`, bypasses the admin check.    |

### Example

```python
from press.guards import team_guard

class PressRole(Document):
    @team_guard.only_admin()
    def validate(self):
        self.validate_duplicate_title()

    @dashboard_whitelist()
    @team_guard.only_admin(skip=lambda _, args: args.get("skip_validations", False))
    def add_user(self, user, skip_validations=False):
        # ...
```

In the first example, only admins can validate (save) a Press Role. In the
second, the admin check can be conditionally skipped when `skip_validations` is
`True`.

## `team_guard.only_member`

Restricts the method to **team members** — any user listed in the team's member
list.

### Parameters

| Parameter       | Type            | Default                         | Description                                     |
|-----------------|-----------------|---------------------------------|-------------------------------------------------|
| `team`          | `Callable`      | `lambda document, _: str(document.team)` | Extracts the team name from the document and arguments. |
| `user`          | `Callable`      | `lambda _, __: str(frappe.session.user)` | Extracts the user to check membership for.      |
| `error_message` | `str` or `None` | `None`                          | Custom error message. Defaults to "Only team member can perform this action." |

### Example

```python
from press.guards import team_guard

class PressRole(Document):
    @dashboard_whitelist()
    @team_guard.only_admin(skip=lambda _, args: args.get("skip_validations", False))
    @team_guard.only_member(
        user=lambda _, args: str(args.get("user")),
        error_message=_("User is not a member of the team"),
    )
    def add_user(self, user, skip_validations=False):
        # ...
```

Here, `only_member` checks that the `user` argument is a member of the team
before allowing them to be added to the role. Note how `user` is extracted from
the method arguments rather than the session.

## Stacking

Team guards can be stacked with each other and with other decorators. When
stacked, they execute top-to-bottom:

```python
@dashboard_whitelist()
@team_guard.only_admin(skip=lambda _, args: args.get("skip_validations", False))
@team_guard.only_member(
    user=lambda _, args: str(args.get("user")),
    error_message=_("User is not a member of the team"),
)
def add_user(self, user, skip_validations=False):
    # ...
```

In this example:

1. `dashboard_whitelist` validates the request.
2. `only_admin` checks the caller is a team admin (skippable).
3. `only_member` verifies the target `user` is a team member.

## Notes

- Membership is checked against the `Team Member` child table.
- Admin status is determined by the `Team.is_admin_user()` method; ownership by
  `Team.is_team_owner()`.
- The `team` and `user` callables receive `(document, bound_arguments)` where
  `bound_arguments` is an `OrderedDict` of the method's resolved arguments.
