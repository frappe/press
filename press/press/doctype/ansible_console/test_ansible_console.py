# Copyright (c) 2023, Frappe and Contributors
# See license.txt

import json
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from press.access.test_employee_consent import create_test_employee
from press.press.doctype.ansible_console.ansible_console import (
	AnsibleConsole,
	check_inventory_access,
	execute_command,
)
from press.press.doctype.server.server import BaseServer
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.team.team import Team
from press.press.doctype.team.test_team import create_test_team


def create_test_console_user(role: str = "Press Infrastructure Manager") -> Team:
	"""A desk employee with `role` and a team of their own."""
	return create_test_employee(role)


@patch("frappe.sendmail", new=Mock())
def grant_server_access(employee: Team, server: str, **permissions) -> None:
	"""An accepted Support Access of the server's team for `employee`."""
	access = frappe.get_doc(
		{
			"doctype": "Support Access",
			"requested_by": employee.user,
			"requested_team": employee.name,
			"reason": "Debugging",
			"resources": [{"document_type": "Server", "document_name": server}],
		}
	).insert(ignore_permissions=True)
	allowed_till = add_to_date(now_datetime(), hours=1)
	frappe.db.set_value(
		"Support Access",
		access.name,
		{"status": "Accepted", "access_allowed_till": allowed_till, **permissions},
	)


def add_team_member(team: str, user: str) -> None:
	team_doc = Team("Team", team)
	team_doc.append("team_members", {"user": user})
	team_doc.save(ignore_permissions=True)


class TestAnsibleConsole(FrappeTestCase):
	def test_ansible_console_run(self):
		console = frappe.get_doc("Ansible Console")
		console.inventory = "localhost,"
		console.command = "ls"
		console.run()

		self.assertEqual(len(console.output), 1)
		output = console.output[0]

		self.assertEqual(output.host, "localhost")
		self.assertEqual(output.status, "Unreachable")

	def test_ansible_console_run_creates_console_log(self):
		count_before = frappe.db.count("Ansible Console Log")

		console = frappe.get_doc("Ansible Console")
		console.inventory = "localhost,"
		console.command = "ls"
		console.run()

		count_after = frappe.db.count("Ansible Console Log")
		self.assertEqual(count_before + 1, count_after)


