# Copyright (c) 2022, Frappe and Contributors
# See license.txt
from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.site_plan.test_site_plan import create_test_plan

if TYPE_CHECKING:
	from press.press.doctype.app.app import App
	from press.press.doctype.release_group.release_group import ReleaseGroup


def create_test_saas_settings(group: ReleaseGroup | None = None, apps: list[App] | None = None):
	"""Create a test saas_settings"""
	if not apps:
		apps = [create_test_app()]
	app = apps[-1]
	if not group:
		group = create_test_release_group(apps)
	plan = create_test_plan("Site")
	return frappe.get_doc(
		{
			"doctype": "Saas Settings",
			"app": app.name,
			"apps": [{"app": app.name}],
			"domain": "fc.dev",
			"cluster": "Default",
			"group": group.name,
			"plan": plan.name,
			"site_plan": plan.name,
		}
	).insert(ignore_permissions=True, ignore_links=True)


class TestSaasSettings(FrappeTestCase):
	pass
