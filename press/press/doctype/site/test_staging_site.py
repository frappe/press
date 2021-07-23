# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals
from press.press.doctype.site.test_site import create_test_bench

import unittest
from unittest.mock import Mock, patch

import frappe
from .staging_site import StagingSite

from press.press.doctype.agent_job.agent_job import AgentJob


@patch.object(AgentJob, "after_insert", new=Mock())
class TestStagingSite(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_create_staging_site(self):
		bench = create_test_bench()
		site = StagingSite(bench.name).insert()
		self.assertTrue(site.staging)
