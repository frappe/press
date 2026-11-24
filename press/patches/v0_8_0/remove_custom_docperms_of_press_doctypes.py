import frappe

from press.access.core_permissions import is_press_doctype


def execute():
	"""A Custom DocPerm hides every rule in the DocType JSON, so Press DocTypes get their rules from code again.
	Each deleted rule stays in Deleted Document."""
	rules = frappe.get_all("Custom DocPerm", ["name", "parent"])
	doctypes = {rule.parent for rule in rules if is_press_doctype(rule.parent)}
	for rule in rules:
		if rule.parent in doctypes:
			frappe.delete_doc("Custom DocPerm", rule.name, ignore_permissions=True, force=True)
	for doctype in doctypes:
		frappe.clear_cache(doctype=doctype)
