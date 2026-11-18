# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

import typing
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, format_datetime

from press.agent import Agent
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.server.test_server_monitoring import patch_public_server_health_metrics
from press.press.doctype.site.site import SHARED_SERVER_MOVE_COOLDOWN_DAYS
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_action.site_action import SiteAction

if typing.TYPE_CHECKING:
	from press.press.doctype.server.server import Server
	from press.press.doctype.site.site import Site

# (free memory ratio, idle cpu ratio, used disk ratio)
ROOMY = (0.6, 0.9, 0.2)
CROWDED = (0.1, 0.2, 0.95)


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
# A second bench on a deployed group asks the agent how big the last image was
@patch.object(Agent, "get", new=Mock(return_value={"size": 0}))
class TestSharedServerMigration(FrappeTestCase):
	"""Moving a site from one shared server to another in the same region."""

	def setUp(self):
		self.bench = create_test_bench(public_server=True)
		self.site: Site = create_test_site(bench=self.bench.name)
		self.group = frappe.get_doc("Release Group", self.bench.group)
		self.region = frappe.db.get_value("Server", self.site.server, "cluster")

	def tearDown(self):
		frappe.db.rollback()

	def add_server_running_the_group(self, public: bool = True, cluster: str | None = None) -> Server:
		server = create_test_server(cluster=cluster or self.region, public=public)
		create_test_bench(group=self.group, server=server.name)
		return server

	def record_shared_server_move(self, days_ago: int = 0, status: str = "Success") -> str:
		with patch.object(SiteAction, "after_insert", new=Mock()):
			action = frappe.get_doc(
				{
					"doctype": "Site Action",
					"site": self.site.name,
					"action_type": "Move Site To Another Shared Server",
					"team": self.site.team,
					"arguments": "{}",
					"status": status,
				}
			).insert()

		frappe.db.set_value(
			"Site Action",
			action.name,
			"creation",
			add_to_date(None, days=-days_ago),
			update_modified=False,
		)
		return action.name

	def offered_servers(self, capacity: dict[str, tuple[float, float, float]]) -> list[dict]:
		with patch_public_server_health_metrics({self.site.server: ROOMY, **capacity}):
			return self.site.shared_servers_with_free_capacity()

	def test_shared_server_running_the_same_bench_group_is_offered_with_its_bench(self):
		destination = self.add_server_running_the_group()

		servers = self.offered_servers({destination.name: ROOMY})

		self.assertEqual([server["name"] for server in servers], [destination.name])
		self.assertEqual(
			servers[0]["bench"],
			frappe.db.get_value("Bench", {"group": self.group.name, "server": destination.name}, "name"),
		)

	def test_server_the_site_already_runs_on_is_not_offered(self):
		self.assertEqual(self.offered_servers({}), [])

	def test_dedicated_server_is_not_offered(self):
		destination = self.add_server_running_the_group(public=False)

		self.assertEqual(self.offered_servers({destination.name: ROOMY}), [])

	def test_shared_server_in_another_region_is_not_offered(self):
		other_region = create_test_cluster("Frankfurt", public=True)
		destination = self.add_server_running_the_group(cluster=other_region.name)

		self.assertEqual(self.offered_servers({destination.name: ROOMY}), [])

	def test_shared_server_without_an_active_bench_of_the_group_is_not_offered(self):
		destination = self.add_server_running_the_group()
		frappe.db.set_value("Bench", {"server": destination.name}, "status", "Archived")

		self.assertEqual(self.offered_servers({destination.name: ROOMY}), [])

	def test_shared_server_held_back_from_scheduling_is_not_offered(self):
		destination = self.add_server_running_the_group()
		frappe.db.set_value("Server", destination.name, "exclude_for_scheduling", 1)

		self.assertEqual(self.offered_servers({destination.name: ROOMY}), [])

	def test_shared_server_without_room_is_not_offered(self):
		destination = self.add_server_running_the_group()

		self.assertEqual(self.offered_servers({destination.name: CROWDED}), [])

	def test_roomiest_shared_server_is_the_one_picked(self):
		crowded = self.add_server_running_the_group()
		roomy = self.add_server_running_the_group()

		with patch_public_server_health_metrics(
			{self.site.server: ROOMY, crowded.name: (0.25, 0.55, 0.5), roomy.name: ROOMY}
		):
			self.assertEqual(self.site.pick_shared_server_for_migration()["name"], roomy.name)

	def test_region_is_named_when_no_shared_server_has_room(self):
		destination = self.add_server_running_the_group()

		with patch_public_server_health_metrics({self.site.server: ROOMY, destination.name: CROWDED}):
			self.assertRaisesRegex(
				frappe.ValidationError,
				f"No other shared server in {self.site.region_title} has room for this site right now",
				self.site.pick_shared_server_for_migration,
			)

	def test_server_asked_for_by_name_is_refused_when_it_has_no_room(self):
		crowded = self.add_server_running_the_group()
		self.add_server_running_the_group()

		with patch_public_server_health_metrics(
			{self.site.server: ROOMY, crowded.name: CROWDED, "roomy": ROOMY}
		):
			self.assertRaisesRegex(
				frappe.ValidationError,
				f"Shared server {crowded.name} has no room for this site right now",
				self.site.pick_shared_server_for_migration,
				crowded.name,
			)

	def test_site_whose_bench_runs_on_no_other_shared_server_is_told_where_to_go_instead(self):
		with patch_public_server_health_metrics({self.site.server: ROOMY}):
			self.assertRaisesRegex(
				frappe.ValidationError,
				"bench runs on no other shared server in .*You can move the site to a different region",
				self.site.pick_shared_server_for_migration,
			)

	def test_second_move_inside_the_cooldown_is_refused_with_the_date_of_the_next_one(self):
		self.record_shared_server_move(days_ago=10)
		next_move = add_to_date(None, days=SHARED_SERVER_MOVE_COOLDOWN_DAYS - 10)

		self.assertRaisesRegex(
			frappe.ValidationError,
			f"It can move again after {format_datetime(next_move, 'MMM d, YYYY')}",
			self.site.validate_shared_server_move_cooldown,
		)

	def test_move_is_allowed_once_the_cooldown_has_passed(self):
		self.record_shared_server_move(days_ago=SHARED_SERVER_MOVE_COOLDOWN_DAYS + 1)

		self.site.validate_shared_server_move_cooldown()

	def test_cancelled_move_does_not_hold_the_site_back(self):
		self.record_shared_server_move(days_ago=1, status="Cancelled")

		self.site.validate_shared_server_move_cooldown()

	def test_failed_move_does_not_hold_the_site_back(self):
		self.record_shared_server_move(days_ago=1, status="Failure")

		self.site.validate_shared_server_move_cooldown()

	def test_the_move_being_validated_does_not_hold_itself_back(self):
		action_name = self.record_shared_server_move(days_ago=0, status="Scheduled")

		self.site.validate_shared_server_move_cooldown(exclude_action=action_name)

	def test_migration_target_is_refused_inside_the_cooldown(self):
		destination = self.add_server_running_the_group()
		self.record_shared_server_move(days_ago=5)

		with patch_public_server_health_metrics({self.site.server: ROOMY, destination.name: ROOMY}):
			self.assertRaisesRegex(
				frappe.ValidationError,
				"already moved to another shared server in the last 60 days",
				self.site.get_shared_server_migration_target,
			)

	def test_migration_target_names_the_region_and_the_destination(self):
		destination = self.add_server_running_the_group()

		with patch_public_server_health_metrics({self.site.server: ROOMY, destination.name: ROOMY}):
			target = self.site.get_shared_server_migration_target()

		self.assertEqual(target["region"], self.site.region_title)
		self.assertEqual(target["destination_server"]["name"], destination.name)
		self.assertEqual(target["destination_server"]["free_memory_percent"], 60.0)

	def test_site_on_a_dedicated_server_cannot_move_to_a_shared_server(self):
		dedicated_bench = create_test_bench()
		site: Site = create_test_site(bench=dedicated_bench.name)

		self.assertRaisesRegex(
			frappe.ValidationError,
			"This site is not on a shared server",
			site.get_shared_server_migration_target,
		)

	def test_option_is_offered_to_a_site_on_a_shared_server(self):
		option = self.site.get_migration_options()["Move Site To Another Shared Server"]

		self.assertFalse(option["hidden"])
		self.assertEqual(option["options"]["region"], self.site.region_title)
		self.assertEqual(option["options"]["cooldown_days"], SHARED_SERVER_MOVE_COOLDOWN_DAYS)

	def test_option_is_hidden_from_a_site_on_a_dedicated_server(self):
		site: Site = create_test_site(bench=create_test_bench().name)

		option = site.get_migration_options()["Move Site To Another Shared Server"]

		self.assertTrue(option["hidden"])
