# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import json
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date

from press.access.test_employee_consent import create_test_employee
from press.press.doctype.bench.bench import Bench
from press.press.doctype.bench_shell.bench_shell import BenchShell, run_command
from press.press.doctype.bench_shell_log.bench_shell_log import create_bench_shell_log
from press.press.doctype.site.test_site import create_test_bench
from press.press.doctype.team.test_team import create_test_press_admin_team

EXECUTE_RESULT = {
	"command": "ls",
	"status": "Success",
	"start": "2026-11-13T18:00:00",
	"end": "2026-11-13T18:00:01",
	"duration": 1.0,
	"output": "apps sites",
	"directory": "/home/frappe/frappe-bench",
	"traceback": None,
	"returncode": 0,
}


@patch("frappe.sendmail", new=Mock())
@patch.object(Bench, "docker_execute", return_value=EXECUTE_RESULT)
@patch("press.press.doctype.bench_shell.bench_shell.frappe.db.commit", new=Mock())
class TestBenchShell(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.staff = create_test_employee("Press Support Engineer")
		self.customer_bench = create_test_bench(create_test_press_admin_team().user)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def run_as(self, user: str, bench: str, as_root: bool = False) -> BenchShell:
		frappe.set_user(user)
		shell = BenchShell({"doctype": "Bench Shell", "bench": bench, "command": "ls", "as_root": as_root})
		shell.run_command()
		return shell

	def grant_ssh(self, group: str, **permissions):
		access = frappe.get_doc(
			{
				"doctype": "Support Access",
				"requested_by": self.staff.user,
				"requested_team": self.staff.name,
				"reason": "Debugging",
				"resources": [{"document_type": "Release Group", "document_name": group}],
			}
		).insert(ignore_permissions=True)
		allowed_till = add_to_date(None, hours=1)
		frappe.db.set_value(
			"Support Access",
			access.name,
			{"status": "Accepted", "access_allowed_till": allowed_till, **permissions},
		)

	def test_bench_shell_user_runs_command_on_bench_of_own_team(self, docker_execute):
		own_bench = create_test_bench(self.staff.user)
		shell = self.run_as(self.staff.user, own_bench.name)
		self.assertEqual(shell.output, "apps sites")
		docker_execute.assert_called_once()

	def test_bench_shell_user_cannot_run_on_other_team_bench_without_consent(self, docker_execute):
		with self.assertRaisesRegex(
			frappe.PermissionError, "Request Support Access with SSH on the bench group"
		):
			self.run_as(self.staff.user, self.customer_bench.name)
		docker_execute.assert_not_called()

	def test_bench_shell_user_cannot_run_with_grant_that_lacks_bench_ssh(self, docker_execute):
		self.grant_ssh(self.customer_bench.group)
		with self.assertRaisesRegex(
			frappe.PermissionError, "Request Support Access with SSH on the bench group"
		):
			self.run_as(self.staff.user, self.customer_bench.name)
		docker_execute.assert_not_called()

	def test_bench_shell_user_runs_on_other_team_bench_with_bench_ssh_grant(self, docker_execute):
		self.grant_ssh(self.customer_bench.group, bench_ssh=1)
		shell = self.run_as(self.staff.user, self.customer_bench.name)
		self.assertEqual(shell.output, "apps sites")
		docker_execute.assert_called_once()

	def test_bench_shell_user_cannot_run_as_root_even_with_bench_ssh_grant(self, docker_execute):
		self.grant_ssh(self.customer_bench.group, bench_ssh=1)
		with self.assertRaisesRegex(
			frappe.PermissionError, "Only a System Manager can run a command as root"
		):
			self.run_as(self.staff.user, self.customer_bench.name, as_root=True)
		docker_execute.assert_not_called()

	def test_bench_shell_user_cannot_run_on_public_bench_group_even_with_bench_ssh_grant(
		self, docker_execute
	):
		frappe.db.set_value("Release Group", self.customer_bench.group, "public", 1)
		self.grant_ssh(self.customer_bench.group, bench_ssh=1)
		with self.assertRaisesRegex(frappe.PermissionError, "Public bench groups need a System Manager"):
			self.run_as(self.staff.user, self.customer_bench.name)
		docker_execute.assert_not_called()

	def test_staff_without_bench_shell_role_cannot_run_command(self, docker_execute):
		other_staff = create_test_employee()
		with self.assertRaisesRegex(frappe.PermissionError, "This action is only allowed for"):
			self.run_as(other_staff.user, self.customer_bench.name)
		docker_execute.assert_not_called()

	def test_system_manager_runs_as_root_on_other_team_bench_without_consent(self, docker_execute):
		system_manager = create_test_employee("System Manager")
		shell = self.run_as(system_manager.user, self.customer_bench.name, as_root=True)
		self.assertEqual(shell.output, "apps sites")
		self.assertTrue(docker_execute.call_args.kwargs["as_root"])

	def test_whitelisted_run_command_checks_consent_even_for_document_of_another_doctype(
		self, docker_execute
	):
		frappe.set_user(self.staff.user)
		crafted = {"doctype": "Build Cache Shell", "bench": self.customer_bench.name, "command": "ls"}
		with self.assertRaisesRegex(
			frappe.PermissionError, "Request Support Access with SSH on the bench group"
		):
			run_command(json.dumps(crafted))
		docker_execute.assert_not_called()


@patch("press.press.doctype.bench_shell_log.bench_shell_log.frappe.db.commit", new=Mock())
class TestBenchShellLogOwner(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_bench_shell_log_of_staff_command_is_owned_and_readable_by_staff(self):
		staff = create_test_employee("Press Support Engineer")
		bench = create_test_bench(staff.user)
		frappe.set_user(staff.user)
		create_bench_shell_log(EXECUTE_RESULT, bench.name, "ls", None, save_output=True)
		log = frappe.get_last_doc("Bench Shell Log", {"bench": bench.name})
		self.assertEqual(log.owner, staff.user)
		self.assertTrue(frappe.has_permission("Bench Shell Log", "read", doc=log))
