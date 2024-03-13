# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import frappe
import unittest
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.marketplace_app.test_marketplace_app import (
	create_test_marketplace_app,
)


def create_test_marketplace_app_plan(app: str = "frappe"):
	"""Create a test marketplace_app_plan"""
	if not frappe.db.exists("Marketplace App", app):
		create_test_app(name=app)
		create_test_marketplace_app(app)

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


class TestMarketplaceAppPlan(unittest.TestCase):
	pass
