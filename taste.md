# Taste

Guidelines for writing good code in this project.

## General

- Choose clean code over clever code.
- Write object-oriented code. Behaviour belongs on the object it describes.
- Keep functions small — 10 lines is a good target. If a function needs a comment to explain what a block does, that block should be its own function.
- Keep comments short — one line is best, two lines at most. A comment that needs more is a sign the code should be clearer or the explanation belongs in a doc.
- Keep files between 100 and 300 lines. A file that keeps growing is a sign that it is doing too many things.
- Avoid abbreviations. Spell names out. Short names are fine only for loop variables or genuinely obvious abbreviations (`doc`, `e`).
- Reuse. Write as little code as possible. If you are about to write something that sounds general, check whether it already exists.
- Build the minimum that works, then iterate. Do not add structure for hypothetical future requirements.
- Fail loud at the boundary. If an external call fails, raise — don't swallow and fall back. The operator retries by clicking the button.

## Functions and methods

- A new utility that is specific to one doctype lives in that doctype's module.
- A utility reused across doctypes lives in a dedicated module and is imported explicitly — not through a God-module re-export.
- Module-level helper functions are preferable to static methods for logic that does not need `self`.
- If two methods always run back-to-back, they should probably be one method.

## Tests

- Always write tests. Make sure they pass before considering work done.
- Use `tearDown` with `frappe.db.rollback()` so tests are re-runnable without wiping the database.
- Mock only what you must. Prefer real objects and DB records over mocks.
- Test names should be long enough that a failing test tells you exactly what broke, without reading the body.
- When testing that something was blocked or rejected, assert the specific error message or the resulting state — not just that an exception was raised.

## Frappe-specific

- Use `frappe.db.set_value` for single-field updates on existing records; use `doc.save()` when multiple fields change together.
- Prefer the controller class directly — `Site("Site", name)` over `frappe.get_doc("Site", name)` — especially when that controller is defined in the same file. It's shorter, and it gives the type checker and the reader the concrete type.
- Use `frappe.get_cached_doc` for documents that are read frequently and not mutated.
- Prefer `frappe.db.exists` for existence checks over `frappe.get_value` with a null check.
- `ignore_permissions=True` is acceptable inside scheduled jobs and background hooks that run as Administrator, where the permission model does not apply.
