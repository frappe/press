# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.access import dashboard_access_rules
from press.access.support_access import has_support_access
from press.press.doctype.account_request.account_request import AccountRequest
from press.press.doctype.agent_job.test_agent_job import create_test_agent_job
from press.press.doctype.remote_file.remote_file import RemoteFile
from press.press.doctype.remote_file.test_remote_file import create_test_remote_file
from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.team.team import Team
from press.press.doctype.team.test_team import create_test_press_admin_team


def create_test_employee(role: str = "Press Marketplace Manager") -> Team:
	"""A Frappe Cloud employee: a system user with a team of their own.
	The default role is not System Manager, which is exempt from the employee checks."""
	team = create_test_press_admin_team()
	frappe.get_doc("User", team.user).add_roles(role)
	return team


@patch("frappe.sendmail", new=Mock())
@patch.object(Site, "get_login_sid", new=Mock(return_value="sid"))
class TestEmployeeConsent(FrappeTestCase):
	"""An employee switched into a customer team needs the consent of that team."""

	def setUp(self):
		super().setUp()
		self.site = create_test_site(team=create_test_press_admin_team().name)
		self.employee = create_test_employee()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def act_as_employee_in_site_team(self):
		frappe.set_user(self.employee.user)
		switched = patch("press.utils.get_current_team", return_value=self.site.team)
		switched.start()
		self.addCleanup(switched.stop)

	def grant(self, **permissions):
		access = frappe.get_doc(
			{
				"doctype": "Support Access",
				"requested_by": self.employee.user,
				"requested_team": self.employee.name,
				"reason": "Debugging",
				"resources": [{"document_type": "Site", "document_name": self.site.name}],
			}
		).insert(ignore_permissions=True)
		allowed_till = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=1)
		frappe.db.set_value(
			"Support Access",
			access.name,
			{"status": "Accepted", "access_allowed_till": allowed_till, **permissions},
		)

	def site_rules(self) -> frappe._dict:
		data = frappe._dict(doctype="Site", name=self.site.name, team=self.site.team)
		return dashboard_access_rules(data)

	def test_employee_switched_into_site_team_cannot_login_as_administrator_without_consent(self):
		self.act_as_employee_in_site_team()
		with self.assertRaisesRegex(frappe.PermissionError, "You do not have permission"):
			Site("Site", self.site.name).login()

	def test_employee_with_login_grant_can_login_as_administrator(self):
		self.grant(login_as_administrator=1)
		self.act_as_employee_in_site_team()
		self.assertEqual(Site("Site", self.site.name).login(), "sid")

	def test_employee_grant_without_login_permission_does_not_allow_login_as_administrator(self):
		self.grant(site_domains=1)
		self.act_as_employee_in_site_team()
		with self.assertRaisesRegex(frappe.PermissionError, "You do not have permission"):
			Site("Site", self.site.name).login()

	def test_employee_who_is_member_of_site_team_can_login_as_administrator_without_grant(self):
		team = frappe.get_doc("Team", self.site.team)
		team.append("team_members", {"user": self.employee.user})
		team.save()
		self.act_as_employee_in_site_team()
		self.assertEqual(Site("Site", self.site.name).login(), "sid")

	def test_member_employee_can_login_as_administrator_from_desk_without_switching_team(self):
		team = frappe.get_doc("Team", self.site.team)
		team.append("team_members", {"user": self.employee.user})
		team.save()
		frappe.set_user(self.employee.user)
		self.assertEqual(Site("Site", self.site.name).login(), "sid")

	def login_as_team(self):
		frappe.db.set_value("Site", self.site.name, "additional_system_user_created", 1)
		return Site("Site", self.site.name).login_as_team()

	def test_employee_switched_into_site_team_cannot_login_as_team_user_without_consent(self):
		self.act_as_employee_in_site_team()
		with self.assertRaisesRegex(frappe.PermissionError, "You do not have permission"):
			self.login_as_team()

	def test_system_manager_switched_into_site_team_can_login_as_team_user_without_grant(self):
		self.employee = create_test_employee("System Manager")
		self.act_as_employee_in_site_team()
		self.assertTrue(self.login_as_team().endswith("?sid=sid"))

	def test_employee_with_login_grant_logs_in_as_team_user_and_team_is_notified(self):
		self.grant(login_as_administrator=1)
		self.act_as_employee_in_site_team()
		self.assertTrue(self.login_as_team().endswith("?sid=sid"))
		notification = {"team": self.site.team, "type": "Resource Access", "reference_name": self.site.name}
		self.assertTrue(frappe.db.exists("Press Notification", notification))

	def test_team_owner_logs_in_as_team_user_without_grant(self):
		frappe.set_user(frappe.db.get_value("Team", self.site.team, "user"))
		self.assertTrue(self.login_as_team().endswith("?sid=sid"))
		activity = {"site": self.site.name, "action": "Login as Administrator"}
		self.assertEqual(
			frappe.db.get_value("Site Activity", activity, "reason"), "Logged in as the team user."
		)

	def test_administrator_can_login_as_administrator_without_grant(self):
		frappe.set_user("Administrator")
		self.assertEqual(Site("Site", self.site.name).login(), "sid")

	def test_system_manager_switched_into_site_team_can_login_as_administrator_without_grant(self):
		self.employee = create_test_employee("System Manager")
		self.act_as_employee_in_site_team()
		self.assertEqual(Site("Site", self.site.name).login(), "sid")

	def test_system_manager_dashboard_restricts_no_action_or_tab_without_consent(self):
		self.employee = create_test_employee("System Manager")
		self.act_as_employee_in_site_team()
		rules = self.site_rules()
		self.assertEqual(rules.actions_access, {})
		self.assertEqual(rules.tabs_access, {})

	def test_employee_dashboard_hides_login_and_domains_without_consent(self):
		self.act_as_employee_in_site_team()
		rules = self.site_rules()
		self.assertFalse(rules.actions_access["Login As Administrator"])
		self.assertFalse(rules.tabs_access["Domains"])

	def test_employee_dashboard_shows_login_and_domains_with_consent(self):
		self.grant(login_as_administrator=1, site_domains=1)
		self.act_as_employee_in_site_team()
		rules = self.site_rules()
		self.assertTrue(rules.actions_access["Login As Administrator"])
		self.assertTrue(rules.tabs_access["Domains"])

	def test_employee_dashboard_keeps_tabs_that_need_no_consent(self):
		self.act_as_employee_in_site_team()
		rules = self.site_rules()
		self.assertTrue(rules.tabs_access["Backups"])
		self.assertTrue(rules.tabs_access["Actions"])
		self.assertTrue(rules.actions_access["View in Desk"])

	def test_employee_reads_site_of_another_team_without_consent(self):
		self.act_as_employee_in_site_team()
		self.assertTrue(has_support_access("Site", self.site.name))

	def test_support_agent_dashboard_still_hides_backups_tab(self):
		agent = create_test_press_admin_team()
		frappe.get_doc("User", agent.user).add_roles("Press Support Agent")
		frappe.set_user(agent.user)
		self.assertFalse(self.site_rules().tabs_access["Backups"])