@patch.object(BaseServer, "after_insert", new=Mock())
@patch("frappe.db.commit", new=lambda: None)
class TestAnsibleConsoleServerAccess(FrappeTestCase):
	"""Press Infrastructure Manager runs commands only on servers that its user may reach."""

	def setUp(self):
		super().setUp()
		self.employee = create_test_console_user()
		self.server = create_test_server()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def check_as_employee(self, inventory: str) -> str | None:
		frappe.set_user(self.employee.user)
		return check_inventory_access(inventory)

	def test_server_console_user_is_refused_on_a_public_server(self):
		public_server = create_test_server(public=True)
		with self.assertRaisesRegex(frappe.PermissionError, f"You cannot reach Server {public_server.name}"):
			self.check_as_employee(f"{public_server.name},")

	def test_server_console_user_reaches_a_server_of_a_team_they_are_member_of(self):
		add_team_member(self.server.team, self.employee.user)
		self.assertEqual(self.check_as_employee(f" {self.server.name} ,"), f"{self.server.name},")

	def test_server_console_user_reaches_a_dedicated_server_with_server_ssh_support_access(self):
		grant_server_access(self.employee, self.server.name, server_ssh=1)
		self.assertEqual(self.check_as_employee(f"{self.server.name},"), f"{self.server.name},")

	def test_server_ssh_support_access_on_server_covers_its_database_server(self):
		database_server = self.server.database_server
		frappe.db.set_value("Database Server", database_server, "team", self.server.team)
		grant_server_access(self.employee, self.server.name, server_ssh=1)
		self.assertEqual(self.check_as_employee(database_server), f"{database_server},")

	def test_server_ssh_on_app_server_of_another_team_does_not_cover_the_database_server(self):
		database_server = self.server.database_server
		frappe.db.set_value("Database Server", database_server, "team", create_test_team().name)
		grant_server_access(self.employee, self.server.name, server_ssh=1)
		with self.assertRaisesRegex(
			frappe.PermissionError, f"You cannot reach Database Server {database_server}"
		):
			self.check_as_employee(database_server)

	def test_server_ssh_support_access_requested_by_another_employee_does_not_reach_the_server(self):
		grant_server_access(create_test_console_user(), self.server.name, server_ssh=1)
		with self.assertRaisesRegex(frappe.PermissionError, f"You cannot reach Server {self.server.name}"):
			self.check_as_employee(f"{self.server.name},")

	def test_server_console_user_is_refused_on_a_dedicated_server_without_consent(self):
		with self.assertRaisesRegex(frappe.PermissionError, f"You cannot reach Server {self.server.name}"):
			self.check_as_employee(f"{self.server.name},")

	def test_support_access_without_server_ssh_does_not_reach_the_server(self):
		grant_server_access(self.employee, self.server.name)
		with self.assertRaisesRegex(frappe.PermissionError, f"You cannot reach Server {self.server.name}"):
			self.check_as_employee(f"{self.server.name},")

	def test_one_unreachable_host_refuses_the_whole_inventory(self):
		add_team_member(self.server.team, self.employee.user)
		other_server = create_test_server()
		with self.assertRaisesRegex(frappe.PermissionError, f"You cannot reach Server {other_server.name}"):
			self.check_as_employee(f"{self.server.name},{other_server.name},")

	def test_server_console_user_is_refused_on_a_host_that_is_not_a_server(self):
		with self.assertRaisesRegex(
			frappe.PermissionError,
			"unknown.fc.dev is not the name of a Server, Database Server or Proxy Server",
		):
			self.check_as_employee("unknown.fc.dev,")

	def test_server_console_user_is_refused_on_the_all_group(self):
		with self.assertRaisesRegex(
			frappe.PermissionError, "all is not the name of a Server, Database Server or Proxy Server"
		):
			self.check_as_employee("all")

	def test_server_console_user_is_refused_on_groups_patterns_ranges_ports_and_files(self):
		add_team_member(self.server.team, self.employee.user)
		for inventory in ("*", "f[1:3].fc.dev,", f"{self.server.name}:22,", "/etc/ansible/hosts", ""):
			with (
				self.subTest(inventory=inventory),
				self.assertRaisesRegex(frappe.PermissionError, "List servers by name, separated by commas"),
			):
				self.check_as_employee(inventory)

	def test_member_without_server_console_role_is_refused(self):
		self.employee = create_test_console_user("Press Support Engineer")
		add_team_member(self.server.team, self.employee.user)
		with self.assertRaisesRegex(frappe.PermissionError, "This action is only allowed for"):
			self.check_as_employee(f"{self.server.name},")

	def test_system_manager_runs_any_inventory_unchanged(self):
		self.employee = create_test_console_user("System Manager")
		self.assertEqual(self.check_as_employee("localhost,"), "localhost,")

	@patch("press.press.doctype.ansible_console.ansible_console.AnsibleAdHoc")
	def test_run_uses_the_checked_inventory_and_logs_as_the_server_console_user(self, ansible):
		ansible.return_value.run.return_value = []
		add_team_member(self.server.team, self.employee.user)
		frappe.set_user(self.employee.user)
		sent = {"inventory": self.server.name, "command": "ls", "owner": "Administrator"}
		console = AnsibleConsole({"doctype": "Ansible Console", **sent})
		console.run()
		ansible.assert_called_once_with(sources=f"{self.server.name},")
		log = {"owner": self.employee.user, "inventory": f"{self.server.name},"}
		self.assertTrue(frappe.db.exists("Ansible Console Log", log))

	@patch("press.press.doctype.ansible_console.ansible_console.AnsibleAdHoc")
	def test_run_refuses_an_unreachable_server_before_ansible_starts(self, ansible):
		frappe.set_user(self.employee.user)
		console = AnsibleConsole({"doctype": "Ansible Console", "inventory": f"{self.server.name},"})
		with self.assertRaisesRegex(frappe.PermissionError, f"You cannot reach Server {self.server.name}"):
			console.run()
		ansible.assert_not_called()

	@patch("frappe.enqueue")
	def test_execute_command_refuses_an_unreachable_server_before_it_enqueues(self, enqueue):
		frappe.set_user(self.employee.user)
		doc = json.dumps({"doctype": "Ansible Console", "inventory": f"{self.server.name},", "command": "ls"})
		with self.assertRaisesRegex(frappe.PermissionError, f"You cannot reach Server {self.server.name}"):
			execute_command(doc)
		enqueue.assert_not_called()

	@patch("frappe.enqueue")
	def test_execute_command_enqueues_for_a_reachable_server(self, enqueue):
		grant_server_access(self.employee, self.server.name, server_ssh=1)
		frappe.set_user(self.employee.user)
		doc = json.dumps({"doctype": "Ansible Console", "inventory": f"{self.server.name},", "command": "ls"})
		execute_command(doc)
		enqueue.assert_called_once()

	@patch("frappe.enqueue")
	def test_execute_command_refuses_a_document_that_is_not_an_ansible_console(self, enqueue):
		frappe.set_user(self.employee.user)
		with self.assertRaisesRegex(frappe.PermissionError, "Send an Ansible Console document"):
			execute_command(json.dumps({"doctype": "Serial Console Log", "inventory": "localhost,"}))
		enqueue.assert_not_called()
