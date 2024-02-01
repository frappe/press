# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import frappe
import unittest
from press.press.doctype.app.test_app import create_test_app

from press.press.doctype.plan.test_plan import create_test_plan


def create_test_marketplace_app_plan(app: str = "frappe"):
	"""Create a test marketplace_app_plan"""
	if not frappe.db.exists("Marketplace App", app):
		create_test_app(name=app)

	return create_test_plan("Marketplace App", app)


class TestMarketplaceAppPlan(unittest.TestCase):
	pass
