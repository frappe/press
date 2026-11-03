# Copyright (c) 2024, Frappe and Contributors
# See license.txt

from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.press_role.test_press_role import create_permission_role
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.team.test_team import create_test_press_admin_team, create_test_team
from press.press.doctype.team.test_team_members import user_context
from press.press.doctype.team_change.team_change import TeamChange, confirm_transfer


@patch.object(AppSource, "create_release", create_test_app_release)
@patch.object(frappe, "sendmail", new=Mock())
class TestTeamChange(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.from_team = create_test_team()
		self.to_team = create_test_team()
		self.to_team.append("team_members", {"user": self.to_team.user})
		self.to_team.servers_enabled = 1
		self.to_team.save(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_site_transfer_request_expires_48_hours_after_it_is_sent(self):
		site = create_test_site(team=self.from_team.name)
		team_change = self._request(site)
		hours_left = (team_change.expires_on - now_datetime()).total_seconds() / 3600
		self.assertAlmostEqual(hours_left, 48, delta=0.1)

	def test_second_site_transfer_request_is_blocked_while_the_first_is_pending(self):
		site = create_test_site(team=self.from_team.name)
		self._request(site)
		with self.assertRaises(frappe.ValidationError) as cm:
			self._request(site)
		self.assertIn("was already sent to", str(cm.exception))

	def test_new_site_transfer_request_is_allowed_after_the_old_one_expires(self):
		site = create_test_site(team=self.from_team.name)
		self._expire(self._request(site))
		self.assertTrue(self._request(site).name)

	def test_site_transfer_request_rejected_for_member_without_admin_access(self):
		site = create_test_site(team=self.from_team.name)
		member = create_test_press_admin_team().user
		self.from_team.append("team_members", {"user": member})
		self.from_team.save(ignore_permissions=True)
		site.flags.ignore_permissions = False  # left on by insert, it would skip the admin check

		with user_context(member), self.assertRaises(frappe.PermissionError) as cm:
			site.send_change_team_request(self.to_team.user, "")
		self.assertIn("Only team admin", str(cm.exception))

	def test_confirm_link_refuses_an_expired_request_and_keeps_the_owner(self):
		site = create_test_site(team=self.from_team.name)
		team_change = self._expire(self._request(site))
		self._confirm(team_change)
		self.assertEqual(frappe.db.get_value("Site", site.name, "team"), self.from_team.name)
		self.assertIn("expired", frappe.local.message_title + frappe.local.response.get("message", ""))

	def test_confirm_link_refuses_a_request_that_was_already_used(self):
		site = create_test_site(team=self.from_team.name)
		team_change = self._request(site)
		self._confirm(team_change)
		self._confirm(team_change)
		self.assertIn("already been used", frappe.local.response.get("message", ""))

	def test_confirm_site_transfer_moves_site_records_and_removes_role_permissions(self):
		site = create_test_site(team=self.from_team.name)
		self._add_role_permission(site=site.name)
		self._confirm(self._request(site))

		self.assertEqual(frappe.db.get_value("Site", site.name, "team"), self.to_team.name)
		self.assertFalse(frappe.db.exists("Press Role Permission", {"site": site.name}))

	def test_confirm_bench_transfer_moves_group_and_removes_role_permissions(self):
		group = create_test_release_group([create_test_app()], user=self.from_team.user)
		self._add_role_permission(release_group=group.name)
		self._confirm(self._request(group))

		self.assertEqual(frappe.db.get_value("Release Group", group.name, "team"), self.to_team.name)
		self.assertFalse(frappe.db.exists("Press Role Permission", {"release_group": group.name}))

	def test_server_transfer_request_blocked_when_receiving_team_cannot_have_servers(self):
		server = create_test_server(team=self.from_team.name)
		self.to_team.db_set("servers_enabled", 0)
		with self.assertRaises(frappe.ValidationError) as cm:
			self._request(server)
		self.assertIn("can't have dedicated servers", str(cm.exception))

	def test_server_transfer_request_blocked_for_self_hosted_server(self):
		server = create_test_server(team=self.from_team.name, is_self_hosted=True)
		with self.assertRaises(frappe.ValidationError) as cm:
			self._request(server)
		self.assertIn("Self-hosted servers can't be transferred", str(cm.exception))

	def test_server_transfer_request_blocked_for_server_with_managed_database(self):
		server = create_test_server(team=self.from_team.name)
		server.db_set({"is_managed_database": 1, "database_server": ""})
		with self.assertRaises(frappe.ValidationError) as cm:
			self._request(server)
		self.assertIn("Servers with a managed database can't be transferred", str(cm.exception))

	def test_server_transfer_request_blocked_when_bench_group_also_runs_on_another_server(self):
		server = create_test_server(team=self.from_team.name)
		other_server = create_test_server(team=self.from_team.name)
		create_test_release_group(
			[create_test_app()], user=self.from_team.user, servers=[server.name, other_server.name]
		)
		with self.assertRaises(frappe.ValidationError) as cm:
			self._request(server)
		self.assertIn("raise a support ticket", str(cm.exception))

	def test_server_transfer_request_blocked_when_another_teams_site_is_on_the_server(self):
		server, _, site = self._server_with_group_and_site()
		create_test_site(team=create_test_team().name, bench=site.bench)
		with self.assertRaises(frappe.ValidationError) as cm:
			self._request(server)
		self.assertIn("Sites of other teams are on this server", str(cm.exception))

	def test_server_transfer_request_blocked_while_a_server_operation_is_running(self):
		server = create_test_server(team=self.from_team.name)
		self._add_running_job("Press Job", server.name, job_type="Resize Server")
		with self.assertRaises(frappe.ValidationError) as cm:
			self._request(server)
		self.assertIn("A server operation (like a resize or snapshot) is running", str(cm.exception))

	def test_server_transfer_request_not_blocked_by_running_site_jobs(self):
		server, _, site = self._server_with_group_and_site()
		self._add_running_job("Agent Job", server.name, job_type="Backup Site", site=site.name)
		self.assertEqual(self._request(server).document_name, server.name)

	def test_server_transfer_request_not_blocked_by_server_operation_stuck_for_over_a_day(self):
		server = create_test_server(team=self.from_team.name)
		self._add_running_job("Press Job", server.name, hours_ago=25, job_type="Resize Server")
		self.assertEqual(self._request(server).document_name, server.name)

	def test_confirm_server_transfer_moves_server_database_server_group_and_site(self):
		server, group, site = self._server_with_group_and_site()
		self._add_role_permission(server=server.name)
		self._confirm(self._request(server))

		for doctype, name in (
			("Server", server.name),
			("Database Server", server.database_server),
			("Virtual Machine", server.virtual_machine),
			("Release Group", group.name),
			("Site", site.name),
		):
			self.assertEqual(frappe.db.get_value(doctype, name, "team"), self.to_team.name, doctype)
		self.assertFalse(frappe.db.exists("Press Role Permission", {"server": server.name}))

	def test_confirm_server_transfer_rechecks_blockers_and_moves_nothing_when_one_appears(self):
		server, _, site = self._server_with_group_and_site()
		team_change = self._request(server)
		self.to_team.db_set("servers_enabled", 0)
		self._confirm(team_change)

		self.assertEqual(frappe.db.get_value("Server", server.name, "team"), self.from_team.name)
		self.assertEqual(frappe.db.get_value("Site", site.name, "team"), self.from_team.name)
		self.assertIn("can't have dedicated servers", frappe.local.response.get("message", ""))

	def test_press_user_cannot_insert_a_completed_team_change_to_take_another_teams_site(self):
		site = create_test_site(team=self.from_team.name)
		taker = create_test_press_admin_team()
		with user_context(taker.user), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "Team Change",
					"document_type": "Site",
					"document_name": site.name,
					"from_team": self.from_team.name,
					"to_team": taker.name,
					"transfer_completed": 1,
				}
			).insert()
		self.assertEqual(frappe.db.get_value("Site", site.name, "team"), self.from_team.name)

	def test_site_transfer_request_and_confirm_work_for_users_with_only_the_press_user_role(self):
		sender = create_test_press_admin_team()
		receiver = create_test_press_admin_team()
		receiver.append("team_members", {"user": receiver.user})
		receiver.save(ignore_permissions=True)
		site = create_test_site(team=sender.name)

		with user_context(sender.user):
			site.send_change_team_request(receiver.user, "Handing over to the client")
		team_change = frappe.get_last_doc("Team Change", {"document_name": site.name})
		self._confirm(team_change, receiver.user)

		self.assertEqual(frappe.db.get_value("Site", site.name, "team"), receiver.name)

	def _request(self, doc) -> TeamChange:
		with user_context(self.from_team.user):
			doc.send_change_team_request(self.to_team.user, "test")
		return frappe.get_last_doc("Team Change", {"document_name": doc.name})

	def _confirm(self, team_change: TeamChange, user: str | None = None):
		frappe.local.response = frappe._dict()
		frappe.local.message_title = ""
		# Commit and rollback would end the test's own transaction
		with (
			user_context(user or self.to_team.user),
			patch.object(frappe, "respond_as_web_page", self._capture_page),
			patch.object(frappe.db, "commit", new=Mock()),
			patch.object(frappe.db, "rollback", new=Mock()),
		):
			confirm_transfer(team_change.key, team_change.document_type)

	@staticmethod
	def _capture_page(title, html, **kwargs):
		frappe.local.message_title = str(title)
		frappe.local.response["message"] = str(html)

	def _expire(self, team_change: TeamChange) -> TeamChange:
		team_change.db_set("expires_on", add_to_date(now_datetime(), hours=-1))
		return team_change

	def _add_role_permission(self, **document):
		role = create_permission_role(self.from_team.name)
		frappe.get_doc(
			{"doctype": "Press Role Permission", "team": self.from_team.name, "role": role.name, **document}
		).insert(ignore_permissions=True)

	def _server_with_group_and_site(self):
		server = create_test_server(team=self.from_team.name)
		group = create_test_release_group(
			[create_test_app()], user=self.from_team.user, servers=[server.name]
		)
		bench = create_test_bench(group=group, server=server.name)
		site = create_test_site(team=self.from_team.name, bench=bench.name)
		return server, group, site

	@staticmethod
	def _add_running_job(doctype: str, server: str, hours_ago: int = 0, **fields) -> str:
		job = frappe.get_doc(
			{"doctype": doctype, "server_type": "Server", "server": server, "status": "Running", **fields}
		)
		job.set_new_name()
		job.db_insert()  # skip hooks, which would start running the job
		frappe.db.set_value(
			doctype,
			job.name,
			"creation",
			add_to_date(now_datetime(), hours=-hours_ago),
			update_modified=False,
		)
		return job.name
