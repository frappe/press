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
	def tearDown(self):
		frappe.db.rollback()

	def _create_bench_with_n_sites_with_x_plan(
		self, n: int, x: float, bench: str = None
	) -> Bench:
		plan = create_test_plan("Site", price_usd=x)
		if not bench:
			site = create_test_site("testsite-0", bench=bench)
			create_test_subscription(site.name, plan.name, site.team)
			bench = site.bench
			n -= 1
		count = frappe.db.count("Site", {"bench": bench})
		for i in range(n):
			site = create_test_site(f"testsite-{count + i}", bench=bench)
			create_test_subscription(site.name, plan.name, site.team)
		return frappe.get_doc("Bench", bench)

	def test_work_load_is_calculated_correctly(self):
		bench = self._create_bench_with_n_sites_with_x_plan(3, 5)
		self.assertEqual(bench.work_load, 1.5)
		bench = self._create_bench_with_n_sites_with_x_plan(3, 10, bench.name)
		self.assertEqual(bench.work_load, 4.5)

	def test_work_load_gives_reasonable_numbers(self):
		bench1 = self._create_bench_with_n_sites_with_x_plan(3, 5)
		bench2 = self._create_bench_with_n_sites_with_x_plan(3, 10)
		bench3 = self._create_bench_with_n_sites_with_x_plan(6, 5)
		bench4 = self._create_bench_with_n_sites_with_x_plan(6, 10)
		self.assertGreater(bench2.work_load, bench1.work_load)
		self.assertGreater(bench4.work_load, bench3.work_load)
		self.assertGreater(bench4.work_load, bench2.work_load)
