# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from unittest.mock import Mock, patch

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.bench.bench import Bench
from press.press.doctype.plan.test_plan import create_test_plan
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.subscription.test_subscription import create_test_subscription


@patch.object(AgentJob, "after_insert", new=Mock())
class TestBench(unittest.TestCase):
	def setUp(self):
		self.bench_count = 0  # to uniquely name sites in benches

	def tearDown(self):
		frappe.db.rollback()

	def _create_bench_with_n_sites_with_cpu_time(
		self, n: int, x: float, bench: str = None
	) -> Bench:
		"""Creates new bench if None given."""
		plan = create_test_plan("Site", cpu_time=x)

		if not bench:
			self.bench_count += 1
			site = create_test_site(f"site-0-{self.bench_count}")
			create_test_subscription(site.name, plan.name, site.team)  # map site with plan
			bench = site.bench
			n -= 1
			count = 1
		else:
			count = frappe.db.count("Site", {"bench": bench})
		for i in range(n):
			site = create_test_site(f"site-{count + i}-{self.bench_count}", bench=bench)
			create_test_subscription(site.name, plan.name, site.team)
		return frappe.get_doc("Bench", bench)

	def test_work_load_is_calculated_correctly(self):
		bench = self._create_bench_with_n_sites_with_cpu_time(3, 5)
		self.assertEqual(bench.work_load, 15)
		bench = self._create_bench_with_n_sites_with_cpu_time(3, 10, bench.name)
		self.assertEqual(bench.work_load, 45)

	def test_work_load_gives_reasonable_numbers(self):
		bench1 = self._create_bench_with_n_sites_with_cpu_time(3, 5)
		bench2 = self._create_bench_with_n_sites_with_cpu_time(3, 10)
		bench3 = self._create_bench_with_n_sites_with_cpu_time(6, 5)
		bench4 = self._create_bench_with_n_sites_with_cpu_time(6, 10)
		self.assertGreater(bench2.work_load, bench1.work_load)
		self.assertGreater(bench4.work_load, bench3.work_load)
		self.assertGreater(bench4.work_load, bench2.work_load)
