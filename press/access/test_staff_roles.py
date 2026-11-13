# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import json
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.access.staff_roles import check_staff_role, use_saved_document
from press.press.doctype.agent_job.test_agent_job import fake_agent_job
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.team.test_team import create_test_team
from press.tests.test_staff_role_scopes import PROFILE_SCOPES, create_staff_user

DESK_BUTTON_CALLS = [
	("/api/method/run_doc_method", "Invoice", "refund"),
	("/api/v2/document/Marketplace App/frappe/method/delete", "Marketplace App", "delete"),
	("/api/v2/document/Marketplace App/frappe/method/delete/", "Marketplace App", "delete"),
	("/api/resource/TLS Certificate/example.com", "TLS Certificate", "get_private_key"),
	("/api/v2/method/run_doc_method", "Server", "generate_on_prem_failover_config"),
]


def press_desk_button(path: str, doctype: str, method: str):
	"""Run the staff role check for a request that presses `method` on a `doctype` record."""
	form = frappe._dict({"run_method": method} if "/resource/" in path else {"method": method})
	if "run_doc_method" in path:
		form.update({"docs": json.dumps({"doctype": doctype}), "document": {"doctype": doctype}})
	run_hook(check_staff_role, path, form)


def run_hook(hook, path: str, form: dict) -> dict:
	with (
		patch.object(frappe.local, "request", SimpleNamespace(path=path), create=True),
		patch.object(frappe.local, "form_dict", frappe._dict(form)),
	):
		hook()
		return frappe.local.form_dict


def send_form(document: dict) -> dict:
	"""The document that a desk button call runs on after `use_saved_document`."""
	form = run_hook(use_saved_document, "/api/method/run_doc_method", {"docs": json.dumps(document)})
	return frappe.parse_json(form["docs"])


