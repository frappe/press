# Copyright (c) 2023, Frappe and Contributors
# See license.txt

import typing

import frappe
from frappe.tests.utils import FrappeTestCase

if typing.TYPE_CHECKING:
	from press.press.doctype.app.app import App

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.root_domain.test_root_domain import create_test_root_domain
from press.press.doctype.site_plan.test_site_plan import create_test_plan


def create_test_product_trial(
	app: "App",
):
	frappe_app = create_test_app()
	trial_plan = create_test_plan("Site", is_trial_plan=True)
	domain = create_test_root_domain("local.fc.frappe.dev")
	release_group = create_test_release_group([frappe_app, app])
	product_trial = frappe.get_doc(
		{
			"doctype": "Product Trial",
			"name": app.name,
			"title": app.title,
			"apps": [
				{
					"app": "frappe",
				},
				{
					"app": app.name,
				},
			],
			"trial_plan": trial_plan.name,
			"domain": domain.name,
			"release_group": release_group.name,
			"email_subject": "Test Subject",
			"email_header_content": "Test Header",
		}
	).insert(ignore_if_duplicate=True)
	product_trial.reload()
	return product_trial


class TestProductTrial(FrappeTestCase):
	def setUp(self):
		from press.press.doctype.cluster.test_cluster import create_test_cluster

		create_test_cluster("Mumbai", public=True)
		create_test_cluster("Bahrain", region="me-south-1", public=True)
		self.product = create_test_product_trial(create_test_app("signup_domain_app"))
		create_test_root_domain("m.local.fc.frappe.dev", default_cluster="Mumbai")
		create_test_root_domain("b.local.fc.frappe.dev", default_cluster="Bahrain")

	def tearDown(self):
		frappe.db.rollback()

	def test_signup_domain_uses_subdomain_of_resolved_cluster(self):
		self.assertEqual(self.product.get_signup_domain("Mumbai"), "m.local.fc.frappe.dev")

	def test_signup_domain_falls_back_to_nearest_subdomain_when_cluster_has_none(self):
		# UAE has no subdomain; Bahrain is the nearest cluster that does
		self.assertEqual(self.product.get_signup_domain("UAE"), "b.local.fc.frappe.dev")

	def test_signup_domain_returns_apex_only_when_no_subdomains_exist(self):
		self.product.domain = create_test_root_domain("solo.fc.frappe.dev").name
		self.assertEqual(self.product.get_signup_domain("Mumbai"), "solo.fc.frappe.dev")
