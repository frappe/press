# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.ui_test_helpers import create_test_user
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.marketplace_app.utils import (
	get_rating_percentage_distribution,
	number_k_format,
)
from press.press.doctype.team.test_team import create_test_team


def create_test_marketplace_app(app: str, team: str | None = None, sources: list[dict] | None = None):
	marketplace_app = frappe.get_doc(
		{
			"doctype": "Marketplace App",
			"app": app,
			"description": "Test App",
			"team": team,
			"sources": sources,
		}
	).insert(ignore_if_duplicate=True)
	marketplace_app.reload()
	return marketplace_app


def create_test_marketplace_app_plan(app: str):
	return frappe.get_doc(
		{
			"doctype": "Marketplace App Plan",
			"title": "Test Plan",
			"price_inr": 1000,
			"price_usd": 12,
			"app": app,
			"versions": [{"version": "Version 14"}],
			"features": [{"description": "Feature 1"}],
			"enabled": 1,
		}
	).insert(ignore_permissions=True)


def create_team_with_press_user():
	email = frappe.mock("email")
	create_test_user(email)
	user = frappe.get_doc("User", {"email": email})
	user.remove_roles(*frappe.get_all("Role", pluck="name"))
	user.add_roles("Press User")
	return create_test_team(email)


class TestMarketplaceApp(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	@patch.object(AppSource, "create_release", new=Mock())
	@patch.object(AppSource, "validate_dependent_apps", new=Mock())
	@patch(
		"press.press.doctype.marketplace_app.marketplace_app.validate_frappe_version_for_branch", new=Mock()
	)
	def test_add_version_uses_app_source_when_sources_child_table_is_empty(self):
		"""Regression: a draft app whose versions were all removed has an empty `sources` child table
		but still has App Source records. add_version used to crash with IndexError on self.sources[0];
		it should now find the source by repository and add the version."""
		team = create_test_team()
		app = create_test_app(f"mp_test_{frappe.generate_hash(length=8).lower()}", "Empty Sources App")
		create_test_app_source(
			"Version 14",
			app,
			repository_url="https://github.com/frappe/erpnext",
			branch="master",
			team=team.name,
		)
		marketplace_app = create_test_marketplace_app(app.name, team=team.name)
		self.assertEqual(len(marketplace_app.sources), 0)

		marketplace_app.add_version(
			version="Version 15", repo_owner="frappe", repo_name="erpnext", branch="version-15"
		)

		marketplace_app.reload()
		self.assertIn("Version 15", [s.version for s in marketplace_app.sources])

	def test_add_version_throws_readable_error_when_no_source_exists_for_repo(self):
		"""add_version must throw a readable error (not IndexError) when neither an existing source
		nor any App Source for the selected repository exists."""
		team = create_test_team()
		app = create_test_app(f"mp_test_{frappe.generate_hash(length=8).lower()}", "No Source App")
		marketplace_app = create_test_marketplace_app(app.name, team=team.name)

		with self.assertRaises(frappe.ValidationError) as context:
			marketplace_app.add_version(
				version="Version 15", repo_owner="frappe", repo_name="erpnext", branch="version-15"
			)
		self.assertIn("No app source found for frappe/erpnext", str(context.exception))

	def create_marketplace_app_for_team(self, team):
		app_name = f"perm_app_{frappe.generate_hash(length=8).lower()}"
		create_test_app(app_name, app_name.replace("_", " ").title())
		return create_test_marketplace_app(app_name, team=team.name)

	def test_number_format_util(self):
		test_cases_map = {
			0: "0",
			10: "10",
			999: "999",
			1000: "1k",
			8100: "8.1k",
			8900: "8.9k",
			8990: "9k",
			7102: "7.1k",
			10031: "10k",
			708609: "708.6k",
		}

		for input_value, expected_output in test_cases_map.items():
			self.assertEqual(number_k_format(input_value), expected_output)

	def test_rating_percentage_distribution(self):
		test_table = [
			{
				"test_reviews": [{"rating": 4}, {"rating": 5}, {"rating": 1}],
				"expected_result": {1: 33, 2: 0, 3: 0, 4: 33, 5: 33},
			},
			{
				"test_reviews": [{"rating": 5}, {"rating": 5}, {"rating": 5}],
				"expected_result": {1: 0, 2: 0, 3: 0, 4: 0, 5: 100},
			},
			{
				"test_reviews": [],
				"expected_result": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
			},
		]

		for test_case in test_table:
			test_reviews = test_case["test_reviews"]
			test_reviews = [frappe._dict(r) for r in test_reviews]
			got = get_rating_percentage_distribution(test_reviews)

			self.assertDictEqual(got, test_case["expected_result"])

	def test_press_user_can_manage_only_own_team_marketplace_apps(self):
		own_team = create_team_with_press_user()
		other_team = create_team_with_press_user()
		app_name = f"perm_app_{frappe.generate_hash(length=8).lower()}"
		create_test_app(app_name, "Permission Test App")
		other_app = self.create_marketplace_app_for_team(other_team)

		with self.set_user(own_team.user):
			app = frappe.get_doc(
				{
					"doctype": "Marketplace App",
					"app": app_name,
					"title": "Permission Test App",
					"description": "Test App",
					"team": own_team.name,
				}
			).insert()

			app.check_permission("read")
			app.description = "Updated Test App"
			app.save()

			self.assertEqual(
				frappe.db.get_value("Marketplace App", app.name, "description"), "Updated Test App"
			)
			self.assertIn(app.name, frappe.get_list("Marketplace App", pluck="name"))
			self.assertNotIn(other_app.name, frappe.get_list("Marketplace App", pluck="name"))

			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Marketplace App", other_app.name).check_permission("read")

			other_app.description = "Cross-team update"
			with self.assertRaises(frappe.PermissionError):
				other_app.save()

			with self.assertRaises(frappe.PermissionError):
				frappe.delete_doc("Marketplace App", other_app.name)

	def test_press_user_can_manage_only_own_team_marketplace_app_plans(self):
		own_team = create_team_with_press_user()
		other_team = create_team_with_press_user()
		app = self.create_marketplace_app_for_team(own_team)
		other_app = self.create_marketplace_app_for_team(other_team)
		other_plan = create_test_marketplace_app_plan(other_app.name)

		with self.set_user(own_team.user):
			plan = frappe.get_doc(
				{
					"doctype": "Marketplace App Plan",
					"title": "Test Plan",
					"price_inr": 1000,
					"price_usd": 12,
					"app": app.name,
					"versions": [{"version": "Version 14"}],
					"features": [{"description": "Feature 1"}],
					"enabled": 1,
				}
			).insert()

			plan.check_permission("read")
			plan.title = "Updated Test Plan"
			plan.save()

			self.assertEqual(
				frappe.db.get_value("Marketplace App Plan", plan.name, "title"), "Updated Test Plan"
			)
			self.assertIn(plan.name, frappe.get_list("Marketplace App Plan", pluck="name"))
			self.assertNotIn(other_plan.name, frappe.get_list("Marketplace App Plan", pluck="name"))

			with self.assertRaises(frappe.PermissionError):
				frappe.get_doc("Marketplace App Plan", other_plan.name).check_permission("read")

			other_plan = frappe.get_doc("Marketplace App Plan", other_plan.name)
			other_plan.title = "Cross-team update"
			with self.assertRaises(frappe.PermissionError):
				other_plan.save()

			with self.assertRaises(frappe.PermissionError):
				frappe.delete_doc("Marketplace App Plan", other_plan.name)
