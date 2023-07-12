# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import frappe
import unittest

from press.press.doctype.plan.test_plan import create_test_plan


def create_test_marketplace_app_plan(app: str = "frappe"):
	"""Create a test marketplace_app_plan"""
	return frappe.get_doc(
		{
			"doctype": "Marketplace App Plan",
			"plan": create_test_plan("Marketplace App").name,
			"app": app,
			"versions": [{"version": "Version 14"}],
			"features": [{"description": "Feature 1"}],
			"enabled": 1,
		}
	).insert(ignore_permissions=True)


class TestMarketplaceAppPlan(unittest.TestCase):
	pass
