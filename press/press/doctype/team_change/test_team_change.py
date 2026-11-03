# Copyright (c) 2024, Frappe and Contributors
# See license.txt

from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.database_server.test_database_server import create_test_database_server
from press.press.doctype.invoice.invoice import Invoice
from press.press.doctype.press_role.test_press_role import create_permission_role
from press.press.doctype.release_group.release_group import ReleaseGroup
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.server_plan.test_server_plan import create_test_server_plan
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.subscription.test_subscription import create_test_subscription
from press.press.doctype.team.test_team import add_card, create_test_press_admin_team, create_test_team
from press.press.doctype.team.test_team_members import user_context
from press.press.doctype.team_change.balance import unallocated_credit_by_source
from press.press.doctype.team_change.team_change import TeamChange, confirm_transfer


def create_team_change(
	from_team: str,
	to_team: str,
	resources: list[tuple[str, str]] | None = None,
	transfer_type: str = "Specific Resources",
	**fields,
) -> TeamChange:
	"""A desk transfer, as a System Manager makes it"""
	return frappe.get_doc(
		{
			"doctype": "Team Change",
			"transfer_type": transfer_type,
			"from_team": from_team,
			"to_team": to_team,
			"reason": "Customer moved the account",
			"resources": [
				{"document_type": doctype, "document_name": name} for doctype, name in resources or []
			],
			**fields,
		}
	).insert()


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

	def test_confirm_bench_transfer_moves_the_benches_of_the_group_too(self):
		server, group, _ = self._server_with_group_and_site()
		bench = frappe.get_last_doc("Bench", {"group": group.name, "server": server.name})
		self._confirm(self._request(group))

		self.assertEqual(frappe.db.get_value("Bench", bench.name, "team"), self.to_team.name)

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


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
@patch.object(Invoice, "create_invoice_on_frappeio", new=Mock())
class TestAdminTeamChange(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.old_team = create_test_press_admin_team()
		self.new_team = create_test_press_admin_team()
		self.new_team.db_set("servers_enabled", 1)
		self.database_server = create_test_database_server()
		self.server = create_test_server(database_server=self.database_server.name, team=self.old_team.name)
		frappe.db.set_value("Database Server", self.database_server.name, "team", self.old_team.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def create_group_on_server(self):
		group = create_test_release_group(
			[create_test_app()], user=self.old_team.user, servers=[self.server.name]
		)
		bench = create_test_bench(group=group, server=self.server.name)
		return group, bench

	def create_server_snapshot(self) -> str:
		"""Inserted straight into the db, so no cloud snapshot is taken"""
		snapshot = frappe.get_doc(
			doctype="Server Snapshot",
			app_server=self.server.name,
			database_server=self.database_server.name,
			team=self.old_team.name,
			status="Completed",
			provider="AWS EC2",
			cluster=self.server.cluster,
		)
		snapshot.db_insert()
		return snapshot.name

	def team_of(self, doctype: str, name: str) -> str:
		return frappe.db.get_value(doctype, name, "team")

	def balance_of(self, team: str) -> float:
		return frappe.get_doc("Team", team).get_balance()

	def create_draft_invoice_with_usage(self, team: str, amount: float) -> str:
		invoice = frappe.get_doc(
			doctype="Invoice", team=team, period_start=frappe.utils.today(), type="Subscription"
		).insert()
		frappe.get_doc(doctype="Usage Record", team=team, amount=amount).insert().submit()
		return invoice.name

	def transfer_server(self):
		create_team_change(self.old_team.name, self.new_team.name, [("Server", self.server.name)]).transfer()

	def full_account_transfer(self, **kwargs) -> TeamChange:
		return create_team_change(
			self.old_team.name, self.new_team.name, transfer_type="Full Account", **kwargs
		)

	def fetched_rows(self, team_change: TeamChange) -> list[tuple[str, str]]:
		team_change.fetch_resources()
		return [(row.document_type, row.document_name) for row in team_change.resources]

	# Specific resources

	def test_server_transfer_moves_server_database_server_virtual_machines_and_subscriptions(self):
		plan = create_test_server_plan()
		subscription = create_test_subscription(
			self.server.name, plan.name, self.old_team.name, "Server", "Server Plan"
		)

		self.transfer_server()

		self.assertEqual(self.team_of("Server", self.server.name), self.new_team.name)
		self.assertEqual(self.team_of("Database Server", self.database_server.name), self.new_team.name)
		self.assertEqual(self.team_of("Virtual Machine", self.server.virtual_machine), self.new_team.name)
		self.assertEqual(
			self.team_of("Virtual Machine", self.database_server.virtual_machine), self.new_team.name
		)
		self.assertEqual(self.team_of("Subscription", subscription.name), self.new_team.name)

	def test_server_transfer_moves_its_snapshots_and_the_snapshot_billing_subscriptions(self):
		snapshot = self.create_server_snapshot()
		plan = frappe.get_doc(
			doctype="Server Snapshot Plan",
			name="Snapshot plan for the team transfer test",
			provider="AWS EC2",
			price_inr=10,
			enabled=1,
		).insert()
		subscription = create_test_subscription(
			snapshot, plan.name, self.old_team.name, "Server Snapshot", "Server Snapshot Plan"
		)

		self.transfer_server()

		self.assertEqual(self.team_of("Server Snapshot", snapshot), self.new_team.name)
		self.assertEqual(self.team_of("Subscription", subscription.name), self.new_team.name)

	def test_server_transfer_skips_the_dashboard_blockers_and_moves_the_autoscale_secondary(self):
		secondary = create_test_server(team=self.old_team.name)
		frappe.db.set_value("Server", self.server.name, "secondary_server", secondary.name)

		self.transfer_server()

		self.assertEqual(self.team_of("Server", self.server.name), self.new_team.name)
		self.assertEqual(self.team_of("Server", secondary.name), self.new_team.name)

	def test_server_transfer_moves_its_on_prem_failover_config(self):
		failover = frappe.get_doc(
			doctype="On-Prem Failover",
			app_server=self.server.name,
			database_server=self.database_server.name,
			team=self.old_team.name,
			cluster=self.server.cluster,
		)
		failover.set_new_name()
		failover.db_insert()  # skip hooks, which would set up the wireguard network

		self.transfer_server()

		self.assertEqual(self.team_of("On-Prem Failover", failover.name), self.new_team.name)

	def test_server_transfer_takes_the_source_teams_groups_benches_and_sites_on_it(self):
		group, bench = self.create_group_on_server()
		own_site = create_test_site(bench=bench.name, team=self.old_team.name)
		archived_site = create_test_site(bench=bench.name, team=self.old_team.name)
		frappe.db.set_value("Site", archived_site.name, "status", "Archived")
		other_team_site = create_test_site(bench=bench.name, team=create_test_team().name)
		other_team = self.team_of("Site", other_team_site.name)

		self.transfer_server()

		self.assertEqual(self.team_of("Release Group", group.name), self.new_team.name)
		self.assertEqual(self.team_of("Bench", bench.name), self.new_team.name)
		self.assertEqual(self.team_of("Site", own_site.name), self.new_team.name)
		self.assertEqual(self.team_of("Site", archived_site.name), self.old_team.name)
		self.assertEqual(self.team_of("Site", other_team_site.name), other_team)

	# The second bench of a group asks the agent for the last image size
	@patch.object(ReleaseGroup, "check_app_server_storage", new=Mock())
	def test_server_transfer_leaves_a_group_that_also_runs_on_a_kept_server_with_the_old_team(self):
		kept_server = create_test_server(team=self.old_team.name)
		group = create_test_release_group(
			[create_test_app()], user=self.old_team.user, servers=[self.server.name, kept_server.name]
		)
		bench_on_moved_server = create_test_bench(group=group, server=self.server.name)
		bench_on_kept_server = create_test_bench(group=group, server=kept_server.name)
		site_on_moved_server = create_test_site(bench=bench_on_moved_server.name, team=self.old_team.name)

		self.assertIn(("Release Group", group.name), self.fetched_rows(self.full_account_transfer()))
		self.transfer_server()

		self.assertEqual(self.team_of("Server", self.server.name), self.new_team.name)
		self.assertEqual(self.team_of("Site", site_on_moved_server.name), self.new_team.name)
		self.assertEqual(self.team_of("Release Group", group.name), self.old_team.name)
		self.assertEqual(self.team_of("Bench", bench_on_moved_server.name), self.old_team.name)
		self.assertEqual(self.team_of("Bench", bench_on_kept_server.name), self.old_team.name)

	def test_specific_transfer_moves_several_resources_of_different_types_at_once(self):
		self.create_group_on_server()
		site_elsewhere = create_test_site(team=self.old_team.name)
		kept_site = create_test_site(team=self.old_team.name)

		create_team_change(
			self.old_team.name,
			self.new_team.name,
			[("Server", self.server.name), ("Site", site_elsewhere.name)],
		).transfer()

		self.assertEqual(self.team_of("Server", self.server.name), self.new_team.name)
		self.assertEqual(self.team_of("Site", site_elsewhere.name), self.new_team.name)
		self.assertEqual(self.team_of("Site", kept_site.name), self.old_team.name)

	def test_release_group_transfer_moves_its_benches_but_not_its_deploy_history(self):
		group, bench = self.create_group_on_server()

		create_team_change(self.old_team.name, self.new_team.name, [("Release Group", group.name)]).transfer()

		self.assertEqual(self.team_of("Release Group", group.name), self.new_team.name)
		self.assertEqual(self.team_of("Bench", bench.name), self.new_team.name)
		self.assertEqual(self.team_of("Deploy Candidate", bench.candidate), self.old_team.name)

	def test_desk_transfer_gets_no_confirmation_key_or_expiry_and_records_who_ran_it(self):
		team_change = create_team_change(
			self.old_team.name, self.new_team.name, [("Server", self.server.name)]
		)
		team_change.transfer()

		self.assertFalse(team_change.key)
		self.assertFalse(team_change.expires_on)
		self.assertEqual(team_change.transferred_by, "Administrator")
		self.assertTrue(team_change.transferred_on)

	@patch.object(frappe, "sendmail", new=Mock())
	def test_desk_transfer_button_is_refused_on_a_dashboard_request(self):
		site = create_test_site(team=self.old_team.name)
		with user_context(self.old_team.user):
			site.send_change_team_request(self.new_team.user, "")
		request = frappe.get_last_doc("Team Change", {"document_name": site.name})

		with self.assertRaisesRegex(frappe.ValidationError, "receiving team accepts from the emailed link"):
			request.transfer()
		self.assertEqual(self.team_of("Site", site.name), self.old_team.name)

	def test_resource_of_another_team_is_rejected(self):
		_, bench = self.create_group_on_server()
		other_site = create_test_site(bench=bench.name, team=create_test_team().name)

		with self.assertRaisesRegex(frappe.ValidationError, "isn't owned by the source team"):
			create_team_change(self.old_team.name, self.new_team.name, [("Site", other_site.name)])

	def test_same_resource_listed_twice_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "listed more than once"):
			create_team_change(
				self.old_team.name,
				self.new_team.name,
				[("Server", self.server.name), ("Server", self.server.name)],
			)

	def test_transfer_with_no_resources_is_rejected(self):
		team_change = create_team_change(self.old_team.name, self.new_team.name)

		with self.assertRaisesRegex(frappe.ValidationError, "Add at least one resource"):
			team_change.transfer()

	def test_transfer_to_the_source_team_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "source team and the target team are the same"):
			create_team_change(self.old_team.name, self.old_team.name, [("Server", self.server.name)])

	def test_transfer_to_a_disabled_team_is_refused_when_the_team_change_is_saved(self):
		self.new_team.db_set("enabled", 0)

		with self.assertRaisesRegex(frappe.ValidationError, f"The team {self.new_team.name} is disabled"):
			self.transfer_server()
		self.assertEqual(self.team_of("Server", self.server.name), self.old_team.name)

	def test_server_row_is_refused_when_the_target_team_cannot_have_servers(self):
		self.new_team.db_set("servers_enabled", 0)

		with self.assertRaisesRegex(frappe.ValidationError, "Turn on Servers Enabled for the team"):
			self.transfer_server()
		self.assertEqual(self.team_of("Server", self.server.name), self.old_team.name)

	def test_public_server_is_refused_when_the_team_change_is_saved(self):
		frappe.db.set_value("Server", self.server.name, "public", 1)

		with self.assertRaisesRegex(frappe.ValidationError, "isn't public or self hosted"):
			create_team_change(self.old_team.name, self.new_team.name, [("Server", self.server.name)])
		self.assertEqual(self.team_of("Server", self.server.name), self.old_team.name)

	def test_archived_site_is_refused_when_the_team_change_is_saved(self):
		_, bench = self.create_group_on_server()
		site = create_test_site(bench=bench.name, team=self.old_team.name)
		frappe.db.set_value("Site", site.name, "status", "Archived")

		with self.assertRaisesRegex(frappe.ValidationError, "An archived site can't be transferred"):
			create_team_change(self.old_team.name, self.new_team.name, [("Site", site.name)])

	def test_resource_picker_offers_only_movable_resources_of_the_source_team(self):
		from press.press.doctype.team_change.transfer import transferable_doctypes, transferable_resources

		broken_server = create_test_server(team=self.old_team.name)
		frappe.db.set_value("Server", broken_server.name, "status", "Broken")
		other_team_server = create_test_server(team=self.new_team.name)

		offered = transferable_resources("Server", "", "name", 0, 50, {"team": self.old_team.name})

		offered_names = [name for (name,) in offered]
		self.assertIn(self.server.name, offered_names)
		self.assertNotIn(broken_server.name, offered_names)
		self.assertNotIn(other_team_server.name, offered_names)
		self.assertEqual(
			transferable_doctypes("DocType", "", "name", 0, 20, {}),
			[["Server"], ["Release Group"], ["Site"]],
		)

	def test_resource_picker_is_refused_to_dashboard_users(self):
		from press.press.doctype.team_change.transfer import transferable_resources

		frappe.set_user(self.new_team.user)

		# frappe.only_for lets every user through while tests run
		with patch.dict(frappe.local.flags, {"in_test": False}), self.assertRaises(frappe.PermissionError):
			transferable_resources("Server", "", "name", 0, 50, {"team": self.old_team.name})

	def test_completed_transfer_cannot_be_saved_again(self):
		team_change = create_team_change(
			self.old_team.name, self.new_team.name, [("Server", self.server.name)]
		)
		team_change.transfer()

		team_change.reason = "Edited after the transfer"
		with self.assertRaisesRegex(frappe.ValidationError, "already complete"):
			team_change.save()

	def test_dashboard_user_cannot_run_the_admin_transfer(self):
		team_change = create_team_change(
			self.old_team.name, self.new_team.name, [("Server", self.server.name)]
		)
		frappe.set_user(self.old_team.user)

		with patch.dict(frappe.local.flags, {"in_test": False}), self.assertRaises(frappe.PermissionError):
			team_change.transfer()
		frappe.set_user("Administrator")
		self.assertEqual(self.team_of("Server", self.server.name), self.old_team.name)

	# Full account

	def test_full_account_fetch_leaves_out_what_moves_with_a_listed_server_and_moves_only_included_rows(
		self,
	):
		group, bench = self.create_group_on_server()
		moved_site = create_test_site(bench=bench.name, team=self.old_team.name)
		# On a server the old team doesn't own, so only its row decides whether it moves
		kept_site = create_test_site(team=self.old_team.name)
		team_change = self.full_account_transfer()

		self.assertCountEqual(
			self.fetched_rows(team_change), [("Server", self.server.name), ("Site", kept_site.name)]
		)
		for row in team_change.resources:
			row.include = row.document_name != kept_site.name
		team_change.transfer()

		self.assertEqual(self.team_of("Server", self.server.name), self.new_team.name)
		self.assertEqual(self.team_of("Database Server", self.database_server.name), self.new_team.name)
		self.assertEqual(self.team_of("Release Group", group.name), self.new_team.name)
		self.assertEqual(self.team_of("Bench", bench.name), self.new_team.name)
		self.assertEqual(self.team_of("Site", moved_site.name), self.new_team.name)
		self.assertEqual(self.team_of("Site", kept_site.name), self.old_team.name)

	def test_fetch_resources_is_only_for_a_full_account_transfer(self):
		team_change = create_team_change(self.old_team.name, self.new_team.name)

		with self.assertRaisesRegex(frappe.ValidationError, "Fetch Resources is for a full account transfer"):
			team_change.fetch_resources()

	def test_full_account_fetch_leaves_out_a_server_that_is_not_active_and_refuses_it_as_a_row(self):
		frappe.db.set_value("Server", self.server.name, "status", "Broken")
		team_change = self.full_account_transfer()

		team_change.fetch_resources()
		self.assertNotIn(self.server.name, [row.document_name for row in team_change.resources])

		team_change.append("resources", {"document_type": "Server", "document_name": self.server.name})
		with self.assertRaisesRegex(frappe.ValidationError, "Only an Active server"):
			team_change.save()
		self.assertEqual(self.team_of("Server", self.server.name), self.old_team.name)

	def test_balance_can_be_moved_only_in_a_full_account_transfer(self):
		with self.assertRaisesRegex(frappe.ValidationError, "only in a full account transfer"):
			create_team_change(
				self.old_team.name, self.new_team.name, [("Server", self.server.name)], move_balance=True
			)

	def test_full_account_without_balance_option_leaves_credit_and_invoices_with_the_old_team(self):
		self.old_team.allocate_credit_amount(500, source="Prepaid Credits")
		invoice = self.create_draft_invoice_with_usage(self.old_team.name, 200)

		self.full_account_transfer(resources=[("Server", self.server.name)]).transfer()

		self.assertEqual(self.balance_of(self.old_team.name), 500)
		self.assertEqual(self.balance_of(self.new_team.name), 0)
		self.assertEqual(frappe.db.get_value("Invoice", invoice, "status"), "Draft")

	def test_balance_move_keeps_the_source_of_each_credit(self):
		self.old_team.allocate_credit_amount(500, source="Prepaid Credits")
		self.old_team.allocate_credit_amount(100, source="Free Credits")
		team_change = self.full_account_transfer(move_balance=True)

		team_change.transfer()

		self.assertEqual(self.balance_of(self.old_team.name), 0)
		self.assertEqual(self.balance_of(self.new_team.name), 600)
		self.assertEqual(
			unallocated_credit_by_source(self.new_team.name), {"Prepaid Credits": 500, "Free Credits": 100}
		)
		self.assertEqual(frappe.db.get_value("Team Change", team_change.name, "balance_moved"), 600)

	def test_balance_move_pays_the_current_invoice_first_and_moves_only_the_rest(self):
		self.old_team.allocate_credit_amount(500, source="Prepaid Credits")
		invoice = self.create_draft_invoice_with_usage(self.old_team.name, 200)

		self.full_account_transfer(move_balance=True).transfer()

		status, period_end = frappe.db.get_value("Invoice", invoice, ("status", "period_end"))
		self.assertEqual(status, "Paid")
		self.assertEqual(period_end, frappe.utils.getdate())
		self.assertEqual(self.balance_of(self.old_team.name), 0)
		self.assertEqual(self.balance_of(self.new_team.name), 300)

	def test_balance_move_pays_an_unpaid_invoice_before_moving_credit(self):
		invoice = Invoice("Invoice", self.create_draft_invoice_with_usage(self.old_team.name, 200))
		invoice.finalize_invoice()
		self.assertEqual(invoice.status, "Unpaid")
		self.old_team.allocate_credit_amount(500, source="Prepaid Credits")

		self.full_account_transfer(move_balance=True).transfer()

		self.assertEqual(frappe.db.get_value("Invoice", invoice.name, "status"), "Paid")
		self.assertEqual(self.balance_of(self.new_team.name), 300)

	def test_balance_move_leaves_an_unpaid_invoice_with_a_shortfall_unpaid_with_the_credit_applied(self):
		invoice = Invoice("Invoice", self.create_draft_invoice_with_usage(self.old_team.name, 200))
		invoice.finalize_invoice()
		self.assertEqual(invoice.status, "Unpaid")
		self.old_team.allocate_credit_amount(80, source="Prepaid Credits")

		self.full_account_transfer(move_balance=True).transfer()

		status, applied, due = frappe.db.get_value(
			"Invoice", invoice.name, ("status", "applied_credits", "amount_due")
		)
		self.assertEqual((status, applied, due), ("Unpaid", 80, 120))
		self.assertEqual(self.balance_of(self.new_team.name), 0)

	def test_balance_move_leaves_an_invoice_stripe_already_holds_and_moves_all_credit(self):
		invoice = self.create_draft_invoice_with_usage(self.old_team.name, 200)
		frappe.db.set_value("Invoice", invoice, "stripe_invoice_id", "in_test_held_by_stripe")
		self.old_team.allocate_credit_amount(500, source="Prepaid Credits")

		self.full_account_transfer(move_balance=True).transfer()

		status, applied = frappe.db.get_value("Invoice", invoice, ("status", "applied_credits"))
		self.assertEqual((status, applied), ("Draft", 0))
		self.assertEqual(self.balance_of(self.new_team.name), 500)

	@patch.object(Invoice, "create_razorpay_payment")
	@patch.object(Invoice, "create_stripe_invoice")
	def test_balance_move_on_card_settles_from_credit_only_and_leaves_the_shortfall_unpaid(
		self, create_stripe_invoice: Mock, create_razorpay_payment: Mock
	):
		add_card(self.old_team)
		self.old_team.allocate_credit_amount(100, source="Prepaid Credits")
		invoice = self.create_draft_invoice_with_usage(self.old_team.name, 200)
		team_change = self.full_account_transfer(move_balance=True, resources=[("Server", self.server.name)])

		team_change.transfer()

		create_stripe_invoice.assert_not_called()
		create_razorpay_payment.assert_not_called()
		status, amount_due = frappe.db.get_value("Invoice", invoice, ("status", "amount_due"))
		self.assertNotEqual(status, "Paid")
		self.assertEqual(amount_due, 100)
		self.assertEqual(self.team_of("Server", self.server.name), self.new_team.name)
		team_change.reload()
		self.assertEqual(team_change.transfer_completed, 1)
		self.assertEqual(team_change.balance_moved, 0)
		self.assertEqual(self.balance_of(self.new_team.name), 0)

	def test_balance_move_between_currencies_needs_an_exchange_rate_and_converts_with_it(self):
		self.old_team.allocate_credit_amount(830, source="Prepaid Credits")
		frappe.db.set_value("Team", self.new_team.name, "currency", "USD")

		with self.assertRaisesRegex(frappe.ValidationError, "Enter the exchange rate from INR to USD"):
			self.full_account_transfer(move_balance=True)

		team_change = self.full_account_transfer(move_balance=True, exchange_rate=1 / 83)
		team_change.transfer()

		self.assertEqual(self.balance_of(self.old_team.name), 0)
		self.assertEqual(self.balance_of(self.new_team.name), 10)
