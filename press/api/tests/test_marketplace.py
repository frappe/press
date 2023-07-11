# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt


import unittest
from unittest.mock import Mock, patch

import frappe
from press.api.marketplace import create_app_plan
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.marketplace_app.test_marketplace_app import (
	create_test_marketplace_app,
)
from press.press.doctype.team.test_team import create_test_press_admin_team


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestAPIMarketplace(unittest.TestCase):
	def setUp(self):
		app = create_test_app()
		team = create_test_press_admin_team()
		self.marketplace_app = create_test_marketplace_app(app=app.name, team=team.name)

	def tearDown(self):
		frappe.db.rollback()

	def test_create_marketplace_app_plan(self):
		plan_data = {
			"price_inr": 820,
			"price_usd": 10,
			"plan_title": "Test Marketplace Plan",
			"features": ["feature 1", "feature 2"]
		}
		before_count = frappe.db.count("Marketplace App Plan")
		create_app_plan(self.marketplace_app.name, plan_data)
		after_count = frappe.db.count("Marketplace App Plan")
		self.assertEqual(before_count + 1, after_count)
