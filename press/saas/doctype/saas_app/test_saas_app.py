# Copyright (c) 2022, Frappe and Contributors
# See license.txt

import frappe

from frappe.tests.utils import FrappeTestCase


def create_test_saas_app(app: str):
	return frappe.get_doc({"doctype": "Saas App", "app": app}).insert(
		ignore_if_duplicate=True
	)


class TestSaasApp(FrappeTestCase):
	pass
