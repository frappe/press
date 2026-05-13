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
	pass
