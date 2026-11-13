# Copyright (c) 2023, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.ansible_console.test_ansible_console import (
	add_team_member,
	create_test_console_user,
	grant_server_access,
)
from press.press.doctype.serial_console_log.serial_console_log import SerialConsoleLog
from press.press.doctype.server.server import BaseServer, Server
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.virtual_machine.test_virtual_machine import create_test_virtual_machine
from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


@patch.object(BaseServer, "after_insert", new=Mock())
@patch.object(VirtualMachine, "client", new=Mock())
@patch("frappe.enqueue_doc", new=Mock())
@patch("frappe.db.commit", new=lambda: None)
class TestSerialConsoleAccess(FrappeTestCase):
	"""Press Infrastructure Manager opens the serial console only of servers that its user may reach."""

	def setUp(self):
		super().setUp()
		self.employee = create_test_console_user()
		self.server = create_test_server(provider="AWS EC2")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def credentials_as_employee(self, server=None) -> dict:
		virtual_machine = VirtualMachine("Virtual Machine", (server or self.server).virtual_machine)
		frappe.set_user(self.employee.user)
		return virtual_machine.get_serial_console_credentials()

	def reboot_as_employee(self) -> None:
		frappe.set_user(self.employee.user)
		Server("Server", self.server.name).reboot_with_serial_console()

	def test_server_console_user_is_refused_the_serial_console_of_a_public_server(self):
		public_server = create_test_server(public=True)
		with self.assertRaisesRegex(frappe.PermissionError, f"You cannot reach Server {public_server.name}"):
			self.credentials_as_employee(public_server)

	def test_server_console_user_gets_serial_console_of_a_server_of_their_team(self):
		add_team_member(self.server.team, self.employee.user)
		credentials = self.credentials_as_employee()
		self.assertTrue(credentials["username"].endswith(".port0"))

	def test_server_console_user_gets_serial_console_with_server_ssh_support_access(self):
		grant_server_access(self.employee, self.server.name, server_ssh=1)
		credentials = self.credentials_as_employee()
		self.assertTrue(credentials["username"].endswith(".port0"))

	def test_server_console_user_is_refused_the_serial_console_without_consent(self):
		with self.assertRaisesRegex(frappe.PermissionError, f"You cannot reach Server {self.server.name}"):
			self.credentials_as_employee()

	def test_server_console_user_is_refused_the_serial_console_of_a_machine_without_server(self):
		virtual_machine = create_test_virtual_machine()
		frappe.set_user(self.employee.user)
		with self.assertRaisesRegex(
			frappe.PermissionError, f"Virtual Machine {virtual_machine.name} has no server"
		):
			virtual_machine.get_serial_console_credentials()

	def test_member_without_server_console_role_is_refused_the_serial_console(self):
		self.employee = create_test_console_user("Press Support Engineer")
		add_team_member(self.server.team, self.employee.user)
		with self.assertRaisesRegex(frappe.PermissionError, "This action is only allowed for"):
			self.credentials_as_employee()

	def test_server_console_user_reboots_a_reachable_server_and_owns_the_log(self):
		grant_server_access(self.employee, self.server.name, server_ssh=1)
		self.reboot_as_employee()
		log = {"server": self.server.name, "action": "reboot", "owner": self.employee.user}
		self.assertTrue(frappe.db.exists("Serial Console Log", log))

	def test_reboot_with_serial_console_is_refused_without_consent_and_leaves_no_log(self):
		with self.assertRaisesRegex(frappe.PermissionError, f"You cannot reach Server {self.server.name}"):
			self.reboot_as_employee()
		self.assertFalse(frappe.db.exists("Serial Console Log", {"server": self.server.name}))

	def test_run_sysrq_is_refused_on_a_log_of_an_unreachable_server(self):
		self.server.reboot_with_serial_console()
		log = frappe.db.get_value("Serial Console Log", {"server": self.server.name}, "name")
		frappe.set_user(self.employee.user)
		with self.assertRaisesRegex(frappe.PermissionError, f"You cannot reach Server {self.server.name}"):
			SerialConsoleLog("Serial Console Log", log).run_sysrq()
