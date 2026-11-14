# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.model import get_permitted_fields
from frappe.permissions import add_permission
from frappe.tests.utils import FrappeTestCase

from press.access.core_permissions import CORE_RULES, as_rule, merged_rules, sync_core_permissions
from press.access.test_employee_consent import create_test_employee
from press.patches.v0_8_0 import remove_custom_docperms_of_press_doctypes


def create_user(role: str) -> str:
	return str(create_test_employee(role).user)


def clear_meta(*doctypes: str):
	# A bare clear_cache keeps the DocType meta, which holds the permission rules
	for doctype in doctypes:
		frappe.clear_cache(doctype=doctype)


class TestCorePermissions(FrappeTestCase):
	"""Press keeps the rules of its roles on Frappe DocTypes in code, and writes them on migrate."""

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		clear_meta("Error Log", "Email Queue", "Server", "Note")

	def test_sync_lets_infrastructure_manager_read_error_log(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Error Log"})
		clear_meta("Error Log")
		user = create_user("Press Infrastructure Manager")
		self.assertFalse(frappe.has_permission("Error Log", "read", user=user))
		sync_core_permissions()
		self.assertTrue(frappe.has_permission("Error Log", "read", user=user))
		self.assertFalse(frappe.has_permission("Error Log", "delete", user=user))

	def test_sync_keeps_the_rules_of_frappe(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Error Log"})
		sync_core_permissions()
		rule = {"parent": "Error Log", "role": "System Manager", "permlevel": 0}
		self.assertEqual(frappe.db.get_value("Custom DocPerm", rule, "delete"), 1)

	def test_sync_rewrites_nothing_when_the_rules_match(self):
		# Console Log has an owner-only rule, and Email Queue has field levels
		sync_core_permissions()
		filters = {"parent": ("in", list(CORE_RULES))}
		before = frappe.get_all("Custom DocPerm", filters, pluck="name", order_by="name")
		setters = frappe.get_all("Property Setter", {"doc_type": "Email Queue"}, pluck="name")
		sync_core_permissions()
		self.assertEqual(frappe.get_all("Custom DocPerm", filters, pluck="name", order_by="name"), before)
		self.assertEqual(
			frappe.get_all("Property Setter", {"doc_type": "Email Queue"}, pluck="name"), setters
		)

	def test_rule_of_press_replaces_standard_rule_of_same_role_and_level(self):
		standard = as_rule({"role": "Press Infrastructure Manager", "permlevel": 0, "read": 1, "delete": 1})
		press = as_rule({"role": "Press Infrastructure Manager", "permlevel": 0, "read": 1})
		self.assertEqual(merged_rules([standard], [press]), [press])

	def test_owner_only_rule_stays_next_to_rule_for_all_documents(self):
		everyone = as_rule({"role": "Press Infrastructure Manager", "read": 1})
		owner = as_rule({"role": "Press Infrastructure Manager", "read": 1, "if_owner": 1})
		self.assertEqual(len(merged_rules([everyone], [owner])), 2)

	def test_infrastructure_manager_reads_email_queue_without_message_or_attachments(self):
		sync_core_permissions()
		clear_meta("Email Queue")
		fields = get_permitted_fields("Email Queue", user=create_user("Press Infrastructure Manager"))
		self.assertIn("error", fields)
		self.assertNotIn("message", fields)
		self.assertNotIn("attachments", fields)

	def test_system_manager_reads_email_queue_message(self):
		sync_core_permissions()
		clear_meta("Email Queue")
		fields = get_permitted_fields("Email Queue", user=create_user("System Manager"))
		self.assertIn("message", fields)
		self.assertIn("attachments", fields)

	def test_custom_docperm_on_press_doctype_is_refused(self):
		with self.assertRaisesRegex(frappe.PermissionError, "Change the rules of Server in its DocType JSON"):
			add_permission("Server", "Press Support L1")

	def test_custom_docperm_on_core_doctype_with_rules_in_code_is_refused(self):
		with self.assertRaisesRegex(frappe.PermissionError, "press/access/core_permissions.py"):
			add_permission("Error Log", "Press Support L1")

	def test_custom_docperm_on_other_core_doctype_is_allowed(self):
		add_permission("Note", "Press Support L1")
		self.assertTrue(frappe.db.exists("Custom DocPerm", {"parent": "Note", "role": "Press Support L1"}))


class TestRemoveCustomDocPermsOfPressDocTypes(FrappeTestCase):
	"""The patch brings back the rules of the DocType JSON, and keeps rules on Frappe DocTypes."""

	def tearDown(self):
		frappe.db.rollback()
		clear_meta("Server", "Note")

	def insert_rule(self, doctype: str, role: str):
		rule = frappe.get_doc({"doctype": "Custom DocPerm", "parent": doctype, "role": role, "read": 1})
		rule.flags.from_press_code = True
		rule.insert(ignore_permissions=True)
		clear_meta(doctype)
		return rule

	def test_patch_brings_back_the_json_rules_of_a_press_doctype(self):
		rule = self.insert_rule("Server", "Site Manager")
		user = create_user("Press Infrastructure Manager")
		self.assertFalse(frappe.has_permission("Server", "read", user=user))
		remove_custom_docperms_of_press_doctypes.execute()
		self.assertTrue(frappe.has_permission("Server", "read", user=user))
		self.assertTrue(frappe.db.exists("Deleted Document", {"deleted_name": rule.name}))

	def test_patch_keeps_custom_docperms_of_frappe_doctypes(self):
		rule = self.insert_rule("Note", "Press Support L1")
		remove_custom_docperms_of_press_doctypes.execute()
		self.assertTrue(frappe.db.exists("Custom DocPerm", rule.name))


class TestPressDocTypeRules(FrappeTestCase):
	"""Rules that production kept in Custom DocPerm now ship in the DocType JSON."""

	def test_billing_manager_submits_payout_orders_and_payment_due_extensions(self):
		user = create_user("Press Billing Manager")
		for doctype in ("Payout Order", "Payment Due Extension"):
			with self.subTest(doctype=doctype):
				self.assertTrue(frappe.has_permission(doctype, "submit", user=user))
