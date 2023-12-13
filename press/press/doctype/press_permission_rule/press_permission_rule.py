# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


DEFAULT_RULE = {
	"*": {
		"*": {
			"allow": ["*"],
			"restrict": [],
		}
	}
}

RESTRICTED_DOCTYPES = [
	"Site",
	"Release Group",
	"Server",
	"Database Server",
	"Marketplace App",
]

class PressPermissionRule(Document):
	def validate(self):
		self.validate_rule()

	def validate_rule(self):
		rules = frappe.parse_json(self.rule)
		if not rules:
			self.rules = DEFAULT_RULE
			return

		for doctype, document_names in rules.items():
			if doctype == "*":
				continue

			if doctype not in RESTRICTED_DOCTYPES:
				frappe.throw(f"{doctype} is not a valid doctype for permission rule.")

			if not isinstance(document_names, dict):
				frappe.throw(f"Invalid rule for {doctype}. Rule must be a dictionary.")

			for document_name, rule in document_names.items():
				if document_name == "*":
					continue

				if not isinstance(rule, dict):
					frappe.throw(f"Invalid rule for {doctype} > {document_name}. Rule must be a dictionary.")

				allow = rule.get("allow", None)
				restrict = rule.get("restrict", None)
				if allow and not isinstance(allow, list):
					frappe.throw(f"Invalid allow for {doctype} > {document_name}. Allow must be a list.")
				if restrict and not isinstance(restrict, list):
					frappe.throw(f"Invalid restrict for {doctype} > {document_name}. Restrict must be a list.")

				# TODO: validate allow and restrict values


def has_user_permission(doctype: str, name: str, method: str, permission_rules: list = None):
	user = frappe.session.user
	allowed = False

	if doctype not in RESTRICTED_DOCTYPES:
		return True

	if not permission_rules:
		permission_rules = get_permission_rules(user)

	for rule_name in set(permission_rules):
		rule_applies_to_user = frappe.db.exists(
			"Press Permission Rule User", {"parent": rule_name, "user": user}
		)
		if not rule_applies_to_user:
			continue

		rules = frappe.db.get_value("Press Permission Rule", rule_name, "rule")
		rules = frappe.parse_json(rules)
		doctype_rule = rules.get(doctype, None) or rules.get("*", None)
		if not doctype_rule:
			allowed = True
			continue

		document_rule = doctype_rule.get(name, None) or doctype_rule.get("*", None)
		if not document_rule:
			allowed = True
			continue

		allowed_methods = document_rule.get("allow", None)
		restricted_methods = document_rule.get("restrict", None)
		if not allowed_methods and not restricted_methods:
			allowed = True

		if (
				allowed_methods
				and (method in allowed_methods or "*" in allowed_methods)
			):
			allowed = True

		if (
				restricted_methods
				and method not in restricted_methods
				and "*" not in restricted_methods
			):
			allowed = True

	return allowed


def get_permission_rules(user: str = None) -> list:
	if not user:
		user = frappe.session.user

	permission_rules = frappe.get_all(
		"Press Permission Rule User",
		filters={"user": user},
		fields=["parent"],
		distinct=True,
	)
	return [rule.parent for rule in permission_rules]


def get_permitted_methods(doc: Document):
	permitted_methods = []
	user = frappe.session.user
	permission_rules = get_permission_rules(user)
	for rule_name in set(permission_rules):
		rules = frappe.db.get_value("Press Permission Rule", rule_name, "rule")
		rules = frappe.parse_json(rules)
		doctype_rule = rules.get(doc.doctype, None)
		if not doctype_rule:
			continue

		document_rule = doctype_rule.get(doc.name, None)
		if not document_rule:
			continue

		allowed_methods = document_rule.get("allow", None)
		restricted_methods = document_rule.get("restrict", None)
		if allowed_methods:
			permitted_methods += allowed_methods
		if restricted_methods:
			permitted_methods = [
				method
				for method in permitted_methods
				if method not in restricted_methods
			]

	return permitted_methods


