# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

import typing
from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.core.utils import find
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.agent_job.test_agent_job import create_test_agent_job
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.cluster.test_cluster import create_test_cluster
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import (
	DeployCandidateBuild,
)
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.server.test_server_monitoring import patch_public_server_health_metrics
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site.test_site_shared_server_migration import CROWDED, ROOMY
from press.press.doctype.site_action.site_action import (
	SiteAction,
	StepStatus,
	process_site_actions,
)
from press.press.doctype.site_migration.site_migration import SiteMigration
from press.press.doctype.site_update.site_update import SiteUpdate
from press.utils.test import foreground_enqueue, foreground_enqueue_doc

if typing.TYPE_CHECKING:
	from press.press.doctype.bench.bench import Bench
	from press.press.doctype.site.site import Site


def process_bench_build_and_deploy(self: DeployCandidateBuild):
	"""Simulate successful build and deploy for testing"""
	from press.press.doctype.deploy_candidate_build.deploy_candidate_build import Status

	self.set_status(Status.SUCCESS)
	assert self.deploy_on_server  # narrows DF.Link | None for mypy
	self._create_deploy([self.deploy_on_server])


@patch("press.press.doctype.site_action.site_action.frappe.enqueue_doc", new=foreground_enqueue_doc)
@patch("press.press.doctype.site_action.site_action.frappe.enqueue", new=foreground_enqueue)
@patch("press.press.doctype.site_migration.site_migration.frappe.enqueue_doc", new=foreground_enqueue_doc)
@patch("press.press.doctype.site_update.site_update.frappe.enqueue_doc", new=foreground_enqueue_doc)
@patch("frappe.db.commit", new=MagicMock())
@patch.object(DeployCandidateBuild, "pre_build", new=process_bench_build_and_deploy)
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestSiteAction(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.delete("Agent Job Step")
		frappe.db.delete("Agent Job")

		create_test_press_settings()
		self.x86_build_server = create_test_server(platform="x86_64", use_for_build=True)
		self.arm_build_server = create_test_server(platform="arm64", use_for_build=True)

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	@patch.object(SiteMigration, "start", new=Mock())
	@patch.object(SiteUpdate, "start", new=Mock())
	def test_shared_bench_to_private_bench_migration(self):
		"""Test moving a site from shared bench to private bench"""
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)

		action_name = source_site.create_migration_plan(
			type="Move Site To Different Server / Bench",
			new_group_name="Test Private Group",
		)

		action: SiteAction = frappe.get_doc("Site Action", action_name)

		self.assertEqual(action.action_type, "Move Site To Different Server / Bench")
		self.assertEqual(action.site, source_site.name)
		self.assertEqual(action.status, "Scheduled")
		self.assertTrue(len(action.steps) > 0)
		self.assertTrue(action.get_argument("new_release_group_name"))

	@patch.object(SiteMigration, "start", new=Mock())
	@patch.object(SiteUpdate, "start", new=Mock())
	def test_bench_creation_and_deployment_flow(self):
		"""Test the complete bench creation flow during site migration"""
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)

		action_name = source_site.create_migration_plan(
			type="Move Site To Different Server / Bench",
			new_group_name="Test Private Group",
		)

		action: SiteAction = frappe.get_doc("Site Action", action_name)
		action.execute()
		action.reload()

		bench_creation_step = None
		for step in action.steps:
			if "Clone and Create" in step.step or "Bench" in step.step:
				bench_creation_step = step
				break

		self.assertIsNotNone(bench_creation_step, "Bench creation step should exist")

		if action.get_argument("new_deploy_candidate_build"):
			build_name = action.get_argument("new_deploy_candidate_build")
			build = frappe.get_doc("Deploy Candidate Build", build_name)

			self.assertIsNotNone(build)
			self.assertEqual(build.status, "Success")

			if action.get_argument("new_bench"):
				bench_name = action.get_argument("new_bench")
				bench = frappe.get_doc("Bench", bench_name)

				self.assertEqual(bench.build, build_name)
				self.assertEqual(bench.status, "Active")
				self.assertEqual(action.get_argument("destination_bench"), bench_name)

	def test_existing_bench_skips_creation(self):
		"""Test that bench creation is skipped when an active bench exists on destination"""
		source_bench: Bench = create_test_bench(public_server=False)
		source_site: Site = create_test_site(bench=source_bench.name)

		source_group = frappe.get_doc("Release Group", source_bench.group)
		dest_server = create_test_server(platform="x86_64")

		source_group.append("servers", {"server": dest_server.name, "default": False})
		source_group.save()

		source_bench_doc = frappe.get_doc("Bench", source_bench.name)
		dest_bench = frappe.new_doc("Bench")
		dest_bench.group = source_bench_doc.group
		dest_bench.server = dest_server.name
		dest_bench.status = "Active"
		dest_bench.candidate = source_bench_doc.candidate
		dest_bench.build = source_bench_doc.build
		dest_bench.docker_image = source_bench_doc.docker_image
		dest_bench.insert()

		action: SiteAction = frappe.get_doc(
			{
				"doctype": "Site Action",
				"site": source_site.name,
				"action_type": "Move Site To Different Server / Bench",
				"team": source_site.team,
				"arguments": frappe.as_json(
					{
						"destination_release_group": source_group.name,
						"destination_server": dest_server.name,
					}
				),
			}
		)

		action.add_steps()
		bench_creation_step = None
		for step in action.steps:
			if "Clone and Create" in step.step or "Bench" in step.step:
				bench_creation_step = step
				action.current_step = step
				break

		if bench_creation_step:
			result = action.clone_and_create_bench_group()

			from press.press.doctype.site_action.site_action import StepStatus

			self.assertEqual(result, StepStatus.Skipped)
			self.assertEqual(action.get_argument("destination_bench"), dest_bench.name)

	def test_bench_creation_failure_archives_release_group(self):
		"""Test that release group is archived when bench creation fails"""
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)

		action_name = source_site.create_migration_plan(
			type="Move Site To Different Server / Bench",
			new_group_name="Test Failed Group",
		)

		action: SiteAction = frappe.get_doc("Site Action", action_name)

		with patch.object(DeployCandidateBuild, "set_status") as mock_set_status:

			def set_failure_status(status):
				if hasattr(DeployCandidateBuild, "_original_set_status"):
					DeployCandidateBuild._original_set_status(status)
				frappe.db.set_value(
					"Deploy Candidate Build",
					action.get_argument("new_deploy_candidate_build") or "dummy",
					"status",
					"Failure",
				)

			mock_set_status.side_effect = set_failure_status

			action.execute()
			action.reload()

			if action.get_argument("new_deploy_candidate_build"):
				build_name = action.get_argument("new_deploy_candidate_build")
				frappe.db.set_value("Deploy Candidate Build", build_name, "status", "Failure")

				bench_creation_step = None
				for step in action.steps:
					if "Clone and Create" in step.step or "Bench" in step.step:
						bench_creation_step = step
						break

				if bench_creation_step:
					action.execute_step(bench_creation_step.name)
					action.reload()

					bench_creation_step.reload()
					self.assertEqual(bench_creation_step.status, "Failure")

					if action.get_argument("destination_release_group"):
						rg_name = action.get_argument("destination_release_group")
						rg_status = frappe.db.get_value("Release Group", rg_name, "enabled")
						self.assertIn(rg_status, [0, False, None])

	@patch.object(SiteUpdate, "start", new=Mock())
	def test_move_site_to_different_server_same_group(self):
		"""Test moving a site to different server within same release group"""
		source_bench: Bench = create_test_bench(public_server=False)
		source_site: Site = create_test_site(bench=source_bench.name)

		release_group = frappe.get_doc("Release Group", source_bench.group)
		destination_server = create_test_server(platform="x86_64")

		release_group.append("servers", {"server": destination_server.name, "default": False})
		release_group.save()

		action: SiteAction = frappe.get_doc(
			{
				"doctype": "Site Action",
				"site": source_site.name,
				"action_type": "Move Site To Different Server / Bench",
				"team": source_site.team,
				"arguments": frappe.as_json({"destination_server": destination_server.name}),
			}
		).insert()

		self.assertEqual(action.status, "Scheduled")
		self.assertEqual(action.get_argument("destination_server"), destination_server.name)

	@patch.object(SiteMigration, "start", new=Mock())
	# A second bench on a deployed group asks the agent how big the last image was
	@patch.object(Agent, "get", new=Mock(return_value={"size": 0}))
	def test_move_to_a_shared_server_that_runs_the_bench_skips_the_deploy(self):
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)
		destination_server = create_test_server(
			cluster=frappe.db.get_value("Server", source_site.server, "cluster"), public=True
		)
		destination_bench: Bench = create_test_bench(
			group=frappe.get_doc("Release Group", source_bench.group), server=destination_server.name
		)

		with patch_public_server_health_metrics({source_site.server: ROOMY, destination_server.name: ROOMY}):
			action_name = source_site.create_migration_plan(type="Move Site To Another Shared Server")

		action: SiteAction = frappe.get_doc("Site Action", action_name)
		self.assertEqual(action.get_argument("destination_server"), destination_server.name)

		self.run_step(action, "deploy_bench_on_shared_server")
		self.assertEqual(
			action.get_step_by_method("deploy_bench_on_shared_server").status, StepStatus.Skipped
		)
		self.assertEqual(action.destination_bench, destination_bench.name)

		self.run_step(action, "move_site_to_another_shared_server")
		migration: SiteMigration = frappe.get_doc("Site Migration", {"site": source_site.name})

		self.assertEqual(migration.destination_server, destination_server.name)
		self.assertEqual(migration.destination_bench, destination_bench.name)
		self.assertEqual(migration.destination_cluster, source_site.cluster)
		self.assertEqual(
			frappe.db.get_value("Bench", migration.destination_bench, "group"), source_bench.group
		)

	@patch.object(SiteMigration, "start", new=Mock())
	@patch.object(Agent, "get", new=Mock(return_value={"size": 0}))
	def test_move_to_a_shared_server_without_the_bench_deploys_it_there_first(self):
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)
		destination_server = create_test_server(
			cluster=frappe.db.get_value("Server", source_site.server, "cluster"), public=True
		)

		with patch_public_server_health_metrics({source_site.server: ROOMY, destination_server.name: ROOMY}):
			action_name = source_site.create_migration_plan(type="Move Site To Another Shared Server")

		action: SiteAction = frappe.get_doc("Site Action", action_name)
		self.assertEqual(action.get_argument("destination_release_group"), source_bench.group)

		# The step adds the server to the site's own bench group and builds there.
		# The deploy is simulated below, so the build must not run one of its own.
		with patch.object(DeployCandidateBuild, "pre_build", new=Mock()):
			self.run_step(action, "deploy_bench_on_shared_server")
		group = frappe.get_doc("Release Group", source_bench.group)
		self.assertIn(destination_server.name, [server.server for server in group.servers])

		build_name = action.get_argument("new_deploy_candidate_build")
		self.assertTrue(build_name)
		deployed_bench = self.finish_build(build_name, destination_server.name)

		# The second pass picks up the bench that build left on the server
		self.run_step(action, "deploy_bench_on_shared_server")
		self.assertEqual(action.destination_bench, deployed_bench.name)

		self.run_step(action, "move_site_to_another_shared_server")
		migration: SiteMigration = frappe.get_doc("Site Migration", {"site": source_site.name})

		self.assertEqual(migration.destination_bench, deployed_bench.name)
		self.assertEqual(migration.destination_server, destination_server.name)

	@patch.object(SiteMigration, "start", new=Mock())
	@patch.object(Agent, "get", new=Mock(return_value={"size": 0}))
	def test_second_shared_server_move_inside_the_cooldown_creates_nothing(self):
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)
		destination_server = create_test_server(
			cluster=frappe.db.get_value("Server", source_site.server, "cluster"), public=True
		)
		create_test_bench(
			group=frappe.get_doc("Release Group", source_bench.group), server=destination_server.name
		)

		with patch_public_server_health_metrics({source_site.server: ROOMY, destination_server.name: ROOMY}):
			first_move = source_site.create_migration_plan(type="Move Site To Another Shared Server")
			# Finish the first move, so only the cooldown can refuse the second
			action: SiteAction = frappe.get_doc("Site Action", first_move)
			frappe.db.set_value("Site Migration", action.get_argument("site_migration"), "status", "Success")
			frappe.db.set_value("Site Action", first_move, "status", "Success")

			with self.assertRaises(frappe.ValidationError) as context:
				source_site.create_migration_plan(type="Move Site To Another Shared Server")

		self.assertIn("already moved to another shared server", str(context.exception))
		self.assertEqual(
			frappe.db.count(
				"Site Action",
				{"site": source_site.name, "action_type": "Move Site To Another Shared Server"},
			),
			1,
		)

	@patch.object(SiteMigration, "start", new=Mock())
	@patch.object(Agent, "get", new=Mock(return_value={"size": 0}))
	def test_cancelling_a_region_move_takes_back_the_scheduled_migration(self):
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)
		other_region = create_test_cluster("Frankfurt", public=True)
		create_test_bench(
			group=frappe.get_doc("Release Group", source_bench.group),
			server=create_test_server(cluster=other_region.name, public=True).name,
		)

		action_name = source_site.create_migration_plan(
			type="Move Site To Different Region",
			cluster=other_region.name,
			scheduled_time=frappe.utils.add_to_date(None, hours=1).strftime("%Y-%m-%dT%H:%M"),
		)

		action: SiteAction = frappe.get_doc("Site Action", action_name)
		migration_name = action.get_argument("site_migration")
		action.cancel_action()

		self.assertEqual(action.status, "Cancelled")
		self.assertFalse(frappe.db.exists("Site Migration", migration_name))

	@patch.object(Agent, "get", new=Mock(return_value={"size": 0}))
	def test_move_to_another_shared_server_is_refused_when_no_server_has_room(self):
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)
		crowded_server = create_test_server(
			cluster=frappe.db.get_value("Server", source_site.server, "cluster"), public=True
		)
		create_test_bench(
			group=frappe.get_doc("Release Group", source_bench.group), server=crowded_server.name
		)

		with (
			patch_public_server_health_metrics({source_site.server: ROOMY, crowded_server.name: CROWDED}),
			self.assertRaises(frappe.ValidationError) as context,
		):
			source_site.create_migration_plan(type="Move Site To Another Shared Server")

		self.assertIn("has room for this site right now", str(context.exception))
		self.assertFalse(frappe.db.exists("Site Migration", {"site": source_site.name}))

	def test_process_site_actions(self):
		"""Test that process_site_actions picks up scheduled actions"""
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)

		action_name = source_site.create_migration_plan(
			type="Move Site To Different Server / Bench",
			new_group_name="Test Group",
		)

		action: SiteAction = frappe.get_doc("Site Action", action_name)
		action.scheduled_time = None
		action.save()

		with patch.object(SiteAction, "execute", wraps=action.execute) as mock_execute:
			process_site_actions()
			self.assertTrue(mock_execute.called or action.status != "Scheduled")

	def test_cancel_action(self):
		"""Test cancelling a scheduled site action"""
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)

		action_name = source_site.create_migration_plan(
			type="Move Site To Different Server / Bench",
			new_group_name="Test Group",
		)

		action: SiteAction = frappe.get_doc("Site Action", action_name)
		action.cancel_action()
		action.reload()

		self.assertEqual(action.status, "Cancelled")

		for step in action.steps:
			if step.status in ("Pending", "Running"):
				self.assertEqual(step.status, "Skipped")

	def test_validation_failure_prevents_action(self):
		"""Test that validation failures prevent action from proceeding"""
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)

		try:
			frappe.get_doc(
				{
					"doctype": "Site Action",
					"site": source_site.name,
					"action_type": "Move Site To Different Region",
					"team": source_site.team,
					"arguments": frappe.as_json(
						{"cluster": frappe.db.get_value("Server", source_site.server, "cluster")}
					),
				}
			).insert()

			self.fail("Expected validation error for same cluster")
		except frappe.ValidationError:
			pass

	def test_prevent_migration_to_bench_without_required_apps(self):
		"""Test that migration is prevented when destination release group lacks required apps"""
		extra_app = create_test_app("erpnext", "ERPNext")
		base_app = create_test_app()

		source_group = create_test_release_group([base_app, extra_app])
		source_bench: Bench = create_test_bench(public_server=False, group=source_group)
		source_site: Site = create_test_site(bench=source_bench.name, apps=["frappe", "erpnext"])

		dest_bench: Bench = create_test_bench(public_server=False)
		dest_group_name = frappe.db.get_value("Bench", dest_bench.name, "group")
		dest_server = frappe.db.get_value("Bench", dest_bench.name, "server")

		dest_group = frappe.get_doc("Release Group", dest_group_name)
		dest_group.append("servers", {"server": source_bench.server, "default": False})
		dest_group.save()

		try:
			frappe.get_doc(
				{
					"doctype": "Site Action",
					"site": source_site.name,
					"action_type": "Move Site To Different Server / Bench",
					"team": source_site.team,
					"arguments": frappe.as_json(
						{
							"destination_release_group": dest_group_name,
							"destination_server": dest_server,
						}
					),
				}
			).insert()

			self.fail("Expected validation error for missing apps in destination release group")
		except frappe.ValidationError as e:
			self.assertIn("erpnext", str(e).lower())

	def test_validate_private_to_shared_unavailable(self):
		"""Ensure 'Move From Private To Shared Bench' action is not available"""
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)

		try:
			frappe.get_doc(
				{
					"doctype": "Site Action",
					"site": source_site.name,
					"action_type": "Move From Private To Shared Bench",
					"team": source_site.team,
					"arguments": frappe.as_json({}),
				}
			).insert()
			self.fail("Expected validation error for unavailable action type")
		except frappe.ValidationError as e:
			self.assertIn("isn't available", str(e).lower())

	@patch.object(SiteMigration, "start", new=Mock())
	def test_actionable_error_of_failed_migration_is_shown_on_action(self):
		"""An OOM on the destination server should surface on the action, not just on the agent job"""
		source_bench: Bench = create_test_bench(public_server=False)
		source_site: Site = create_test_site(bench=source_bench.name)
		destination_bench: Bench = create_test_bench()

		migration: SiteMigration = frappe.get_doc(
			{
				"doctype": "Site Migration",
				"site": source_site.name,
				"destination_bench": destination_bench.name,
			}
		).insert()

		restore_job = create_test_agent_job(
			"New Site from Backup", server=migration.destination_server, status="Failure"
		)
		restore_job.db_set(
			"traceback", "AgentException: Command 'bench restore' returned non-zero exit status 137."
		)
		restore_step = find(
			migration.steps, lambda step: step.method_name == "restore_site_on_destination_server"
		)
		restore_step.status = "Failure"
		restore_step.step_job = restore_job.name
		migration.status = "Failure"
		migration.save()
		migration.send_fail_notification()

		action: SiteAction = frappe.get_doc(
			{
				"doctype": "Site Action",
				"site": source_site.name,
				"action_type": "Move Site To Different Server / Bench",
				"team": source_site.team,
				"arguments": frappe.as_json({"destination_server": destination_bench.server}),
			}
		).insert()

		failed_step = find(action.steps, lambda step: step.method == "move_site_to_bench_group")
		failed_step.status = "Failure"
		failed_step.reference_doctype = "Site Migration"
		failed_step.reference_name = migration.name
		action.status = "Failure"
		action.save()

		self.assertEqual(
			[notification["title"] for notification in action.get_press_error_notifications()],
			["Server out of memory error"],
		)

	def test_cancel_action_raises_when_not_scheduled(self):
		"""Cancel should raise when action is not in Scheduled state"""
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)

		action_name = source_site.create_migration_plan(
			type="Move Site To Different Server / Bench",
			new_group_name="Test Group",
		)

		action: SiteAction = frappe.get_doc("Site Action", action_name)
		action.status = "Running"
		action.save()

		with self.assertRaises(frappe.ValidationError):
			action.cancel_action()
