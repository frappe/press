# Copyright (c) 2019, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from press.access.test_employee_consent import create_test_employee
from press.press.doctype.server.server import Server
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.press.doctype.user_ssh_certificate.user_ssh_certificate import UserSSHCertificate
from press.press.doctype.user_ssh_key.test_user_ssh_key import create_test_user_ssh_key

HYBRID_ONLY = "Press Hybrid Server Manager reaches only self-hosted servers"
NO_ACCESS = "You cannot reach Server"
NO_ROLE = "You need the Press Infrastructure Manager or Press Hybrid Server Manager role"


@patch("frappe.sendmail", new=Mock())
class TestUserSSHCertificateIssuer(FrappeTestCase):
	"""Staff without full SSH rights issue certificates only for themselves, for one server they may reach."""

	def setUp(self):
		super().setUp()
		self.customer = create_test_press_admin_team()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def employee_with_role(self, role: str) -> str:
		self.employee = create_test_employee(role)
		self.key = create_test_user_ssh_key(str(self.employee.user))
		return str(self.employee.user)

	def customer_server(self, **kwargs) -> Server:
		return create_test_server(team=self.customer.name, **kwargs)

	def new_certificate(self, issuer: str, server: Server, **fields) -> UserSSHCertificate:
		frappe.set_user(issuer)
		certificate = {
			"doctype": "User SSH Certificate",
			"user": issuer,
			"user_ssh_key": self.key.name,
			"server_type": "Server",
			"access_server": server.name,
			"reason": "Debugging",
			"validity": "3h",
		}
		return UserSSHCertificate({**certificate, **fields})

	def issue(self, issuer: str, server: Server, **fields) -> UserSSHCertificate:
		return self.new_certificate(issuer, server, **fields).insert()

	def grant_server_ssh(self, server: Server, server_ssh: int = 1, requester=None):
		requester = requester or self.employee
		access = frappe.get_doc(
			{
				"doctype": "Support Access",
				"requested_by": requester.user,
				"requested_team": requester.name,
				"reason": "Debugging",
				"resources": [{"document_type": "Server", "document_name": server.name}],
			}
		).insert(ignore_permissions=True)
		allowed_till = add_to_date(now_datetime(), hours=1)
		frappe.db.set_value(
			"Support Access",
			access.name,
			{"status": "Accepted", "access_allowed_till": allowed_till, "server_ssh": server_ssh},
		)

	def test_hybrid_ssh_role_issues_certificate_for_self_hosted_server_without_consent(self):
		user = self.employee_with_role("Press Hybrid Server Manager")
		certificate = self.issue(user, self.customer_server(is_self_hosted=True))
		self.assertTrue(frappe.db.exists("User SSH Certificate", certificate.name))

	def test_hybrid_ssh_role_cannot_issue_certificate_for_server_that_is_not_self_hosted(self):
		user = self.employee_with_role("Press Hybrid Server Manager")
		with self.assertRaisesRegex(frappe.PermissionError, HYBRID_ONLY):
			self.issue(user, self.customer_server())

	def test_server_console_role_cannot_issue_certificate_for_public_server(self):
		user = self.employee_with_role("Press Infrastructure Manager")
		with self.assertRaisesRegex(frappe.PermissionError, NO_ACCESS):
			self.issue(user, create_test_server(public=True))

	def test_server_console_role_issues_certificate_for_server_of_own_team(self):
		user = self.employee_with_role("Press Infrastructure Manager")
		certificate = self.issue(user, create_test_server(team=self.employee.name))
		self.assertTrue(frappe.db.exists("User SSH Certificate", certificate.name))

	def test_server_console_role_issues_certificate_for_customer_server_with_server_ssh_consent(self):
		user = self.employee_with_role("Press Infrastructure Manager")
		server = self.customer_server()
		self.grant_server_ssh(server)
		certificate = self.issue(user, server)
		self.assertTrue(frappe.db.exists("User SSH Certificate", certificate.name))

	def test_server_console_role_cannot_issue_certificate_for_customer_server_without_consent(self):
		user = self.employee_with_role("Press Infrastructure Manager")
		with self.assertRaisesRegex(frappe.PermissionError, NO_ACCESS):
			self.issue(user, self.customer_server())

	def test_server_console_role_cannot_issue_certificate_when_consent_lacks_server_ssh(self):
		user = self.employee_with_role("Press Infrastructure Manager")
		server = self.customer_server()
		self.grant_server_ssh(server, server_ssh=0)
		with self.assertRaisesRegex(frappe.PermissionError, NO_ACCESS):
			self.issue(user, server)

	def test_server_console_and_hybrid_roles_cannot_issue_all_servers_certificate(self):
		server = self.customer_server(is_self_hosted=True)
		for role in ("Press Infrastructure Manager", "Press Hybrid Server Manager"):
			with self.subTest(role=role):
				user = self.employee_with_role(role)
				with self.assertRaisesRegex(frappe.PermissionError, "certificate for all servers"):
					self.issue(user, server, all_servers=1)
				frappe.set_user("Administrator")

	def test_staff_cannot_issue_certificate_for_another_user(self):
		user = self.employee_with_role("Press Hybrid Server Manager")
		server = self.customer_server(is_self_hosted=True)
		with self.assertRaisesRegex(frappe.PermissionError, "only issue an SSH certificate for yourself"):
			self.issue(user, server, user=self.customer.user)

	def test_staff_cannot_issue_certificate_with_ssh_key_of_another_user(self):
		user = self.employee_with_role("Press Hybrid Server Manager")
		other_key = create_test_user_ssh_key(self.customer.user)
		server = self.customer_server(is_self_hosted=True)
		with self.assertRaisesRegex(frappe.PermissionError, "for an SSH key of your own"):
			self.issue(user, server, user_ssh_key=other_key.name)
		self.assertFalse(frappe.db.exists("User SSH Certificate", {"user_ssh_key": other_key.name}))

	def test_pasted_public_key_is_replaced_by_the_public_key_of_the_selected_ssh_key(self):
		user = self.employee_with_role("Press Hybrid Server Manager")
		pasted = create_test_user_ssh_key(self.customer.user).ssh_public_key
		certificate = self.issue(user, self.customer_server(is_self_hosted=True), ssh_public_key=pasted)
		stored = frappe.db.get_value("User SSH Certificate", certificate.name, "ssh_public_key")
		self.assertEqual(stored, self.key.ssh_public_key)

	def test_staff_cannot_validate_certificate_whose_public_key_differs_from_its_ssh_key(self):
		user = self.employee_with_role("Press Hybrid Server Manager")
		pasted = create_test_user_ssh_key(self.customer.user).ssh_public_key
		certificate = self.new_certificate(user, self.customer_server(is_self_hosted=True))
		certificate.ssh_public_key = pasted
		with self.assertRaisesRegex(frappe.PermissionError, "for an SSH key of your own"):
			certificate.validate()

	def test_server_console_role_cannot_use_server_ssh_consent_requested_by_another_employee(self):
		user = self.employee_with_role("Press Infrastructure Manager")
		server = self.customer_server()
		self.grant_server_ssh(server, requester=create_test_employee("Press Infrastructure Manager"))
		with self.assertRaisesRegex(frappe.PermissionError, NO_ACCESS):
			self.issue(user, server)

	def test_staff_without_ssh_role_cannot_create_or_issue_certificate(self):
		user = self.employee_with_role("Press Marketplace Manager")
		self.assertFalse(frappe.has_permission("User SSH Certificate", "create", user=user))
		certificate = self.new_certificate(user, self.customer_server(is_self_hosted=True))
		with self.assertRaisesRegex(frappe.PermissionError, NO_ROLE):
			certificate.insert(ignore_permissions=True)

	def test_site_manager_role_no_longer_creates_certificates(self):
		user = self.employee_with_role("Site Manager")
		self.assertFalse(frappe.has_permission("User SSH Certificate", "create", user=user))

	def test_system_manager_issues_all_servers_certificate_for_another_user(self):
		user = self.employee_with_role("System Manager")
		other_user = self.customer.user
		certificate = self.issue(user, create_test_server(public=True), user=other_user, all_servers=1)
		self.assertEqual(frappe.db.get_value("User SSH Certificate", certificate.name, "user"), other_user)

	def test_ssh_manager_issues_all_servers_certificate_for_another_user(self):
		user = self.employee_with_role("Press SSH Manager")
		other_user = self.customer.user
		certificate = self.issue(user, create_test_server(public=True), user=other_user, all_servers=1)
		self.assertEqual(frappe.db.get_value("User SSH Certificate", certificate.name, "user"), other_user)