@patch("frappe.sendmail", new=Mock())
@patch.object(RemoteFile, "exists", new=Mock(return_value=True))
class TestEmployeeRestore(FrappeTestCase):
	"""Only those who can download a backup can restore a site from it."""

	def setUp(self):
		super().setUp()
		self.site = create_test_site(team=create_test_press_admin_team().name)
		self.backup = create_test_remote_file(site=self.site.name, file_path="backups/database.sql.gz")
		self.employee = create_test_employee()
		self.job = create_test_agent_job()
		restore_job = patch("press.agent.Agent.restore_site", return_value=self.job)
		restore_job.start()
		self.addCleanup(restore_job.stop)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def restore(self, site) -> str:
		site.db_set("remote_database_file", self.backup.name)
		frappe.set_user(self.employee.user)
		return Site("Site", site.name).restore_site()

	def test_employee_outside_site_team_cannot_restore_site_from_its_own_backup(self):
		with self.assertRaisesRegex(frappe.PermissionError, "Employees cannot restore or copy a site"):
			self.restore(self.site)

	def test_employee_cannot_restore_their_own_site_from_a_customer_backup(self):
		own_site = create_test_site(team=self.employee.name)
		with self.assertRaisesRegex(frappe.PermissionError, "Employees cannot download the backups"):
			self.restore(own_site)

	def test_employee_who_is_member_of_site_team_can_restore_site(self):
		team = frappe.get_doc("Team", self.site.team)
		team.append("team_members", {"user": self.employee.user})
		team.save()
		self.assertEqual(self.restore(self.site), self.job.name)

	def test_administrator_can_restore_site_of_any_team(self):
		self.site.db_set("remote_database_file", self.backup.name)
		self.assertEqual(Site("Site", self.site.name).restore_site(), self.job.name)

	def test_system_manager_outside_site_team_can_restore_site_from_its_backup(self):
		self.employee = create_test_employee("System Manager")
		self.assertEqual(self.restore(self.site), self.job.name)

	def test_system_manager_can_restore_their_own_site_from_a_customer_backup(self):
		self.employee = create_test_employee("System Manager")
		own_site = create_test_site(team=self.employee.name)
		self.assertEqual(self.restore(own_site), self.job.name)

	def test_employee_outside_site_team_cannot_restore_site_from_physical_backup(self):
		frappe.set_user(self.employee.user)
		with self.assertRaisesRegex(frappe.PermissionError, "Employees cannot restore or copy a site"):
			Site("Site", self.site.name).restore_site_from_physical_backup("some-backup")

	def create_site_from_backup(self):
		bench = create_test_bench()
		frappe.set_user(self.employee.user)
		return create_test_site(
			bench=bench.name, team=self.employee.name, remote_database_file=self.backup.name
		)

	def test_employee_cannot_create_a_site_in_desk_from_a_customer_backup(self):
		with self.assertRaisesRegex(frappe.PermissionError, "Employees cannot download the backups"):
			self.create_site_from_backup()

	def test_system_manager_can_create_a_site_in_desk_from_a_customer_backup(self):
		self.employee = create_test_employee("System Manager")
		self.employee.db_set("free_account", 1)
		with patch("press.agent.Agent.new_site_from_backup", return_value=self.job):
			site = self.create_site_from_backup()
		self.assertEqual(site.remote_database_file, self.backup.name)

	def test_employee_who_is_member_of_backup_team_can_create_a_site_from_its_backup(self):
		team = frappe.get_doc("Team", self.site.team)
		team.append("team_members", {"user": self.employee.user})
		team.save()
		self.employee.db_set("free_account", 1)
		with patch("press.agent.Agent.new_site_from_backup", return_value=self.job):
			site = self.create_site_from_backup()
		self.assertEqual(site.remote_database_file, self.backup.name)

	def test_employee_can_save_existing_site_that_already_carries_a_customer_backup(self):
		self.site.db_set("remote_database_file", self.backup.name)
		frappe.set_user(self.employee.user)
		site = Site("Site", self.site.name)
		site.timezone = "Asia/Kolkata"
		site.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Site", site.name, "timezone"), "Asia/Kolkata")

	def test_employee_cannot_replicate_a_customer_site(self):
		frappe.set_user(self.employee.user)
		replication = frappe.get_doc(
			{"doctype": "Site Replication", "site": self.site.name, "subdomain": "copy"}
		)
		with self.assertRaisesRegex(frappe.PermissionError, "Employees cannot restore or copy a site"):
			replication.insert(ignore_permissions=True)

	def test_system_manager_passes_the_backup_check_when_replicating_a_customer_site(self):
		self.employee = create_test_employee("System Manager")
		frappe.set_user(self.employee.user)
		replication = frappe.get_doc(
			{"doctype": "Site Replication", "site": self.site.name, "subdomain": "copy"}
		)
		# Insert would start the copy through the agent; the check lives in validate.
		replication.validate()


