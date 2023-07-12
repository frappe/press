# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt


import unittest
from unittest.mock import Mock, patch

import frappe
from press.api.marketplace import (
	add_app,
	create_app_plan,
	options_for_marketplace_app,
	options_for_quick_install,
	reset_features_for_plan,
)
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.marketplace_app.test_marketplace_app import (
	create_test_marketplace_app,
)
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.site.test_site import create_test_bench, create_test_site


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestAPIMarketplace(unittest.TestCase):
	def setUp(self):
		self.app = create_test_app("erpnext", "ERPNext")
		self.team = create_test_press_admin_team()
		self.version = "Version 14"
		self.marketplace_app = create_test_marketplace_app(
			app=self.app.name, team=self.team.name
		)
		self.app_source = create_test_app_source(version=self.version, app=self.app)
		self.app_release = create_test_app_release(self.app_source)
		create_test_marketplace_app(
			app=self.app.name,
			sources=[{"version": self.version, "source": self.app_source.name}],
		)
		self.plan_data = {
			"price_inr": 820,
			"price_usd": 10,
			"plan_title": "Test Marketplace Plan",
			"features": ["feature 1", "feature 2"],
		}

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_create_marketplace_app_plan(self):
		frappe.set_user(self.team.user)
		before_count = frappe.db.count("Marketplace App Plan")
		create_app_plan(self.marketplace_app.name, self.plan_data)
		after_count = frappe.db.count("Marketplace App Plan")
		self.assertEqual(before_count + 1, after_count)

	def test_reset_features_for_plan(self):
		plan_doc = create_app_plan(self.marketplace_app.name, self.plan_data)
		new_features = ["feature 3", "feature 4"]
		reset_features_for_plan(plan_doc, new_features)

		self.assertEqual([feature.description for feature in plan_doc.features], new_features)

	def test_options_for_quick_install(self):
		frappe_app = create_test_app()

		frappe_source = create_test_app_source(version=self.version, app=frappe_app)
		frappe_release = create_test_app_release(frappe_source)
		create_test_marketplace_app(
			app=frappe_app.name,
			sources=[{"version": self.version, "source": frappe_source.name}],
		)

		group1 = create_test_release_group([frappe_app], frappe_version=self.version)
		group2 = create_test_release_group([frappe_app, self.app])
		group1.db_set("team", self.team.name)
		group2.db_set("team", self.team.name)
		bench1 = create_test_bench(
			group=group1,
			apps=[
				{
					"app": frappe_app.name,
					"hash": frappe_release.hash,
					"source": frappe_source.name,
					"release": frappe_release.name,
				}
			],
		)
		bench2 = create_test_bench(
			group=group2,
			apps=[
				{
					"app": frappe_app.name,
					"hash": frappe_release.hash,
					"source": frappe_source.name,
					"release": frappe_release.name,
				},
				{
					"app": self.app.name,
					"hash": self.app_release.hash,
					"source": self.app_source.name,
					"release": self.app_release.name,
				},
			],
		)

		create_test_site(subdomain="test1", bench=bench1.name, team=self.team.name)
		create_test_site(subdomain="test2", bench=bench2.name, team=self.team.name)

		frappe.set_user(self.team.user)
		options = options_for_quick_install(self.app.name)

		self.assertEqual(options["release_groups"][0]["name"], group1.name)

	def test_add_app(self):
		app = create_test_app('test_app', 'Test App')
		app_source = create_test_app_source(version=self.version, app=app)

		marketplace_app = add_app(source=app_source.name, app=app.name)

		self.assertIsNotNone(frappe.db.exists("Marketplace App", marketplace_app))
