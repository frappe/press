"""The rules of Press roles on Frappe DocTypes.

Press cannot change the DocType JSON of Frappe, so the rules live here. Every migrate and every
install writes the rules of Frappe and these rules to Custom DocPerm. Change this file, not the Role Permissions Manager.
"""

import frappe
from frappe.core.doctype.doctype.doctype import clear_permissions_cache
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

INFRASTRUCTURE = "Press Infrastructure Manager"
# Roles of other apps, which a site may not have
OPTIONAL_ROLES = {"Agent"}

CORE_RULES: dict[str, list[dict]] = {
	# Job internals, so that SREs can debug without System Manager
	"RQ Job": [{"role": INFRASTRUCTURE, "read": 1}],
	"RQ Worker": [{"role": INFRASTRUCTURE, "read": 1}],
	"Error Log": [{"role": INFRASTRUCTURE, "read": 1}],
	"Scheduled Job Log": [{"role": INFRASTRUCTURE, "read": 1}],
	"Scheduled Job Type": [{"role": INFRASTRUCTURE, "read": 1}],
	"Patch Log": [{"role": INFRASTRUCTURE, "read": 1}],
	"Email Queue": [
		{"role": INFRASTRUCTURE, "read": 1},
		# The message and attachments are at permlevel 1, see FIELD_LEVELS
		{"role": "System Manager", "permlevel": 1, "read": 1, "write": 1, "export": 1},
	],
	"Email Account": [
		{"role": INFRASTRUCTURE, "read": 1},
		{"role": "Press Marketplace Manager", "read": 1, "export": 1},
		{"role": "Agent", "read": 1, "export": 1},
	],
	# The SQL guard in press/access/sql_guard.py limits what the console runs
	"System Console": [{"role": INFRASTRUCTURE, "read": 1, "write": 1}],
	"Console Log": [{"role": INFRASTRUCTURE, "read": 1, "if_owner": 1}],
}

# Email bodies hold password reset links and login codes
FIELD_LEVELS: dict[str, dict[str, int]] = {
	"Email Queue": {"message": 1, "attachments": 1},
}


def sync_core_permissions():
	"""Write the rules of Frappe and Press to Custom DocPerm, for each DocType in `CORE_RULES`."""
	for doctype, rules in CORE_RULES.items():
		sync_rules(
			doctype, merged_rules(standard_rules(doctype), [as_rule(rule) for rule in rules if needed(rule)])
		)
	for doctype, levels in FIELD_LEVELS.items():
		for fieldname, permlevel in levels.items():
			sync_field_level(doctype, fieldname, permlevel)


def needed(rule: dict) -> bool:
	return rule["role"] not in OPTIONAL_ROLES or bool(frappe.db.exists("Role", rule["role"]))


def merged_rules(standard: list[dict], press: list[dict]) -> list[dict]:
	"""One rule for each role, level and owner flag, as Frappe expects. The rule of Press wins."""
	merged = {rule_key(rule): rule for rule in standard + press}
	return list(merged.values())


def rule_key(rule: dict) -> tuple:
	return (rule["role"], rule["permlevel"], rule["if_owner"])


def sync_field_level(doctype: str, fieldname: str, permlevel: int):
	setter = {"doc_type": doctype, "field_name": fieldname, "property": "permlevel"}
	if frappe.db.get_value("Property Setter", setter, "value") != str(permlevel):
		make_property_setter(
			doctype, fieldname, "permlevel", permlevel, "Int", validate_fields_for_doctype=False
		)


def standard_rules(doctype: str) -> list[dict]:
	rules = frappe.get_all("DocPerm", {"parent": doctype}, rule_fields())
	return [as_rule(rule) for rule in rules]


def as_rule(rule: dict) -> dict:
	"""A rule with every right, so that rules from code and from the database compare equal."""
	return {key: rule.get(key) or (None if key == "role" else 0) for key in rule_fields()}


def rule_fields() -> list[str]:
	"""The role, the level and every right that both DocPerm and Custom DocPerm store."""
	checks = [str(df.fieldname) for df in frappe.get_meta("Custom DocPerm").fields if df.fieldtype == "Check"]
	standard = frappe.get_meta("DocPerm")
	return ["role", "permlevel", *(field for field in checks if standard.has_field(field))]


def sync_rules(doctype: str, rules: list[dict]):
	if sorted_rules(custom_rules(doctype)) == sorted_rules(rules):
		return
	frappe.db.delete("Custom DocPerm", {"parent": doctype})
	for rule in rules:
		custom_rule = frappe.get_doc({"doctype": "Custom DocPerm", "parent": doctype, **rule})
		custom_rule.flags.from_press_code = True
		custom_rule.insert(ignore_permissions=True)
	clear_permissions_cache(doctype)


def custom_rules(doctype: str) -> list[dict]:
	rules = frappe.get_all("Custom DocPerm", {"parent": doctype}, rule_fields())
	return [as_rule(rule) for rule in rules]


def sorted_rules(rules: list[dict]) -> list[tuple]:
	return sorted(tuple(rule.values()) for rule in rules)


def refuse_rule_outside_code(doc, method=None):
	"""Custom DocPerm hides the rules of the DocType JSON, so rules of Press DocTypes live in code."""
	# Other apps may add their rules on migrate. The next sync of Press still wins on CORE_RULES.
	if doc.flags.from_press_code or frappe.flags.in_migrate or frappe.flags.in_install:
		return
	if doc.parent in CORE_RULES:
		frappe.throw(
			f"Press keeps the rules of {doc.parent} in press/access/core_permissions.py. Change them there.",
			frappe.PermissionError,
		)
	if is_press_doctype(doc.parent):
		frappe.throw(
			f"Change the rules of {doc.parent} in its DocType JSON in Press. A Custom DocPerm hides them all.",
			frappe.PermissionError,
		)


def is_press_doctype(doctype: str) -> bool:
	"""Whether Press ships the DocType JSON. A DocType made in desk keeps its rules in the database."""
	module, custom = frappe.get_cached_value("DocType", doctype, ["module", "custom"]) or (None, 1)
	return not custom and frappe.get_cached_value("Module Def", str(module), "app_name") == "press"
