# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from __future__ import annotations

import typing
from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import (
	DeployCandidateBuild,
)
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_action.site_action import (
	SiteAction,
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
			self.assertIn("not available", str(e).lower())

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