@patch.object(AccountRequest, "send_verification_email", new=Mock())
class TestEmployeeTeamInvite(FrappeTestCase):
	"""Only the team and its member employees can invite people into it."""

	def setUp(self):
		super().setUp()
		self.team = create_test_press_admin_team()
		self.employee = create_test_employee()
		self.email = frappe.mock("email")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def invite(self, user: str):
		frappe.set_user(user)
		Team("Team", self.team.name).invite_team_member(self.email)

	def assert_invited(self):
		invite = {"team": self.team.name, "email": self.email, "invited_by": ("is", "set")}
		self.assertTrue(frappe.db.exists("Account Request", invite))

	def test_employee_outside_team_cannot_invite_members_to_it(self):
		with self.assertRaisesRegex(frappe.PermissionError, "Employees cannot invite members"):
			self.invite(self.employee.user)
		self.assertFalse(frappe.db.exists("Account Request", {"email": self.email}))

	def test_employee_who_is_member_of_team_can_invite_members(self):
		self.team.append("team_members", {"user": self.employee.user})
		self.team.save()
		self.invite(self.employee.user)
		self.assert_invited()

	def test_system_manager_outside_team_can_invite_members_to_it(self):
		self.invite(create_test_employee("System Manager").user)
		self.assert_invited()

	def test_team_owner_can_invite_members(self):
		self.invite(self.team.user)
		self.assert_invited()
