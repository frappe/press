# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt


import unittest
from unittest.mock import MagicMock, Mock, patch

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.bench.bench import Bench, StagingSite
from press.press.doctype.plan.test_plan import create_test_plan
from press.press.doctype.server.server import scale_workers
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.subscription.test_subscription import create_test_subscription


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestStagingSite(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_create_staging_site(self):
		bench = create_test_bench()  # also creates press settings
		frappe.db.set_single_value(
			"Press Settings", "staging_plan", create_test_plan("Site").name
		)
		count_before = frappe.db.count("Site")

		site = StagingSite(bench).insert()

		self.assertTrue(site.staging)
		count_after = frappe.db.count("Site")
		self.assertEqual(count_after - count_before, 1)


@patch.object(AgentJob, "after_insert", new=Mock())
@patch("press.press.doctype.server.server.frappe.db.commit", new=MagicMock)
class TestBench(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _create_bench_with_n_sites_with_cpu_time(
		self, n: int, x: float, bench: str = None
	) -> Bench:
		"""Creates new bench if None given."""
		plan = create_test_plan("Site", cpu_time=x)

		if not bench:
			site = create_test_site()
			create_test_subscription(site.name, plan.name, site.team)  # map site with plan
			bench = site.bench
			n -= 1
		for i in range(n):
			site = create_test_site(bench=bench)
			create_test_subscription(site.name, plan.name, site.team)
		return frappe.get_doc("Bench", bench)

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
		self.assertEqual(bench.gunicorn_workers, 24)
		self.assertEqual(bench.background_workers, 8)
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
		bench2 = create_test_bench(
			group=frappe.get_doc("Release Group", bench.group), server=bench.server
		)
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
		bench2 = create_test_bench(
			group=frappe.get_doc("Release Group", bench.group), server=bench.server
		)
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
