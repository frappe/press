# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import frappe
import unittest

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.marketplace_app.test_marketplace_app import (
	create_test_marketplace_app,
)
from press.marketplace.doctype.marketplace_app_plan.test_marketplace_app_plan import (
	create_test_marketplace_app_plan,
)
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.test_team import create_test_team


def create_test_marketplace_app_subscription(
	site: str = None, app: str = None, plan: str = None, team: str = None
):
	app = (
		app if app and frappe.db.exists("Marketplace App", app) else create_test_app().name
	)
	create_test_marketplace_app(app)
	plan = plan if plan else create_test_marketplace_app_plan().name
	team = team if team else create_test_team().name
	site = site if site else create_test_site(team=team).name
	print(frappe.db.exists("Marketplace App Plan", plan))
	subscription = frappe.get_doc(
		{
			"doctype": "Subscription",
			"document_type": "Marketplace App",
			"document_name": app,
			"plan_type": "Marketplace App Plan",
			"plan": plan,
			"site": site,
			"team": team,
		}
	).insert(ignore_if_duplicate=True)
	return subscription


class TestMarketplaceAppSubscription(unittest.TestCase):
	pass
