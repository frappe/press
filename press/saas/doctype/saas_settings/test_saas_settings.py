# Copyright (c) 2022, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.site_plan.test_site_plan import create_test_plan
from press.press.doctype.release_group.release_group import ReleaseGroup
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)


def create_test_saas_settings(group: ReleaseGroup = None):
	"""Create a test saas_settings"""
	if not group:
		group = (create_test_release_group([create_test_app()]),)
	return frappe.get_doc(
		{
			"doctype": "Saas Settings",
			"app": "frappe",
			"apps": [{"app": "frappe"}],
			"domain": "fc.dev",
			"cluster": "Default",
			"group": group.name,
			"plan": create_test_plan("Site").name,
			"site_plan": create_test_plan("Site").name,
		}
	).insert(ignore_permissions=True)


class TestSaasSettings(FrappeTestCase):
	pass