class TestStaffRoles(FrappeTestCase):
	"""Desk staff press a marked document button only with its scope role."""

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_support_cannot_press_buttons_of_other_scopes_from_desk(self):
		frappe.set_user(create_staff_user("Press Support Engineer"))
		for path, doctype, method in DESK_BUTTON_CALLS:
			with self.subTest(path=path), self.assertRaises(frappe.PermissionError):
				press_desk_button(path, doctype, method)

	def test_marked_buttons_work_for_their_scope_role_and_for_customers(self):
		for user in (create_staff_user(*PROFILE_SCOPES), create_test_team().user):
			frappe.set_user(user)
			for path, doctype, method in DESK_BUTTON_CALLS:
				with self.subTest(user=user, path=path):
					press_desk_button(path, doctype, method)

	def test_marked_buttons_still_work_when_press_code_calls_them(self):
		frappe.set_user(create_staff_user("Press Support Engineer"))
		press_desk_button("/api/method/run_doc_method", "Server", "update_tls_certificate")
		press_desk_button("/api/method/press.api.billing.finalize_invoices", "Invoice", "finalize_invoice")
		certificate = frappe.get_doc({"doctype": "TLS Certificate"})
		self.assertIsNone(certificate.get_private_key())

	def test_staff_who_cannot_write_a_record_run_its_buttons_on_the_saved_copy(self):
		job_type = frappe.get_all("Agent Job Type", limit=1, pluck="name")[0]
		frappe.set_user(create_staff_user("Press Support Engineer"))
		sent = send_form({"doctype": "Agent Job Type", "name": job_type, "modified": "2000-01-01"})
		self.assertEqual(sent["modified"], str(frappe.db.get_value("Agent Job Type", job_type, "modified")))

	def test_staff_who_cannot_create_a_record_cannot_run_buttons_on_a_new_one(self):
		frappe.set_user(create_staff_user("Press Support Engineer"))
		with self.assertRaises(frappe.PermissionError):
			send_form({"doctype": "Agent Job", "request_path": "made-up", "request_method": "POST"})

	def test_staff_who_can_write_a_record_keep_their_form_values(self):
		team = create_test_team().name
		frappe.set_user(create_staff_user("Press Support Engineer"))
		sent = send_form({"doctype": "Team", "name": team, "modified": "2000-01-01"})
		self.assertEqual(sent["modified"], "2000-01-01")

	def test_support_and_reliability_engineers_can_press_server_buttons_that_queue_agent_jobs(self):
		server = create_test_server()
		if not frappe.db.exists("Agent Job Type", "Ping Job"):
			frappe.get_doc({"doctype": "Agent Job Type", "name": "Ping Job"}).insert()
		for profile in ("Press Support Engineer", "Press Site Reliability Engineer"):
			frappe.set_user(create_staff_user(profile))
			with self.subTest(profile=profile), fake_agent_job("Ping Job"):
				self.assertTrue(frappe.db.exists("Agent Job", server.ping_agent_job()))
			frappe.set_user("Administrator")

	def test_staff_cannot_hide_a_marked_method_behind_a_second_doctype(self):
		frappe.set_user(create_staff_user("Press Support Engineer"))
		form = {"method": "refund", "docs": json.dumps({"doctype": "Team"}), "dt": "Invoice", "dn": "x"}
		with self.assertRaises(frappe.PermissionError):
			run_hook(check_staff_role, "/api/method/run_doc_method", form)
		form = {
			"method": "refund",
			"docs": json.dumps({"doctype": "Team"}),
			"document": {"doctype": "Invoice"},
		}
		with self.assertRaises(frappe.PermissionError):
			run_hook(check_staff_role, "/api/v2/method/run_doc_method", form)
		form = {"cmd": "frappe.handler.run_doc_method", "method": "refund", "dt": "Invoice", "dn": "x"}
		with self.assertRaises(frappe.PermissionError):
			run_hook(check_staff_role, "/", form)

	def test_staff_get_the_saved_copy_in_every_document_key(self):
		job_type = frappe.get_all("Agent Job Type", limit=1, pluck="name")[0]
		frappe.set_user(create_staff_user("Press Support Engineer"))
		made_up = json.dumps({"doctype": "Agent Job Type", "name": job_type, "modified": "2000-01-01"})
		form = run_hook(
			use_saved_document, "/api/v2/method/run_doc_method/", {"docs": made_up, "document": made_up}
		)
		saved = str(frappe.db.get_value("Agent Job Type", job_type, "modified"))
		self.assertEqual(
			[frappe.parse_json(form[key])["modified"] for key in ("docs", "document")], [saved, saved]
		)

	def test_press_support_reads_what_engineers_read_and_changes_nothing(self):
		user = create_staff_user("Press Support")
		doctypes = frappe.get_all(
			"DocPerm", {"role": "Press Support Engineer", "read": 1, "permlevel": 0}, pluck="parent"
		)
		for doctype in doctypes:
			with self.subTest(doctype=doctype):
				self.assertTrue(frappe.has_permission(doctype, "read", user=user))
		changes = ("write", "create", "delete", "submit", "cancel", "amend", "import")
		for permission in frappe.get_all("DocPerm", {"role": "Press Support"}, ["*"]):
			with self.subTest(doctype=permission.parent):
				self.assertEqual([ptype for ptype in changes if permission[ptype]], [])

	def test_press_support_presses_only_buttons_safe_for_readers(self):
		frappe.set_user(create_staff_user("Press Support"))
		press_desk_button("/api/method/run_doc_method", "Site", "get_backup_schedule")
		press_desk_button("/api/v2/document/Server/x/method/ping_agent/", "Server", "ping_agent")
		blocked = [
			("/api/method/run_doc_method", {"method": "archive", "dt": "Site", "dn": "x"}),
			("/api/v2/document/Agent Job/x/method/retry/", {}),
			(
				"/api/method/run_doc_method",
				{"method": "delete_remote_object", "dt": "Remote File", "dn": "x"},
			),
			("/api/method/press.api.client.run_doc_method", {"dt": "Site", "dn": "x", "method": "archive"}),
			("/api/method/press.api.client.delete", {"doctype": "Site", "name": "x"}),
		]
		for path, form in blocked:
			with self.subTest(path=path), self.assertRaisesRegex(frappe.PermissionError, "only read"):
				run_hook(check_staff_role, path, form)

	def test_roles_that_are_not_read_only_still_press_every_button(self):
		for profiles in [("Press Support Engineer",), ("Press Support", "Press Site Reliability Engineer")]:
			frappe.set_user(create_staff_user(*profiles))
			with self.subTest(profiles=profiles):
				run_hook(check_staff_role, "/api/v2/document/Agent Job/x/method/retry/", {})
				run_hook(check_staff_role, "/api/method/run_doc_method", {"method": "archive", "dt": "Site"})
			frappe.set_user("Administrator")
