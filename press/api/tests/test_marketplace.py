# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt


import unittest
from unittest.mock import Mock, patch

import frappe
from press.api.marketplace import (
	add_app,
	add_reply,
	add_version,
	become_publisher,
	change_app_plan,
	communication,
	create_app_plan,
	create_approval_request,
	developer_toggle_allowed,
	get_apps,
	get_app,
	get_latest_approval_request,
	get_marketplace_subscriptions_for_site,
	get_publisher_profile_info,
	get_subscriptions_list,
	get_apps_with_plans,
	new_app,
	options_for_quick_install,
	change_branch,
	remove_version,
	reset_features_for_plan,
	review_stages,
	start_review,
	subscriptions,
	update_app_description,
	update_app_links,
	update_app_plan,
	update_app_summary,
	update_app_title,
	releases,
	update_publisher_profile,
)
from press.marketplace.doctype.marketplace_app_plan.test_marketplace_app_plan import (
	create_test_marketplace_app_plan,
)
from press.marketplace.doctype.marketplace_app_subscription.test_marketplace_app_subscription import (
	create_test_marketplace_app_subscription,
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
		self.app_source = create_test_app_source(version=self.version, app=self.app)
		self.app_release = create_test_app_release(self.app_source)
		self.marketplace_app = create_test_marketplace_app(
			app=self.app.name,
			team=self.team.name,
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
		app = create_test_app("test_app", "Test App")
		app_source = create_test_app_source(version=self.version, app=app)
		marketplace_app = add_app(source=app_source.name, app=app.name)
		self.assertIsNotNone(frappe.db.exists("Marketplace App", marketplace_app))

	def test_add_app_already_added(self):
		app = create_test_app("test_app3", "Test App 3")
		app_source = create_test_app_source(version=self.version, app=app)
		create_test_marketplace_app(
			app=app.name,
			team=self.team.name,
			sources=[{"version": self.version, "source": app_source.name}],
		)
		new_source = create_test_app_source(version="Nightly", app=app)
		frappe.set_user(self.team.user)
		marketplace_app = add_app(source=new_source.name, app=app.name)
		self.assertIsNotNone(frappe.db.exists("Marketplace App", marketplace_app))

	def test_get_marketplace_subscriptions_for_site(self):
		site = create_test_site(subdomain="test1", team=self.team.name)
		plan = create_test_marketplace_app_plan(self.marketplace_app.name)
		create_test_marketplace_app_subscription(
			site=site.name, app=self.app.name, team=self.team.name, plan=plan.name
		)

		self.assertIsNotNone(get_marketplace_subscriptions_for_site(site.name))

	def test_change_app_plan(self):
		subscription = create_test_marketplace_app_subscription()
		new_plan = create_test_marketplace_app_plan()
		change_app_plan(subscription.name, new_plan.name)

		self.assertEqual(
			new_plan.name,
			frappe.db.get_value(
				"Marketplace App Subscription", subscription.name, "marketplace_app_plan"
			),
		)
		self.assertEqual(
			new_plan.plan,
			frappe.db.get_value("Marketplace App Subscription", subscription.name, "plan"),
		)

	def test_get_subscription_list(self):
		self.assertEqual([], get_subscriptions_list("frappe"))
		create_test_marketplace_app_subscription(app="frappe")
		self.assertIsNotNone(get_subscriptions_list("frappe"))

	def test_update_app_plan(self):
		m_plan = create_test_marketplace_app_plan()
		plan = frappe.get_doc("Plan", m_plan.plan)

		updated_plan_data = {
			"price_inr": plan.price_inr + 100,
			"price_usd": plan.price_usd + 1,
			"plan_title": plan.plan_title + " updated",
			"features": ["feature 3", "feature 4"],
		}
		update_app_plan(m_plan.name, updated_plan_data)
		m_plan.reload()
		plan.reload()

		self.assertEqual(plan.price_inr, updated_plan_data["price_inr"])
		self.assertEqual(plan.price_usd, updated_plan_data["price_usd"])
		self.assertEqual(plan.plan_title, updated_plan_data["plan_title"])
		self.assertEqual(m_plan.features[0].description, updated_plan_data["features"][0])
		self.assertEqual(m_plan.features[1].description, updated_plan_data["features"][1])

	def test_become_publisher(self):
		frappe.set_user(self.team.user)
		become_publisher()
		self.team.reload()
		self.assertTrue(self.team.is_developer)

	def test_developer_toggle_allowed(self):
		is_developer = self.team.is_developer

		allowed = developer_toggle_allowed()
		self.assertEqual(not allowed, is_developer == 0)

	def test_get_apps(self):
		frappe.set_user(self.team.user)
		self.marketplace_app.db_set("team", self.team.name)
		apps = get_apps()
		self.assertEqual(apps[0].name, self.marketplace_app.name)

	def test_get_app(self):
		app = get_app("erpnext")
		self.assertEqual(app.name, "erpnext")

	def test_update_app_title(self):
		frappe.set_user(self.team.user)
		update_app_title(self.marketplace_app.name, "New Title")
		self.marketplace_app.reload()
		self.assertEqual(self.marketplace_app.title, "New Title")

	def test_update_app_links(self):
		frappe.set_user(self.team.user)
		update_app_links(
			self.marketplace_app.name,
			{
				"website": "https://github.com",
				"support": "https://github.com",
				"documentation": "https://github.com",
				"privacy_policy": "https://github.com",
				"terms_of_service": "https://github.com",
			},
		)
		self.marketplace_app.reload()
		self.assertEqual(self.marketplace_app.website, "https://github.com")
		self.assertEqual(self.marketplace_app.support, "https://github.com")

	def test_update_app_summary(self):
		frappe.set_user(self.team.user)
		summary = frappe.mock("paragraph")
		update_app_summary(self.marketplace_app.name, summary)
		self.marketplace_app.reload()
		self.assertEqual(self.marketplace_app.description, summary)

	def test_update_app_description(self):
		frappe.set_user(self.team.user)
		desc = frappe.mock("paragraph")
		update_app_description(self.marketplace_app.name, desc)
		self.marketplace_app.reload()
		self.assertEqual(self.marketplace_app.long_description, desc)

	def test_releases(self):
		frappe.set_user(self.team.user)
		r = releases(app=self.marketplace_app.name, source=self.app_source.name)
		self.assertEqual(r[0].name, self.app_release.name)

	def test_app_release_approvals(self):
		frappe.set_user(self.team.user)
		create_approval_request(self.marketplace_app.name, self.app_release.name)
		latest_approval = get_latest_approval_request(self.app_release.name)
		self.assertIsNotNone(latest_approval)

	def test_new_app(self):
		app = {
			"name": "email_delivery_service",
			"title": "Email Delivery Service",
			"version": "Version 14",
			"repository_url": "https://github.com/frappe/email_delivery_service",
			"branch": "develop",
			"github_installation_id": "",
		}
		name = new_app(app)
		self.assertEqual(name, app["name"])

	def test_get_apps_with_plans(self):
		frappe_app = create_test_app()
		group2 = create_test_release_group(
			[frappe_app, self.app], frappe_version=self.version
		)
		create_test_marketplace_app(
			app=frappe_app.name,
			sources=[{"version": self.version, "source": group2.apps[0].source}],
		)
		create_app_plan(frappe_app.name, self.plan_data)
		apps = get_apps_with_plans(["frappe", "erpnext"], group2.name)
		self.assertEqual(apps[0].name, frappe_app.name)

	def test_publisher_profile(self):
		frappe.set_user(self.team.user)
		publisher_info = {
			"display_name": "Test Publisher",
			"contact_email": self.team.user,
			"website": "https://github.com",
		}
		update_publisher_profile(publisher_info)
		updated_name = "Test Publisher 2"
		update_publisher_profile({"display_name": updated_name})
		info = get_publisher_profile_info()
		self.assertEqual(info["profile_info"].contact_email, self.team.user)
		self.assertEqual(info["profile_info"].display_name, updated_name)

	def test_get_subscription(self):
		site = create_test_site(subdomain="test1", team=self.team.name)
		plan = create_test_marketplace_app_plan(self.marketplace_app.name)
		create_test_marketplace_app_subscription(
			site=site.name, app=self.app.name, team=self.team.name, plan=plan.name
		)
		frappe.set_user(self.team.user)
		self.assertIsNotNone(subscriptions())

	def test_change_branch(self):
		old_branch = self.app_source.branch
		change_branch(
			self.marketplace_app.name, self.app_source.name, "Version 14", "develop"
		)
		self.app_source.reload()
		self.assertNotEqual(old_branch, self.app_source.branch)

	def test_add_version(self):
		old_versions = len(self.marketplace_app.sources)
		add_version(self.marketplace_app.name, "develop", "Nightly")
		self.marketplace_app.reload()
		self.assertEqual(old_versions + 1, len(self.marketplace_app.sources))

	def test_remove_version(self):
		old_versions = len(self.marketplace_app.sources)
		add_version(self.marketplace_app.name, "develop", "Nightly")
		remove_version(self.marketplace_app.name, "Nightly")
		self.marketplace_app.reload()
		self.assertEqual(old_versions, len(self.marketplace_app.sources))

	def test_app_review_steps(self):
		frappe.set_user(self.team.user)

		# description, links and publish
		old_stages = review_stages(self.marketplace_app.name)
		self.assertEqual(False, old_stages["links"])
		self.assertEqual(False, old_stages["description"])
		self.assertEqual(False, old_stages["publish"])
		self.marketplace_app.description = "Test"
		self.marketplace_app.long_description = "Test Text"
		self.marketplace_app.website = frappe.mock("url")
		self.marketplace_app.support = frappe.mock("url")
		self.marketplace_app.documentation = frappe.mock("url")
		self.marketplace_app.save(ignore_permissions=True)
		self.marketplace_app.reload()
		new_stages = review_stages(self.marketplace_app.name)
		self.assertEqual(True, new_stages["description"])
		self.assertEqual(True, new_stages["links"])

		# reply
		add_reply(self.marketplace_app.name, "Test")
		comm = communication(self.marketplace_app.name)
		self.assertIsNotNone(comm)

		# ready for review
		self.assertNotEqual(self.marketplace_app.status, "In Review")
		start_review(self.marketplace_app.name)
		self.marketplace_app.reload()
		self.assertEqual(self.marketplace_app.status, "In Review")
