# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import annotations

import unittest
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
from press.press.doctype.agent_job.agent_job import AgentJob, poll_pending_jobs
from press.press.doctype.agent_job.test_agent_job import fake_agent_job
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.bench.bench import (
	MAX_BACKGROUND_WORKERS,
	MAX_GUNICORN_WORKERS,
	Bench,
	StagingSite,
	archive_obsolete_benches,
	archive_obsolete_benches_for_server,
)
from press.press.doctype.deploy_candidate_difference.test_deploy_candidate_difference import (
	create_test_deploy_candidate_differences,
)
from press.press.doctype.release_group.release_group import ReleaseGroup
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.server.server import Server, scale_workers
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.subscription.test_subscription import create_test_subscription
from press.press.doctype.version_upgrade.test_version_upgrade import (
	create_test_version_upgrade,
)
from press.utils import get_current_team
from press.utils.test import foreground_enqueue, foreground_enqueue_doc

if TYPE_CHECKING:
	from press.press.doctype.press_settings.press_settings import PressSettings
	from press.press.doctype.team.team import Team


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestStagingSite(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_create_staging_site(self):
		bench = create_test_bench()  # also creates press settings
		frappe.db.set_single_value("Press Settings", "staging_plan", create_test_plan("Site").name)
		count_before = frappe.db.count("Site")

		site = StagingSite(bench).insert()

		self.assertTrue(site.staging)
		count_after = frappe.db.count("Site")
		self.assertEqual(count_after - count_before, 1)


@patch.object(AgentJob, "after_insert", new=Mock())
@patch("press.press.doctype.server.server.frappe.enqueue_doc", new=foreground_enqueue_doc)
@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
class TestBench(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _create_bench_with_n_sites_with_cpu_time(
		self, n: int, x: float, bench: str | None = None, public_server: bool = False
	) -> Bench:
		"""Creates new bench if None given."""
		plan = create_test_plan("Site", cpu_time=x)

		if not bench:
			site = create_test_site(public_server=public_server)
			create_test_subscription(site.name, plan.name, site.team)  # map site with plan
			bench = site.bench
			n -= 1
		for _i in range(n):
			site = create_test_site(bench=bench)
			create_test_subscription(site.name, plan.name, site.team)
		return Bench("Bench", bench)

	@patch.object(Agent, "rebuild_bench", new=lambda x, y: "Triggered agent job")
	def test_minimum_rebuild_memory(self):
		bench = self._create_bench_with_n_sites_with_cpu_time(3, 5, public_server=False)
		bench_public = self._create_bench_with_n_sites_with_cpu_time(3, 5, public_server=True)
		bench.memory_swap = 5000
		bench.memory_high = 928

		high_prometheus_memory = 3073741182
		low_prometheus_memeory = 1073741182
		high_memory_max = 4020
		low_memory_max = 1029

		press_settings: PressSettings = frappe.get_doc("Press Settings")

		if not press_settings.minimum_rebuild_memory:
			press_settings.certbot_directory = "./"
			press_settings.eff_registration_email = "test"
			press_settings.minimum_rebuild_memory = 2
			press_settings.save()

		bench.memory_max = low_memory_max
		bench.save()

		with patch.object(Bench, "get_free_memory", new=lambda x: high_prometheus_memory):
			# Low memory_max should not affect rebuild for dedicated servers
			self.assertEqual(bench.get_memory_info(), (True, high_prometheus_memory / (1024**3), 2))
			self.assertEqual(bench.rebuild(), "Triggered agent job")

		with self.assertRaises(frappe.ValidationError):
			# Raise on public servers
			bench_public.rebuild()

		bench.memory_max = high_memory_max
		bench.save()

		with patch.object(Bench, "get_free_memory", new=lambda x: low_prometheus_memeory), self.assertRaises(
			frappe.ValidationError
		):
			# Should not rebuild due to low server mem
			self.assertEqual(bench.get_memory_info(), (True, low_prometheus_memeory / (1024**3), 2))
			bench.rebuild()

		bench.memory_max = high_memory_max
		bench.save()

		with patch.object(
			Bench, "get_free_memory", new=lambda x: high_prometheus_memory
		):  # Testing with 3GB from prometheus query
			self.assertEqual(bench.get_memory_info(), (True, high_prometheus_memory / (1024**3), 2))
			self.assertEqual(bench.rebuild(), "Triggered agent job")

	def test_workload_is_calculated_correctly(self):
		bench = self._create_bench_with_n_sites_with_cpu_time(3, 5)
		self.assertEqual(bench.workload, 15)
		bench = self._create_bench_with_n_sites_with_cpu_time(3, 10, bench.name)
		self.assertEqual(bench.workload, 45)

	def test_workload_gives_reasonable_numbers(self):
		bench1 = self._create_bench_with_n_sites_with_cpu_time(3, 5)
		bench2 = self._create_bench_with_n_sites_with_cpu_time(3, 10)
		bench3 = self._create_bench_with_n_sites_with_cpu_time(6, 5)
		bench4 = self._create_bench_with_n_sites_with_cpu_time(6, 10)
		self.assertGreater(bench2.workload, bench1.workload)
		self.assertGreater(bench4.workload, bench3.workload)
		self.assertGreater(bench4.workload, bench2.workload)

	def test_workers_get_allocated(self):
		bench = self._create_bench_with_n_sites_with_cpu_time(3, 5)
		workers_before = (bench.background_workers, bench.gunicorn_workers)  # 1, 2
		scale_workers()
		bench.reload()
		workers_after = (bench.background_workers, bench.gunicorn_workers)
		self.assertGreater(workers_after[1], workers_before[1])
		self.assertGreater(workers_after[0], workers_before[0])

	def test_auto_scale_uses_release_groups_max_workers_when_set(self):
		bench = self._create_bench_with_n_sites_with_cpu_time(3, 5)
		self.assertEqual(bench.gunicorn_workers, 2)
		self.assertEqual(bench.background_workers, 1)
		group = frappe.get_doc("Release Group", bench.group)
		scale_workers()
		bench.reload()
		self.assertEqual(bench.gunicorn_workers, MAX_GUNICORN_WORKERS)
		self.assertEqual(bench.background_workers, MAX_BACKGROUND_WORKERS)
		group.db_set("max_gunicorn_workers", 8)
		group.db_set("max_background_workers", 4)
		scale_workers()
		bench.reload()
		self.assertEqual(bench.gunicorn_workers, 8)
		self.assertEqual(bench.background_workers, 4)

	def test_auto_scale_uses_release_groups_max_workers_respecting_ram_available_on_server(
		self,
	):
		bench = self._create_bench_with_n_sites_with_cpu_time(3, 5)
		group = frappe.get_doc("Release Group", bench.group)
		group.db_set("max_gunicorn_workers", 48)
		group.db_set("max_background_workers", 8)
		scale_workers()
		bench.reload()
		self.assertEqual(bench.gunicorn_workers, 48)
		bench2 = create_test_bench(group=frappe.get_doc("Release Group", bench.group), server=bench.server)
		self._create_bench_with_n_sites_with_cpu_time(3, 5, bench2.name)
		scale_workers()
		bench.reload()
		bench2.reload()
		# assuming max gunicorn workers for default server (16gb RAM) is 52
		self.assertLess(bench.gunicorn_workers, 48)
		self.assertLess(bench2.gunicorn_workers, 48)

	def test_auto_scale_uses_release_groups_min_workers_when_set(self):
		bench = self._create_bench_with_n_sites_with_cpu_time(3, 5)
		self.assertEqual(bench.gunicorn_workers, 2)
		self.assertEqual(bench.background_workers, 1)
		frappe.db.set_value("Server", bench.server, "ram", 1600)
		scale_workers()
		bench.reload()
		self.assertEqual(bench.gunicorn_workers, 5)  # for for such low ram
		self.assertEqual(bench.background_workers, 2)
		group = frappe.get_doc("Release Group", bench.group)
		group.db_set("min_gunicorn_workers", 8)
		group.db_set("min_background_workers", 4)
		scale_workers()
		bench.reload()
		self.assertEqual(bench.gunicorn_workers, 8)
		self.assertEqual(bench.background_workers, 4)
		frappe.db.set_value("Server", bench.server, "ram", 16000)
		scale_workers()
		bench.reload()
		self.assertGreater(bench.gunicorn_workers, 8)
		self.assertGreater(bench.background_workers, 4)

	def test_auto_scale_uses_release_groups_min_workers_respecting_ram_available_on_server(
		self,
	):
		bench = self._create_bench_with_n_sites_with_cpu_time(3, 5)
		frappe.db.set_value("Server", bench.server, "ram", 1600)
		scale_workers()
		bench.reload()
		self.assertEqual(bench.gunicorn_workers, 5)
		self.assertEqual(bench.background_workers, 2)
		group = frappe.get_doc("Release Group", bench.group)
		group.db_set("min_gunicorn_workers", 12)
		group.db_set("min_background_workers", 6)
		scale_workers()
		bench.reload()
		self.assertEqual(bench.gunicorn_workers, 12)
		self.assertEqual(bench.background_workers, 6)
		bench2 = create_test_bench(group=ReleaseGroup("Release Group", bench.group), server=bench.server)
		self._create_bench_with_n_sites_with_cpu_time(3, 5, bench2.name)
		scale_workers()
		bench.reload()
		bench2.reload()
		# assuming max gunicorn workers for default server (16gb RAM) is 52
		self.assertGreaterEqual(bench.gunicorn_workers, 12)
		self.assertGreaterEqual(bench2.gunicorn_workers, 12)

	def test_auto_scale_uses_release_groups_max_and_min_workers_when_set(self):
		bench = self._create_bench_with_n_sites_with_cpu_time(3, 5)
		self.assertEqual(bench.gunicorn_workers, 2)
		self.assertEqual(bench.background_workers, 1)
		group = frappe.get_doc("Release Group", bench.group)
		group.db_set("max_gunicorn_workers", 10)
		group.db_set("max_background_workers", 5)
		scale_workers()
		bench.reload()
		self.assertEqual(bench.gunicorn_workers, 10)
		self.assertEqual(bench.background_workers, 5)
		frappe.db.set_value("Server", bench.server, "ram", 1600)
		scale_workers()
		bench.reload()
		self.assertEqual(bench.gunicorn_workers, 5)  # autoscaled for for such low ram
		self.assertEqual(bench.background_workers, 2)
		group.db_set("min_gunicorn_workers", 8)
		group.db_set("min_background_workers", 4)
		scale_workers()
		bench.reload()
		self.assertEqual(bench.gunicorn_workers, 8)
		self.assertEqual(bench.background_workers, 4)
		frappe.db.set_value("Server", bench.server, "ram", 16000)
		scale_workers()
		bench.reload()
		self.assertEqual(bench.gunicorn_workers, 10)
		self.assertEqual(bench.background_workers, 5)

	def test_set_bench_memory_limits_on_server_adds_memory_limit_on_bench_on_auto_scale(
		self,
	):
		bench1 = self._create_bench_with_n_sites_with_cpu_time(3, 5)
		bench2 = self._create_bench_with_n_sites_with_cpu_time(3, 5)

		frappe.db.set_value("Server", bench1.server, "set_bench_memory_limits", False)
		frappe.db.set_value("Server", bench2.server, "set_bench_memory_limits", False)

		scale_workers()

		bench1.reload()
		bench2.reload()
		self.assertEqual(bench1.memory_high, 0)
		self.assertEqual(bench1.memory_max, 0)
		self.assertEqual(bench2.memory_high, 0)
		self.assertEqual(bench2.memory_max, 0)
		frappe.db.set_value("Server", bench1.server, "set_bench_memory_limits", True)
		server = Server("Server", bench1.server)

		scale_workers()

		bench1.reload()
		bench2.reload()
		self.assertTrue(bench1.memory_high)
		self.assertTrue(bench1.memory_max)
		self.assertTrue(bench1.memory_swap)
		self.assertEqual(
			bench1.memory_high,
			512
			+ bench1.gunicorn_workers * server.GUNICORN_MEMORY
			+ bench1.background_workers * server.BACKGROUND_JOB_MEMORY,
		)
		self.assertEqual(
			bench1.memory_max,
			512
			+ bench1.gunicorn_workers * server.GUNICORN_MEMORY
			+ bench1.background_workers * server.BACKGROUND_JOB_MEMORY
			+ server.GUNICORN_MEMORY
			+ server.BACKGROUND_JOB_MEMORY,
		)
		self.assertEqual(bench1.memory_swap, bench1.memory_max * 2)

		self.assertFalse(bench2.memory_high)
		self.assertFalse(bench2.memory_max)
		self.assertFalse(bench2.memory_swap)

	def test_memory_limits_set_to_server_ram_when_skip_memory_limits_is_set(self):
		bench1 = self._create_bench_with_n_sites_with_cpu_time(3, 5)
		bench2 = self._create_bench_with_n_sites_with_cpu_time(3, 5)

		bench1.reload()
		bench2.reload()
		self.assertEqual(bench1.memory_high, 0)
		self.assertEqual(bench1.memory_max, 0)
		self.assertEqual(bench2.memory_high, 0)
		self.assertEqual(bench2.memory_max, 0)
		frappe.db.set_value("Server", bench1.server, "set_bench_memory_limits", True)
		frappe.db.set_value("Bench", bench1.name, "skip_memory_limits", True)

		# Server.set_bench_memory_limits now defaults to True
		# Unset bench2.server set_bench_memory_limits to test the unset case
		frappe.db.set_value("Server", bench2.server, "set_bench_memory_limits", False)
		server = Server("Server", bench1.server)

		scale_workers()

		bench1.reload()
		bench2.reload()
		self.assertTrue(bench1.memory_high)
		self.assertEqual(bench1.memory_high, server.ram - 1024)
		self.assertEqual(bench1.memory_max, server.ram)
		self.assertEqual(bench1.memory_swap, server.ram * 2)

		self.assertFalse(bench2.memory_high)
		self.assertFalse(bench2.memory_max)
		self.assertFalse(bench2.memory_swap)

	@patch("press.press.doctype.team.team.frappe.enqueue_doc", new=foreground_enqueue_doc)
	def test_workers_reallocated_on_site_unsuspend(self):
		bench1 = self._create_bench_with_n_sites_with_cpu_time(3, 5)  # current team
		bench2 = self._create_bench_with_n_sites_with_cpu_time(3, 5)

		frappe.db.set_value("Site", {"name": ("is", "set")}, "status", "Suspended")
		frappe.db.set_value("Server", bench1.server, "ram", 32000)

		scale_workers()

		self.assertEqual(bench1.workload, 0)
		self.assertEqual(bench2.workload, 0)
		self.assertEqual(bench1.gunicorn_workers, 2)
		self.assertEqual(bench2.gunicorn_workers, 2)

		team: Team = get_current_team(get_doc=True)
		team.unsuspend_sites()

		del bench1.workload  # cached properties
		del bench2.workload
		bench1.reload()
		bench2.reload()

		self.assertEqual(bench1.workload, 15)
		self.assertEqual(bench2.workload, 15)
		self.assertGreater(bench1.gunicorn_workers, 2)
		self.assertGreater(bench2.gunicorn_workers, 2)


@patch("press.press.doctype.bench.bench.frappe.db.commit", new=MagicMock)
class TestArchiveObsoleteBenches(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_private_obsolete_benches_archived(self):
		priv_group = create_test_release_group(apps=[create_test_app()], public=False)

		create_test_bench(group=priv_group, creation=frappe.utils.add_days(None, -10))
		benches_before = frappe.db.count("Bench", {"status": "Active"})
		with fake_agent_job("Archive Bench"):
			archive_obsolete_benches()
			poll_pending_jobs()
		benches_after = frappe.db.count("Bench", {"status": "Active"})
		self.assertEqual(
			benches_before - benches_after,
			1,
		)

	def test_old_public_benches_without_sites_archived(self):
		pub_group = create_test_release_group(apps=[create_test_app()], public=True)

		bench1 = create_test_bench(group=pub_group, creation=frappe.utils.add_days(None, -10))
		benches_before = frappe.db.count("Bench", {"status": "Active"})
		with fake_agent_job("Archive Bench"):
			archive_obsolete_benches()
			poll_pending_jobs()
		benches_after = frappe.db.count("Bench", {"status": "Active"})
		self.assertEqual(benches_after, benches_before)  # nothing got archived
		bench2 = create_test_bench(group=pub_group, server=bench1.server)
		create_test_deploy_candidate_differences(bench2.candidate)
		with fake_agent_job("Archive Bench"):
			archive_obsolete_benches()
			poll_pending_jobs()
		benches_after = frappe.db.count("Bench", {"status": "Active"})
		self.assertEqual(benches_after, benches_before)  # older bench got archived

	def test_private_benches_where_version_upgrade_scheduled_is_not_archived(self):
		priv_group = create_test_release_group(apps=[create_test_app()], public=False)
		bench = create_test_bench(group=priv_group, creation=frappe.utils.add_days(None, -10))

		bench2 = create_test_bench(server=bench.server)  # same server, different group
		site = create_test_site(bench=bench2.name)

		priv_group.add_server(bench.server, deploy=False)  # version upgrade validation
		create_test_version_upgrade(site.name, priv_group.name)
		benches_before = frappe.db.count("Bench", {"status": "Active"})
		with fake_agent_job("Archive Bench"):
			archive_obsolete_benches()
			poll_pending_jobs()
		benches_after = frappe.db.count("Bench", {"status": "Active"})
		self.assertEqual(benches_after, benches_before)

	@patch(
		"press.press.doctype.bench.bench.archive_obsolete_benches_for_server",
		wraps=archive_obsolete_benches_for_server,
	)
	@patch("press.press.doctype.bench.bench.frappe.enqueue", new=foreground_enqueue)
	def test_benches_archived_for_multiple_servers_via_multiple_jobs(self, mock_archive_by_server: MagicMock):
		priv_group = create_test_release_group(apps=[create_test_app()], public=False)
		create_test_bench(group=priv_group, creation=frappe.utils.add_days(None, -10))
		priv_group2 = create_test_release_group(apps=[create_test_app()], public=False)
		create_test_bench(group=priv_group2, creation=frappe.utils.add_days(None, -10))

		benches_before = frappe.db.count("Bench", {"status": "Active"})
		with fake_agent_job("Archive Bench"):
			archive_obsolete_benches()
			poll_pending_jobs()
		benches_after = frappe.db.count("Bench", {"status": "Active"})
		self.assertEqual(benches_before - benches_after, 2)
		self.assertEqual(mock_archive_by_server.call_count, 2)
