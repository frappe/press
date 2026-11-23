# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from press.access.actions import ReleaseGroupActions, SiteActions
from press.access.server_access import can_reach_server
from press.access.support_access import can_perform
from press.access.test_employee_consent import create_test_employee
from press.press.doctype.bench.bench import Bench
from press.press.doctype.bench_shell.bench_shell import BenchShell
from press.press.doctype.bench_shell.test_bench_shell import EXECUTE_RESULT
from press.press.doctype.incident.incident import Incident
from press.press.doctype.release_group.release_group import ReleaseGroup
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.team.test_team import create_test_press_admin_team


def create_test_incident(
	server: str, status: str = "Confirmed", hours_ago: int = 1, owner: str = "Administrator", **fields
):
	"""An incident row without its hooks, which call people and start investigations."""
	created = add_to_date(now_datetime(), hours=-hours_ago)
	incident = frappe.get_doc(
		{
			"doctype": "Incident",
			"name": frappe.generate_hash(length=10),
			"server": server,
			"status": status,
			"type": "Server Down",
			"creation": created,
			"modified": created,
			"owner": owner,
			**fields,
		}
	)
	incident.db_insert()
	return incident


@patch("frappe.sendmail", new=Mock())
@patch.object(Bench, "docker_execute", new=Mock(return_value=EXECUTE_RESULT))
@patch("press.press.doctype.bench_shell.bench_shell.frappe.db.commit", new=Mock())
class TestIncidentAccess(FrappeTestCase):
	"""SREs and L2 support reach the resources of an open incident without the consent of their team."""

	def setUp(self):
		super().setUp()
		shared_server = create_test_server(public=True)
		self.server = str(shared_server.name)
		self.paired_database_server = str(shared_server.database_server)
		self.proxy_server = str(shared_server.proxy_server)
		self.customer = create_test_press_admin_team()
		self.customer_team = str(self.customer.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def act_as(self, role: str):
		frappe.set_user(str(create_test_employee(role).user))

	def test_sre_reaches_shared_server_of_confirmed_incident(self):
		create_test_incident(self.server)
		self.act_as("Press Infrastructure Manager")
		self.assertTrue(can_reach_server("Server", self.server))

	def test_sre_cannot_reach_shared_server_without_incident(self):
		self.act_as("Press Infrastructure Manager")
		self.assertFalse(can_reach_server("Server", self.server))

	def test_sre_reaches_server_of_acknowledged_or_investigating_incident(self):
		self.act_as("Press Infrastructure Manager")
		for status in ("Acknowledged", "Investigating"):
			with self.subTest(status=status):
				incident = create_test_incident(self.server, status=status)
				self.assertTrue(can_reach_server("Server", self.server))
				frappe.db.delete("Incident", {"name": incident.name})

	def test_sre_cannot_reach_server_of_incident_that_staff_created(self):
		self.act_as("Press Infrastructure Manager")
		create_test_incident(self.server, owner=str(frappe.session.user))
		self.assertFalse(can_reach_server("Server", self.server))

	def test_incident_server_cannot_be_changed_after_insert(self):
		incident = Incident("Incident", str(create_test_incident(self.server).name))
		incident.load_doc_before_save()
		incident.server = str(create_test_server(public=True).name)
		with self.assertRaisesRegex(frappe.CannotChangeConstantError, "Value cannot be changed"):
			incident.validate_set_only_once()

	def test_sre_cannot_reach_server_of_resolved_incident(self):
		create_test_incident(self.server, status="Resolved")
		self.act_as("Press Infrastructure Manager")
		self.assertFalse(can_reach_server("Server", self.server))

	def test_sre_cannot_reach_server_of_validating_incident(self):
		create_test_incident(self.server, status="Validating")
		self.act_as("Press Infrastructure Manager")
		self.assertFalse(can_reach_server("Server", self.server))

	def test_sre_cannot_reach_server_of_open_incident_older_than_six_hours(self):
		create_test_incident(self.server, status="Investigating", hours_ago=7)
		self.act_as("Press Infrastructure Manager")
		self.assertFalse(can_reach_server("Server", self.server))

	def test_sre_reaches_database_server_paired_with_incident_app_server(self):
		create_test_incident(self.server)
		self.act_as("Press Infrastructure Manager")
		self.assertTrue(can_reach_server("Database Server", self.paired_database_server))

	def test_sre_reaches_proxy_server_that_incident_names(self):
		create_test_incident(self.server, resource_type="Proxy Server", resource=self.proxy_server)
		self.act_as("Press Infrastructure Manager")
		self.assertTrue(can_reach_server("Proxy Server", self.proxy_server))

	def test_sre_cannot_reach_proxy_server_of_incident_that_names_no_proxy(self):
		create_test_incident(self.server)
		self.act_as("Press Infrastructure Manager")
		self.assertFalse(can_reach_server("Proxy Server", self.proxy_server))

	def test_sre_cannot_reach_database_server_that_incident_names_but_server_does_not_use(self):
		database_server = str(create_test_server().database_server)
		create_test_incident(self.server, resource_type="Database Server", resource=database_server)
		self.act_as("Press Infrastructure Manager")
		self.assertFalse(can_reach_server("Database Server", database_server))

	def test_sre_cannot_reach_other_shared_server_during_incident(self):
		create_test_incident(self.server)
		other_server = str(create_test_server(public=True).name)
		self.act_as("Press Infrastructure Manager")
		self.assertFalse(can_reach_server("Server", other_server))

	def test_employee_without_incident_role_cannot_reach_server_of_incident(self):
		create_test_incident(self.server)
		self.act_as("Press Marketplace Manager")
		self.assertFalse(can_reach_server("Server", self.server))

	def create_customer_bench(self) -> Bench:
		return create_test_bench(str(self.customer.user), server=self.server)

	def test_l2_runs_bench_shell_on_customer_bench_of_incident_server(self):
		bench = self.create_customer_bench()
		create_test_incident(self.server)
		self.act_as("Press Support Engineer")
		shell = BenchShell({"doctype": "Bench Shell", "bench": str(bench.name), "command": "ls"})
		shell.run_command()
		self.assertEqual(shell.output, "apps sites")

	def test_l2_cannot_run_bench_shell_on_customer_bench_after_incident_is_resolved(self):
		bench = self.create_customer_bench()
		create_test_incident(self.server, status="Resolved")
		self.act_as("Press Support Engineer")
		shell = BenchShell({"doctype": "Bench Shell", "bench": str(bench.name), "command": "ls"})
		with self.assertRaisesRegex(frappe.PermissionError, "Request Support Access with SSH"):
			shell.run_command()

	def test_l2_gets_bench_ssh_on_customer_group_with_bench_on_incident_server(self):
		bench = self.create_customer_bench()
		create_test_incident(self.server)
		self.act_as("Press Support Engineer")
		self.assertTrue(
			can_perform(
				"Release Group", str(bench.group), self.customer_team, ReleaseGroupActions.SSHAccess.value
			)
		)

	def test_l2_cannot_login_as_administrator_on_site_of_incident_server(self):
		site = create_test_site(bench=self.create_customer_bench().name, team=self.customer_team)
		create_test_incident(self.server)
		self.act_as("Press Support Engineer")
		self.assertFalse(
			can_perform("Site", str(site.name), self.customer_team, SiteActions.LoginAsAdmin.value)
		)

	def test_l2_cannot_run_bench_shell_on_public_group_bench_of_incident_server(self):
		bench = self.create_customer_bench()
		frappe.db.set_value("Release Group", bench.group, "public", 1)
		create_test_incident(self.server)
		self.act_as("Press Support Engineer")
		shell = BenchShell({"doctype": "Bench Shell", "bench": str(bench.name), "command": "ls"})
		with self.assertRaisesRegex(frappe.PermissionError, "Public bench groups need a System Manager"):
			shell.run_command()

	def test_l2_gets_no_bench_ssh_on_group_with_a_bench_outside_the_incident(self):
		bench = self.create_customer_bench()
		group = ReleaseGroup("Release Group", str(bench.group))
		# A second deploy of the group asks the agent for its image size
		with patch.object(ReleaseGroup, "check_app_server_storage", new=Mock()):
			create_test_bench(str(self.customer.user), group=group, server=str(create_test_server().name))
		create_test_incident(self.server)
		self.act_as("Press Support Engineer")
		self.assertFalse(
			can_perform(
				"Release Group", str(bench.group), self.customer_team, ReleaseGroupActions.SSHAccess.value
			)
		)

	def test_l2_opens_domains_tab_of_site_on_incident_server(self):
		site = create_test_site(bench=self.create_customer_bench().name, team=self.customer_team)
		create_test_incident(self.server)
		self.act_as("Press Support Engineer")
		self.assertTrue(can_perform("Site", str(site.name), self.customer_team, "Domains"))

	def test_support_l1_gets_no_bench_ssh_on_group_of_incident_server(self):
		bench = self.create_customer_bench()
		create_test_incident(self.server)
		self.act_as("Press Support L1")
		self.assertFalse(
			can_perform(
				"Release Group", str(bench.group), self.customer_team, ReleaseGroupActions.SSHAccess.value
			)
		)