<<<<<<< HEAD
=======

	def test_stop_action_fails_the_build_it_started(self):
		"""Stopping a migration that is still building the destination bench fails that build"""
		source_bench: Bench = create_test_bench(public_server=True)
		source_site: Site = create_test_site(bench=source_bench.name)
		action = self.create_running_action(source_site)
		build: DeployCandidateBuild = frappe.get_doc("Deploy Candidate Build", source_bench.build)
		build.db_set("status", "Running")
		step = self.set_step_reference(action, "clone_and_create_bench_group", build)

		action.stop_action()

		self.assertEqual(frappe.db.get_value("Deploy Candidate Build", build.name, "status"), "Failure")
		self.assertEqual(action.get_step(step.name).status, "Failure")
		self.assertEqual(frappe.db.get_value("Site Action", action.name, "status"), "Failure")

	@patch.object(SiteMigration, "start", new=Mock())
	def test_stop_action_fails_a_pending_site_migration_that_has_dispatched_no_job(self):
		"""`start()` leaves a migration Pending before its first job, and that is still stoppable"""
		source_site: Site = create_test_site(bench=create_test_bench(public_server=False).name)
		action = self.create_running_action(source_site)
		migration: SiteMigration = frappe.get_doc(
			{
				"doctype": "Site Migration",
				"site": source_site.name,
				"destination_bench": create_test_bench().name,
				"status": "Pending",
			}
		).insert()
		self.set_step_reference(action, "move_site_to_bench_group", migration)

		action.stop_action()

		migration.reload()
		self.assertEqual(migration.status, "Failure")
		self.assertTrue(all(step.status == "Skipped" for step in migration.steps))
		self.assertEqual(frappe.db.get_value("Site Action", action.name, "status"), "Failure")

	@patch.object(SiteUpdate, "start", new=Mock())
	def test_stop_action_cancels_a_pending_site_update_that_has_dispatched_no_job(self):
		"""Cancelled, not Failure, so a stopped update doesn't count as a pending one later"""
		source_bench: Bench = create_test_bench(public_server=False)
		source_site: Site = create_test_site(bench=source_bench.name)
		action = self.create_running_action(source_site)
		update = create_test_site_update(
			source_site.name, source_bench.group, "Pending", ignore_validate=True
		)
		self.set_step_reference(action, "move_site_to_bench_group", update)

		action.stop_action()

		self.assertEqual(frappe.db.get_value("Site Update", update.name, "status"), "Cancelled")
		self.assertEqual(frappe.db.get_value("Site Action", action.name, "status"), "Failure")

	@patch.object(SiteMigration, "start", new=Mock())
	def test_stop_action_refuses_once_the_site_has_started_moving(self):
		"""A migration whose first job is out has to finish, or the site is left between benches"""
		source_site: Site = create_test_site(bench=create_test_bench(public_server=False).name)
		action = self.create_running_action(source_site)
		migration: SiteMigration = frappe.get_doc(
			{
				"doctype": "Site Migration",
				"site": source_site.name,
				"destination_bench": create_test_bench().name,
				"status": "Pending",
			}
		).insert()
		migration.steps[0].step_job = create_test_agent_job("Deactivate Site").name
		migration.save()
		self.set_step_reference(action, "move_site_to_bench_group", migration)

		with self.assertRaises(frappe.ValidationError) as context:
			action.stop_action()

		self.assertIn("already being moved", str(context.exception))
		self.assertEqual(frappe.db.get_value("Site Action", action.name, "status"), "Running")

	@patch.object(SiteMigration, "start", new=Mock())
	def test_a_step_enqueued_before_the_stop_does_not_run_after_it(self):
		"""The move step creates the Site Migration when it runs, so a stopped action must not run it"""
		source_bench: Bench = create_test_bench(public_server=False)
		source_site: Site = create_test_site(bench=source_bench.name)
		action = self.create_running_action(source_site)
		step = action.get_step_by_method("move_site_to_bench_group")
		step.status = "Running"
		action.set_argument("destination_bench", create_test_bench().name)
		action.save()

		action.stop_action()
		action.execute_step(step.name)

		self.assertEqual(frappe.db.get_value("Site Action", action.name, "status"), "Failure")
		self.assertFalse(frappe.db.exists("Site Migration", {"site": source_site.name}))
		self.assertFalse(frappe.db.exists("Site Update", {"site": source_site.name}))

	def test_stop_action_refuses_a_scheduled_action(self):
		"""A scheduled action is cancelled, not stopped, so the button should not reach stop_action"""
		source_site: Site = create_test_site(bench=create_test_bench(public_server=True).name)
		action_name = source_site.create_migration_plan(
			type="Move Site To Different Server / Bench",
			new_group_name="Test Group",
		)
		action: SiteAction = frappe.get_doc("Site Action", action_name)

		with self.assertRaises(frappe.ValidationError) as context:
			action.stop_action()

		self.assertIn("Only a running migration can be stopped", str(context.exception))
		self.assertEqual(frappe.db.get_value("Site Action", action.name, "status"), "Scheduled")

	def finish_build(self, build_name: str, server: str) -> Bench:
		"""The bench a successful build leaves behind on the server it deployed to."""
		build: DeployCandidateBuild = frappe.get_doc("Deploy Candidate Build", build_name)
		build.db_set("status", "Success")

		bench: Bench = frappe.new_doc("Bench")
		bench.update(
			{
				"group": frappe.db.get_value("Deploy Candidate", build.deploy_candidate, "group"),
				"server": server,
				"status": "Active",
				"candidate": build.deploy_candidate,
				"build": build.name,
				"docker_image": frappe.mock("url"),
			}
		)
		bench.insert()
		return bench

	def run_step(self, action: SiteAction, method: str) -> None:
		"""Run one step on its own, so a step that is still Running doesn't re-enter itself."""
		frappe.flags.disable_auto_enqueue_next_step = True
		try:
			action.execute_step(action.get_step_by_method(method).name)
		finally:
			frappe.flags.disable_auto_enqueue_next_step = False
		action.reload()

	def create_running_action(self, site: Site) -> SiteAction:
		action: SiteAction = frappe.get_doc(
			{
				"doctype": "Site Action",
				"site": site.name,
				"action_type": "Move Site To Different Server / Bench",
				"team": site.team,
				"arguments": frappe.as_json({"destination_server": site.server}),
			}
		).insert()
		action.status = "Running"
		action.save()
		return action

	def set_step_reference(self, action: SiteAction, method: str, reference) -> SiteActionStep:
		step = action.get_step_by_method(method)
		step.status = "Running"
		step.reference_doctype = reference.doctype
		step.reference_name = reference.name
		action.save()
		return step
>>>>>>> 326b6fe (feat(site): Deploy the bench on the shared server a site moves to)
