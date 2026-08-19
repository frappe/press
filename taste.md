# Taste

Guidelines for writing good code in this project.

## General

- Choose clean code over clever code.
- Write object-oriented code. Behaviour belongs on the object it describes.
<<<<<<< HEAD
- Keep functions small — 10 lines is a good target. If a function needs a comment to explain what a block does, that block should be its own function.
- Keep files between 100 and 300 lines. A file that keeps growing is a sign that it is doing too many things.
- Avoid abbreviations. Spell names out. Short names are fine only for loop variables or genuinely obvious abbreviations (`doc`, `e`).
- Reuse. Write as little code as possible. If you are about to write something that sounds general, check whether it already exists.
- Build the minimum that works, then iterate. Do not add structure for hypothetical future requirements.
- Fail loud at the boundary. If an external call fails, raise — don't swallow and fall back. The operator retries by clicking the button.
=======
- Keep functions small. 10 lines is a good target. If a function needs a comment
  to explain a block, make that block its own function.
- Keep comments short. One line is best, two lines at most. If a comment needs
  more than two lines, make the code clearer, or move the explanation to a doc.
- Keep files between 100 and 300 lines. A file that continues to grow does too
  many things.
- Avoid abbreviations. Spell names out. Short names are correct only for loop
  variables and for obvious abbreviations (`doc`, `e`).
- Reuse. Write as little code as possible. If you are about to write something
  that sounds general, search for it first. It can exist already.
- Build the minimum that works, then iterate. Do not add structure for future
  requirements that no one asked for.
- Fail loud at the boundary. If an external call fails, raise the error. Do not
  catch it and fall back. The operator retries with the button.
>>>>>>> cabdcfe64 (docs(agents): Rewrite the agent instruction files in simple english)

## Functions and methods

- A new utility that is specific to one doctype lives in that doctype's module.
- A utility that more than one doctype uses lives in its own module. Import it
  directly, not through a God-module that re-exports it.
- Module-level helper functions are better than static methods for logic that
  does not need `self`.
- If two methods always run back-to-back, make them one method.

## Tests

- Always write tests. Make sure that they pass before you call the work done.
- Use `tearDown` with `frappe.db.rollback()`, so that the tests run again
  without a wipe of the database.
- Mock only what you must. Use real objects and database records where you can.
- Test names must be long enough that a failed test tells you what broke,
  without a read of the body.
- When you test that the code blocked or rejected an operation, assert the
  specific error message or the final state. Do not assert only that an
  exception occurred.

## Frappe-specific

<<<<<<< HEAD
- Use `frappe.db.set_value` for single-field updates on existing records; use `doc.save()` when multiple fields change together.
- Use `frappe.get_cached_doc` for documents that are read frequently and not mutated.
- Prefer `frappe.db.exists` for existence checks over `frappe.get_value` with a null check.
- `ignore_permissions=True` is acceptable inside scheduled jobs and background hooks that run as Administrator, where the permission model does not apply.
=======
- Use `frappe.db.set_value` for a single-field update on an existing record. Use
  `doc.save()` when several fields change together.
- Use the controller class directly: `Site("Site", name)` instead of
  `frappe.get_doc("Site", name)`. This is important when the controller is in
  the same file. It is shorter, and it gives the type checker and the reader the
  concrete type.
- Use `frappe.get_cached_doc` for documents that the code reads often and does
  not change.
- Use `frappe.db.exists` for an existence check, instead of `frappe.get_value`
  with a null check.
- `ignore_permissions=True` is acceptable in scheduled jobs and background hooks
  that run as Administrator, where the permission model does not apply.
>>>>>>> cabdcfe64 (docs(agents): Rewrite the agent instruction files in simple english)
